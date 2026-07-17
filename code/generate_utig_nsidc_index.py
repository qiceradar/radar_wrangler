#! /usr/bin/env python3
"""
In the future, I want data providers to be able to add one-off profiles
by simply editing a CSV file with the appropriate fields.

So, to experiment with that workflow, I'm dividing the UTIG download
into creating the index and then downloading it.

At NSIDC, UTIG's data can be browsed in a folder structure rooted at:
* hicars1: https://cmr.earthdata.nasa.gov/virtual-directory/collections/C3204978631-NSIDC_CPRD/temporal
* hicars2: https://cmr.earthdata.nasa.gov/virtual-directory/collections/C3204981465-NSIDC_CPRD/temporal

The directory structure is:

/temporal/yyyy/mm/dd/{instrument}_{yyyy}{doy}_{project}_{set}_{transect}_{granule}.nc

However, downloads will be a link like
https://data.nsidc.earthdatacloud.nasa.gov/nsidc-cumulus-prod-protected/ICEBRIDGE/IR1HI1B/1/2009/01/02/IR1HI1B_2009002_MCM_JKB1a_DGC02a_000.nc

Previously, data was at:
* hicars1: https://n5eil01u.ecs.nsidc.org/ICEBRIDGE/IR1HI1B.001/
* hicars2: https://n5eil01u.ecs.nsidc.org/ICEBRIDGE/IR2HI1B.001/

Now that EarthData will export a list of all granules matching a filter,
this script is simply reformatting that list to have the right columns.
For UTIG data, the additional metadata can be extracted from the
granule's filename.
"""

import os
import pathlib
import re

def create_index_from_urls(input_files: list[pathlib.Path], output_file: pathlib.Path) -> None:
    institution = "UTIG"
    pattern  = "(?P<date_string>\d{4}/\d{2}/\d{2}).*_(?P<pst>[0-9a-zA-Z]+_[0-9a-zA-Z]+_[0-9a-zA-Z]+)_(?P<granule>\d{3})\.nc"
    with open(output_file, 'w') as fp:
        fp.write("institution,flight,segment,granule,url\n")
        for input_file in input_files:
            for line in open(input_file):
                url = line.strip()
                mm = re.search(pattern, url)
                if mm is None:
                    print(f"Unable to parse: {url}")
                    continue
                date_str = mm.group("date_string").replace('/', '.')
                granule_str = mm.group("granule")
                pst_str = mm.group("pst")
                # institution, flight,segment,granule,url
                output = f"{institution},{date_str},{pst_str},{granule_str},{url}\n"
                fp.write(output)


if __name__ == "__main__":
    index_dir = "../data/UTIG"
    try:
        pp = pathlib.Path(index_dir)
        pp.mkdir(parents=True, exist_ok=True)
    except Exception as ex:
        print("Could not create {}".format(index_dir))
        print(ex)
        raise (ex)
    index_filepath = os.path.join(index_dir, "utig_nsidc_index.csv")
    hicars1_inputfile = os.path.join(index_dir, "nsidc_download_urls_hicars1.txt")
    hicars2_inputfile = os.path.join(index_dir, "nsidc_download_urls_hicars2.txt")
    create_index_from_urls([hicars1_inputfile, hicars2_inputfile], index_filepath)