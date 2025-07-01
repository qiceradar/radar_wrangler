#! /usr/bin/env python3
"""
Download the "best" version for each line from data.cresis.ku.edu
# TODO: Consider downloading _all_ versions, and making them available?

This is the most complete set of data collected by CReSIS, but it doesn't
have good metadata for who actually owns the data.
"""


import os
import pathlib
import pickle
import sqlite3
import subprocess
from typing import Dict


def download_cresis(
    data_dir: str, datafiles: Dict, antarctic_index: str, arctic_index: str
):
    """
    Download all CReSIS data from the KU servers.
    """

    institution = "CRESIS"
    connections = {}
    cursors = {}
    connections["ANTARCTIC"] = sqlite3.connect(antarctic_index)
    connections["ARCTIC"] = sqlite3.connect(arctic_index)
    for region in ["ANTARCTIC", "ARCTIC"]:
        cursors[region] = connections[region].cursor()
        cursors[region].execute("PRAGMA foreign_keys = ON")

    for region, campaigns in datafiles.items():
        print(region)
        # if region == "ARCTIC":
        #     continue
        for campaign, products in campaigns.items():
            print(campaign)
            for product, segments in products.items():
                print(".. {}".format(product))
                for segment, frames in segments.items():
                    print(".... {}".format(segment))
                    dest_dir = "{}/{}/CRESIS/{}/{}/{}".format(
                        data_dir, region, campaign, product, segment
                    )
                    try:
                        pp = pathlib.Path(dest_dir)
                        pp.mkdir(parents=True, exist_ok=True)
                    except FileExistsError:
                        raise Exception("Could not create {}.".format(dest_dir))
                        continue

                    for frame, data_url in frames.items():
                        filename = data_url.split("/")[-1]
                        dest_filepath = os.path.join(dest_dir, filename)
                        rel_filepath = os.path.join(
                            region, institution, campaign, product, segment, filename
                        )

                        if os.path.exists(dest_filepath):
                            filesize = os.path.getsize(dest_filepath)
                            print(
                                f"Skipping {filename}: file already exists with size {filesize}"
                            )
                        else:
                            print(f"Downloading {dest_filepath}")
                            wget_cmd = 'wget -c --directory-prefix="{}" "{}"'.format(
                                dest_dir, data_url
                            )
                            print(wget_cmd)
                            subprocess.getoutput(wget_cmd)

                        # And, update the database with info about this granule/frame
                        filesize = os.path.getsize(dest_filepath)
                        granule = frame.split(".")[0].split("_")[-1]
                        granule_name = f"{institution}_{campaign}_{segment}_{granule}"
                        data_format = "cresis_mat"
                        download_method = "wget"
                        cursors[region].execute(
                            "INSERT OR REPLACE INTO granules VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            [
                                str(granule_name),
                                institution,
                                campaign,
                                segment,
                                granule,
                                product,
                                data_format,
                                download_method,
                                data_url,
                                str(rel_filepath),
                                str(filesize),
                            ],
                        )
                        connections[region].commit()

    for _region, connection in connections.items():
        connection.close()


def main(data_dir: str, antarctic_index: str, arctic_index: str):
    index_filepath = "../../data/CRESIS/cresis_datafiles.pkl"

    cresis_datafiles = pickle.load(open(index_filepath, "rb"))

    download_cresis(data_dir, cresis_datafiles, antarctic_index, arctic_index)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "data_directory", help="Root directory for all QIceRadar-managed radargrams."
    )
    parser.add_argument(
        "antarctic_index",
        help="Geopackage database to update with metadata about Antarctic campaigns and granules",
    )
    parser.add_argument(
        "arctic_index",
        help="Geopackage database to update with metadata about Arctic campaigns and granules",
    )

    args = parser.parse_args()

    main(args.data_directory, args.antarctic_index, args.arctic_index)
