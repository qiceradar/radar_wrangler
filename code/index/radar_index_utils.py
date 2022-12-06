"""
Utility functions for extracing/subsampling viewable tracks from full datasets.
"""

import pyproj


def subsample_tracks(lat, lon, min_spacing):
    '''
    Subsample the input coordinates so sequential points are separated by at least min_spacing.
    This assumes that the BEDMAP CSVs provide coordinate in sequential order w/r/t data collection
    '''
    geod = pyproj.Geod(ellps="WGS84")
    lengths = geod.line_lengths(lon, lat)
    keep_idxs = [0]

    cumulative_dist = 0
    for idx, segment_dist in enumerate(lengths):
        cumulative_dist += segment_dist
        if cumulative_dist >= min_spacing:
            # Segment corresponding to length at idx is between point[idx] and point[idx+1],
            # and we want to add the second point of the segment.
            keep_idxs.append(idx+1)
            cumulative_dist = 0
    return lat[keep_idxs], lon[keep_idxs]
