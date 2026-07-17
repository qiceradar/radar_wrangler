#! /usr/bin/env python3
"""
Update the granules table using contents of unzipped tarball from Zenodo.
"""

import os
import pathlib
import re
import sqlite3


def main(data_dir: str, index: str,) -> None:
    campaign_basedir = pathlib.Path(f"{data_dir}/ANTARCTIC/KOPRI/KRT1")

    granule_filepaths = list(campaign_basedir.glob("*.nc"))

    if len(granule_filepaths) == 0:
        print(f"Unable to find any netCDFs under {campaign_basedir}")
        return


    connection = sqlite3.connect(index)
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")

    region = "ANTARCTIC"
    institution = "KOPRI"
    campaign = "KRT1"
    product = "KHERA1B"
    url = "https://zenodo.org/records/3874655"
    data_format = "utig_netcdf"
    download_method = "zenodo_krt1"

    expr = "KHERA1B_(?P<year>[0-9]{4})(?P<doy>[0-9]{3})_(?P<project>[a-zA-Z0-9]*)_(?P<set>[a-zA-Z0-9]*)_(?P<transect>[a-zA-Z0-9]*)_(?P<granule>[0-9]{3}).nc"

    for filepath in granule_filepaths:
        filename = filepath.name
        filesize = os.path.getsize(filepath)

        mm = re.match(expr, filename)
        if mm is None:
            print(f"Could not parse filename: {filename}")
            continue

        relpath = f"{region}/{institution}/{campaign}/{filename}"
        segment = f"{mm['project']}/{mm['set']}/{mm['transect']}"
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
