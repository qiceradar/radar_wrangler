#! /usr/bin/env python3
"""
Generate a CSV file with information about every granule available on CReSIS's server.

(In retrospect, maybe I should have looked into their FTP server?)
"""

import os
import re

import requests
from bs4 import BeautifulSoup

from index_utils import Granule, read_granule_list, write_granule_list


def reindex_cresis(index_filepath: str, partial: bool) -> None:
    print("Reindexing Cresis ")
    cresis_url = "https://data.cresis.ku.edu/data/rds"
    reqs = requests.get(cresis_url)
    soup = BeautifulSoup(reqs.text, "html.parser")

    if partial:
        cresis_granules = read_granule_list(index_filepath)
    else:
        cresis_granules = []

    loaded_campaigns = {granule.campaign for granule in cresis_granules}
    print(f"Already processed campaigns: {loaded_campaigns}")

    institution = "CRESIS"
    download_method = "wget"
    data_format = "cresis_mat"

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

    for campaign in campaigns:
        print()
        print(campaign)

        if campaign in loaded_campaigns:
            continue

        if "Antarctica" in campaign:
            region = "ANTARCTIC"
        else:
            region = "ARCTIC"

        campaign_url = "{}/{}".format(cresis_url, campaign)
        reqs = requests.get(campaign_url)
        soup = BeautifulSoup(reqs.text, "html.parser")
        product_dirs = [link.get("href").strip("/") for link in soup.find_all("a")]
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
            if pp in product_dirs:
                product = pp
                break
        print("Product: {}".format(product))
        if product is None:
            print(f"Could not find data product for campaign {campaign}. Available directories = {product_dirs}")
            continue

        product_url = "{}/{}".format(campaign_url, product)
        reqs = requests.get(product_url)
        soup = BeautifulSoup(reqs.text, "html.parser")
        segments = set()
        for link in soup.find_all("a"):
            href = link.get("href").strip("/")
            try:
                flight_date, flight_seg = map(int, href.split("_"))
                segments.add(href)
            except Exception:
                continue

        segments = list(segments)
        segments.sort()

        for segment in segments:  # e.g. "20041118_01"
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

            for filename in files:  # e.g. "Data_19930623_01_001.mat"
                granule_url = "{}/{}".format(segment_url, filename)

                # represents a number, but the leading zeroes matter
                granule_num = filename.split(".")[0].split("_")[-1]

                # Must be unique; primary key in database
                granule_name = f"{institution}_{campaign}_{segment}_{granule_num}"

                relative_filepath = os.path.join(
                    region, institution, campaign, product, segment, filename
                )

                granule = Granule(
                    granule_name,
                    region,
                    institution,
                    campaign,
                    segment,
                    granule_num,
                    product,  # data_product
                    data_format,
                    relative_filepath,
                    granule_url,  # download_url
                    download_method,
                )
                cresis_granules.append(granule)

        loaded_campaigns.add(campaign)
        # Cache progress, since this is so slow
        write_granule_list(index_filepath, cresis_granules)


def main(partial: bool):
    index_filepath = "../../data/cresis_granules.csv"

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
