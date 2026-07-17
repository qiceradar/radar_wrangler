#! /usr/bin/env python3

"""
Download AWI radar data from Pangaea.

Pangaea may return small HTML placeholder files (~10kB) instead of actual
data when the requested files need to be loaded from tape. This script
detects those placeholders and uses a sliding retry buffer: up to
BUFFER_SIZE files are kept in-flight, new files are tried immediately
as slots free up, and retries are spaced at least TAPE_RETRY_WAIT apart.
"""

import collections
import os
import os.path
import pathlib
import re
import sqlite3
import subprocess
import tempfile
import time

# mapping from campaign to dataset
datasets = {}
datasets["ANT_95_96"] = 995486
datasets["ANT_96_97"] = 974229
datasets["ANT_97_98"] = 974295
datasets["ANT_98_99"] = 974402

datasets["ANT_00_01"] = 974431
datasets["ANT_01_02"] = 974432
datasets["ANT_02_03"] = 982598

datasets["ANT_05_06"] = 974441

datasets["ANT_07_08"] = 974448
datasets["ANT_08_09"] = 974453

datasets["ANT_10_11"] = 974319

datasets["ANT_15_16"] = 987347
datasets["ANT_16_17"] = 984741

# datasets["JuRaS_2018"] = 962670 -- this one was replaced by 976759
datasets["ANT_18_19_JURAS"] = 976759
# datasets["CHIRP_2019"] = 963264 -- this one was replaced by 982515
datasets["ANT_18_19"] = 982515

datasets["ANT_22_23"] = 971622  # Embargoed until 2027
datasets["ANT_23_24_CHARISO"] = 990049
datasets["ANT_23_24"] = 981128
datasets["ANT_24_25_CHARISO"] = 991465


# experimentally determined. 15 wasn't ever enough; 20 has been mixed.
# The longest wait I've seen so far is 100 seconds.
TAPE_RETRY_WAIT = 20  # seconds
MAX_TAPE_RETRIES = 10  # 10 retries
BUFFER_SIZE = 10


def is_valid_netcdf(filepath: str) -> bool:
    """Check if file starts with NetCDF/HDF5 magic bytes."""
    with open(filepath, "rb") as f:
        magic = f.read(4)
    return magic == b"\x89HDF" or magic[:3] == b"CDF"


def is_tape_placeholder(filepath: str) -> bool:
    """Check if file is an HTML placeholder returned when data is on tape."""
    try:
        with open(filepath, "r", errors="ignore") as f:
            head = f.read(1024)
        return "<!doctype html>" in head.lower()
    except Exception:
        return False


def try_download(url: str, dest_filepath: str, filename: str, dataset: int) -> str:
    """Attempt to download a single file.

    Returns 'ok', 'tape', or 'skip'.
    """
    print(f"\n  Downloading {filename}")
    try:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            curl_cmd = ["curl", url, "--output", temp_file.name]
            subprocess.check_call(curl_cmd)
            # TODO: for plugin download, replace this with
            #       `shutil.move` for cross-platform compatibility
            move_cmd = ["mv", temp_file.name, dest_filepath]
            subprocess.check_call(move_cmd)
    except subprocess.CalledProcessError as ex:
        print(f"Failed to download {dataset}, {filename}: {ex}")
        return "skip"

    if is_valid_netcdf(dest_filepath):
        return "ok"
    elif is_tape_placeholder(dest_filepath):
        with open(dest_filepath, "r", errors="ignore") as f:
            head_lines = [f.readline() for _ in range(5)]
        print(f"Received HTML placeholder for {filename}:")
        for line in head_lines:
            print(f"  {line.rstrip()}")
        os.remove(dest_filepath)
        return "tape"
    else:
        print(f"ERROR: Unexpected file type returned for {filename}; skipping")
        os.remove(dest_filepath)
        return "skip"


def insert_granule(
    cursor,
    connection,
    file_info: dict,
    institution: str,
    campaign: str,
    data_format: str,
    download_method: str,
) -> None:
    """Insert or update a granule record in the database."""
    filesize = os.path.getsize(file_info["dest_filepath"])
    cursor.execute(
        "INSERT OR REPLACE INTO granules VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            str(file_info["granule_name"]),
            institution,
            campaign,
            file_info["flight"],
            file_info["granule"],
            "",  # product (multiple products included in single file)
            data_format,
            download_method,
            file_info["url"],
            str(file_info["relative_filepath"]),
            str(filesize),
        ],
    )
    connection.commit()


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

    # For the MCoRDS data
    mcords_expr = "Data_(?P<flight>[0-9]{8}_[0-9]{2})_(?P<granule>[0-9]{3})_standard.nc"
    # Filenames for the 1995/96 EMR data
    # antr1996_9602102402_EMR600_19960210_00.nc
    emr95_expr = "antr[0-9]{4}_(?P<ymd>[0-9]{6})(?P<hs>[0-9]{4})_(?P<emr>EMR[0-9]{2,3})_[0-9]{8}_(?P<granule>[0-9]{2})\.nc"
    # Filenames for the 1996/97 EMR data. And 97/98.
    # It appears that the 5th digit indicates system: 2 for EMR600, 3 for EMR60
    # 19973209_stp10.nc
    emr96_expr = "(?P<flight>[0-9]{8})_stp10.nc"
    emr15_expr = "(?P<flight>[0-9]{8})_stp7.nc"

    try:
        pp = pathlib.Path(dest_dir)
        pp.mkdir(parents=True, exist_ok=True)
    except FileExistsError as ex:
        print(ex)
        raise Exception(f"Could not create {dest_dir}; already exists")

    # Phase 1: Parse file list. Handle already-existing files; queue the rest.
    download_queue = collections.deque()
    for ff in open(f"../data/AWI/dataset_{dataset}_files.txt", "r"):
        filename = ff.strip()

        mcords_match = re.match(mcords_expr, filename)
        emr95_match = re.match(emr95_expr, filename)
        emr96_match = re.match(emr96_expr, filename)

        if mcords_match is None and emr95_match is None and emr96_match is None:
            print(f"Unable to extract flight and segment from {filename}. Continuing")
            continue
        elif mcords_match is not None:
            flight = mcords_match.group("flight")
            granule = mcords_match.group("granule")
        elif emr95_match is not None:
            # supporting both versions of data, but calling them different flights
            # "FLIGHT" will be YYMMDD_EMR##
            flight = emr95_match.group("ymd") + "_" + emr95_match.group("emr")
            granule = emr95_match.group("hs")
        elif emr96_match is not None:
            flight = emr96_match.group("flight")
            granule = "0"

        granule_name = pathlib.Path(f"{institution}_{campaign}_{flight}_{granule}")
        # wget doesn't work for these, but curl does!
        dest_filepath = f"{dest_dir}/{filename}"
        relative_filepath = os.path.join(region, institution, campaign, filename)
        url = f"{root_url}{filename}"

        file_info = {
            "filename": filename,
            "flight": flight,
            "granule": granule,
            "granule_name": granule_name,
            "dest_filepath": dest_filepath,
            "relative_filepath": relative_filepath,
            "url": url,
        }

        if os.path.exists(dest_filepath):
            filesize = os.path.getsize(dest_filepath)
            print(f"Skipping {dest_filepath}: file already exists with size {filesize}")
            insert_granule(
                cursor,
                connection,
                file_info,
                institution,
                campaign,
                data_format,
                download_method,
            )
        else:
            download_queue.append(file_info)

    # Phase 2: Process downloads with a sliding retry buffer.
    # New files are tried immediately as they fill buffer slots.
    # Tape placeholders stay in the buffer for retry.
    # Each round takes at least TAPE_RETRY_WAIT seconds.
    buffer = []  # list of (file_info, retry_count)

    # Initial fill: try new files until buffer is full or queue is empty
    while len(buffer) < BUFFER_SIZE and len(download_queue) > 0:
        file_info = download_queue.popleft()
        result = try_download(
            file_info["url"], file_info["dest_filepath"], file_info["filename"], dataset
        )
        if result == "ok":
            insert_granule(
                cursor,
                connection,
                file_info,
                institution,
                campaign,
                data_format,
                download_method,
            )
        elif result == "tape":
            buffer.append((file_info, 0))

    while len(buffer) > 0:
        round_start = time.time()

        # 1. Retry everything in the buffer
        new_buffer = []
        for file_info, retries in buffer:
            result = try_download(
                file_info["url"],
                file_info["dest_filepath"],
                file_info["filename"],
                dataset,
            )
            if result == "ok":
                insert_granule(
                    cursor,
                    connection,
                    file_info,
                    institution,
                    campaign,
                    data_format,
                    download_method,
                )
            elif result == "tape" and retries < MAX_TAPE_RETRIES:
                new_buffer.append((file_info, retries + 1))
            elif result == "tape":
                print(
                    f"Giving up on {file_info['filename']} after "
                    f"{MAX_TAPE_RETRIES} retries. "
                    f"Re-run the script later to try again."
                )
        buffer = new_buffer

        # 2. Fill freed slots from queue, trying each new file immediately
        while len(buffer) < BUFFER_SIZE and download_queue:
            file_info = download_queue.popleft()
            result = try_download(
                file_info["url"],
                file_info["dest_filepath"],
                file_info["filename"],
                dataset,
            )
            if result == "ok":
                insert_granule(
                    cursor,
                    connection,
                    file_info,
                    institution,
                    campaign,
                    data_format,
                    download_method,
                )
            elif result == "tape":
                buffer.append((file_info, 0))

        # 3. Don't retry the same files faster than TAPE_RETRY_WAIT
        if buffer:
            elapsed = time.time() - round_start
            remaining = TAPE_RETRY_WAIT - elapsed
            if remaining > 0:
                print(
                    f"Waiting {remaining:.0f}s for {len(buffer)} files "
                    f"to be staged from tape..."
                )
                time.sleep(remaining)

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
