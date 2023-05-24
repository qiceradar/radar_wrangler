#! /usr/bin/env python3
from bs4 import BeautifulSoup  # For parsing html and extracting the links
import pathlib  # for creating directory data will be saved to
import requests  # For downloading index page
import subprocess

# TODO: This should probably be moved into data/AWI, mirroring the BAS indices
datasets = {
    "ANTARCTIC": (
        907146,  # Zipped format; can't download README or examply python script, haven't tried data itself yet.
        942989,  # 2018 UWB Roi Baudouin -> *.mat format
    ),
    "ARCTIC": (
        928569,  # 2018 NEGIS Shear Margins -> has qlook.zip, sar1.zip, sar2.zip, as well as some QGIS files
        914258,  # 2018 EGRIP-NOR
        949391,  # 2018 Nioghalvfjerdsbrae
        949619,  # 1998 Nioghalvfjerdsbrae -> EWR, *.mat format
    ),
}


def list_awi_data(dataset_id):
    dataset_link = (
        "https://doi.pangaea.de/10.1594/PANGAEA.{}?format=html#download".format(
            dataset_id
        )
    )
    print("Scraping: {}".format(dataset_link))
    reqs = requests.get(dataset_link)
    soup = BeautifulSoup(reqs.text, "html.parser")

    # Two places the data could be ...
    datafile_prefix = "https://download.pangaea.de/dataset/{}/files/".format(dataset_id)
    pangaea_prefix = "https://hs.pangaea.de/"

    all_urls = [
        link.get("href")
        for link in soup.find_all("a")
        if link.get("href").startswith(datafile_prefix)
        or link.get("href").startswith(pangaea_prefix)
    ]
    return all_urls


def download_awi():
    for pole, dataset_ids in datasets.items():
        print(pole)
        for dataset_id in dataset_ids:
            dest_dir = "/Volumes/RadarData/{}/AWI/{}".format(pole, dataset_id)
            print("saving to: {}".format(dest_dir))

            try:
                pp = pathlib.Path(dest_dir)
                pp.mkdir(parents=True, exist_ok=True)
            except FileExistsError:
                raise Exception("Could not create {}.".format(dest_dir))

            # if dataset_id in [907146, 942989, 928569, 949391, 914258]:
            #    continue
            data_urls = list_awi_data(dataset_id)
            print("\n".join(data_urls))

            # `wget --content-on-error` is required; for some reason, plain wget gives error code 500.
            for data_url in data_urls:
                # WTF. This I can run the resulting command in the terminal, but not via subprocess
                wget_cmd = [
                    "wget",
                    "-c",
                    "--content-on-error",
                    "--directory-prefix={}".format(dest_dir),
                    "{}".format(data_url),
                ]
                print(" ".join(wget_cmd))
                try:
                    output = subprocess.getoutput(" ".join(wget_cmd))

                    print(output)
                except Exception as ex:
                    print(ex)
                    raise (Exception)


if __name__ == "__main__":
    download_awi()
