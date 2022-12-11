#! /usr/bin/env python3

from radar_index_utils import subsample_tracks

import os
import pandas as pd
import pathlib
import pyproj


def load_lat_lon(filepath):
    '''Open file in the BEDMAP CVS format and extract just lat long from it'''
    data = pd.read_csv(filepath, skiprows=18)

    lon_index = [col for col in data.columns if 'longitude' in col][0]
    lat_index = [col for col in data.columns if 'latitude' in col][0]
    lon = data[lon_index]
    lat = data[lat_index]
    return lat, lon


def subsample_bedmap(data_directory, index_directory, force):
    bedmap_dir = os.path.join(data_directory, "ANTARCTIC", "BEDMAP")
    output_dir = os.path.join(index_directory, "ANTARCTIC", "BEDMAP")

    institutions = {}

    for compilation in os.listdir(bedmap_dir):
        compilation_dir = os.path.join(bedmap_dir, compilation)
        for filename in os.listdir(compilation_dir):
            if filename.startswith('.'):
                continue
            elif filename.startswith('BEDMAP1'):
                institution = "BEDMAP1"
                year = 1966
                air = True
                campaign = "BEDMAP1"
            else:
                ff = filename.strip('.csv')
                tokens = ff.split('_')
                institution = tokens[0]
                year = int(tokens[1])
                air = "AIR" == tokens[-2]
                campaign = "_".join(tokens[2:-2])
            if institution not in institutions:
                institutions[institution] = []
            # Cache this for later processing
            filepath = os.path.join(compilation_dir, filename)
            institutions[institution].append((year, campaign, air, filepath))

    ps71 = pyproj.Proj('epsg:3031')
    min_spacing = 200  # meters between successive points

    for institution, campaigns in institutions.items():
        print("Subsampling {}".format(institution))
        for campaign in campaigns:
            _, _, _, datafilepath = campaign
            institution_dir = os.path.join(output_dir, institution)
            try:
                pp = pathlib.Path(institution_dir)
                pp.mkdir(parents=True, exist_ok=True)
            except FileExistsError as ex:
                raise Exception(
                    "Could not create {}: {}.".format(institution_dir, ex))
            out_filename = datafilepath.split("/")[-1]
            out_filepath = os.path.join(institution_dir, out_filename)
            if force or not os.path.exists(out_filepath):
                lat, lon = load_lat_lon(datafilepath)
                lat, lon = subsample_tracks(lat, lon, min_spacing)
                xx, yy = ps71.transform(lon, lat)
                with open(datafilepath, 'r') as in_fp, open(out_filepath, 'w') as out_fp:
                    for _ in range(18):
                        line = in_fp.readline()
                        out_fp.write(line)
                    out_fp.write("ps71_easting, ps71_northing\n")
                    out_fp.writelines(["{},{}\n".format(pt[0], pt[1])
                                      for pt in zip(xx, yy)])


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("data_directory",
                        help="Root directory for all QIceRadar-managed radargrams.")
    parser.add_argument("index_directory",
                        help="Root directory for generated subsampled files")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    subsample_bedmap(args.data_directory, args.index_directory, args.force)
