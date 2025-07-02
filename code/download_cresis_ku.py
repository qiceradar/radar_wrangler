#! /usr/bin/env python3
"""
Download the "best" version for each line from data.cresis.ku.edu
# TODO: Consider downloading _all_ versions, and making them available?

This is the most complete set of data collected by CReSIS, but it doesn't
have good metadata for who actually owns the data.
"""


import pathlib
import subprocess
import tempfile

from radar_wrangler_utils import Granule, read_granule_list


def download_cresis(data_dir: str, granules: list[Granule]):
    """
    Download all CReSIS data from the KU servers.
    """

    for granule in granules:
        dest_filepath = pathlib.Path(data_dir, granule.relative_filepath)
        try:
            pp = dest_filepath.parent
            pp.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            raise Exception("Could not create {}.".format(pp))
            continue

        if not dest_filepath.is_file():
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                wget_cmd = [
                    "wget",
                    "--quiet",
                    "--output-document",
                    temp_file.name,
                    granule.download_url,
                ]
                print(f"{dest_filepath}: {' '.join(wget_cmd)}")
                subprocess.check_call(wget_cmd)
                print("subprocess returned...")
                move_cmd = ["mv", temp_file.name, dest_filepath]
                subprocess.check_call(move_cmd)
                print("Got {}!".format(pathlib.Path(dest_filepath).name))

        # Check if download succeeded
        if not dest_filepath.is_file():
            # There are a handful of files that are listed in the CReSIS website
            # but where the actual radargram gives
            # "Forbidden: You don't have permission to access this resource".
            # So, check that download was successful
            print(f"Cannot find downloaded file {dest_filepath}")


def main(data_dir: str) -> None:
    index_filepath = "../data/cresis_granules.csv"

    cresis_granules = read_granule_list(index_filepath)

    download_cresis(data_dir, cresis_granules)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "data_directory", help="Root directory for all QIceRadar-managed radargrams."
    )

    args = parser.parse_args()

    main(args.data_directory)
