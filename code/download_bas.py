#! /usr/bin/env python3

import csv
import os
import os.path
import pathlib
import re
import sqlite3
import subprocess
import tempfile


def download_all_bas(qiceradar_dir: str, antarctic_index: str, arctic_index: str):
    """
    Ensures that all BAS data has been downloaded to the specified root
    directory, and updates the input index database with url and path info.
    """
    institution = "BAS"
    index_dir = "../../data/BAS"

    campaign_indices = {
        ff.split(".")[0]: f"{index_dir}/{ff}"
        for ff in os.listdir(index_dir)
        if ff.endswith(".csv")
    }

    for campaign, filepath in campaign_indices.items():
        if campaign in ["GOG3"]:
            region = "ARCTIC"
            connection = sqlite3.connect(arctic_index)
        else:
            region = "ANTARCTIC"
            connection = sqlite3.connect(antarctic_index)
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")

        campaign_dir = f"{region}/{institution}/{campaign}"
        dest_dir = f"{qiceradar_dir}/{campaign_dir}"
        print(
            f"Saving campaign {campaign} from institution {institution} to {dest_dir}"
        )
        try:
            pp = pathlib.Path(dest_dir)
            pp.mkdir(parents=True, exist_ok=True)
        except FileExistsError as ex:
            raise Exception(
                "Could not create {} for {}'s campaign {}: {}.".format(
                    dest_dir, institution, campaign, ex
                )
            )

        with open(filepath) as csvfile:
            csv_reader = csv.DictReader(csvfile)
            for flight in csv_reader:
                # print("{} {}: {}".format(
                #     campaign, flight['name'], flight['url']))
                # TODO: Consider checking filesize for complete download, rather than checking file exists?
                #    However, that would require somehow having the metadata for expected file size, and IIRC, that may differ slightly
                #    on different filesystems.
                #    => `wget -c` may be the answer to this! Let wget check sizes.
                relative_filepath = f"{campaign_dir}/{flight['name']}"
                dest_filepath = f"{qiceradar_dir}/{relative_filepath}"
                # Save data about this granule to the database
                # TODO:
                # filepath (wheere it should be saved within the QIceRadar directory structure)
                # url (where we'll download it from)
                # download_method: 'wget' in this case.

                # format is {campaign}_{segment}.nc
                # This is the problem -- need to be more robust to their file names.
                # The challenge is we have an unpredictable number of underscores.
                # e.g.: WISE_ISODYN_W09.nc, WISE_ISODYN_10_.nc, and WISE_IDOSYN_10B_A.nc
                # and BBAS_B27.nc
                # Whatever I do, GOG3 will break it: IR2HI2_2014130_GRANT_JKB2k_X2Aa_icethk
                if campaign in [
                    "AGAP",
                    "BBAS",
                    "FISS2015",
                    "FISS2016",
                    "ICEGRAV",
                    "IMAFI",
                    "POLARGAP",
                ]:
                    expr = r"(?P<campaig>[A-Z0-9]+)_(?P<flight>[A-Za-z0-9_]+).nc"
                elif campaign in ["GRADES_IMAGE", "ITGC_2019", "WISE_ISODYN"]:
                    expr = r"(?P<campaign>[A-Z0-9]+_[A-Z0-9]+)_(?P<flight>[A-Za-z0-9_]+).nc"
                else:
                    print(f"NYI: trying to parse filename from BAS campaign {campaign}")
                    continue
                mm = re.match(expr, flight["name"])
                if mm is None:
                    print(f"Unable to parse flight: {flight['name']}")
                    continue
                segment = mm.group("flight")
                granule_name = pathlib.Path(
                    f"{institution}_{campaign}_{segment}"
                ).with_suffix("")
                # TODO: the BAS formats are COMPLICATED. each campaign is different.
                #       I haven't decided yet whether I want to name them differently,
                #       or handle it in the BAS parser. I'm leaning towards the later.
                # NB: GOG3 was released by BAS, but was UTIG's radar.
                if campaign in ["GOG3"]:
                    data_format = "ice_thickness"
                else:
                    data_format = "bas_netcdf"
                download_method = "wget"
                filesize = -1
                if os.path.exists(dest_filepath):
                    filesize = os.path.getsize(dest_filepath)
                    print(
                        "Skipping {}: file already exists with size {}".format(
                            flight["name"], filesize
                        )
                    )
                else:
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
                                "{}".format(flight["url"]),
                            ]

                            subprocess.check_call(wget_cmd)
                            # TODO: for plugin download, replace this with
                            #       `shutil.move` for cross-platform compatibility
                            move_cmd = ["mv", temp_file.name, dest_filepath]
                            subprocess.check_call(move_cmd)
                            print("Got {}!".format(flight["name"]))
                            filesize = os.path.getsize(dest_filepath)

                    except subprocess.CalledProcessError as ex:
                        print("Failed to download {}: {}".format(flight["name"], ex))
                cursor.execute(
                    "INSERT OR REPLACE INTO granules VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        str(granule_name),
                        institution,
                        campaign,
                        segment,
                        "",  # granule
                        "",  # product (multiple products included in single file)
                        data_format,
                        download_method,
                        flight["url"],
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
    parser.add_argument(
        "arctic_index",
        help="Geopackage database to update with metadata about Arctic campaigns and granules",
    )
    args = parser.parse_args()
    download_all_bas(args.data_directory, args.antarctic_index, args.arctic_index)
