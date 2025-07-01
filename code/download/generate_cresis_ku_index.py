#! /usr/bin/env python3
"""
Generate a CSV file with information about every granule available on CReSIS's server.

(In retrospect, maybe I should have looked into their FTP server?)
"""

import pickle
import re

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
        # cresis_datafiles = read_granule_list(index_filepath)
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
        # write_granule_list(index_filepath)
        with open(index_filepath, "wb") as fp:
            pickle.dump(cresis_datafiles, fp)

    return cresis_datafiles


def main(partial: bool):
    index_filepath = "../../data/CRESIS/cresis_datafiles.pkl"

    reindex_cresis(index_filepath, partial)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--partial",
        help="If reindexing, start from existing index?",
        action="store_true"
    )

    args = parser.parse_args()

    main(args.partial)
