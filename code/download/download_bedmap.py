#! /usr/bin/env python3

from bs4 import BeautifulSoup
import csv
import os
import os.path
import pathlib
import requests
import subprocess
import tempfile


def download_file(filename, url, dest_dir):
    """
    Download the file at input url and put it in dest_dir as filename.
    * Skips download if file with same name already exists
    * Initially downloads to a temporary file to avoid corrupting the
      data directory with partially-downloaded files.
    """
    dest_filepath = os.path.join(dest_dir, filename)

    if os.path.exists(dest_filepath):
        print("Skipping {}: file already exists with size {}"
              .format(filename, os.path.getsize(dest_filepath)))
    else:
        try:
            # Create a temporary file to avoid having to clean up partial downloads.
            # This may not be ideal if the temporary file is created in a different filesystem than the
            # output file belongs in. (I expect to eventually be downloading data to an external drive/NAS)
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                # wget_cmd = ["wget", "--no-clobber", "--quiet", "--output-document", dest_filepath, flight['url']]
                # If saving to a temp file, get rid of --no-clobber, since the file will already have been created.
                wget_cmd = ["wget", "--quiet", "--output-document",
                            temp_file.name, "{}".format(url)]
                subprocess.check_call(wget_cmd)
                move_cmd = ["mv", temp_file.name, dest_filepath]
                subprocess.check_call(move_cmd)
                print("Got {}!".format(filename))
        except subprocess.CalledProcessError as ex:
            print("Failed to download BEDMAP: {}".format(ex))


def download_rammada(doi, dest_dir):
    '''
    Find and download all links formatted like data entries on a given rammada page.
    '''
    try:
        pp = pathlib.Path(dest_dir)
        pp.mkdir(parents=True, exist_ok=True)
    except FileExistsError as ex:
        raise Exception(
            "Could not create {}. Error: {}".format(dest_dir, ex))

    data_link = 'https://ramadda.data.bas.ac.uk/repository/entry/show?entryid=' + \
        doi.split('/')[-1]
    reqs = requests.get(data_link)
    soup = BeautifulSoup(reqs.text, 'html.parser')

    base_url = 'https://ramadda.data.bas.ac.uk'
    prefix = '/repository/entry/get/'

    all_urls = [link.get('href') for link in soup.find_all('a')]
    download_urls = [base_url +
                     url for url in all_urls if url.startswith(prefix)]
    filenames = [url.strip(base_url+prefix).split('?')[0]
                 for url in download_urls]

    for ff, uu in zip(filenames, download_urls):
        download_file(ff, uu, dest_dir)


def download_all_bedmap(bedmap_data_dir):
    bedmap1_doi = "https://doi.org/10.5285/f64815ec-4077-4432-9f55-0ce230f46029"
    bedmap2_doi = "https://doi.org/10.5285/2fd95199-365e-4da1-ae26-3b6d48b3e6ac"
    bedmap3_doi = "https://doi.org/10.5285/91523ff9-d621-46b3-87f7-ffb6efcd1847"

    bedmap1_dest_dir = os.path.join(bedmap_data_dir, "BEDMAP1")
    download_rammada(bedmap1_doi, bedmap1_dest_dir)

    bedmap2_dest_dir = os.path.join(bedmap_data_dir, "BEDMAP2")
    download_rammada(bedmap2_doi, bedmap2_dest_dir)

    bedmap3_dest_dir = os.path.join(bedmap_data_dir, "BEDMAP3")
    download_rammada(bedmap3_doi, bedmap3_dest_dir)


if __name__ == "__main__":
    # These directories should be set by the top-level configuration
    data_dir = "/Volumes/RadarData"
    bedmap_data_dir = os.path.join(data_dir, "BEDMAP_new")
    download_all_bedmap(bedmap_data_dir)
