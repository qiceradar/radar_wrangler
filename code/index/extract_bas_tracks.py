#! /usr/bin/env python3

from radar_index_utils import subsample_tracks

import netCDF4 as nc
import os
import pathlib
import pyproj


def subsample_bas(data_directory, index_directory):
    ps71 = pyproj.Proj('epsg:3031')
    bas_dir = os.path.join(data_directory, "ANTARCTIC", "BAS")
    output_dir = os.path.join(index_directory, "ANTARCTIC", "BAS")

    campaigns = [dd for dd in os.listdir(bas_dir)
                 if os.path.isdir(os.path.join(bas_dir, dd))]
    for campaign in campaigns:
        campaign_dir = os.path.join(bas_dir, campaign)
        output_campaign_dir = os.path.join(output_dir, campaign)
        try:
            pp = pathlib.Path(output_campaign_dir)
            pp.mkdir(parents=True, exist_ok=True)
        except FileExistsError as ex:
            raise Exception(
                "Could not create {}: {}.".format(output_campaign_dir, ex))

        datafiles = [dd for dd in os.listdir(campaign_dir)
                     if dd.endswith('nc')]
        for filename in datafiles:
            filepath = os.path.join(campaign_dir, filename)
            outfilename = filename.replace('.nc', '.csv')
            outfilepath = os.path.join(output_campaign_dir, outfilename)
            print("Subsampling {} -> {}".format(filename, outfilepath))

            try:
                dd = nc.Dataset(filepath, 'r')
            except Exception as ex:
                print("Could not parse {}".format(filepath))
                continue
            lat = dd.variables['latitude_layerData'][:].data
            lon = dd.variables['longitude_layerData'][:].data
            min_spacing = 200
            sub_lat, sub_lon = subsample_tracks(lat, lon, min_spacing)
            xx, yy = ps71.transform(sub_lon, sub_lat)

            # Preserve alll available metadata when exporting into format
            # that QGIS can use as a layer data source
            fields = [aa for aa in dir(dd) if type(getattr(dd, aa)) is str]

            with open(outfilepath, 'w') as fp:
                # TODO: Update this to exclude stuff like __doc__
                metadata = ["# {}: {}\n".format(
                    field, getattr(dd, field).replace('\n', '\n## '))
                    for field in fields]
                fp.writelines(metadata)
                fp.write("ps71_easting, ps71_northing\n")
                data = ["{},{}\n".format(pt[0], pt[1]) for pt in zip(xx, yy)]
                fp.writelines(data)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("data_directory",
                        help="Root directory for all QIceRadar-managed radargrams.")
    parser.add_argument("index_directory",
                        help="Root directory for generated subsampled files")
    args = parser.parse_args()
    subsample_bas(args.data_directory, args.index_directory)
