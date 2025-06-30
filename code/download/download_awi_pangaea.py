#! /usr/bin/env python3

"""
On first run, this script created a bunch of 12kB files.
However, with no modifications, it then seemed to work fine.
So ... there's some error that I'm not catching.
"""

import os
import os.path
import pathlib
import re
import sqlite3
import subprocess
import tempfile

# mapping from campaign to dataset
datasets = {}
datasets["JuRaS_2018"] = 962670
datasets["CHIRP_2019"] = 963264


def download_awi(root_dir: str, antarctic_index: str, campaign: str) -> None:
    dataset = datasets[campaign]
    root_url = f"https://download.pangaea.de/dataset/{dataset}/files/"

    connection = sqlite3.connect(antarctic_index)
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")

    region = "ANTARCTIC"
    institution = "AWI"
    data_format = "awi_netcdf"
    download_method = "curl"
    # QUESTION: Should I break these down into flights, separate
    #   from how they were downloaded?
    #   (That would match how UTIG/CReSIS organize their granules.)
    dest_dir = os.path.join(root_dir, region, institution, campaign)

    expr = "Data_(?P<flight>[0-9]{8}_[0-9]{2})_(?P<granule>[0-9]{3})_standard.nc"

    try:
        pp = pathlib.Path(dest_dir)
        pp.mkdir(parents=True, exist_ok=True)
    except FileExistsError as ex:
        print(ex)
        raise Exception(f"Could not create {dest_dir}; already exists")

    for ff in open(f"../../data/AWI/dataset_{dataset}_files.txt", 'r'):
        filename = ff.strip()

        mm = re.match(expr, filename)
        if mm is None:
            print(f"Unable to extract flight and segment from {filename}. Continuing")
            continue
        flight = mm.group('flight')
        granule = mm.group('granule')
        granule_name = pathlib.Path(f"{institution}_{campaign}_{flight}_{granule}")
        # wget doesn't work for these, but curl does!
        dest_filepath = f"{dest_dir}/{filename}"
        relative_filepath = os.path.join(region, institution, campaign, filename)
        url = f"{root_url}{filename}"

        if os.path.exists(dest_filepath):
            filesize = os.path.getsize(dest_filepath)
            print(f"Skipping {dest_filepath}: file already exists with size {filesize}")
        else:
            print(f"Downloading {filename} to {dest_filepath}")
            try:
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    curl_cmd = ["curl", url, "--output", temp_file.name]
                    print(f"downloading to {temp_file.name}")
                    subprocess.check_call(curl_cmd)
                    # TODO: for plugin download, replace this with
                    #       `shutil.move` for cross-platform compatibility
                    move_cmd = ["mv", temp_file.name, dest_filepath]
                    subprocess.check_call(move_cmd)
                    filesize = os.path.getsize(dest_filepath)
            except subprocess.CalledProcessError as ex:
                print(f"Failed to download {dataset}, {filename}: {ex}")
        cursor.execute(
            "INSERT OR REPLACE INTO granules VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                str(granule_name),
                institution,
                campaign,
                flight,
                granule,  # granule
                "",  # product (multiple products included in single file)
                data_format,
                download_method,
                url,
                str(relative_filepath),
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
    # parser.add_argument(
    #     "arctic_index",
    #     help="Geopackage database to update with metadata about Arctic campaigns and granules",
    # )
    args = parser.parse_args()

    for campaign, dataset in datasets.items():
        print(f"Downloading dataset {dataset}")
        download_awi(args.data_directory, args.antarctic_index, campaign)
