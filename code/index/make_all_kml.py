#! /usr/bin/env python3

"""
Create KML files for each PST, using subsampled CSV paths that
have already been extracted.
"""

import csv
import os
import pathlib
import simplekml

from radar_index_utils import count_skip_lines


def create_kmls(index_directory):
    blue = (31, 120, 138, 255)
    for region in ["ARCTIC", "ANTARCTIC"]:
        for provider in ["BAS", "CRESIS", "KOPRI", "LDEO", "UTIG"]:
            data_dir = os.path.join(index_directory, region, provider)
            if not os.path.isdir(data_dir):
                print("No {} data from {}".format(region, provider))
                continue
            campaigns = [
                dd
                for dd in os.listdir(data_dir)
                if os.path.isdir(os.path.join(data_dir, dd))
            ]
            campaigns.sort()
            for campaign in campaigns:
                print("Creating KMLs for campaign: {}".format(campaign))
                campaign_dir = os.path.join(data_dir, campaign)
                campaign_kml = simplekml.Kml()
                # Each campaign has PSTs, each of which is split into granules
                # psts = [
                #     dd
                #     for dd in os.listdir(campaign_dir)
                #     if os.path.isdir(os.path.join(campaign_dir, dd))
                # ]

                for csv_filepath in pathlib.Path(campaign_dir).rglob("*.csv"):
                    coords = None
                    skip_lines = count_skip_lines(csv_filepath)
                    with open(csv_filepath, "r") as csvfile:
                        # TODO: This is a terrible hack, the CSV reader should
                        #       be able to handle whatever comments we add.
                        for _ in range(skip_lines):
                            next(csvfile)

                        csv_reader = csv.DictReader(csvfile)
                        coords = [
                            (pt["Longitude"], pt["Latitude"]) for pt in csv_reader
                        ]
                    if coords is not None:
                        ls = campaign_kml.newlinestring(
                            name=csv_filepath.stem, coords=coords
                        )
                        ls.style.linestyle.color = simplekml.Color.rgb(*blue)
                kml_filepath = os.path.join(data_dir, campaign + ".kml")
                campaign_kml.save(kml_filepath)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "index_directory", help="Root directory for generated subsampled files"
    )
    args = parser.parse_args()
    create_kmls(args.index_directory)


if __name__ == "__main__":
    main()
