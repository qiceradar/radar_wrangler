#! /usr/bin/env python3

from radar_index_utils import subsample_tracks_rdp

import h5py
import netCDF4
import numpy as np
import os
import pathlib
import pyproj
import scipy
import scipy.io


corrupt_files = [
    # These 3 have bad positioning data thanks to interpolating longitude (Issue #2)
    # https://github.com/qiceradar/radar_wrangler/issues/2
    "IR2HI1B_2011031_ICP3_JKB2d_F56T01e_002",
    "IR2HI1B_2013015_ICP5_JKB2h_RIGGS1a_003",
    "IR2HI1B_2013025_ICP5_JKB2h_RIGGS1b_006",
    # And these CRESIS files have similarly corrupt data
    # (This seems to be in *every* flight from the 2002 season)
    # https://github.com/qiceradar/radar_wrangler/issues/4
    "Data_20021128_01_002",
    "Data_20021128_01_004",
    "Data_20021204_01_002",
    "Data_20021204_01_003",
    "Data_20021204_01_007",
    "Data_20021206_01_001",  # Single bad longitude point (-7 amid -92's)
    "Data_20021210_01_010",  # 18 among -68's
    "Data_20021210_01_012",  # Single bad longitude (15 amid -68's)
    "Data_20021212_01_005",
    "Data_20021212_01_007",
    "Data_20021126_01_004",  # -22 among -64's
    "Data_20021128_01_008",
]


def extract_flightlines(data_directory, index_directory, epsilon, force):
    """
    Traverse the RadarData directories and extract flight paths for any
    radargrams that are found.
    """
    for region in ["ARCTIC", "ANTARCTIC"]:
        print("Handling {} data".format(region))
        region_dir = os.path.join(data_directory, region)
        for provider in ["BAS", "CRESIS", "KOPRI", "LDEO", "UTIG"]:
            provider_dir = os.path.join(region_dir, provider)
            if not os.path.isdir(provider_dir):
                print(".. No {} data from {}".format(region, provider))
                continue
            print(".. {}".format(provider))
            campaigns = [
                dd
                for dd in os.listdir(provider_dir)
                if os.path.isdir(os.path.join(provider_dir, dd))
            ]
            campaigns.sort()
            for campaign in campaigns:
                print(".... Extracting campaign: {}".format(campaign))
                campaign_dir = os.path.join(provider_dir, campaign)
                # CRESIS is a bit annoying because they put a "product" folder in between campaign + segment
                # TODO: Fix this hack!
                # TODO: This should just crawl the whole directory structure, rather than having me hard-code it.
                if "CRESIS" == provider:
                    products = [
                        dd
                        for dd in os.listdir(campaign_dir)
                        if os.path.isdir(os.path.join(campaign_dir, dd))
                    ]
                    # We only need one for the index of flight lines.
                    campaign_dir = os.path.join(campaign_dir, products[0])

                # Each campaign has segments. For some providers,
                # those will be further split into granules
                segments = [
                    dd for dd in os.listdir(campaign_dir) if not dd.startswith(".")
                ]
                segments.sort()
                for segment in segments:
                    # Check if segment is a dir, if so, go to granules.
                    segment_path = os.path.join(campaign_dir, segment)
                    if os.path.isdir(segment_path):
                        granules = [
                            ss
                            for ss in os.listdir(segment_path)
                            if ss.endswith("nc") or ss.endswith("mat")
                        ]
                        granules.sort()
                        for granule in granules:
                            granule_filepath = os.path.join(segment_path, granule)
                            filename = pathlib.Path(granule_filepath).stem
                            output_granule_filepath = (
                                os.path.join(
                                    index_directory,
                                    region,
                                    provider,
                                    campaign,
                                    segment,
                                    filename,
                                )
                                + ".csv"
                            )
                            if force or not os.path.exists(output_granule_filepath):
                                extract_file(
                                    region,
                                    provider,
                                    granule_filepath,
                                    output_granule_filepath,
                                    epsilon,
                                )
                    else:
                        filename = pathlib.Path(segment_path).stem
                        output_segment_filepath = (
                            os.path.join(
                                index_directory, region, provider, campaign, filename
                            )
                            + ".csv"
                        )
                        if force or not os.path.exists(output_segment_filepath):
                            extract_file(
                                region,
                                provider,
                                segment_path,
                                output_segment_filepath,
                                epsilon,
                            )


def extract_file(region, provider, input_filepath, output_filepath, epsilon):
    if pathlib.Path(input_filepath).stem in corrupt_files:
        return

    # TODO: Can't assume perfectly clean input data directories, so this
    #       needs to handle detecting that it's been asked to process
    #       an invalid file.
    # I'm not sure why my filesystem adds "._" files...
    if pathlib.Path(input_filepath).stem.startswith("."):
        return

    # TODO: Figure out how to get the RDP algorithm to use lat/lon
    #   for cross-track error calculations.
    #   https://github.com/qiceradar/radar_wrangler/issues/1
    # Output data is in lat/lon, but for subsampling the flight paths we
    # need to project them into a cartesian coordinate system.
    if region == "ANTARCTIC":
        # Polar stereographic about 71S
        proj = pyproj.Proj("epsg:3031")
    elif region == "ARCTIC":
        # Projection used by QGreenland, as documented in section 4.3.1 of:
        # https://www.qgreenland.org/files/inline-files/UserGuide_3.pdf
        proj = pyproj.Proj("epsg:3413")
    else:
        print("Unrecognized region {} -- cannot downsample.".format(region))
        return

    # TODO: Can't assume perfectly clean input data directories, so this
    #       needs to handle detecting that it's been asked to process
    #       an invalid file.
    # I'm not sure why my filesystem adds "._" files...
    if pathlib.Path(input_filepath).stem.startswith("."):
        return
    if "BAS" == provider:
        result = extract_bas_coords(input_filepath)
    elif "CRESIS" == provider:
        result = extract_cresis_coords(input_filepath)
    elif "KOPRI" == provider:
        # KOPRI uses the same file format as UTIG's ICECAP/EAGLE/OIA.
        result = extract_utig_coords(input_filepath)
    elif "LDEO" == provider:
        result = extract_ldeo_coords(input_filepath)
    elif "UTIG" == provider:
        result = extract_utig_coords(input_filepath)
    else:
        print(
            "Unsupported data provider: {}. Skipping {}".format(
                provider, input_filepath
            )
        )
        return

    if result is None:
        print("Unable to extract data from: {}".format(input_filepath))
        return

    # Only create output directory if we have something to put there.
    # Otherwise, will create directories for non-radargram directories
    # in RadarData.
    output_dir = pathlib.Path(output_filepath).parent
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except FileExistsError as ex:
        print("Could not create {}".format(output_dir))
        raise (ex)

    lon, lat = result
    lat = np.array(lat)
    lon = np.array(lon)

    # I don't love transforming into and out of a map projection, but
    # I haven't yet figured out how to run RDP on geographic coordinates.
    xx, yy = proj.transform(lon, lat)
    sx, sy = subsample_tracks_rdp(xx, yy, epsilon)
    # TODO: This is massively hacky, and fails e.g. on sparsely sampled flights.
    #    Would probably be better to fall back to the along-track-distance
    #    subsampling method.
    sampling_factor = 5
    if len(sx) > 50 and sampling_factor * len(sx) > len(xx):
        msg = "RDP yielded {} / {} points for {}. Decimating.".format(
            len(sx), len(xx), input_filepath
        )
        print(msg)
        sx = xx[::50]
        sy = yy[::50]
    sub_lon, sub_lat = proj.transform(
        np.array(sx), np.array(sy), direction=pyproj.enums.TransformDirection.INVERSE
    )

    print("Saving subsampled data to {}".format(output_filepath))
    with open(output_filepath, "w") as fp:
        # TODO: Add some sort of metadata here? At one point, I tried
        #       automatically extracting it from the BAS netCDF files,
        #       but other institutions weren't consistent.
        # TODO: Should probably rename fields to easting/northing
        fp.write("ps71_easting,ps71_northing\n")
        data = ["{},{}\n".format(pt[0], pt[1]) for pt in zip(sx, sy)]
        fp.writelines(data)


def extract_bas_coords(input_filepath):
    try:
        dd = netCDF4.Dataset(input_filepath, "r")
    except Exception:
        print("Could not parse {}".format(input_filepath))
        return
    lat = dd.variables["latitude_layerData"][:].data
    lon = dd.variables["longitude_layerData"][:].data
    return lon, lat


def extract_cresis_coords(input_filepath):
    """
    CRESIS isn't consistent regarding which matlab file version they used.
    So, try using scipy (works for <= 7.2) and h5py (works for 7.3)
    """
    try:
        dd = scipy.io.loadmat(input_filepath)
        lat = dd["Latitude"].flatten()  # At least with scipy.io, data is nested.
        lon = dd["Longitude"].flatten()
    except Exception:
        try:
            dd = h5py.File(input_filepath, "r")
            lat = dd["Latitude"][:].flatten()
            lon = dd["Longitude"][:].flatten()
        except Exception:
            print("Could not parse {}".format(input_filepath))
            return
    return lon, lat


def extract_ldeo_coords(input_filepath):
    """
    Only tested on AGAP-GAMBIT data; no guarantee it'll work on others.
    """
    try:
        dd = netCDF4.Dataset(input_filepath, "r")
    except Exception:
        print("Could not parse {}".format(input_filepath))
        return
    lat = dd["Lat"][:].data
    lon = dd["Lon"][:].data
    return lon, lat


def extract_utig_coords(input_filepath):
    try:
        data = netCDF4.Dataset(input_filepath, "r")
    except Exception as ex:
        print("Couldn't open {} as netCDF".format(input_filepath))
        print(ex)
        return

    if "latitude" in data.variables.keys():
        # The AGASEA data was released using latitude/longitude
        lat = data["latitude"][:].data
        lon = data["longitude"][:].data
    elif "lat" in data.variables.keys():
        # The ICECAP, EAGLE, OIA, and 2018_DIC data was
        # released using lat/lon
        lat = data["lat"][:].data
        lon = data["lon"][:].data
    else:
        errmsg = "{} doesn't have recognized position data".format(input_filepath)
        print(errmsg)
        return

    return lon, lat


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "data_directory", help="Root directory for all QIceRadar-managed radargrams."
    )
    parser.add_argument(
        "index_directory", help="Root directory for generated subsampled files"
    )
    parser.add_argument(
        "--epsilon", default=5.0, help="Maximum cross-track error for RDP subsampling."
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    extract_flightlines(
        args.data_directory, args.index_directory, args.epsilon, args.force
    )


if __name__ == "__main__":
    main()
