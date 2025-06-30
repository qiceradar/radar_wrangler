#! /usr/bin/env python3
"""
Download the "best" version for each line from data.cresis.ku.edu
# TODO: Consider downloading _all_ versions, and making them available?

This is the most complete set of data collected by CReSIS, but it doesn't
have good metadata for who actually owns the data.
"""


import os
import pathlib
import pickle
import re
import sqlite3
import subprocess
from typing import Dict

import requests
from bs4 import BeautifulSoup


def reindex_cresis(index_filepath: str, partial: bool):
    print("Reindexing Cresis ")
    cresis_url = "https://data.cresis.ku.edu/data/rds"
    reqs = requests.get(cresis_url)
    soup = BeautifulSoup(reqs.text, "html.parser")

    # Each campaign seems to have two links, but we only want one.
    campaigns = set()
    for link in soup.find_all("a"):
        href = link.get("href")
        try:
            int(href[0:4])  # valid campaign names start with YYYY.
        except Exception:
            continue
        campaign = href.strip("/")
        campaigns.add(campaign)

    campaigns = list(campaigns)
    campaigns.sort()
    print("All Campaigns: \n ", "\n".join(campaigns))

    if partial:
        cresis_datafiles = pickle.load(open(index_filepath, "rb"))
    else:
        cresis_datafiles = {"ANTARCTIC": {}, "ARCTIC": {}}

    for campaign in campaigns:
        print()
        print(campaign)
        if "Antarctica" in campaign:
            region = "ANTARCTIC"
        else:
            region = "ARCTIC"
        if campaign in cresis_datafiles[region]:
            continue

        campaign_url = "{}/{}".format(cresis_url, campaign)
        reqs = requests.get(campaign_url)
        soup = BeautifulSoup(reqs.text, "html.parser")
        dirs = [link.get("href").strip("/") for link in soup.find_all("a")]
        # From their README: "The standard L1B files are, in order of increasing quality
        # CSARP_qlook, CSARP_csarpcombined, CSARP_standard, and CSARP_mvdr directories.
        product_priorities = [
            "CSARP_mvdr",
            "CSARP_standard",
            "CSARP_csarp-combined",
            "CSARP_qlook",
        ]
        product = None
        for pp in product_priorities:
            if pp in dirs:
                product = pp
                break
        print("Product: {}".format(product))

        product_url = "{}/{}".format(campaign_url, product)
        reqs = requests.get(product_url)
        soup = BeautifulSoup(reqs.text, "html.parser")
        segments = set()
        for link in soup.find_all("a"):
            href = link.get("href").strip("/")
            try:
                date, seg = map(int, href.split("_"))
                segments.add(href)
            except Exception:
                continue

        segments = list(segments)
        segments.sort()

        product_datafiles = {}
        for segment in segments:
            segment_url = "{}/{}".format(product_url, segment)
            reqs = requests.get(segment_url)
            soup = BeautifulSoup(reqs.text, "html.parser")
            files = set()
            combined_regex = "Data_[0-9]{8}_[0-9]{2}_[0-9]{3}.mat"
            for link in soup.find_all("a"):
                href = link.get("href").strip("/")
                if re.match(combined_regex, href) is not None:
                    files.add(href)
            files = list(files)
            files.sort()

            product_datafiles[segment] = {
                file: "{}/{}".format(segment_url, file) for file in files
            }

        # In order to be compatible with the partial-reindex hack / have
        # the ability to restart the script, don't create the campaign key
        # until we're ready to fill it in
        cresis_datafiles[region][campaign] = {}
        cresis_datafiles[region][campaign][product] = product_datafiles
        # Cache progress, since this is so slow
        with open(index_filepath, "wb") as fp:
            pickle.dump(cresis_datafiles, fp)

    return cresis_datafiles


def download_cresis(
    data_dir: str, datafiles: Dict, antarctic_index: str, arctic_index: str
):
    """
    Download all CReSIS data from the KU servers.
    """

    # First, add all campaigns to the geopackage
    institution = "CRESIS"
    connections = {}
    cursors = {}
    connections["ANTARCTIC"] = sqlite3.connect(antarctic_index)
    connections["ARCTIC"] = sqlite3.connect(arctic_index)
    for region in ["ANTARCTIC", "ARCTIC"]:
        cursors[region] = connections[region].cursor()
        cursors[region].execute("PRAGMA foreign_keys = ON")

    for region, campaigns in datafiles.items():
        print(region)
        # if region == "ARCTIC":
        #     continue
        for campaign, products in campaigns.items():
            print(campaign)
            for product, segments in products.items():
                print(".. {}".format(product))
                for segment, frames in segments.items():
                    print(".... {}".format(segment))
                    dest_dir = "{}/{}/CRESIS/{}/{}/{}".format(
                        data_dir, region, campaign, product, segment
                    )
                    try:
                        pp = pathlib.Path(dest_dir)
                        pp.mkdir(parents=True, exist_ok=True)
                    except FileExistsError:
                        raise Exception("Could not create {}.".format(dest_dir))
                        continue

                    for frame, data_url in frames.items():
                        filename = data_url.split("/")[-1]
                        dest_filepath = os.path.join(dest_dir, filename)
                        rel_filepath = os.path.join(
                            region, institution, campaign, product, segment, filename
                        )

                        if os.path.exists(dest_filepath):
                            filesize = os.path.getsize(dest_filepath)
                            print(
                                f"Skipping {filename}: file already exists with size {filesize}"
                            )
                        else:
                            print(f"Downloading {dest_filepath}")
                            wget_cmd = 'wget -c --directory-prefix="{}" "{}"'.format(
                                dest_dir, data_url
                            )
                            print(wget_cmd)
                            subprocess.getoutput(wget_cmd)

                        # And, update the database with info about this granule/frame
                        filesize = os.path.getsize(dest_filepath)
                        granule = frame.split(".")[0].split("_")[-1]
                        granule_name = f"{institution}_{campaign}_{segment}_{granule}"
                        data_format = "cresis_mat"
                        download_method = "wget"
                        cursors[region].execute(
                            "INSERT OR REPLACE INTO granules VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            [
                                str(granule_name),
                                institution,
                                campaign,
                                segment,
                                granule,
                                product,
                                data_format,
                                download_method,
                                data_url,
                                str(rel_filepath),
                                str(filesize),
                            ],
                        )
                        connections[region].commit()

    for _region, connection in connections.items():
        connection.close()


def main(data_dir: str, antarctic_index: str, arctic_index: str, reindex: bool, partial: bool):
    index_filepath = "../../data/CRESIS/cresis_datafiles.pkl"
    if not reindex:
        cresis_datafiles = pickle.load(open(index_filepath, "rb"))

    else:
        cresis_datafiles = reindex_cresis(index_filepath, partial)

    download_cresis(data_dir, cresis_datafiles, antarctic_index, arctic_index)


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
    parser.add_argument("--reindex", action="store_true")
    parser.add_argument(
        "--partial",
        help="If reindexing, start from existing index?",
        action="store_true"
    )

    args = parser.parse_args()

    main(args.data_directory, args.antarctic_index, args.arctic_index, args.reindex, args.partial)
