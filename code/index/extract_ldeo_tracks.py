#! /usr/bin/env python3
"""
For now, only includes the AGAP_GAMBIT survey.

I have not yet managed to get more than sample data from Rosetta.
"""

from radar_index_utils import subsample_tracks

import netCDF4 as nc
import numpy as np
import os
import pathlib
import pyproj


def main(data_directory: str, index_directory: str):
    """
    For now, this appends all segments in a flight line together.
    In the final index version, we may want them to show up as separate
    shapes within the line's layer, for better granularity selecting what to download.
    """
    output_agap_dir = os.path.join(
        index_directory, "ANTARCTIC", "LDEO", "AGAP_GAMBIT")
    print("Saving data to: {}".format(output_agap_dir))
    try:
        pp = pathlib.Path(output_agap_dir)
        pp.mkdir(parents=True, exist_ok=True)
    except FileExistsError as ex:
        raise Exception(
            "Could not create {}: {}.".format(output_agap_dir, ex))

    agap_dir = "{}/ANTARCTIC/LDEO/AGAP_GAMBIT".format(data_directory)
    print(os.listdir(agap_dir))
    flightlines = [ll for ll in os.listdir(agap_dir)
                   if os.path.isdir(os.path.join(agap_dir, ll))]

    print(flightlines)
    ps71 = pyproj.Proj('epsg:3031')

    for flightline in flightlines:
        print("Processing: {}".format(flightline))
        flight_dir = os.path.join(agap_dir, flightline)
        segments = [ss for ss in os.listdir(flight_dir)
                    if ss.endswith('nc')]
        if 0 == len(segments):
            # The directory for line 520 doesn't have any data
            continue

        lat = []
        lon = []
        for segment in segments:
            segment_filepath = os.path.join(flight_dir, segment)
            data = nc.Dataset(segment_filepath, 'r')
            lat.extend(data['Lat'][:].data)
            lon.extend(data['Lon'][:].data)
        lat = np.array(lat)
        lon = np.array(lon)

        min_spacing = 200
        sub_lat, sub_lon = subsample_tracks(lat, lon, min_spacing)
        xx, yy = ps71.transform(sub_lon, sub_lat)

        line_filepath = os.path.join(output_agap_dir, flightline) + ".csv"
        print("Saving {} to {}".format(flightline, line_filepath))
        with open(line_filepath, 'w') as fp:
            # TODO: Add some sort of metadata here
            fp.write("ps71_easting, ps71_northing\n")
            data = ["{},{}\n".format(pt[0], pt[1]) for pt in zip(xx, yy)]
            fp.writelines(data)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("data_directory",
                        help="Root directory for all QIceRadar-managed radargrams.")
    parser.add_argument("index_directory",
                        help="root directory where subsampled tracks belong.")
    args = parser.parse_args()
    main(args.data_directory, args.index_directory)
