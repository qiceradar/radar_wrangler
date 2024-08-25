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

data_citations = {}
data_citations["JuRaS_2018"] = "Franke, Steven; Helm, Veit; Steinhage, Daniel; Jansen, Daniela (2024): Airborne radio-echo sounding data from Jutulstraumen Glacier (western Dronning Maud Land, East Antarctica) recorded with the AWI UWB radar system [dataset]. PANGAEA, https://doi.org/10.1594/PANGAEA.962670"
data_citations["CHIRP_2019"] = "Franke, Steven; Jansen, Daniela; Drews, Reinhard; Steinhage, Daniel; Helm, Veit; Eisen, Olaf (2023): Ultra-wideband radar data over the ice shelves and ice rises in eastern Dronning Maud Land (East Antarctica) [dataset]. PANGAEA, https://doi.org/10.1594/PANGAEA.963264"

science_citations = {}
science_citations["JuRaS_2018"] = (
    # Supplement to:
    "Franke, Steven; Wolovick, Michael; Drews, Reinhard; Jansen, Daniela; Matsuoka, Kenichi; Bons, Paul D (2024): Sediment freeze‐on and transport near the onset of a fast‐flowing glacier in East Antarctica. Geophysical Research Letters, 51, e2023GL107164, https://doi.org/10.1029/2023GL107164",
    # Related to:
    "Franke, Steven; Eisermann, Hannes; Jokat, Wilfried; Eagles, Graeme; Asseng, Jölund; Miller, Heinrich; Steinhage, Daniel; Helm, Veit; Eisen, Olaf; Jansen, Daniela (2021): Preserved landscapes underneath the Antarctic Ice Sheet reveal the geomorphological history of Jutulstraumen Basin. Earth Surface Processes and Landforms, 46(13), 2728-2745, https://doi.org/10.1002/esp.5203",
    "Franke, Steven; Gerber, Tamara Annina; Warren, Craig; Jansen, Daniela; Eisen, Olaf; Dahl-Jensen, Dorthe (2023): Investigating the Radar Response of Englacial Debris Entrained Basal Ice Units in East Antarctica Using Electromagnetic Forward Modeling. IEEE Transactions on Geoscience and Remote Sensing, 61, 1-16, https://doi.org/10.1109/TGRS.2023.3277874",
)
science_citations["CHIRP_2019"] = (
    # Supplement to:
    "Koch, Inka; Drews, Reinhard; Franke, Steven; Jansen, Daniela; Oraschewski, Falk M; Muhle, Leah Sophie; Višnjević, Vjeran; Matsuoka, Kenichi; Pattyn, Frank; Eisen, Olaf (2023): Radar internal reflection horizons from multisystem data reflect ice dynamic and surface accumulation history along the Princess Ragnhild Coast, Dronning Maud Land, East Antarctica. Journal of Glaciology, 1-19, https://doi.org/10.1017/jog.2023.93",
    # Related to:
    "Koch, Inka; Drews, Reinhard; Muhle, Lea Sophie; Franke, Steven; Jansen, Daniela; Oraschewski, Falk M; Spiegel, Heiko; Višnjević, Vjeran; Matsuoka, Kenichi; Pattyn, Frank; Eisen, Olaf (2023): Internal reflection horizons of ice shelves and ice rises in eastern Dronning Maud Land (East Antarctica) from multisystem radio-echo sounding data. PANGAEA, https://doi.org/10.1594/PANGAEA.950383",
)


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

    # Science citation is optional; data and doi required
    try:
        science_citation = "\n".join(science_citations[campaign])
    except KeyError:
        science_citation = ""
    print(f"Adding campaign.\n {campaign}\n {institution} \n {data_citations[campaign]} \n {science_citation} ")
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
