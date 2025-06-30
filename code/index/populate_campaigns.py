#! /usr/bin/env python3
"""
We manually maintain YAML files specifying the requested data and
science citations for each campaign.

Rerun this script to update the index when any of these files are
changed.
"""

import sqlite3
import yaml


def main(antarctic_index, arctic_index):
    campaign_filepaths = [
        "../../data/awi_campaigns.yaml",
        "../../data/bas_campaigns.yaml",
        "../../data/cresis_campaigns.yaml",
        "../../data/utig_campaigns.yaml"
    ]

    connections = {}
    cursors = {}
    connections["ANTARCTIC"] = sqlite3.connect(antarctic_index)
    connections["ARCTIC"] = sqlite3.connect(arctic_index)
    for region in ["ANTARCTIC", "ARCTIC"]:
        cursors[region] = connections[region].cursor()
        cursors[region].execute("PRAGMA foreign_keys = ON")

    for campaign_filepath in campaign_filepaths:
        campaigns = yaml.safe_load(open(campaign_filepath, 'r'))
        for campaign in campaigns:
            region = campaign["region"]
            try:
                cursors[region].execute(
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

            connections[region].commit()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "antarctic_index",
        help="Geopackage database to update with metadata about Antarctic campaigns and granules",
    )
    parser.add_argument(
        "arctic_index",
        help="Geopackage database to update with metadata about Arctic campaigns and granules",
    )

    args = parser.parse_args()

    main(args.antarctic_index, args.arctic_index)
