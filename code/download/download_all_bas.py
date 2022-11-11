#! /usr/bin/env python3

import csv
import os
import os.path
import pathlib
import subprocess
import tempfile


# These directories will be set by the top-level configuration
code_dir = "/Users/lindzey/Documents/QIceRadar"
index_dir = "{}/radar_wrangler/data".format(code_dir)
radargram_dir = "/Volumes/RadarData"


def download_all_BAS():
    institution = "BAS"
    institution_index_dir = "{}/{}".format(index_dir, institution)

    survey_indices = {ff.split('.')[0]: "{}/{}".format(institution_index_dir, ff)
                      for ff in os.listdir(institution_index_dir)
                      if ff.endswith(".csv")}

    for survey, filepath in survey_indices.items():
        dest_dir = "{}/{}/{}".format(radargram_dir, institution, survey)
        print("Saving survey {} to {}".format(survey, dest_dir))
        try:
            pp = pathlib.Path(dest_dir)
            pp.mkdir(parents=True, exist_ok=True)
        except FileExistsError as ex:
            raise Exception("Could not create {} for {}'s survey {}: {}."
                            .format(dest_dir, institution, survey, ex))

        with open(filepath) as csvfile:
            csv_reader = csv.DictReader(csvfile)
            for flight in csv_reader:
                # print("{} {}: {}".format(
                #     survey, flight['name'], flight['url']))
                # TODO: Consider checking filesize for complete download, rather than checking file exists?
                #    However, that would require somehow having the metadata for expected file size, and IIRC, that may differ slightly
                #    on different filesystems.
                dest_filepath = "{}/{}".format(dest_dir, flight['name'])
                if os.path.exists(dest_filepath):
                    print("Skipping {}: file already exists with size {}"
                          .format(flight['name'], os.path.getsize(dest_filepath)))
                    continue
                try:
                    # Create a temporary file to avoid having to clean up partial downloads.
                    # This may not be ideal if the temporary file is created in a different filesystem than the
                    # output file belongs in. (I expect to eventually be downloading data to an external drive/NAS)
                    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                        # wget_cmd = ["wget", "--no-clobber", "--quiet", "--output-document", dest_filepath, flight['url']]
                        # If saving to a temp file, get rid of --no-clobber, since the file will already have been created.
                        wget_cmd = ["wget", "--quiet", "--output-document",
                                    temp_file.name, "{}".format(flight['url'])]

                        subprocess.check_call(wget_cmd)
                        move_cmd = ["mv", temp_file.name, dest_filepath]
                        subprocess.check_call(move_cmd)
                        print("Got {}!".format(flight['name']))

                except subprocess.CalledProcessError as ex:
                    print("Failed to download {}: {}".format(
                        flight['name'], ex))


if __name__ == "__main__":
    download_all_BAS()
