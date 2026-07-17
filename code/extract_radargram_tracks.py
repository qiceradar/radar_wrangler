#! /usr/bin/env python3

import os
import pathlib
import sys

import h5py
import netCDF4
import numpy as np
import pyproj
import scipy
import scipy.io

from radar_index_utils import subsample_tracks_rdp

# We apply an extra filtering step to the positioning data from these files
# to remove large jumps before the ground tracks are added to the index.
#
corrupt_files = [
    # UTIG campaign: COLDEX_2023
    # See https://github.com/qiceradar/radar_wrangler/issues/15
    "IR2HI1B_2023013_CLX_MKB2n_R70b_005",
    "IR2HI1B_2022362_CXA1_MKB2m_F04T01a_014",
    "IR2HI1B_2023007_CXA1_MKB2m_F07T10a_000",
    "IR2HI1B_2023007_CXA1_MKB2n_F07T01a_000",
    "IR2HI1B_2023008_CXA1_MKB2n_F08T01a_000",
    "IR2HI1B_2023009_CXA1_MKB2n_F08T03a_002",
    "IR2HI1B_2023010_CXA1_MKB2n_F10T01a_000",
    "IR2HI1B_2023013_CXA1_MKB2n_F11T05a_004",
    "IR2HI1B_2023013_CXA1_MKB2n_F12T01a_000",
    "IR2HI1B_2023024_CXA1_MKB2n_F16T01a_000",
    "IR2HI1B_2023025_CXA1_MKB2n_F16T05a_001",
    "IR2HI1B_2023026_CXA1_MKB2n_F17T07a_001",
    "IR2HI1B_2023026_CXA1_MKB2n_F18T01a_000",
    "IR2HI1B_2023027_CXA1_MKB2n_F18T12a_001",
    "IR2HI1B_2023028_CXA1_MKB2n_SPICE07a_005",
    # UTIG campaign: COLDEX_2024
    "IR2HI1B_2023352_CXA2_MKB2o_F04T01a_007",
    "IR2HI1B_2023362_CXA2_MKB2o_F10T01a_000",
    "IR2HI1B_2023362_CXA2_MKB2o_F10T01a_001",
    "IR2HI1B_2023352_PPT_MKB2o_Y01d_000",
    "IR2HI1B_2023352_PPT_MKB2o_Y01d_001",
    "IR2HI1B_2023352_TAM_MKB2o_SHKTG01a_000",
    "IR2HI1B_2023352_TAM_MKB2o_SHKTG01a_001",
    # UTIG campaign: GIMBLE
    "IRFOC1B_2013015_ICP5_JKB2h_RIGGS1a_003",
    "IRFOC1B_2013025_ICP5_JKB2h_RIGGS1b_006",
    "IRFOC1B_2014341_ICP6_MKB2l_F09T01a_004",
    # UTIG campaign: ICECAP
    # These 3 have bad positioning data thanks to interpolating longitude (Issue #2)
    # https://github.com/qiceradar/radar_wrangler/issues/2
    "IR2HI1B_2011031_ICP3_JKB2d_F56T01e_002",
    "IR2HI1B_2013015_ICP5_JKB2h_RIGGS1a_003",
    "IR2HI1B_2013025_ICP5_JKB2h_RIGGS1b_006",
    # CRESIS campaign: 2002_Antarctica_P3chile
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

# This is a blacklist of files that just shouldn't be used
bad_files = [
    "antr1996_9510130001_EMR60_19951013_00",  # coords are in Germany; test flight?
    "20093104_stp10",  # coords are in the ocean between Norway and Greenland
]


def extract_flightlines(
    antarctic: bool,
    data_directory: pathlib.Path,
    index_directory: pathlib.Path,
    epsilon: float,
    force: bool,
):
    """
    Traverse the RadarData directories and extract flight paths for any
    radargrams that are found.
    """
    if antarctic:
        region = "ANTARCTIC"
    else:
        region = "ARCTIC"
    region_dir = data_directory / region

    for provider in ["AWI", "BAS", "CRESIS", "KOPRI", "LDEO", "UTIG"]:
        provider_dir = region_dir / provider
        if not provider_dir.is_dir():
            print(f".. No data from {provider} in {region}")
            continue
        print(f".. {provider}")
        campaign_dirs = [dd for dd in provider_dir.iterdir() if dd.is_dir()]
        campaign_dirs.sort()
        for campaign_dir in campaign_dirs:
            print(f".... Extracting campaign: {campaign_dir.name}")
            campaign = campaign_dir.stem
            # CRESIS is a bit annoying because they put a "product" folder in between campaign + segment
            # TODO: Fix this hack!
            # TODO: This should just crawl the whole directory structure, rather than having me hard-code it.
            if "CRESIS" == provider:
                products = [dd for dd in campaign_dir.iterdir() if dd.is_dir()]
                # We only need one for the index of flight lines.
                campaign_dir = campaign_dir / products[0]

            # Each campaign has segments. For some providers,
            # those will be further split into granules
            segments = [
                dd for dd in campaign_dir.iterdir() if not dd.name.startswith(".")
            ]
            segments.sort()
            for segment_path in segments:
                # Check if segment is a dir, if so, go to granules.
                segment = segment_path.stem
                if segment_path.is_dir():
                    granules = [
                        ss.name
                        for ss in segment_path.iterdir()
                        if ss.name.endswith(("nc", "mat"))
                    ]
                    granules.sort()
                    for granule in granules:
                        granule_filepath = segment_path / granule
                        output_granule_filepath = (
                            index_directory
                            / region
                            / provider
                            / campaign
                            / segment
                            / (granule_filepath.stem + ".csv")
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
                        index_directory
                        / region
                        / provider
                        / campaign
                        / (filename + ".csv")
                    )
                    if force or not output_segment_filepath.exists():
                        extract_file(
                            region,
                            provider,
                            segment_path,
                            output_segment_filepath,
                            epsilon,
                        )


def extract_file(
    region: str,
    provider: str,
    input_filepath: pathlib.Path,
    output_filepath: pathlib.Path,
    epsilon: float,
):
    # TODO: Can't assume perfectly clean input data directories, so this
    #       needs to handle detecting that it's been asked to process
    #       an invalid file.
    # I'm not sure why my filesystem adds "._" files...
    if input_filepath.name.startswith("."):
        return

    if input_filepath.stem in bad_files:
        print(f"Skipping blacklisted file: {input_filepath.name}")
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
        print(f"Unrecognized region {region} -- cannot downsample.")
        return

    if "AWI" == provider:
        result = extract_awi_coords(input_filepath)
    elif "BAS" == provider:
        result = extract_bas_coords(input_filepath)
    elif "CRESIS" == provider:
        result = extract_cresis_coords(input_filepath)
    elif "KOPRI" == provider:
        # KOPRI uses the same file format as UTIG's ICECAP/EAGLE/OIA.
        # The Zipped file has a lot of other filetypes inside, so only
        # process netCDF files.
        if not input_filepath.name.endswith("nc"):
            return

        result = extract_utig_coords(input_filepath)
    elif "LDEO" == provider:
        result = extract_ldeo_coords(input_filepath)
    elif "UTIG" == provider:
        if not input_filepath.name.endswith("nc"):
            return
        result = extract_utig_coords(input_filepath)
    else:
        print(f"Unsupported data provider: {provider}. Skipping {input_filepath}")
        return

    if result is None:
        print(f"Unable to extract data from: {input_filepath}")
        return

    # Only create output directory if we have something to put there.
    # Otherwise, will create directories for non-radargram directories
    # in RadarData.
    output_dir = output_filepath.parent
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        print(f"Could not create {output_dir}")
        raise

    lon, lat = result
    lat = np.array(lat)
    lon = np.array(lon)

    # I don't love transforming into and out of a map projection, but
    # I haven't yet figured out how to run RDP on geographic coordinates.
    xx, yy = proj.transform(lon, lat)

    if pathlib.Path(input_filepath).stem in corrupt_files:
        dx = xx[1:] - xx[0:-1]
        dy = yy[1:] - yy[0:-1]
        deltas = np.sqrt(dx**2 + dy**2)
        # This only works because we know that we have a very small number
        # of huge outliers, and are only running this on data known to have
        # outliers.
        # I originally tried to only remove the first of each pair, but
        # UTIG has several in a row. For expediency's sake, I'll just remove
        # the points on both sides of the jump.
        bad_idxs = np.where(deltas > np.std(deltas))[0][:]
        good_idxs = [idx for idx in np.arange(len(lat)) if idx not in bad_idxs]
        xx = xx[good_idxs]
        yy = yy[good_idxs]

    sx, sy = subsample_tracks_rdp(xx, yy, epsilon)
    # TODO: This is massively hacky, and fails e.g. on sparsely sampled flights.
    #    Would probably be better to fall back to the along-track-distance
    #    subsampling method.
    sampling_factor = 5
    if len(sx) > 50 and sampling_factor * len(sx) > len(xx):
        msg = f"RDP yielded {len(sx)} / {len(xx)} points for {input_filepath}. Decimating."
        print(msg)
        sx = xx[::50]
        sy = yy[::50]

    print(f"Saving subsampled data to {output_filepath}")
    with open(output_filepath, "w") as fp:
        # TODO: Add some sort of metadata here? At one point, I tried
        #       automatically extracting it from the BAS netCDF files,
        #       but other institutions weren't consistent.
        # TODO: Should probably rename fields to easting/northing
        fp.write("ps71_easting,ps71_northing\n")
        data = [f"{pt[0]},{pt[1]}\n" for pt in zip(sx, sy)]
        fp.writelines(data)


def extract_awi_coords(input_filepath):
    try:
        dd = netCDF4.Dataset(input_filepath, "r")
    except Exception:
        print(f"netCDF4 could not parse {input_filepath}")
        return

    try:
        # AN_08_09 uses lon/lat
        lat = dd.variables["lat"][:].data
        lon = dd.variables["lon"][:].data
        return lon, lat
    except Exception as ex:
        print(f"Can't extract data from {input_filepath}")
        print(ex)
        return None


def extract_bas_coords(input_filepath):
    try:
        dd = netCDF4.Dataset(input_filepath, "r")
    except Exception:
        print(f"Could not parse {input_filepath}")
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
            print(f"Could not parse {input_filepath}")
            return
    return lon, lat


def extract_ldeo_coords(input_filepath):
    """
    Only tested on AGAP-GAMBIT data; no guarantee it'll work on others.
    """
    try:
        dd = netCDF4.Dataset(input_filepath, "r")
    except Exception:
        print(f"Could not parse {input_filepath}")
        return
    lat = dd["Lat"][:].data
    lon = dd["Lon"][:].data
    return lon, lat


def extract_utig_coords(input_filepath):
    try:
        data = netCDF4.Dataset(input_filepath, "r")
    except Exception as ex:
        print(f"Couldn't open {input_filepath} as netCDF")
        print(ex)
        return

    if "latitude" in data.variables:
        # The AGASEA data was released using latitude/longitude
        lat = data["latitude"][:].data
        lon = data["longitude"][:].data
    elif "lat" in data.variables:
        # The ICECAP, EAGLE, OIA, and 2018_DIC data was
        # released using lat/lon
        lat = data["lat"][:].data
        lon = data["lon"][:].data
    else:
        errmsg = f"{input_filepath} doesn't have recognized position data"
        print(errmsg)
        return

    return lon, lat


def main():
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("--antarctic", action="store_true")
    parser.add_argument("--arctic", action="store_true")

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

    antarctic = False
    if args.antarctic:
        antarctic = True
    elif args.arctic:
        antarctic = False
    else:
        print("ERROR: Must specify either --antarctic or --arctic")
        sys.exit(-1)

    extract_flightlines(
        antarctic,
        pathlib.Path(args.data_directory),
        pathlib.Path(args.index_directory),
        args.epsilon,
        args.force,
    )


if __name__ == "__main__":
    main()
