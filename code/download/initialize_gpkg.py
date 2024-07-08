#! /usr/bin/env python3
"""
Initialize the various metadata tables that the download and
index scripts will populate.

Does NOT create the per-campaign tables that will contain geometries.
"""

import argparse
import pathlib
import shutil
import sqlite3


def create_gpkg(empty_file: str, output_file: str):
    """
    Initialize our geopackage database from the default empty database,
    then add the non-geometry tables that will be used to track metadata
    about the radargrams.
    """
    # We do NOT want to overwrite an existing file
    if pathlib.Path(output_file).is_file():
        print(f"Output file {output_file} already exists; not copying empty file")
        # TODO: Consider confirming it has the right tables?
    else:
        shutil.copyfile(empty_file, output_file)

    connection = sqlite3.connect(output_file)
    cursor = connection.cursor()

    cursor.execute("PRAGMA foreign_keys = ON")

    # I checked using their online validator, and it is OK to have additional
    # tables in a geopackage that aren't described in gpkg_contents.

    # These tables serve as enums for other fields.
    cursor.execute("CREATE TABLE IF NOT EXISTS institutions (name TEXT PRIMARY KEY)")
    institutions = ["AWI", "BAS", "CRESIS", "KOPRI", "LDEO", "NASA", "NPI", "UTIG"]
    cursor.executemany(
        "INSERT OR REPLACE INTO institutions VALUES(?)", [[ii] for ii in institutions]
    )
    connection.commit()
    result = cursor.execute("SELECT * from institutions")
    print(f"Institutions: {result.fetchall()}")

    data_formats = [
        "ice_thickness",  # The index contains info about ice thickness lines, if that's all that is available.
        "bas_netcdf",
        "utig_netcdf",
    ]

    cursor.execute("CREATE TABLE IF NOT EXISTS data_formats (name TEXT PRIMARY KEY)")
    cursor.executemany(
        "INSERT OR REPLACE INTO data_formats VALUES(?)", [[ii] for ii in data_formats]
    )
    connection.commit()
    result = cursor.execute("SELECT * from data_formats")
    print(f"Available data formats: {result.fetchall()}")

    download_methods = ["wget", "nsidc", "usapdc_email", "usapdc_captcha", "aad_s3"]
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS download_methods (name TEXT PRIMARY KEY)"
    )
    cursor.executemany(
        "INSERT OR REPLACE INTO download_methods VALUES(?)",
        [[ii] for ii in download_methods],
    )
    connection.commit()
    result = cursor.execute("SELECT * from download_methods")
    print(f"Available download methods: {result.fetchall()}")

    # Previously, we included institution name in name of campaign,
    # but I found that confusing. I think that the campaign names
    # are unique on their own.
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS campaigns (\n"
        "    name TEXT PRIMARY KEY,\n"
        "    institution TEXT NOT NULL,\n"
        "    data_citation TEXT,\n"  # Should include DOI, if available
        "    science_citation TEXT,\n"
        "    FOREIGN KEY (institution) REFERENCES institutions (name)\n"
        ")"
    )

    # Granule name should fully specify the radargram:
    # {institution}_{campaign}_{granule}
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS granules(\n"
        "    name TEXT PRIMARY KEY,\n"
        "    institution TEXT NOT NULL,\n"
        "    campaign TEXT NOT NULL,\n"
        "    segment TEXT NOT NULL,\n"
        "    granule TEXT,\n"
        "    data_product TEXT,\n"
        "    data_format TEXT NOT NULL,\n"
        "    download_method TEXT NOT NULL,\n"
        "    url TEXT NOT NULL,\n"
        "    destination_path TEXT NOT NULL,\n"  # relative to RadarData
        "    filesize INTEGER,\n"  # in bytes
        "    FOREIGN KEY (institution) REFERENCES institutions (name)\n"
        "    FOREIGN KEY (campaign) REFERENCES campaigns (name)\n"
        "    FOREIGN KEY (data_format) REFERENCES data_formats (name)\n"
        "    FOREIGN KEY (download_method) REFERENCES download_methods (name)\n"
        ")"
    )

    connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("empty_file", help="path to example empty geopackage file")
    parser.add_argument("output_file", help="path to output file")

    args = parser.parse_args()
    create_gpkg(args.empty_file, args.output_file)
