#! /usr/bin/env python3
"""
At NSIDC, CReSIS's data is at:
* MCoRDS: https://n5eil01u.ecs.nsidc.org/ICEBRIDGE/IRMCR1B.002/

The directory structure is
* ICRMCR1B.002/
  * yyyy.mm.dd/
    * {instrument}_{yyyy}{doy}_{flight}_{granule}.nc
    * Alongside a .xml, _Echogram.jpg, _Echogram_Picks.jpg, _Map.jpg

(This script is a copy-paste from generate_utig_nsidc_index; if I ever
do a 3rd one, it'll be time to pull out some of these utilities!)
"""

import csv
import netrc  # Used to parse authentication token from ~/.netrc
import os
import pathlib
import re

import requests
from bs4 import BeautifulSoup


def credentials_from_netrc():
    hostname = "urs.earthdata.nasa.gov"
    try:
        nn = netrc.netrc()
        username, _, token = nn.authenticators(hostname)
        if username != "token":
            msg = "This function only supports logging in via authentication tokens."
            print(msg)
            raise Exception(msg)
    except FileNotFoundError as ex:
        print("Can't authenticate -- .netrc file not found")
        raise (ex)

    return token


def main(index_filepath):
    print("Saving index to: {}".format(index_filepath))
    # Crawling the NSIDC website finding URLs is terribly slow, so we
    # need to be able to resume.
    previous_csv = None

    # Check previously-indexed URLs
    previous_urls = set()
    if os.path.isfile(index_filepath):
        print("loading index!")

        with open(index_filepath) as fp:
            csv_reader = csv.DictReader(fp)
            previous_csv = []
            for dd in csv_reader:
                url = dd["url"]
                date_url = "/".join(url.split("/")[:-1])
                previous_urls.add(date_url)
                previous_csv.append(
                    f'{dd["institution"]},{dd["flight"]},{dd["granule"]},{dd["url"]}'
                )
        previous_urls = list(previous_urls)
        previous_urls.sort()
        print(previous_urls)

    mcords_url = "https://n5eil01u.ecs.nsidc.org/ICEBRIDGE/IRMCR1B.002"
    # Extract information from the filename
    # Example: 	IRMCR1B_20121013_01_001.nc
    # TODO: update this for CReSIS filenames!

    regex = "(?P<instrument>[0-9a-zA-Z]+)_(?P<flight_str>[0-9]{8}_[0-9]{2})_(?P<granule>[0-9]{3}).nc"
    token = credentials_from_netrc()
    with requests.sessions.Session() as session, open(index_filepath, "w") as fp:
        fp.write("institution,flight,granule,url\n")
        if previous_csv is not None:
            fp.writelines(previous_csv)

        session.headers.update({"Authorization": "Bearer {0}".format(token)})
        for instrument_url in [mcords_url]:
            print("*************")
            print("Checking {}".format(instrument_url))
            instrument_resp = session.get(instrument_url)
            instrument_soup = BeautifulSoup(instrument_resp.text, "html.parser")

            # Data is organized into yyyy.mm.dd folders
            flight_days = {
                link.get("href").strip("/")
                for link in instrument_soup.find_all("a")
                if re.match("[0-9]{4}.[0-9]{2}.[0-9]{2}", link.get("href")) is not None
            }
            flight_days = list(flight_days)
            flight_days.sort()
            print(flight_days)
            for flight_day in flight_days:
                print("Listing segments for {}".format(flight_day))
                flight_url = "{}/{}".format(instrument_url, flight_day)
                print(flight_url)
                # This is fine, because we index all netcdfs in a given day at the same time.
                if flight_url in previous_urls:
                    print("Skipping {} -- already scraped".format(flight_day))
                    continue
                try:
                    flight_resp = session.get(flight_url)
                except requests.exceptions.ConnectionError as ex:
                    print(ex)
                    print("...trying again")
                    try:
                        flight_resp = session.get(flight_url)
                    except Exception:
                        err_msg = "WARNING: failed to index {}; re-run script".format(
                            flight_url
                        )
                        print(err_msg)
                        # Go ahead and continue because I won't be constantly monitoring the script.
                        continue

                flight_soup = BeautifulSoup(flight_resp.text, "html.parser")
                segment_files = {
                    link.get("href")
                    for link in flight_soup.find_all("a")
                    if link.get("href").endswith("nc")
                }
                segment_files = list(segment_files)
                segment_files.sort()
                print(segment_files)
                for segment_file in segment_files:
                    mm = re.match(regex, segment_file)
                    instrument, flight_str, granule = mm.groups()

                    segment_url = "{}/{}".format(flight_url, segment_file)
                    fp.write(f"NASA,{flight_str},{granule},{segment_url}\n")


if __name__ == "__main__":
    index_dir = "../../data/NASA"
    try:
        pp = pathlib.Path(index_dir)
        pp.mkdir(parents=True, exist_ok=True)
    except Exception as ex:
        print("Could not create {}".format(index_dir))
        print(ex)
        raise (ex)
    # NB: This creates a file including both arctic and antarctic data!
    # The download step will need to determine which region to put data in.
    index_filepath = os.path.join(index_dir, "cresis_nsidc_index.csv")
    main(index_filepath)
