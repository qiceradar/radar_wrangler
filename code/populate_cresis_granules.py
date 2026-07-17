#! /usr/bin/env python3
"""
Update the granules table using generated index files and filesizes from locally downloaded radargrams.
"""

import pathlib
import sqlite3

from radar_wrangler_utils import read_granule_list


def main(antarctic: bool, data_dir: str, index: str,) -> None:
    granule_filepaths = [
        "../data/CReSIS/cresis_granules.csv",
    ]

    connection = sqlite3.connect(index)
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")

    for granule_filepath in granule_filepaths:
        granules = read_granule_list(granule_filepath)

        for granule in granules:
            # Only process one region
            if antarctic and granule.region != "ANTARCTIC":
                continue

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

            cursor.execute(
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
        connection.commit()

    connection.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("--antarctic", action="store_true")
    parser.add_argument("--arctic", action="store_true")


    parser.add_argument(
        "data_directory", help="Root directory for all QIceRadar-managed radargrams."
    )
    parser.add_argument(
        "index",
        help="Geopackage database to update with metadata about  campaigns and granules",
    )

    args = parser.parse_args()


    antarctic = False
    if args.antarctic:
        antarctic = True
    elif args.arctic:
        antarctic = False
    else:
        print(f"ERROR: Must specify either --antarctic or --arctic")
        exit(-1)

    main(antarctic, args.data_directory, args.index)
