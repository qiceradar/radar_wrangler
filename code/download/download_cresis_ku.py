#! /usr/bin/env python3
"""
Download the "best" version for each line from data.cresis.ku.edu

This is the most complete set of data collected by CReSIS, but it doesn't
have good metadata for who actually owns the data.
"""


from bs4 import BeautifulSoup
import pathlib
import pickle
import re
import requests
import subprocess
from typing import Dict


def reindex_cresis():
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

    # TODO: Fix this terrible nested dictionary
    cresis_datafiles = {"ANTARCTIC": {}, "ARCTIC": {}}

    for campaign in campaigns:
        print()
        print(campaign)
        if "Antarctica" in campaign:
            region = "ANTARCTIC"
        else:
            region = "ARCTIC"
        cresis_datafiles[region][campaign] = {}

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
        cresis_datafiles[region][campaign][product] = {}

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

            cresis_datafiles[region][campaign][product][segment] = {
                file: "{}/{}".format(segment_url, file) for file in files
            }


def download_cresis(data_dir: str, datafiles: Dict):
    """
    Download all
    """
    for region, campaigns in datafiles.items():
        print(region)
        if region == "ARCTIC":
            continue
        for campaign, products in campaigns.items():
            print(campaign)
            yy = int(campaign[0:4])
            if yy < 2016:
                print("Already downloaded {}; skipping".format(campaign))
                continue
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

                    for _frame, data_url in frames.items():
                        wget_cmd = 'wget -c --directory-prefix="{}" "{}"'.format(
                            dest_dir, data_url
                        )
                        print(wget_cmd)
                        subprocess.getoutput(wget_cmd)
                        # break  # we're just testing right now ... don't grab everything!


def main(data_dir: str, reindex: bool):
    index_filepath = "../../data/CRESIS/cresis_datafiles.pkl"
    if not reindex:
        cresis_datafiles = pickle.load(open(index_filepath, "rb"))

    else:
        cresis_datafiles = reindex_cresis()
        with open(index_filepath, "rb") as fp:
            pickle.dump(cresis_datafiles, fp)

    download_cresis(data_dir, cresis_datafiles)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "data_directory", help="Root directory for all QIceRadar-managed radargrams."
    )
    parser.add_argument("--reindex", action="store_true")
    args = parser.parse_args()
    main(args.data_directory, args.reindex)
