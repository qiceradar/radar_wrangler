#! /usr/bin/env python3
"""
Create index of PST <-> download info for
campaigns stored at the AAD.

So far, this is:
* OIA
* EAGLE

HOWEVER, they seem to be in the same bucket.
So, sorting them out may be a bit annoying.

They require credentials, which expire every 14 days.
Worse, you are given a separate one for each dataset.
I assume that they'll be set in the environment, as
{EAGLE,OIA}_ACCESS_KEY
{EAGLE,OIA}_SECRET_KEY
These must be obtained from:
EAGLE: https://data.aad.gov.au/dataset/4780/download
OIA: https://data.aad.gov.au/dataset/5256/download
(4346 is the code for the overall project that includes both OIA and EAGLE)
"""

import os
import pathlib
import re
import sqlite3
import subprocess
import tempfile
from dataclasses import dataclass

# This required me to run
# python3 -m pip install boto3
# In QGIS's python install, I _also_ had to manually upgrade urllib3 to 1.26.20
# /path/to/QGIS/binaries/pip install urllib3==1.26.20
import boto3

access_keys = {}
access_keys["OIA"] = os.environ['OIA_ACCESS_KEY']
access_keys["EAGLE"] = os.environ['EAGLE_ACCESS_KEY']

secret_keys = {}
secret_keys["OIA"] = os.environ['OIA_SECRET_KEY']
secret_keys["EAGLE"] = os.environ['EAGLE_SECRET_KEY']

# The Dataverse API allows querying for information based on DOI
# This controls which campaigns are procesed; skipping EAGLE
# for now since it has a totally different format.
dois = {}
# dois["EAGLE"] = "doi:10.26179/5bcff4afc287d"
dois["OIA"] = "doi:10.26179/5wkf-7361"


# TODO: This should probably be put into a more general include?
@dataclass
class Granule:
    filename: str
    institution: str
    region: str  # ANTARCTIC or ARCTIC
    campaign: str
    transect: str  # either flight or PST
    granule: str  # represents a number, but the leading zeroes matter
    product: str  # e.g. ER2HI1B, IR1HI1B, KHERA1B, etc.
    # path (including filename) relative to QIceRadar base data directory where data will be saved
    relpath: str
    url: str  # download link


def create_aad_s3_client(campaign: str):
    endpoint_url = "https://transfer.data.aad.gov.au"

    s3_client = boto3.client(
        's3',
        aws_access_key_id=access_keys[campaign],
        aws_secret_access_key=secret_keys[campaign],
        endpoint_url=endpoint_url
    )

    return s3_client


def create_aad_s3_index():
    # First, build the index mapping individual granules to all data about them
    granules = []
    institution = "UTIG"
    region = "ANTARCTIC"

    bucket = "aadc-datasets"

    datasets = {}
    datasets["EAGLE"] = "AAS_4346_EAGLE_ICECAP_LEVEL2_RADAR_DATA/"
    datasets["OIA"] = "AAS_4346_ICECAP_OIA_RADARGRAMS/"

    for campaign, dataset in datasets.items():
        s3_client = create_aad_s3_client(campaign)

        try:
            result = s3_client.list_objects(
                Bucket=bucket,
                Prefix=dataset
            )
        except Exception:
            print("Unable to access AAD S3 bucket. Do you need new credentials?")
            print("These can be obtained from:")
            print("EAGLE: https://data.aad.gov.au/dataset/4780/download")
            print("OIA: https://data.aad.gov.au/dataset/5256/download")
            return None

        # Used to extract PST and granule
        expr = "AAS_4346_ICECAP_OIA_RADARGRAMS/ICECAP_OIA.SR2HI1B/SR2HI1B_(?P<year>[0-9]{4})(?P<doy>[0-9]{3})_(?P<project>[a-zA-Z0-9]*)_(?P<set>[a-zA-Z0-9]*)_(?P<transect>[a-zA-Z0-9]*)_(?P<granule>[0-9]{3}).nc"
        # Used to extract filename
        filename_expr = "AAS_4346_ICECAP_OIA_RADARGRAMS/ICECAP_OIA.SR2HI1B/(?P<filename>.*)"

        for ff in result["Contents"]:
            if not ff["Key"].endswith(".nc"):
                continue
            key = ff["Key"]
            filesize = ff["Size"]
            print(f"file={key} size={filesize}")

            # TODO: This is hacky! Maybe add another field into the database,
            #  rather than re-using the granule_url?
            # (URL is only the right name for some download methods)
            granule_url = key

            # TODO: I think "product" is meant to be pik1/foc1/etc, but
            # for UTIG data, it becomes the NSIDC/AADC product name.
            # I'm not sure why they're different, since I think it's actually
            # the same processing/airplane/instrument as IR2HI1B.
            # Technically, could recover this from the filenames, but it's
            # constant for the whole dataset.
            product = "SR2HI1B"

            m1 = re.match(expr, key)
            transect = "_".join([m1['project'], m1['set'], m1['transect']])
            granule_seq = m1['granule']

            m2 = re.match(filename_expr, key)
            filename = m2['filename']

            granule_relpath = f"{region}/{institution}/{campaign}/{transect}/{filename}"

            granule = Granule(
                filename,
                institution,
                region,
                campaign,
                transect,
                granule_seq,
                product,
                granule_relpath,
                granule_url,
            )
            granules.append(granule)

    return granules


# NB: Need to test this briefly before pointing it at a directory where I've
# already downloaded the data.
def maybe_download_boto3(url: str, dest_filepath: str, campaign: str) -> int:

    s3_client = create_aad_s3_client(campaign)

    filename = pathlib.Path(dest_filepath).name
    if os.path.exists(dest_filepath):
        filesize = os.path.getsize(dest_filepath)
        print(
            "Skipping {}: file already exists with size {}".format(filename, filesize)
        )
    else:
        # Create directory for campaign
        dest_dir = pathlib.Path(dest_filepath).parent
        try:
            pp = pathlib.Path(dest_dir)
            pp.mkdir(parents=True, exist_ok=True)
        except FileExistsError as ex:
            raise Exception(f"Could not create {dest_dir}: {ex}.")
        try:
            # Create a temporary file to avoid having to clean up partial downloads.
            # This may not be ideal if the temporary file is created in a different filesystem than the
            # output file belongs in. (I expect to eventually be downloading data to an external drive/NAS)
            # TODO: create the temporary file in the same directory? or in the RadarData directory?
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                # wget_cmd = ["wget", "--no-clobber", "--quiet", "--output-document", dest_filepath, flight['url']]
                # If saving to a temp file, get rid of --no-clobber, since the file will already have been created.
                s3_client.download_file('aadc-datasets', url, temp_file.name)
                # TODO: for plugin download, replace this with
                #       `shutil.move` for cross-platform compatibility
                move_cmd = ["mv", temp_file.name, dest_filepath]
                subprocess.check_call(move_cmd)
                print("Got {}!".format(filename))
                filesize = os.path.getsize(dest_filepath)

        except subprocess.CalledProcessError as ex:
            print("Failed to download {}: {}".format(filename, ex))

    return filesize


def download_utig_aad(
    qiceradar_dir: str, antarctic_index: str
):
    """
    Ensures that all data has been downloaded to the specified root
    directory, and updates the input index database with url and path info.
    """
    # UTIG data is saved to ANTARCTIC/UTIG/{campaign}/{transect}/{granule}.nc
    granules = create_aad_s3_index()

    connection = sqlite3.connect(antarctic_index)
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")

    # Update the granules table
    data_format = "utig_netcdf"
    # Make sure this format is in the table
    cursor.execute(f"INSERT OR REPLACE INTO data_formats VALUES('{data_format}')")
    # TODO: rename this to something more accurate? What I really  mean
    #   is something like "URL, no password, can use simple wget or requests.get"
    download_method = "aad_s3"

    for granule in granules:
        if granule.region != "ANTARCTIC":
            msg = f"Script only supports ANTARCTIC data for now! granule={granule}"
            raise Exception(msg)

        dest_filepath = f"{qiceradar_dir}/{granule.relpath}"
        filesize = maybe_download_boto3(granule.url, dest_filepath, granule.campaign)

        # label displayed by Identify Features in QGIS
        granule_name = pathlib.Path(
            f"{granule.institution}_{granule.campaign}_{granule.transect}_{granule.granule}"
        ).with_suffix("")
        cursor.execute(
            "INSERT OR REPLACE INTO granules VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                str(granule_name),
                granule.institution,
                granule.campaign,
                granule.transect,
                granule.granule,
                granule.product,
                data_format,
                download_method,
                granule.url,
                granule.relpath,
                str(filesize),
            ],
        )
        connection.commit()
    connection.close()


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
    args = parser.parse_args()
    download_utig_aad(
        args.data_directory, args.antarctic_index
    )
