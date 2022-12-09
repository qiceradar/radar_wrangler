#! /usr/bin/env python3

"""
Create KML files for each PST, using subsampled CSV paths that
have already been extracted.
"""

import csv
import os
import simplekml


def create_utig_kmls(index_directory):
    blue = (31, 120, 138, 255)
    for region in ["ARCTIC", "ANTARCTIC"]:
        utig_data_dir = os.path.join(index_directory, region, "UTIG")
        campaigns = [dd for dd in os.listdir(utig_data_dir)
                     if os.path.isdir(os.path.join(utig_data_dir, dd))]
        campaigns.sort()
        for campaign in campaigns:
            print("Creating KMLs for campaign: {}".format(campaign))
            campaign_dir = os.path.join(utig_data_dir, campaign)
            # Each campaign has PSTs, each of which is split into granules
            psts = [dd for dd in os.listdir(campaign_dir)
                    if os.path.isdir(os.path.join(campaign_dir, dd))]
            psts.sort()
            for pst in psts:
                print("...{}".format(pst))
                pst_dir = os.path.join(campaign_dir, pst)
                segments = [ss for ss in os.listdir(
                    pst_dir) if ss.endswith('csv')]
                segments.sort()
                kml = simplekml.Kml()
                for segment in segments:
                    csv_filepath = os.path.join(pst_dir, segment)
                    coords = None
                    with open(csv_filepath) as csvfile:
                        csv_reader = csv.DictReader(csvfile)
                        coords = [(pt['Longitude'], pt['Latitude'])
                                  for pt in csv_reader]
                    if coords is not None:
                        ls = kml.newlinestring(
                            name=segment.rstrip(".csv"), coords=coords)
                        ls.style.linestyle.color = simplekml.Color.rgb(*blue)
                kml_filepath = os.path.join(campaign_dir, pst+".kml")
                kml.save(kml_filepath)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("index_directory",
                        help="Root directory for generated subsampled files")
    args = parser.parse_args()
    create_utig_kmls(args.index_directory)


if __name__ == "__main__":
    main()
