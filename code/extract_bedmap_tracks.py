#! /usr/bin/env python3

import json
import os
import pathlib

import numpy as np
import pandas as pd
import pyproj
from radar_index_utils import count_skip_lines, subsample_tracks


def load_lat_lon(filepath):
    """Open file in the BEDMAP CVS format and extract just lat long from it"""
    skip_rows = count_skip_lines(filepath)
    data = pd.read_csv(filepath, skiprows=skip_rows)

    lon_index = [col for col in data.columns if "longitude" in col][0]
    lat_index = [col for col in data.columns if "latitude" in col][0]
    lon = data[lon_index]
    lat = data[lat_index]
    return np.array(lat), np.array(lon)


def subsample_bedmap(data_dir: pathlib.Path, index_dir: pathlib.Path, force: bool):
    bedmap_dir = data_dir / "ANTARCTIC/BEDMAP"
    output_dir = index_dir / "ANTARCTIC/BEDMAP"

    # Individual indices of points in BEDMAP1 that are associated with
    # another known campaign.
    segment_filepath = index_dir / "ANTARCTIC/bm1_matched_segments.json"

    duplicate_segments = json.load(open(segment_filepath, "r"))
    duplicate_idxs = set()
    for s0, s1 in duplicate_segments:
        duplicate_idxs.update(np.arange(s0, s1 + 1))

    institutions = {}

    for compilation in bedmap_dir.glob("BEDMAP*"):
        filepaths = [ff for ff in compilation.glob("*") if not ff.name.startswith('.')]
        for filepath in filepaths:
            print(f"subsample_bedmap: input = {filepath}")
            if filepath.name.startswith("BEDMAP1"):
                institution = "BEDMAP1"
                year = 1966
                air = True
                campaign = "BEDMAP1"
            else:
                ff = filepath.name.strip(".csv")
                tokens = ff.split("_")
                institution = tokens[0]
                year = int(tokens[1])
                air = "AIR" == tokens[-2]
                campaign = "_".join(tokens[2:-2])
            if institution not in institutions:
                institutions[institution] = []
            # Cache this for later processing
            institutions[institution].append((year, campaign, air, filepath))

    ps71 = pyproj.Proj("epsg:3031")
    min_spacing = 200  # meters between successive points

    for institution, campaigns in institutions.items():
        print(f"Subsampling {institution}")
        for campaign in campaigns:
            _, cc, _, in_filepath = campaign
            institution_dir = output_dir / institution
            try:
                institution_dir.mkdir(parents=True, exist_ok=True)
            except FileExistsError as ex:
                raise Exception("Could not create {}: {}.".format(institution_dir, ex))
            out_filepath = os.path.join(institution_dir, in_filepath.name)
            if force or not os.path.exists(out_filepath):
                print(f"Creating {out_filepath}")
                lat, lon = load_lat_lon(in_filepath)

                if cc == "BEDMAP1":
                    good_idxs = [
                        idx
                        for idx in np.arange(0, len(lat))
                        if idx not in duplicate_idxs
                    ]
                    print(f"For BEDMAP1, using {len(good_idxs)} / {len(lat)} points.")

                    lat = lat[good_idxs]
                    lon = lon[good_idxs]

                n_pts = len(lat)
                lat, lon = subsample_tracks(lat, lon, min_spacing)
                print(f"For {in_filepath.stem}, using {len(lat)} / {n_pts} points. ({100*len(lat)/n_pts:0.1f}%)")
                xx, yy = ps71.transform(lon, lat)
                skip_rows = count_skip_lines(in_filepath)
                with (open(in_filepath, "r") as in_fp,
                      open(out_filepath, "w" ) as out_fp):
                    for _ in range(skip_rows):
                        line = in_fp.readline()
                        out_fp.write(line)
                    out_fp.write("ps71_easting,ps71_northing\n")
                    out_fp.writelines(
                        ["{},{}\n".format(pt[0], pt[1]) for pt in zip(xx, yy)]
                    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "data_directory", help="Root directory for all QIceRadar-managed radargrams."
    )
    parser.add_argument(
        "index_directory", help="Root directory for generated subsampled files"
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    data_path = pathlib.Path(args.data_directory)
    index_path = pathlib.Path(args.index_directory)
    subsample_bedmap(data_path, index_path, args.force)

