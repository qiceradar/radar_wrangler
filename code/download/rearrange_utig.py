#! /usr/bin/env python3
"""
There are 5 (and counting) sources of UTIG netCDFs.
We want them to be in a somewhat-consistent directory structure.

1) AGASEA
Released by Stanford, it is the odd one out.
We'll maintain the released directory structure of
UTIG/AGASEA/{DRP,X,Y}##{a,b,c}/{DRP,X,Y}##{a,b,c}_##.nc

2) ICECAP
These are released via NSIDC, where they're sorted into directories
named "yyyy.mm.dd".
Our download script puts them in directories:
UTIG/ICECAP/{project}_{set}_{transect}/{instrument}_yyyydoy_PST_{granule}.nc
This kind of matches the AGASEA ones, though AGASEA elided project/set in the PST directory

3) EAGLE
These can be downloaded from AAD as a single per-season zip file.
Filename convention is the same, other than using instrument "ER2HI1B" rather than "IR2HI1B".

4) 2018_DIC  (Devon Ice Cap)
This is a single zip file from Zenodo. Same filename convention as ICECAP.

5) OIA
Single files downloaded from AAD. Same naming convention as ICECAP.

6) KOPRI's KRT1
Single zip from Zenodo. Same naming convention as ICECAP, but with instrument KHERA1B
"""

import os
import pathlib
import re


def rearrange_files(directory):
    """
    Find all UTIG netCDF files within input directory and sort them
    into directories based on PSTs.
    """
    print("Rearranging files in {}".format(directory))
    regex = "(?P<instrument>[0-9a-zA-Z]+)_(?P<year>[0-9]{4})(?P<doy>[0-9]{3})_(?P<project>[0-9a-zA-Z]+)_(?P<set>[0-9a-zA-Z]+)_(?P<transect>[0-9a-zA-Z]*)_(?P<granule>[0-9]*).nc"
    for path in pathlib.Path(directory).rglob("*.nc"):
        if path.name.startswith("."):
            # Ignore the MAC extended attribute files
            continue
        mm = re.match(regex, path.name)
        if mm is None:
            print("netCDF file that doesn't match name regex: {}".format(path.name))
            continue
        _, _, _, project, ss, transect, _ = mm.groups()
        pst = "_".join((project, ss, transect))
        pst_dir = os.path.join(directory, pst)
        if not os.path.isdir(pst_dir):
            try:
                pp = pathlib.Path(pst_dir)
                pp.mkdir(parents=True, exist_ok=True)
            except Exception as ex:
                print("Could not create {}".format(pst_dir))
                raise (ex)
        dest_filepath = os.path.join(pst_dir, path.name)
        # Don't move files that are already in the right spot
        if dest_filepath == path.absolute().as_posix():
            continue
        print("{} -> {}".format(path.name, dest_filepath))
        os.rename(path.absolute(), dest_filepath)


def main(data_directory):
    antarctic_dir = os.path.join(data_directory, "ANTARCTIC", "UTIG")
    for campaign in ["EAGLE", "OIA"]:
        campaign_dir = os.path.join(antarctic_dir, campaign)
        rearrange_files(campaign_dir)

    kopri_dir = os.path.join(data_directory, "ANTARCTIC", "KOPRI")
    for campaign in ["KRT1"]:
        campaign_dir = os.path.join(kopri_dir, campaign)
        rearrange_files(campaign_dir)

    dic_dir = os.path.join(data_directory, "ARCTIC", "UTIG", "2018_DIC")
    rearrange_files(dic_dir)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "data_directory", help="Root directory for all QIceRadar-managed radargrams."
    )
    args = parser.parse_args()
    main(args.data_directory)
