"""
Common functions used by the detangle_bedmap1_{institution} jupyter notebooks.
"""
import numpy as np
import pandas as pd
import pyproj


def load_bedmap_ll(filepath):
    data = pd.read_csv(filepath, skiprows=18)

    lon_index = [col for col in data.columns if "longitude" in col][0]
    lat_index = [col for col in data.columns if "latitude" in col][0]
    lon = data[lon_index]
    lat = data[lat_index]

    return lon, lat


def load_bedmap_xy_new(filepath) -> np.ndarray:
    data = pd.read_csv(filepath, skiprows=18)

    lon_index = [col for col in data.columns if "longitude" in col][0]
    lat_index = [col for col in data.columns if "latitude" in col][0]
    lon = data[lon_index]
    lat = data[lat_index]
    ps71 = pyproj.Proj("epsg:3031")
    xx, yy = ps71.transform(lon, lat)

    coords = np.array([xx, yy]).transpose()

    return coords


def load_bedmap_xy(filepath):
    data = pd.read_csv(filepath, skiprows=18)

    lon_index = [col for col in data.columns if "longitude" in col][0]
    lat_index = [col for col in data.columns if "latitude" in col][0]
    lon = data[lon_index]
    lat = data[lat_index]
    ps71 = pyproj.Proj("epsg:3031")
    xx, yy = ps71.transform(lon, lat)

    return np.array(xx), np.array(yy)


def subsample_tracks_uniform(xx, yy, min_spacing):
    """
    Subsample the input coordinates so sequential points are separated
    by at least min_spacing, in the input coordinate system.

    This assumes that the input data provides coordinates in sequential
    order w/r/t data collection. (Particularly relevant for BEDMAP and
    anywhere granules are stitched together.)
    """
    good_idxs = [
        idx
        for idx, x, y in zip(np.arange(len(xx)), xx, yy)
        if not (np.isnan(x) or np.isnan(y))
    ]
    xx = xx[good_idxs]
    yy = yy[good_idxs]

    dx = xx[1:] - xx[:-1]
    dy = yy[1:] - yy[:-1]
    lengths = np.sqrt(dx * dx + dy * dy)

    keep_idxs = [0]

    cumulative_dist = 0
    for idx, segment_dist in enumerate(lengths):
        cumulative_dist += segment_dist
        if cumulative_dist >= min_spacing:
            # Segment corresponding to length at idx is between point[idx] and point[idx+1],
            # and we want to add the second point of the segment.
            keep_idxs.append(idx + 1)
            cumulative_dist = 0
    return xx[keep_idxs], yy[keep_idxs]


def find_closest_bedmap(
    survey_xx, survey_yy, bm1_xx, bm1_yy, decimation=None, subsampling=None
):
    """
    For every point in the input survey, find the closest point in BM1.
    For computational reasons, it is usually best to subsample/decimate the input data
    * subsampling: distance (in meters) between output subsampled points
    * decimation: only keep the N-th input point
    """
    if subsampling is not None:
        xx, yy = subsample_tracks_uniform(survey_xx, survey_yy, subsampling)
        print("Subsampled {} -> {}".format(len(survey_xx), len(xx)))
    elif decimation is not None:
        survey_idxs = np.arange(0, len(survey_xx), decimation)
        survey_idxs = np.append(survey_idxs, len(survey_xx) - 1)
        xx = survey_xx[survey_idxs]
        yy = survey_yy[survey_idxs]
    else:
        print("WARNING: attempting to find closest bedmap points at full resolution!")
        xx = survey_xx
        yy = survey_yy

    min_bm1_idxs = -1 * np.ones(xx.shape)

    for idx in np.arange(len(xx)):
        dx = np.abs(bm1_xx - xx[idx])
        dy = np.abs(bm1_yy - yy[idx])
        dists = np.sqrt(dx * dx + dy * dy)
        min_bm1_idxs[idx] = np.argmin(dists)
    # Need array of ints to use as indices
    min_bm1_idxs = list({int(el) for el in min_bm1_idxs})
    return np.array(min_bm1_idxs)


def expand_range(
    group_idxs, survey_xx, survey_yy, bm1_xx, bm1_yy, tolerance=10000, max_gap=np.inf
):
    """
    Our calculated range may miss a few points from the BEDMAP1 dataset, so see if we
    can extend along those indexes while being close to the input survey.

    * group_idxs: indices into bm1 that are definitely in the survey
    * tolerance: distance in meters to consider BM1 point matching the survey
         (This doesn't seem to need to be very precise since the BEDMAP1 points
         are generally contiguous within a survey, so the next survey is likely
         to be a large jump.)
    * max_gap: distance between successive points in BM1 that we'll expand between
    """
    # Distance from point in segment to closest point in the survey
    min_dist = 0
    group_start = min(group_idxs)
    # jump between successive points
    delta = 0
    prev_x = bm1_xx[group_start]
    prev_y = bm1_yy[group_start]
    while min_dist < tolerance and delta < max_gap:
        group_start -= 1
        if group_start < 0:
            break
        dx = np.abs(bm1_xx[group_start] - survey_xx)
        dy = np.abs(bm1_yy[group_start] - survey_yy)
        dists = np.sqrt(dx * dx + dy * dy)
        min_dist = np.min(dists)

        curr_x = bm1_xx[group_start]
        curr_y = bm1_yy[group_start]
        delta = np.sqrt((curr_x - prev_x) ** 2 + (curr_y - prev_y) ** 2)
        prev_x, prev_y = curr_x, curr_y

    print("For BM1 idx {}, min_dist = {:0.2f} km".format(group_start, min_dist / 1000))
    group_start += 1  # This is ugly, but the while loop terminated with group1_start just outside of range.

    group_end = max(group_idxs)
    min_dist = 0
    delta = 0
    prev_x = bm1_xx[group_end]
    prev_y = bm1_yy[group_end]
    while min_dist < tolerance and delta < max_gap:
        group_end += 1
        if group_end >= len(bm1_xx):
            break
        dx = np.abs(bm1_xx[group_end] - survey_xx)
        dy = np.abs(bm1_yy[group_end] - survey_yy)
        dists = np.sqrt(dx * dx + dy * dy)
        min_dist = np.min(dists)
        curr_x = bm1_xx[group_end]
        curr_y = bm1_yy[group_end]
        delta = np.sqrt((curr_x - prev_x) ** 2 + (curr_y - prev_y) ** 2)
        prev_x, prev_y = curr_x, curr_y
    print("For BM1 idx {}, min_dist = {:0.2f} km".format(group_end, min_dist / 1000))
    group_end -= 1

    return group_start, group_end


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
    # Assumes they are sorted!
    for bm1_idx in idxs:
        if bm1_idx - curr_idx > max_skips:
            if length > min_length:
                segments.append((int(start_idx), int(curr_idx)))
            start_idx = bm1_idx
            length = 1
        else:
            length += 1

        curr_idx = bm1_idx
    segments.append((int(start_idx), int(curr_idx)))

    return segments


def segment_indices_gap(idxs, max_skips, min_length, bm_xx, bm_yy, max_gap):
    """
    Split a list of indices into sequential chunks, with an added constraint
    that there won't be a jump of more than max_gap between sequential points.

    * max_skips: maximum gap between indices within the same chunk
    * min_length: minimum points to create a chunk (smaller will be discarded)
    * max_gap: max distance (m) allowed between successive points in a segment
    """
    segments = []
    idxs.sort()
    start_idx = idxs[0]
    curr_idx = start_idx
    length = 1
    # Assumes they are sorted!
    prev_x = bm_xx[start_idx]
    prev_y = bm_yy[start_idx]
    for bm1_idx in idxs:
        curr_x = bm_xx[bm1_idx]
        curr_y = bm_yy[bm1_idx]
        gap = np.sqrt((curr_x - prev_x) ** 2 + (curr_y - prev_y) ** 2)
        prev_x, prev_y = curr_x, curr_y
        if bm1_idx - curr_idx > max_skips:
            if length >= min_length:
                segments.append((start_idx, curr_idx))
            start_idx = bm1_idx
            length = 1
        elif gap >= max_gap:
            if length >= min_length:
                segments.append((start_idx, curr_idx))
            start_idx = bm1_idx
            length = 1
        else:
            length += 1

        curr_idx = bm1_idx
    segments.append((start_idx, curr_idx))

    return segments
