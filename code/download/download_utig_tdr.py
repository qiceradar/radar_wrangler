#! /usr/bin/env python3
"""
Create index of PST <-> persistent URL for
campaigns stored at the Texas Data Repository.

So far, this is:
* COLDEX, seasons 1 & 2
* GIMBLE
"""

import json
import os
import pathlib
import sqlite3
import subprocess
import tempfile
from dataclasses import dataclass
from typing import List

import requests

# The Dataverse API allows querying for information based on DOI
dois = {}
dois["GIMBLE"] = "doi:10.18738/T8/BMXUHX"
dois["COLDEX_2023"] = "doi:10.18738/T8/XPMLCC"
dois["COLDEX_2024"] = "doi:10.18738/T8/FV6VNT"

# to request info about the datasets, append DOI to this URL
dataverse_url = "https://dataverse.tdl.org/api/datasets/:persistentId?persistentId="
# Append individual file ID to this URL to download data
download_url = "https://dataverse.tdl.org/api/access/datafile/"

data_citations = {}
data_citations[
    "GIMBLE"
] = "Young, Duncan A.; Blankenship, Donald D.; Greenbaum, Jamin S.; Quartini, Enrica; Muldoon, Gail L; Habbal, Feras; Lindzey, Laura E.; Greene, Chad A.; Powell, Evelyn M.; Ng, Gregory C.; Richter, Thomas G.; Echeverry, Gonzalo; Kempf, Scott, 2024, Geophysical Investigations of Marie Byrd Land Lithospheric Evolution (GIMBLE) Airborne VHF Radar Transects: 2012/2013 and 2014/2015, https://doi.org/10.18738/T8/BMXUHX, Texas Data Repository, V1"
data_citations[
    "COLDEX_2023"
] = "Young, Duncan; Greenbaum, Jamin S.; Kerr, Megan E.; Singh, Shivangini; Chan, Kristian; Buhl, Dillon P.; Ng, Gregory C.; Kempf, Scott D.; Echeverry, Gonzalo; Blankenship, Donald D., 2024, COLDEX Unfocused Airborne VHF Radar Transects: 2022-2023 South Pole Field Season, https://doi.org/10.18738/T8/XPMLCC, Texas Data Repository, V1"
data_citations[
    "COLDEX_2024"
] = "Young, Duncan; Singh, Shivangini; Kerr, Megan E.; Ng, Gregory; Buhl, Dillon P.; Blankenship, Donald D, 2024, COLDEX Unfocused Airborne VHF Radar Transects: 2023-2024 South Pole Field Season, https://doi.org/10.18738/T8/FV6VNT, Texas Data Repository, V1"

# Really, maybe this should be "related"? (Some groups use it for processing details, other for a scientific paper)
science_citations = {}
science_citations[
    "GIMBLE"
] = "Quartini, E., Blankenship, D. D., and Young, D. A., 2021, Active subglacial volcanism in West Antarctica, Geological Society Of London, Special Publication, 55, 785-803, https://dx.doi.org/10.1144/M55-2019-3 doi: 10.1144/M55-2019-3"
science_citations[
    "COLDEX_2023"
] = "Peters, M. E., Blankenship, D. D., and Morse, D. L., 2005, Analysis techniques for coherent airborne radar sounding: Application to West Antarctic ice streams, Journal Of Geophysical Research, 110, B06303, 10.1029/2004JB003222 doi: 0.1029/2004JB003222"
science_citations[
    "COLDEX_2024"
] = "Peters, M. E., Blankenship, D. D., and Morse, D. L., 2005, Analysis techniques for coherent airborne radar sounding: Application to West Antarctic ice streams, Journal Of Geophysical Research, 110, B06303, 10.1029/2004JB003222 doi: 10.1029/2004JB003222"


@dataclass
class Granule:
    filename: str
    institution: str
    region: str  # ANTARCTIC or ARCTIC
    campaign: str
    transect: str  # either flight or PST
    # path (including filename) relative to QIceRadar base data directory where data will be saved
    relpath: str
    url: str  # download link


def create_dataverse_index():
    # First, build the index mapping individual granules to all data about them
    granules = []
    institution = "UTIG"
    region = "ANTARCTIC"
    for campaign, doi in dois.items():
        query_url = f"{dataverse_url}{doi}"
        print(f"querrying URL: {query_url}")
        resp = requests.get(query_url)
        if resp.status_code != 200:
            msg = f"Could not access data API! status = {resp.status_code}"
            raise Exception(msg)
        parsed = json.loads(resp.text)
        files = parsed["data"]["latestVersion"]["files"]
        for ff in files:
            filename = ff["dataFile"]["filename"]
            if ff["dataFile"]["contentType"] != "application/x-netcdf":
                if filename.endswith(".nc"):
                    msg = f"Bad assumption! file {filename} not of type application/x-netcdf"
                    raise Exception(msg)
                continue
            fileid = ff["dataFile"]["id"]
            granule_url = f"{download_url}{fileid}"
            # For these transects, it appears that Duncan's naming convention is
            # {product}_{yyyydoy}_{p}_{s}_{t}_{granule}.mc
            # Sort them in to PSTs in case we want to support additional products later.
            transect = "_".join(filename.split("_")[-4:-1])
            granule_relpath = f"{region}/{institution}/{campaign}/{transect}/{filename}"
            granule = Granule(
                filename,
                institution,
                region,
                campaign,
                transect,
                granule_relpath,
                granule_url,
            )
            granules.append(granule)
    return granules


def update_qiceradar_antarctic_index_campaigns(
    granules: List[Granule], antarctic_index: str
):
    """
    Update the database file to include metadata for campaigns.
    (Can't update granules because that wants filesize info, which
    is coupled with the download step.)
    """
    connection = sqlite3.connect(antarctic_index)
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    institution = "UTIG"

    # Update the campaigns table
    for campaign in dois.keys():
        try:
            science_citation = science_citations[campaign]
        except KeyError:
            science_citation = ""
        cursor.execute(
            "INSERT OR REPLACE INTO campaigns VALUES(?, ?, ?, ?)",
            [
                campaign,
                institution,
                data_citations[campaign],
                science_citation,
            ],
        )
        connection.commit()
    connection.close


def maybe_download_wget(url: str, dest_filepath: str) -> int:
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
                wget_cmd = [
                    "wget",
                    "--quiet",
                    "--output-document",
                    temp_file.name,
                    url,
                ]
                print(f"{filename}: {wget_cmd}")
                subprocess.check_call(wget_cmd)
                # TODO: for plugin download, replace this with
                #       `shutil.move` for cross-platform compatibility
                move_cmd = ["mv", temp_file.name, dest_filepath]
                subprocess.check_call(move_cmd)
                print("Got {}!".format(filename))
                filesize = os.path.getsize(dest_filepath)

        except subprocess.CalledProcessError as ex:
            print("Failed to download {}: {}".format(filename, ex))

    return filesize


def download_utig_dataverse(
    qiceradar_dir: str, antarctic_index: str, arctic_index: str
):
    """
    Ensures that all data has been downloaded to the specified root
    directory, and updates the input index database with url and path info.
    """
    # UTIG data is saved to ANTARCTIC/UTIG/{campaign}/{transect}/{granule}.nc
    granules = create_dataverse_index()
    update_qiceradar_antarctic_index_campaigns(granules, antarctic_index)

    connection = sqlite3.connect(antarctic_index)
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")

    # Update the granules table
    data_format = "utig_netcdf"
    # Make sure this format is in the table
    cursor.execute(f"INSERT OR REPLACE INTO data_formats VALUES('{data_format}')")
    # TODO: rename this to something more accurate? What I really  mean
    #   is something like "URL, no password, can use simple wget or requests.get"
    download_method = "wget"

    for granule in granules:
        if granule.region != "ANTARCTIC":
            msg = f"Script only supports ANTARCTIC data for now! granule={granule}"
            raise Exception(msg)

        dest_filepath = f"{qiceradar_dir}/{granule.relpath}"
        filesize = maybe_download_wget(granule.url, dest_filepath)

        # label displayed by Identify Features in QGIS
        granule_name = pathlib.Path(
            f"{granule.institution}_{granule.campaign}_{granule.filename}"
        ).with_suffix("")
        cursor.execute(
            "INSERT OR REPLACE INTO granules VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                str(granule_name),
                granule.institution,
                granule.campaign,
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
    parser.add_argument(
        "arctic_index",
        help="Geopackage database to update with metadata about Arctic campaigns and granules",
    )
    args = parser.parse_args()
    download_utig_dataverse(
        args.data_directory, args.antarctic_index, args.arctic_index
    )