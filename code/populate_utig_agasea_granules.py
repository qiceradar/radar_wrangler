#! /usr/bin/env python3
"""
Update the granules table by traversing file tree downloaded from USAP-DC.

This preserves the directory structure in the Google Drive download I was
given in 2022; I have not confirmed that it is always consistent.
"""

import os
import pathlib
import re
import sqlite3


def main(data_dir: str, index: str,) -> None:

    campaign_basedir = pathlib.Path(f"{data_dir}/ANTARCTIC/UTIG/AGASEA")

    granule_filepaths = [fp for fp in campaign_basedir.glob("**/*.nc") if not fp.name.startswith('.')]

    if len(granule_filepaths) == 0:
        print(f"Unable to find any netCDFs under {campaign_basedir}")
        return

    connection = sqlite3.connect(index)
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")

    region = "ANTARCTIC"
    institution = "UTIG"
    campaign = "AGASEA"
    product = "HiCARS_pik1"
    url = "https://www.usap-dc.org/view/dataset/601436"
    data_format = "utig_netcdf"
    download_method = "usapdc_agasea"

    # ~/RadarData/ANTARCTIC/UTIG/AGASEA/X27a/X27a_8.nc
    # They only have transect in the filepath; not sure project/set ...
    expr = "(?P<transect>[a-zA-Z0-9]*)_(?P<granule>[0-9]{1,3}).nc"
    project = "THW"
    pst_set = "SJB"

    for filepath in granule_filepaths:
        filename = filepath.name
        filesize = os.path.getsize(filepath)

        mm = re.match(expr, filename)
        if mm is None:
            print(f"Could not parse filename: {filename}")
            continue

        transect = mm['transect']
        relpath = f"{region}/{institution}/{campaign}/{transect}/{filename}"
        segment = f"{project}_{pst_set}_{transect}"
        granule_seq = mm['granule']
        granule_name = f"{institution}_{campaign}_{segment}_{granule_seq}"

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
