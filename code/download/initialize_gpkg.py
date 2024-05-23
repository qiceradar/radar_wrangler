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
    institutions = ["AWI", "BAS", "CRESIS", "KOPRI", "UTIG"]
    cursor.executemany(
        "INSERT OR REPLACE INTO institutions VALUES(?)", [[ii] for ii in institutions]
    )
    connection.commit()
    result = cursor.execute("SELECT * from institutions")
    print(f"Institutions: {result.fetchall()}")

    # TODO: actually fill in valid file formats =)
    data_formats = []
    cursor.execute("CREATE TABLE IF NOT EXISTS data_formats (name TEXT PRIMARY KEY)")
    cursor.executemany(
        "INSERT OR REPLACE INTO data_formats VALUES(?)", [[ii] for ii in data_formats]
    )
    connection.commit()
    result = cursor.execute("SELECT * from data_formats")
    print(f"Available data formats: {result.fetchall()}")

    download_methods = ["wget"]
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

    # Name of the campaign is expected to be {institution}_{campaign}
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS campaigns (\n"
        "    name TEXT PRIMARY KEY,\n"
        "    data_citation TEXT,\n"
        "    science_citation TEXT,\n"
        "    institution TEXT NOT NULL,\n"
        "    FOREIGN KEY (institution) REFERENCES institutions (name)\n"
        ")"
    )

    # Granule name should fully specify the radargram:
    # {institution}_{campaign}_{granule}
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS granules(\n"
        "    name TEXT PRIMARY KEY,\n"
        "    campaign TEXT NOT NULL,\n"
        "    data_format TEXT NOT NULL,\n"
        "    download_method TEXT NOT NULL,\n"
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
