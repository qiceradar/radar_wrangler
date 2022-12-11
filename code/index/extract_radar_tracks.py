#! /usr/bin/env python3

from radar_index_utils import subsample_tracks_rdp

import h5py
import netCDF4 as nc
import numpy as np
import os
import pathlib
import pyproj
import scipy
import scipy.io


def extract_flightlines(data_directory, index_directory, epsilon, force):
    """
    Traverse the RadarData directories and extract flight paths for any
    radargrams that are found.
    """
    for region in ["ARCTIC", "ANTARCTIC"]:
    #for region in ["ANTARCTIC"]:
        print("Handling {} data".format(region))
        region_dir = os.path.join(data_directory, region)
        for provider in ["BAS", "CRESIS", "LDEO", "UTIG"]:
            provider_dir = os.path.join(region_dir, provider)
            if not os.path.isdir(provider_dir):
                print("..No {} data from {}".format(region, provider))
                continue
            print("..{}".format(provider))
            campaigns = [dd for dd in os.listdir(provider_dir)
                        if os.path.isdir(os.path.join(provider_dir, dd))]
            campaigns.sort()
            for campaign in campaigns:
                print("....Extracting campaign: {}".format(campaign))
                campaign_dir = os.path.join(provider_dir, campaign)
                # CRESIS is a bit annoying because they put a "product" folder in between campaign + segment
                # TODO: Fix this hack!
                # TODO: This should just crawl the whole directory structure, rather than having me hard-code it.
                if "CRESIS" == provider:
                    products = [dd for dd in os.listdir(campaign_dir)
                                if os.path.isdir(os.path.join(campaign_dir, dd))]
                    # We only need one for the index of flight lines.
                    campaign_dir = os.path.join(campaign_dir, products[0])

                # Each campaign has segments. For some providers,
                # those will be further split into granules
                segments = [dd for dd in os.listdir(campaign_dir)
                            if os.path.isdir(os.path.join(campaign_dir, dd))]
                segments.sort()
                for segment in segments:
                    # Check if segment is a dir, if so, go to granules.
                    segment_path = os.path.join(campaign_dir, segment)
                    if os.path.isdir(segment_path):
                        granules = [ss for ss in os.listdir(segment_path)
                                    if ss.endswith('nc') or ss.endswith('mat')]
                        granules.sort()
                        for granule in granules:
                            granule_filepath = os.path.join(segment_path, granule)
                            filename = pathlib.Path(granule_filepath).stem
                            output_granule_filepath = os.path.join(index_directory, region, provider, campaign, segment, filename) + ".csv"
                            if force or not os.path.exists(output_granule_filepath):
                                extract_file(region, provider, granule_filepath, output_granule_filepath, epsilon)
                    else:
                        filename = pathlib.Path(segment_path).stem
                        output_segment_filepath = os.path.join(index_directory, region, provider, campaign, filename)
                        if force or not os.path.exists(output_segment_filepath):
                            extract_file(region, provider, segment_path, output_segment_filepath, epsilon)

def extract_file(region, provider, input_filepath, output_filepath, epsilon):
    output_dir = pathlib.Path(output_filepath).parent
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except FileExistsError as ex:
        print("Could not create {}".format(output_dir))
        raise(ex)

    # TODO: Figure out how to get the RDP algorithm to use lat/lon
    #   for cross-track error calculations.
    # Output data is in lat/lon, but for subsampling the flight paths we
    # need to project them into a cartesian coordinate system.
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
    elif "LDEO" == provider:
        result = extract_ldeo_coords(input_filepath)
    elif "UTIG" == provider:
        result = extract_utig_coords(input_filepath)
    else:
        print("Unsupported data provider: {}. Skipping {}".format(provider, input_filepath))
        return

    if result is None:
        print("Unable to extract data from: {}".format(input_filepath))
        return

    lon, lat = result
    lat = np.array(lat)
    lon = np.array(lon)

    # I don't love transforming into and out of a map projection, but
    # I haven't yet figured out how to run RDP on geographic coordinates.
    xx, yy = proj.transform(lon, lat)
    sx, sy = subsample_tracks_rdp(xx, yy, epsilon)
    sampling_factor = 5
    if len(sx) > 50 and sampling_factor*len(sx) > len(xx):
        msg = "RDP yielded {} / {} points for {}. Decimating.".format(len(sx), len(xx), input_filepath)
        print(msg)
        sx = xx[::50]
        sy = yy[::50]
    sub_lon, sub_lat = proj.transform(np.array(sx), np.array(sy),
                                      direction=pyproj.enums.TransformDirection.INVERSE)

    print("Saving subsampled data to {}".format(output_filepath))
    with open(output_filepath, 'w') as fp:
        # TODO: Add some sort of metadata here? At one point, I tried
        #       automatically extracting it from the BAS netCDF files,
        #       but other institutions weren't consistent.
        fp.write("Longitude,Latitude\n")
        data = ["{},{}\n".format(pt[0], pt[1]) for pt in zip(sub_lon, sub_lat)]
        fp.writelines(data)


def extract_bas_coords(input_filepath):
    try:
        dd = nc.Dataset(input_filepath, 'r')
    except Exception as ex:
        print("Could not parse {}".format(input_filepath))
        return
    lat = dd.variables['latitude_layerData'][:].data
    lon = dd.variables['longitude_layerData'][:].data
    return lon, lat

def extract_cresis_coords(input_filepath):
    """
    CRESIS isn't consistent regarding which matlab file version they used.
    So, try using scipy (works for <= 7.2) and h5py (works for 7.3)
    """
    try:
        dd = scipy.io.loadmat(input_filepath)
        lat = dd['Latitude'].flatten()  # At least with scipy.io, data is nested.
        lon = dd['Longitude'].flatten()
    except:
        try:
            dd = h5py.File(input_filepath, 'r')
            lat = dd['Latitude'][:].flatten()
            lon = dd['Longitude'][:].flatten()
        except Exception as ex:
            print("Could not parse {}".format(input_filepath))
            return
    return lon, lat


def extract_ldeo_coords(input_filepath):
    """
    Only tested on AGAP-GAMBIT data; no guarantee it'll work on others.
    """
    try:
        dd = nc.Dataset(input_filepath, 'r')
    except Exception as ex:
        print("Could not parse {}".format(input_filepath))
        return
    lat = dd['Lat'][:].data
    lon = dd['Lon'][:].data
    return lon, lat


def extract_utig_coords(input_filepath):
    try:
        data = nc.Dataset(input_filepath, 'r')
    except Exception as ex:
        print("Couldn't open {} as netCDF".format(input_filepath))
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
            input_filepath)
        print(errmsg)
        return

    return lon, lat



def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("data_directory",
                        help="Root directory for all QIceRadar-managed radargrams.")
    parser.add_argument("index_directory",
                        help="Root directory for generated subsampled files")
    parser.add_argument("--epsilon", default=5.0, help="Maximum cross-track error for RDP subsampling.")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    extract_flightlines(args.data_directory, args.index_directory, args.epsilon, args.force)


if __name__ == "__main__":
    main()
