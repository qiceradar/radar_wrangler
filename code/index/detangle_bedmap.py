#! /usr/bin/env python3
"""
The goal of this script is to de-duplicate the BEDMAP1 dataset
so that layer in the index only corresponds to points where I
don't know which institution collected them.

This automated approach will miss some, because the ice thickness
data released by institutions is not identital to that included in
BEDMAP1, and there are often lines in BEDMAP1 that clearly correspond
to an existing survey, but aren't in that dataset. Manually associating
those points would take more work than it is worth.

The automated approach first tries to find the closest survey point
for each bedmap point, and if they are close enough, they are associated.
Associated points are grouped into "segments" of contiguous points.

However, the datasets aren't consistent, and there are often points
in bedmap that don't perfectly match the released datasets that supposedly
were the contributions to bedmap1.

The bedmap1 points aren't ordered neatly, but chunks of them seem to be,
so we look at points that are in between the segments, if the gap is small
enough. For these "gap points" in the bedmap dataset, we associate them
to the survey if their distance to a survey linesegment is small enough.
This definitely misses points that are parts of the surveys in any place
where the released points are a subset of the bedmap one, but associating
those surveys would involve too much manual intervention.

There are 3 parameters controlling the matching behavior.

1) max_dist -- maximimum distance from bedmap point to closest point
       in the survey for that bedmap point to be associated automatically.
       This needs to be relatively small to avoid false-positive matches
       where survey lines cross each other or are parallel.
       For many surveys, the points are identical.

2) max_gap_length -- how many bedmap indices can fall between two
       definitely-associated segments and we'll still try to
       match them.

3) max_crosstrack_dist -- how far from the campaign's line segment a
       bedmap point can be and still be associated.
       For some surveys, no bound is needed, but for the BAS RESPAC data,
       this is important since there are random single-point outliers in
       the bedmap index ranges corresponding to RESPAC.
"""

import matplotlib.pyplot as plt

import csv
import json
import numpy as np
import os
import pathlib
import pandas as pd
import pickle
import pyproj
import scipy.spatial  # Used for KDTree
from shapely.geometry import LineString, Point  # Used for projecting BM1 points onto survey segments
import time

duplicate_bm2_campaigns = [
    "AWI_1994_DML1_AIR_BM2", "AWI_1995_DML2_AIR_BM2", "AWI_1996_DML3_AIR_BM2",
    "AWI_1997_DML4_AIR_BM2", "AWI_1998_DML5_AIR_BM2",
    "BAS_1994_Evans_AIR_BM2", "BAS_1998_Dufek_AIR_BM2",
    "NIPR_1992_JARE33_GRN_BM3", "NIPR_1996_JARE37_GRN_BM3",
    "UTIG_1991_CASERTZ_AIR_BM2",
]

def load_bedmap_xy(filepath) -> np.ndarray:
    data = pd.read_csv(filepath, skiprows=18)
    lon_index = [col for col in data.columns if 'longitude' in col][0]
    lat_index = [col for col in data.columns if 'latitude' in col][0]
    lon = data[lon_index]
    lat = data[lat_index]
    ps71=pyproj.Proj('epsg:3031')
    xx, yy = ps71.transform(lon, lat)
    coords = np.array([xx, yy]).transpose()
    return coords

def load_respac_surveys(filepath):
    """
    The raw data was provided in a format I haven't seen before.
    There are labeled columns, with different campaigns separated by a single line saying "Line ####"
    """
    seasons = {}
    season = None
    curr_line = None
    ps71 = pyproj.Proj('epsg:3031')
    with open(filepath, "r") as fp:
        for line in fp:
            if line.startswith('/'):
                continue
            if "Line" in line:
                season = line.split()[1]
                season_name = "BAS_RESPAC_{}".format(season)
                if curr_line is not None:
                    lon, lat = zip(*curr_line)
                    xx, yy = ps71.transform(lon, lat)
                    seasons[season_name] = np.array([xx, yy]).transpose()
                curr_line = []
            else:
                tokens = line.split()
                _, _, lon, lat, _, _, _, _, _, _ = tokens
                try:
                    curr_line.append((float(lon), float(lat)))
                except Exception as ex:
                    # Some records don't have position data; just skip them.
                    continue
    return seasons

def load_spri_xy(filepath):
    # Without specifying the encoding, most of the files have \ufeff in the first fieldname.
    with open(filepath, encoding='utf-8-sig') as csvfile:
        csv_reader = csv.DictReader(csvfile)
        coords = [map(float, (elem['LAT'], elem['LON'])) for elem in csv_reader
                  if len(elem['LAT']) > 0]  # Some of the files end with lines of the form ",,,,"

    lat, lon = zip(*coords)
    ps71 = pyproj.Proj("epsg:3031")
    xx, yy = ps71.transform(lon, lat)
    return np.array([xx, yy]).transpose()


def load_data(data_dir):
    bm1_path = os.path.join(data_dir,
                            "ANTARCTIC/BEDMAP/BEDMAP1/BEDMAP1_1966-2000_AIR_BM1.csv")
    bm1 = load_bedmap_xy(bm1_path)

    campaign_points = {}
    # Start with campaigns from Bedmap2/3
    for campaign in duplicate_bm2_campaigns:
        campaign_path = os.path.join(data_dir, "ANTARCTIC/BEDMAP/BEDMAP2/{}.csv".format(campaign))
        if not pathlib.Path(campaign_path).exists():
            campaign_path = os.path.join(data_dir, "ANTARCTIC/BEDMAP/BEDMAP3/{}.csv".format(campaign))
        campaign_points[campaign] = load_bedmap_xy(campaign_path)

    # BAS released their data from 69-88 in one big file
    respac_filepath = os.path.join(data_dir, "ANTARCTIC/BAS/BAS_RESPAC_Radar.xyz")
    respac_campaigns = load_respac_surveys(respac_filepath)
    campaign_points.update(respac_campaigns)

    # Stanford has released some of the SPRI paths as individual CSVs
    spri_path = os.path.join(data_dir, "ANTARCTIC/STANFORD/radarfilmstudio/antarctica_original_positioning")
    spri_filepaths = [os.path.join(spri_path, ff) for ff in os.listdir(spri_path)
                      if ff.endswith("csv") and not ff.startswith('.')]
    all_spri = []
    for filepath in spri_filepaths:
        flight = pathlib.Path(filepath).stem
        spri_flight = load_spri_xy(filepath)
        xx = spri_flight[:,0]
        yy = spri_flight[:,1]
        all_spri.extend(zip(xx, yy))
    all_spri = np.array(all_spri)
    campaign_points["SPRI"] = all_spri

    return bm1, campaign_points


def find_campaign_matches(bm1_points, campaign_points, max_dists):
    selected_idxs = {}
    campaign_from_bedmap = {}

    for campaign, points in campaign_points.items():
        print("Processing {}".format(campaign))
        t0 = time.time()
        campaign_tree = scipy.spatial.KDTree(points)
        t1 = time.time()
        campaign_from_bedmap_dists, campaign_from_bedmap_idxs = campaign_tree.query(bm1_points, k=1)
        t2 = time.time()
        print("Found closest indices. construction dt = {}, query dt = {}".format(t1-t0, t2-t1))

        candidate_bedmap_idxs, = np.where(campaign_from_bedmap_dists < max_dists[campaign])
        selected_idxs[campaign] = candidate_bedmap_idxs
        campaign_from_bedmap[campaign] = {idx: val for idx, val in enumerate(campaign_from_bedmap_idxs)}

        dt = time.time() - t0
        print("... {:0.2f} seconds".format(dt))
    return selected_idxs, campaign_from_bedmap


def find_gaps(segments, max_skip):
    gaps = np.array([])
    for idx in np.arange(len(segments)-1):
        s0,s1 = segments[idx]
        s2,s3 = segments[idx+1]
        assert s1 >= s0  # There are single-length "segments"
        assert s2 > s1
        assert s3 >= s2
        if s2-s1 < max_skip:
            gaps = np.append(gaps, np.arange(s1+1, s2))
    return gaps.astype(int)


def segment_indices(idxs, max_skips, min_length):
    """
    Split a list of indices into sequential chunks.
    * max_skips: maximum gap between indices within the same chunk
    * min_length: minimum points to create a chunk (smaller will be discarded)
    """
    segments = []
    idxs.sort()
    start_idx = idxs[0]
    curr_idx = start_idx
    length = 1
    for idx in idxs:
        if idx - curr_idx > max_skips:
            if length > min_length:
                segments.append((int(start_idx), int(curr_idx)))
            start_idx = idx
            length = 1
        else:
            length += 1
        curr_idx = idx
    segments.append((int(start_idx), int(curr_idx)))
    return segments


def select_bedmap_indices(bm1_points, campaign_points, matched_idxs,
                          campaign_from_bedmap, max_gap_lengths,
                          max_crosstrack_dists):
    selected_idxs = {}
    for campaign, idxs in matched_idxs.items():
        segments = segment_indices(idxs.astype(int), 1, 1)
        gap_idxs = find_gaps(segments, max_gap_lengths[campaign])

        sx = campaign_points[campaign][:,0]
        sy = campaign_points[campaign][:,1]

        good_gap_idxs = []
        good_gap_dists = []
        for gap_idx in gap_idxs:
            c_idx = campaign_from_bedmap[campaign][gap_idx]

            if c_idx+1 < len(sx):
                seg1 = LineString([Point(sx[c_idx], sy[c_idx]), Point(sx[c_idx+1], sy[c_idx+1])])
            else:
                seg1 = None
            if c_idx > 0:
                seg2 = LineString([Point(sx[c_idx], sy[c_idx]), Point(sx[c_idx-1], sy[c_idx-1])])
            else:
                seg2 = None
            bm1_pt = Point(bm1_points[gap_idx,0], bm1_points[gap_idx,1])
            in_bounds = False
            min_dist = np.inf
            for seg in [seg1, seg2]:
                if seg is None:
                    continue
                seg_len = seg.length
                pp = seg.project(bm1_pt)  # Project bedmap point onto line segment
                dd = seg.distance(bm1_pt)
                min_dist = min(dd, min_dist)

                if pp > 0 and pp < seg_len:
                    if dd < max_crosstrack_dists[campaign]:
                        in_bounds = True
            if in_bounds:
                good_gap_idxs.append(gap_idx)
                good_gap_dists.append(min_dist)

        selected_idxs[campaign] = np.append(idxs, good_gap_idxs)
        print("{}: {} / {} gap indices are good.".format(campaign, len(good_gap_idxs), len(gap_idxs)))
    return selected_idxs


def plot_selected_indices(bm1_points, campaign_points, selected_idxs):
    # Find indices that aren't in ANY of our surveys
    bm1_rejected_idxs = None
    for campaign in selected_idxs.keys():
        if bm1_rejected_idxs is None:
            bm1_rejected_idxs = np.arange(0, bm1_points.shape[0])
        bm1_rejected_idxs = np.setdiff1d(bm1_rejected_idxs, selected_idxs[campaign])

    for campaign, idxs in selected_idxs.items():
        print("Plotting {}".format(campaign))
        idxs = idxs.astype(int)

        fig = plt.figure(figsize=(12,5))
        ax1, ax2, ax3 = fig.subplots(1,3)
        for ax in [ax1, ax2, ax3]:
            ax.axis('off')
            ax.axis('equal')

        sx = campaign_points[campaign][:,0]
        sy = campaign_points[campaign][:,1]

        # Plot just the survey
        ax1.plot(sx, sy, '.', color='lightgrey', markersize=0.5)
        ax1.set_title(campaign)

        if len(idxs) == 0:
            continue

        # Plot the selected/rejected bedmap points
        ax2.plot(sx, sy, '.', color='lightgrey', markersize=0.5)
        ax2.plot(bm1_points[idxs,0], bm1_points[idxs,1], 'k.', markersize=0.5)
        ax2.set_title("selected Bedmap1 points")

        # Plot the unmatched bedmap points
        ax3.plot(sx, sy, '.', color='lightgrey', markersize=0.5)
        ax3.plot(bm1_points[bm1_rejected_idxs,0], bm1_points[bm1_rejected_idxs,1], 'r.', markersize=0.5)
        ax3.set_title("Nearby unmatched Bedmap1")

        for ax in [ax2, ax3]:
            ax.set_xlim(ax1.get_xlim())
            ax.set_ylim(ax1.get_ylim())

        fig.savefig("../../figures/detangling_bedmap_{}.png".format(campaign))

def export_segments(selected_idxs, filepath):
    all_idxs = []
    for idxs in selected_idxs.values():
        all_idxs.extend(idxs)
    segments = segment_indices(all_idxs, 1, 1)
    json.dump(segments, open(filepath, 'w'))

def main(data_directory, force):
    bm1_points, campaign_points = load_data(data_directory)
    # Set up configuration. These values were chosen interactively
    # using detangle_bedmap_general.ipynb
    # 1) Distance from bm1 point to campaign point for a match (meters)
    max_dists = {campaign: 1 for campaign in campaign_points.keys()}
    max_dists["BAS_1998_Dufek_AIR_BM2"] = 100
    max_dists["NIPR_1992_JARE33_GRN_BM3"] = 100
    max_dists["NIPR_1996_JARE37_GRN_BM3"] = 100
    for campaign in campaign_points.keys():
        if "SPRI" in campaign:
            max_dists[campaign] = 100


    # 2) How long of a gap in bedmap1 indices should we look at?
    max_gap_lengths = {campaign: 100 for campaign in campaign_points.keys()}
    for campaign in campaign_points.keys():
        if "SPRI" in campaign:
            max_gap_lengths[campaign] = 1000
        if "RESPAC" in campaign:
            # RESPAC doesn't seem to have gaps
            max_gap_lengths[campaign] = 0
    # 3)
    max_crosstrack_dists = {campaign: 100 for campaign in campaign_points.keys()}  # meters
    for campaign in campaign_points.keys():
        if "AWI" in campaign:
            # AWI is pretty continuous, so grab everythign in the gaps.
            max_crosstrack_dists[campaign] = 50000
    max_crosstrack_dists["NIPR_1992_JARE33_GRN_BM3"] = 500

    ########
    # Find / plot /export the matched segments
    ######
    t0 = time.time()
    try:
        if force:
            raise Exception("Recreating match.")
        selected_idxs = pickle.load(open("selected_idxs.pkl", 'rb'))
    except Exception as ex:
        print(ex)
        print("Could not load selected_idxs; generating")
        # Do both steps here because campaign_from_bedmap is large enough
        # that pickling takes longer than recreating it.
        matched_idxs, campaign_from_bedmap = find_campaign_matches(bm1_points, campaign_points, max_dists)
        selected_idxs = select_bedmap_indices(
            bm1_points, campaign_points, matched_idxs,
            campaign_from_bedmap, max_gap_lengths, max_crosstrack_dists)
        pickle.dump(selected_idxs, open("selected_idxs.pkl", 'wb'))
    t1 = time.time()
    print("{:02f} secs to load/create index matches".format(t1-t0))

    segment_filepath = os.path.join(data_directory, "targ", "ANTARCTIC",
                                    "bm1_matched_segments.json")
    export_segments(selected_idxs, segment_filepath)
    t3 = time.time()

    plot_selected_indices(bm1_points, campaign_points, selected_idxs)
    t4 = time.time()
    print("{:02f} secs to plot results".format(t4-t3))



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("data_directory",
                        help="Root directory for all data")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    main(args.data_directory, args.force)