"""
Utility functions for extracing/subsampling viewable tracks from full datasets.
"""

import pyproj
import numpy as np
import rdp
import time



def count_skip_lines(filepath):
    """
    Count how many comment lines are at the start of a CSV file.

    QGS's vector layer API doesn't appear to have a setting that says
    "ignore all lines starting with a '#'", even though the GUI seems
    to auto-detect that and fill in the number.
    """
    skip_lines = 0
    for line in open(filepath, 'r'):
        if line.startswith("#"):
            skip_lines += 1
        else:
            break
    return skip_lines


def subsample_tracks(lats, lons, min_spacing):
    '''
    Subsample the input coordinates so sequential points are separated by at least min_spacing.
    This assumes that the BEDMAP CSVs provide coordinate in sequential order w/r/t data collection
    '''
    geod = pyproj.Geod(ellps="WGS84")
    # UTIG has some NaNs in their positioning data
    good_idxs = [idx for idx, lat, lon in zip(
        np.arange(len(lats)), lats, lons) if not (np.isnan(lat) or np.isnan(lon))]
    lats = lats[good_idxs]
    lons = lons[good_idxs]

    lengths = geod.line_lengths(lons, lats)
    keep_idxs = [0]

    cumulative_dist = 0
    for idx, segment_dist in enumerate(lengths):
        cumulative_dist += segment_dist
        if cumulative_dist >= min_spacing:
            # Segment corresponding to length at idx is between point[idx] and point[idx+1],
            # and we want to add the second point of the segment.
            keep_idxs.append(idx+1)
            cumulative_dist = 0
    return lats[keep_idxs], lons[keep_idxs]


def subsample_tracks_uniform(xx, yy, min_spacing):
    '''
    Subsample the input coordinates so sequential points are separated
    by at least min_spacing, in the input coordinate system.

    This assumes that the input data provides coordinates in sequential
    order w/r/t data collection. (Particularly relevant for BEDMAP and
    anywhere granules are stitched together.)
    '''
    good_idxs = [idx for idx, x, y in zip(
        np.arange(len(xx)), xx, yy) if not (np.isnan(x) or np.isnan(y))]
    xx = xx[good_idxs]
    yy = yy[good_idxs]

    dx = xx[1:] - xx[:-1]
    dy = yy[1:] - yy[:-1]
    lengths = np.sqrt(dx*dx + dy*dy)

    keep_idxs = [0]

    cumulative_dist = 0
    for idx, segment_dist in enumerate(lengths):
        cumulative_dist += segment_dist
        if cumulative_dist >= min_spacing:
            # Segment corresponding to length at idx is between point[idx] and point[idx+1],
            # and we want to add the second point of the segment.
            keep_idxs.append(idx+1)
            cumulative_dist = 0
    return xx[keep_idxs], yy[keep_idxs]


def subsample_tracks_rdp(xx, yy, epsilon):
    '''
    Use RDP algorithm to subsample the points, guaranteeing no point's error will be more than epsilon
    when projected into PS71 coordinate system.
    '''
    # UTIG has some NaNs in their positioning data
    good_idxs = [idx for idx, x, y in zip(
        np.arange(len(xx)), xx, yy) if not (np.isnan(x) or np.isnan(y))]
    xx = xx[good_idxs]
    yy = yy[good_idxs]

    data = np.array([xx, yy]).transpose()
    t0 = time.time()
    ss = rdp.rdp(data, epsilon=epsilon)
    dt = time.time() - t0
    print(
        "RDP subsampled {} -> {} in {:02f} seconds.".format(len(xx), ss.shape[0], dt))
    return ss[:, 0], ss[:, 1]
