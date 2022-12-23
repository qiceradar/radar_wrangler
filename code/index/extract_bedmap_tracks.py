#! /usr/bin/env python3

from radar_index_utils import subsample_tracks

import numpy as np
import os
import pandas as pd
import pathlib
import pyproj


def load_lat_lon(filepath):
    '''Open file in the BEDMAP CVS format and extract just lat long from it'''
    data = pd.read_csv(filepath, skiprows=18)

    lon_index = [col for col in data.columns if 'longitude' in col][0]
    lat_index = [col for col in data.columns if 'latitude' in col][0]
    lon = data[lon_index]
    lat = data[lat_index]
    return np.array(lat), np.array(lon)


def subsample_bedmap():
    data_dir = "/Users/lindzey/RadarData/ANTARCTIC/BEDMAP"
    output_dir = "/Users/lindzey/RadarData/targ/ANTARCTIC/BEDMAP"
    min_spacing = 200  # meters between successive points

    institutions = {}

    for compilation in os.listdir(data_dir):
        compilation_dir = os.path.join(data_dir, compilation)
        for filename in os.listdir(compilation_dir):
            if filename.startswith('.'):
                continue
            elif filename.startswith('BEDMAP1'):
                institution = "BEDMAP1"
                year = 1966
                air = True
                campaign = "BEDMAP1"
            else:
                ff = filename.strip('.csv')
                tokens = ff.split('_')
                institution = tokens[0]
                year = int(tokens[1])
                air = "AIR" == tokens[-2]
                campaign = "_".join(tokens[2:-2])
            if institution not in institutions:
                institutions[institution] = []
            # Cache this for later processing
            filepath = os.path.join(compilation_dir, filename)
            institutions[institution].append((year, campaign, air, filepath))

    ps71 = pyproj.Proj('epsg:3031')

    for institution, campaigns in institutions.items():
        print("Subsampling {}".format(institution))
        for campaign in campaigns:
            _, cc, _, datafilepath = campaign
            institution_dir = os.path.join(output_dir, institution)
            try:
                pp = pathlib.Path(institution_dir)
                pp.mkdir(parents=True, exist_ok=True)
            except FileExistsError as ex:
                raise Exception(
                    "Could not create {}: {}.".format(institution_dir, ex))
            outfilename = datafilepath.split("/")[-1]
            outfilepath = os.path.join(institution_dir, outfilename)
            lat, lon = load_lat_lon(datafilepath)
            print(type(lat))
            if cc == "BEDMAP1":
                duplicate_idxs = set()
                # See attribute_bedmap1.ipynb for how these ranges were determined.

                # The AWI_1994_DML1_AIR_BM2 survey includes 781379-801917 and 1725226-1730675
                duplicate_idxs.update(np.arange(781_379, 801_917+1))
                duplicate_idxs.update(np.arange(1_725_226, 1_730_675+1))

                # The AWI_1995_DML2_AIR_BM2 survey includes 801918-831196 and 1730676-1738606
                duplicate_idxs.update(np.arange(801_918, 831_196+1))
                duplicate_idxs.update(np.arange(1_730_676, 1_738_606+1))

                # The AWI_1996_DML3_AIR_BM2 survey includes 831197-837311 and 1738668-1740272
                # NOTE: Manually extended this to meet up with DML2; inspection showed where those points belong.
                duplicate_idxs.update(np.arange(831_197, 837_311+1))
                duplicate_idxs.update(np.arange(1_738_607, 1_740_272+1))

                # The AWI_1997_DML4_AIR_BM2 survey includes 837309-895838 and 1740272-1755841
                # NOTE: Overlap with earlier surveys is fine, since we're removing the union of these indices.
                duplicate_idxs.update(np.arange(837_309, 895_838+1))
                duplicate_idxs.update(np.arange(1_740_272, 1_755_841+1))

                # The AWI_1998_DML5_AIR_BM2 survey includes 895429-934046 and 1755734-1766275
                duplicate_idxs.update(np.arange(895_429, 934_046+1))
                duplicate_idxs.update(np.arange(1_755_734, 1_766_275+1))

                # The BAS_1994_Evans_AIR_BM2 survey includes 595688-699239 and 1665967-1701479
                duplicate_idxs.update(np.arange(595_688, 699_239+1))
                duplicate_idxs.update(np.arange(1_665_967, 1_701_479+1))

                # The BAS_1998_Dufek_AIR_BM2 survey includes 1418779-1458533 and 1894448-1905049
                duplicate_idxs.update(np.arange(1_418_779, 1_458_533+1))
                duplicate_idxs.update(np.arange(1_894_448, 1_905_049+1))

                # The UTIG_1991_CASERTZ_AIR_BM2 survey includes 934078-960288 and 1766287-1772888
                duplicate_idxs.update(np.arange(934_078, 960_288+1))
                duplicate_idxs.update(np.arange(1_766_287, 1_772_888+1))

                good_idxs = [idx for idx in np.arange(0, len(lat)) if idx not in duplicate_idxs]
                print("For BEDMAP1, using {} / {} points.".format(len(good_idxs), len(lat)))
                lat = lat[good_idxs]
                lon = lon[good_idxs]
                print(type(lat))

            lat, lon = subsample_tracks(lat, lon, min_spacing)
            xx, yy = ps71.transform(lon, lat)
            with open(datafilepath, 'r') as in_fp, open(outfilepath, 'w') as out_fp:
                for _ in range(18):
                    line = in_fp.readline()
                    out_fp.write(line)
                out_fp.write("ps71_easting, ps71_northing\n")
                out_fp.writelines(["{},{}\n".format(pt[0], pt[1])
                                  for pt in zip(xx, yy)])


if __name__ == "__main__":
    subsample_bedmap()
