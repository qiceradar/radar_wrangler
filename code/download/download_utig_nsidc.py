#! /usr/bin/env python3
"""
Download UTIG's files from NSIDC, as specified in the
input CSV.

Since every UTIG datacenter has a different directory organization,
I've decided to organize UTIG radargrams as:
[region]/UTIG/[campaign]/[PST]/[filename].nc

This script creates that directory structure and downloads radargrams
into the correct place.
---------------------------------------------------------
Modified from one of NSIDC's generated download scripts:
---------------------------------------------------------
# NSIDC Data Download Script
#
# Copyright (c) 2022 Regents of the University of Colorado
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
"""

import pathlib
import os
import csv
import base64
import math
import netrc
import os.path
import sys
import time
from getpass import getpass

from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPCookieProcessor
from urllib.error import HTTPError, URLError


def get_username():
    username = ""
    do_input = input
    username = do_input("Earthdata username (or press Return to use a bearer token): ")
    return username


def get_password():
    password = ""
    while not password:
        password = getpass("password: ")
    return password


def get_token():
    token = ""
    while not token:
        token = getpass("bearer token: ")
    return token


def get_login_credentials():
    """Get user credentials from .netrc or prompt for input."""
    credentials = None
    token = None
    urs_url = "https://urs.earthdata.nasa.gov"

    try:
        info = netrc.netrc()
        username, _, password = info.authenticators(urlparse(urs_url).hostname)
        if username == "token":
            token = password
        else:
            credentials = "{0}:{1}".format(username, password)
            credentials = base64.b64encode(credentials.encode("ascii")).decode("ascii")
    except Exception:
        username = None
        password = None

    if not username:
        username = get_username()
        if len(username):
            password = get_password()
            credentials = "{0}:{1}".format(username, password)
            credentials = base64.b64encode(credentials.encode("ascii")).decode("ascii")
        else:
            token = get_token()

    return credentials, token


def get_speed(time_elapsed, chunk_size):
    if time_elapsed <= 0:
        return ""
    speed = chunk_size / time_elapsed
    if speed <= 0:
        speed = 1
    size_name = ("", "k", "M", "G", "T", "P", "E", "Z", "Y")
    i = int(math.floor(math.log(speed, 1000)))
    p = math.pow(1000, i)
    return "{0:.1f}{1}B/s".format(speed / p, size_name[i])


def output_progress(count, total, status="", bar_len=60):
    if total <= 0:
        return
    fraction = min(max(count / float(total), 0), 1)
    filled_len = int(round(bar_len * fraction))
    percents = int(round(100.0 * fraction))
    bar = "=" * filled_len + " " * (bar_len - filled_len)
    fmt = "  [{0}] {1:3d}%  {2}   ".format(bar, percents, status)
    print("\b" * (len(fmt) + 4), end="")  # clears the line
    sys.stdout.write(fmt)
    sys.stdout.flush()


def cmr_read_in_chunks(file_object, chunk_size=1024 * 1024):
    """Read a file in chunks using a generator. Default chunk size: 1Mb."""
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        yield data


def get_login_response(url, credentials, token):
    opener = build_opener(HTTPCookieProcessor())

    req = Request(url)
    if token:
        req.add_header("Authorization", "Bearer {0}".format(token))
    elif credentials:
        try:
            response = opener.open(req)
            # We have a redirect URL - try again with authorization.
            url = response.url
        except HTTPError:
            # No redirect - just try again with authorization.
            pass
        except Exception as e:
            print("Error{0}: {1}".format(type(e), str(e)))
            sys.exit(1)

        req = Request(url)
        req.add_header("Authorization", "Basic {0}".format(credentials))

    try:
        response = opener.open(req)
    except HTTPError as e:
        err = "HTTP error {0}, {1}".format(e.code, e.reason)
        if "Unauthorized" in e.reason:
            if token:
                err += ": Check your bearer token"
            else:
                err += ": Check your username and password"
        print(err)
        sys.exit(1)
    except Exception as e:
        print("Error{0}: {1}".format(type(e), str(e)))
        sys.exit(1)

    return response


def nsidc_download(dest_dir, url):
    """
    Download file at URL into dest_dir.
    """
    print("Downloading {} to {}".format(url, dest_dir))
    force = False  # Force re-download
    quiet = False  # Suppress debug messages
    credentials = None
    token = None

    if not credentials and not token:
        p = urlparse(url)
        if p.scheme == "https":
            credentials, token = get_login_credentials()

    filename = url.split("/")[-1]
    dest_filepath = os.path.join(dest_dir, filename)

    try:
        response = get_login_response(url, credentials, token)
        length = int(response.headers["content-length"])
        try:
            if not force and length == os.path.getsize(dest_filepath):
                if not quiet:
                    print("  File exists, skipping")
                    return
        except OSError:
            pass
        count = 0
        chunk_size = min(max(length, 1), 1024 * 1024)
        max_chunks = int(math.ceil(length / chunk_size))
        time_initial = time.time()
        with open(dest_filepath, "wb") as out_file:
            for data in cmr_read_in_chunks(response, chunk_size=chunk_size):
                out_file.write(data)
                if not quiet:
                    count = count + 1
                    time_elapsed = time.time() - time_initial
                    download_speed = get_speed(time_elapsed, count * chunk_size)
                    output_progress(count, max_chunks, status=download_speed)
        if not quiet:
            print()
    except HTTPError as e:
        print("HTTP error {0}, {1}".format(e.code, e.reason))
    except URLError as e:
        print("URL error: {0}".format(e.reason))
    except IOError:
        raise


def main(url_filepath, data_dir):
    print("Loading metadata from {}".format(url_filepath))
    with open(url_filepath) as fp:
        csv_reader = csv.DictReader(fp)
        # TODO: These should wind up in the csv file as well.
        region = "ANTARCTIC"
        campaign = "ICECAP"
        for row in csv_reader:
            # fields are institution,flight,segment,granule,url
            print(row)
            institution = row["institution"]
            pst = row["segment"]
            pst_dir = os.path.join(data_dir, region, institution, campaign, pst)
            if not os.path.isdir(pst_dir):
                try:
                    pp = pathlib.Path(pst_dir)
                    pp.mkdir(parents=True, exist_ok=True)
                except Exception as ex:
                    print("Could not create {}".format(pst_dir))
                    raise (ex)
            url = row["url"]
            nsidc_download(pst_dir, url)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("url_list", help="CSV file specifying URLs for all radargrams")
    parser.add_argument(
        "data_directory", help="Root directory for all QIceRadar-managed radargrams."
    )
    args = parser.parse_args()
    main(args.url_list, args.data_directory)
