#! /usr/bin/env python3
"""
We manually maintain YAML files specifying the requested data and
science citations for each campaign.

Rerun this script to update the index when any of these files are
changed.
"""

import sqlite3

import yaml


def main(antarctic: bool, database):
    campaign_filepaths = [
        "../data/awi_campaigns.yaml",
        "../data/bas_campaigns.yaml",
        "../data/cresis_campaigns.yaml",
        "../data/kopri_campaigns.yaml",
        "../data/utig_campaigns.yaml",
    ]

    if antarctic:
        region = "ANTARCTIC"
    else:
        region = "ARCTIC"

    connections = {}
    cursors = {}
    connection = sqlite3.connect(database)
    cursor = connection.cursor()

    for campaign_filepath in campaign_filepaths:
        campaigns = yaml.safe_load(open(campaign_filepath, "r"))
        for campaign in campaigns:
            if campaign["region"] != region:
                print(f"Skipping {campaign['campaign']}; not {region}")
                continue
            try:
                cursor.execute(
                    "INSERT OR REPLACE INTO campaigns VALUES(?, ?, ?, ?)",
                    [
                        campaign["campaign"],
                        campaign["institution"],
                        campaign["data_citation"],
                        campaign["science_citation"],
                    ],
                )
            except KeyError as ex:
                msg = f"Invalid input file. Offending campaign: \n {campaign} /n"
                print(msg)
                raise ex
            except sqlite3.InterfaceError as ex:
                msg = f"sqlite3.InterfaceError. Offending campaign: \n {campaign} \n type(data_citation) = {type(campaign['data_citation'])}"
                print(msg)
                raise ex

            connection.commit()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--antarctic", action="store_true")
    parser.add_argument("--arctic", action="store_true")
    parser.add_argument(
        "index",
        help="Geopackage database to update with metadata about campaigns and granules",
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

    main(antarctic, args.index)
