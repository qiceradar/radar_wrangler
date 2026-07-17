#! /usr/bin/env python3
"""
Update the granules table for SOAR LVS survey, assuming that the user downloaded the files to ${RADAR_DATA}/UTIG/LVS/*.segy
"""

import os
import pathlib
import sqlite3


def main(
    data_dir: str,
    index: str,
) -> None:

    campaign_basedir = pathlib.Path(f"{data_dir}/ANTARCTIC/UTIG/LVS")

    # can't do *.segy because OSX creates files starting with ._
    granule_filepaths = list(campaign_basedir.glob("X*.segy"))
    granule_filepaths.extend(campaign_basedir.glob("Y*.segy"))

    if len(granule_filepaths) == 0:
        print(f"Unable to find any SEGY files under {campaign_basedir}")
        return

    connection = sqlite3.connect(index)
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")

    region = "ANTARCTIC"
    institution = "UTIG"
    campaign = "LVS"
    product = "inco"
    url = "https://www.usap-dc.org/view/dataset/601300"
    data_format = "lvs_segy"
    download_method = "usapdc_lvs"

    granule_seq = 0  # This dataset doesn't have granules

    for filepath in granule_filepaths:
        filename = filepath.name
        filesize = os.path.getsize(filepath)

        segment = filepath.stem
        relpath = f"{region}/{institution}/{campaign}/{filename}"
        granule_name = f"{institution}_{campaign}_{segment}"

        cursor.execute(
            "INSERT OR REPLACE INTO granules VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                granule_name,
                institution,
                campaign,
                segment,
                granule_seq,
                product,
                data_format,
                download_method,
                url,
                relpath,
                str(filesize),
            ],
        )
    connection.commit()

    connection.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "data_directory", help="Root directory for all QIceRadar-managed radargrams."
    )
    parser.add_argument(
        "index",
        help="Geopackage database to update with metadata about  campaigns and granules",
    )

    args = parser.parse_args()

    main(args.data_directory, args.index)
