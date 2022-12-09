#! /usr/bin/env python3

from radar_index_utils import subsample_tracks_rdp

import netCDF4 as nc
import numpy as np
import os
import pathlib
import pyproj


def subsample_utig(data_directory, index_directory, force=False):
    # Not all UTIG data follows the same format
    for region in ["ARCTIC", "ANTARCTIC"]:
        print("Handling {} data".format(region))
        utig_data_dir = os.path.join(data_directory, region, "UTIG")
        campaigns = [dd for dd in os.listdir(utig_data_dir)
                     if os.path.isdir(os.path.join(utig_data_dir, dd))]
        campaigns.sort()
        for campaign in campaigns:
            print("Extracting campaign: {}".format(campaign))
            campaign_dir = os.path.join(utig_data_dir, campaign)
            # Each campaign has PSTs, each of which is split into granules
            psts = [dd for dd in os.listdir(campaign_dir)
                    if os.path.isdir(os.path.join(campaign_dir, dd))]
            psts.sort()
            for pst in psts:
                print("...{}".format(pst))
                pst_dir = os.path.join(campaign_dir, pst)
                segments = [ss for ss in os.listdir(
                    pst_dir) if ss.endswith('nc')]
                segments.sort()

                if 0 == len(segments):
                    print("No netCDF files in {}".format(pst_dir))
                    continue

                output_pst_dir = os.path.join(
                    index_directory, region, "UTIG", campaign, pst)
                try:
                    pp = pathlib.Path(output_pst_dir)
                    pp.mkdir(parents=True, exist_ok=True)
                except FileExistsError as ex:
                    raise Exception(
                        "Could not create {}: {}.".format(output_pst_dir, ex))

                for segment in segments:
                    segment_filepath = os.path.join(pst_dir, segment)
                    segment_filename = segment.replace("nc", "csv")
                    output_filepath = os.path.join(
                        output_pst_dir, segment_filename)
                    if not os.path.exists(output_filepath) or force:
                        extract_segment(
                            region, segment_filepath, output_filepath)


def extract_segment(region, segment_filepath, output_filepath):
    try:
        data = nc.Dataset(segment_filepath, 'r')
    except Exception as ex:
        print("Couldn't open {} as netCDF".format(segment_filepath))
        print(ex)
        return

    if 'latitude' in data.variables.keys():
        # The AGASEA data was released using latitude/longitude
        lat = data['latitude'][:].data
        lon = data['longitude'][:].data
    elif 'lat' in data.variables.keys():
        # The ICECAP, EAGLE, OIA, and 2018_DIC data was
        # released using lat/lon
        lat = data['lat'][:].data
        lon = data['lon'][:].data
    else:
        errmsg = "{} doesn't have recognized position data".format(
            segment_filepath)
        print(errmsg)
        return

    # Downsample segment so final files will be shareable
    lat = np.array(lat)
    lon = np.array(lon)

    # TODO: I really don't love this, because it's region-specific
    if region == "ANTARCTIC":
        # Polar stereographic about 71S
        proj = pyproj.Proj('epsg:3031')
    elif region == "ARCTIC":
        # Projection used by QGreenland, as documented in section 4.3.1 of:
        # https://www.qgreenland.org/files/inline-files/UserGuide_3.pdf
        proj = pyproj.Proj('epsg:3413')
    else:
        print("Unrecognized region {} -- cannot downsample.".format(region))
        return

    # I don't love transforming into and out of a map projection, but
    # I haven't yet figured out how to run RDP on geographic coordinates.
    xx, yy = proj.transform(lon, lat)
    epsilon = 5
    sx, sy = subsample_tracks_rdp(xx, yy, epsilon)
    sampling_factor = 5
    if len(sx) > 50 and sampling_factor*len(sx) > len(xx):
        print(
            "RDP yielded {} / {} points for {}. Decimating.".format(len(sx), len(xx), segment_filepath))
        sx = xx[::50]
        sy = yy[::50]
    sub_lon, sub_lat = proj.transform(np.array(sx), np.array(sy),
                                      direction=pyproj.enums.TransformDirection.INVERSE)

    print("Saving granule to {}".format(output_filepath))
    with open(output_filepath, 'w') as fp:
        # TODO: Add some sort of metadata here
        fp.write("Longitude,Latitude\n")
        data = ["{},{}\n".format(pt[0], pt[1]) for pt in zip(sub_lon, sub_lat)]
        fp.writelines(data)


def test_missing(data_directory, index_directory):
    """
    A handful of UTIG PSTs were a problem, so I want to look at them in more detail.
    => Turns out they had NANs in their positioning data.
    """
    # Tuples of pst_dir, output_path
    problems = ["ANTARCTIC/UTIG/OIA/OIA_JKB2n_X51a",
                "ANTARCTIC/UTIG/OIA/OIA_JKB2n_X60a",
                "ANTARCTIC/UTIG/EAGLE/PEL_JKB2n_Y18a",
                "ANTARCTIC/UTIG/EAGLE/PEL_JKB2n_Y20a",
                ]
    for pst_path in problems:
        pst_dir = os.path.join(data_directory, pst_path)
        output_path = os.path.join(index_directory, pst_path) + ".csv"
        print("{} -> {}".format(pst_dir, output_path))

        segments = [ss for ss in os.listdir(segments.sort())]
        for segment in segments:
            segment_filepath = os.path.join(pst_dir, segment)
            output_filepath = os.path.join(
                index_directory, segment) + ".csv"
            extract_segment("ANTARCTIC", segment_filepath, output_filepath)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("data_directory",
                        help="Root directory for all QIceRadar-managed radargrams.")
    parser.add_argument("index_directory",
                        help="Root directory for generated subsampled files")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    # test_missing(args.data_directory, args.index_directory)
    subsample_utig(args.data_directory, args.index_directory, args.force)


if __name__ == "__main__":
    main()
