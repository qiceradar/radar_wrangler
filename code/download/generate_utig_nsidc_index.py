#! /usr/bin/env python3
"""
In the future, I want data providers to be able to add one-off profiles
by simply editing a CSV file with the appropriate fields.

So, to experiment with that workflow, I'm dividign the UTIG download
into creating the index and then downloading it.

At NSIDC, UTIG's data is at:
* hicars1: https://n5eil01u.ecs.nsidc.org/ICEBRIDGE/IR1HI1B.001/
* hicars2: https://n5eil01u.ecs.nsidc.org/ICEBRIDGE/IR2HI1B.001/

The directory structure is
* IR1HI1B.001 / IR2HI1B.001
  * yyyy.mm.dd/
    * {instrument}_{yyyy}{doy}_{project}_{set}_{transect}_{granule}.nc

TODO: See if the authentication used in download_utig_nsidc is faster
in this script. As is, it is shockingly slow.
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
    # By checking previous URLs, we'll capture both data product and flight/day
    previous_urls = set()
    if os.path.isfile(index_filepath):
        print("loading index!")

        with open(index_filepath) as fp:
            csv_reader = csv.DictReader(fp)
            previous_csv = []
            for dd in csv_reader:
                institution = dd["institution"]
                flight = dd["flight"]
                url = dd["url"]
                date_url = "/".join(url.split("/")[:-1])
                previous_urls.add(date_url)
                previous_csv.append(
                    "{},{},{},{},{}\n".format(
                        institution, flight, dd["segment"], dd["granule"], url
                    )
                )
        previous_urls = list(previous_urls)
        previous_urls.sort()
        print(previous_urls)

    hicars1_url = "https://n5eil01u.ecs.nsidc.org/ICEBRIDGE/IR1HI1B.001"
    hicars2_url = "https://n5eil01u.ecs.nsidc.org/ICEBRIDGE/IR2HI1B.001"
    # Extract information from the filename
    regex = "(?P<instrument>[0-9a-zA-Z]+)_(?P<year>[0-9]{4})(?P<doy>[0-9]{3})_(?P<project>[0-9a-zA-Z]+)_(?P<set>[0-9a-zA-Z]+)_(?P<transect>[0-9a-zA-Z]*)_(?P<granule>[0-9]*).nc"
    token = credentials_from_netrc()
    with requests.sessions.Session() as session, open(index_filepath, "w") as fp:
        fp.write("institution,flight,segment,granule,url\n")
        if previous_csv is not None:
            fp.writelines(previous_csv)

        session.headers.update({"Authorization": "Bearer {0}".format(token)})
        for instrument_url in [hicars1_url, hicars2_url]:
            print("*************")
            print("Checking {}".format(instrument_url))
            instrument_resp = session.get(instrument_url)
            instrument_soup = BeautifulSoup(instrument_resp.text, "html.parser")

            # Each link shows up a few times
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
                    _, _, _, project, ss, transect, granule = mm.groups()
                    pst = "_".join((project, ss, transect))

                    segment_url = "{}/{}".format(flight_url, segment_file)
                    fp.write(
                        "{},{},{},{},{}\n".format(
                            "UTIG", flight_day, pst, granule, segment_url
                        )
                    )


if __name__ == "__main__":
    index_dir = "../../data/UTIG"
    try:
        pp = pathlib.Path(index_dir)
        pp.mkdir(parents=True, exist_ok=True)
    except Exception as ex:
        print("Could not create {}".format(index_dir))
        print(ex)
        raise (ex)
    index_filepath = os.path.join(index_dir, "utig_nsidc_index.csv")
    main(index_filepath)
