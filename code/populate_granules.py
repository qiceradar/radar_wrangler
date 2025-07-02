#! /usr/bin/env python3
"""
Update the granules table using generated index files and filesizes from locally downloaded radargrams.
"""

import pathlib
import sqlite3

from radar_wrangler_utils import read_granule_list


def main(data_dir: str, antarctic_index: str, arctic_index: str) -> None:
    granule_filepaths = [
        "../data/cresis_granules.csv",
    ]

    connections = {}
    cursors = {}
    connections["ANTARCTIC"] = sqlite3.connect(antarctic_index)
    connections["ARCTIC"] = sqlite3.connect(arctic_index)
    for region in ["ANTARCTIC", "ARCTIC"]:
        cursors[region] = connections[region].cursor()
        cursors[region].execute("PRAGMA foreign_keys = ON")

    for granule_filepath in granule_filepaths:
        granules = read_granule_list(granule_filepath)

        for granule in granules:
            dest_filepath = pathlib.Path(data_dir, granule.relative_filepath)
            try:
                filesize = dest_filepath.stat().st_size
            except Exception:
                # There are a handful of files that are listed in the CReSIS website
                # but where the actual radargram gives
                # "Forbidden: You don't have permission to access this resource".
                # So, check that download was successful
                print(f"Cannot find downloaded file {dest_filepath}")
                filesize = -1

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
                    str(filesize),
                ],
            )

        connections[region].commit()

    for _region, connection in connections.items():
        connection.close()


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
