#! /usr/bin/env python3
"""
Download the "best" version for each line from data.cresis.ku.edu
# TODO: Consider downloading _all_ versions, and making them available?

This is the most complete set of data collected by CReSIS, but it doesn't
have good metadata for who actually owns the data.
"""


import pathlib
import sqlite3
import subprocess

from index_utils import Granule, read_granule_list


def download_cresis(
    data_dir: str, granules: list[Granule], antarctic_index: str, arctic_index: str
):
    """
    Download all CReSIS data from the KU servers.
    """

    connections = {}
    cursors = {}
    connections["ANTARCTIC"] = sqlite3.connect(antarctic_index)
    connections["ARCTIC"] = sqlite3.connect(arctic_index)
    for region in ["ANTARCTIC", "ARCTIC"]:
        cursors[region] = connections[region].cursor()
        cursors[region].execute("PRAGMA foreign_keys = ON")

    for granule in granules:
        dest_filepath = pathlib.Path(data_dir, granule.relative_filepath)
        try:
            pp = dest_filepath.parent
            pp.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            raise Exception("Could not create {}.".format(pp))
            continue

        if dest_filepath.is_file():
            filesize = dest_filepath.stat().st_size
        else:
            print(f"Downloading {dest_filepath}")
            wget_cmd = 'wget -c --directory-prefix="{}" "{}"'.format(
                pp, granule.download_url
            )
            print(wget_cmd)
            subprocess.getoutput(wget_cmd)

        # Check if download succeeded
        try:
            filesize = dest_filepath.stat().st_size
        except Exception as ex:
            # There are a handful of files that are listed in the CReSIS website
            # but where the actual radargram gives
            # "Forbidden: You don't have permission to access this resource".
            # So, check that download was successful
            print(f"Cannot find downloaded file {dest_filepath}")
            print(f"{ex}")
            continue

        # And, update the database with info about this granule/frame
        cursors[granule.region].execute(
            "INSERT OR REPLACE INTO granules VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                granule.granule_name,
                granule.institution,
                granule.campaign,
                granule.segment,
                granule.granule,
                granule.data_product,
                granule.data_format,
                granule.download_method,
                granule.download_url,
                granule.relative_filepath,
                str(filesize),  # eventually won't know file size
            ],
        )
        connections[region].commit()

    for _region, connection in connections.items():
        connection.close()


def main(data_dir: str, antarctic_index: str, arctic_index: str):
    index_filepath = "../../data/cresis_granules.csv"

    cresis_granules = read_granule_list(index_filepath)

    download_cresis(data_dir, cresis_granules, antarctic_index, arctic_index)


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
