#! /usr/bin/env python3

from radar_index_utils import subsample_tracks_rdp
from radar_index_utils import count_skip_lines

import numpy as np
import os
import pandas as pd
import pathlib
import pyproj


def extract_flightlines(data_directory, index_directory, epsilon, force):
    """
    Traverse the RadarData directories and extract flight paths for any
    icethickness-only data that are found.
    """

    icethicknesses = [
        # These were cloned from a repo, so for now we're preserving their
        # directory structure, giving the path to a directory containing CSVs.
        (
            "ANTARCTIC",
            "STANFORD",
            "radarfilmstudio/antarctica_original_positioning",
            "SPRI_NSF_TUD",
        ),
    ]

    for region, provider, data_dir, campaign in icethicknesses:
        input_dir = os.path.join(data_directory, region, provider, data_dir)
        print(input_dir)

        # Downloaded data format was a bunch of CSVs
        if provider == "STANFORD":
            flight_filepaths = pathlib.Path(input_dir).glob("*.csv")
            for flight_filepath in flight_filepaths:
                flight = pathlib.Path(flight_filepath).stem
                output_filepath = os.path.join(
                    index_directory, region, provider, campaign, flight + ".csv"
                )
                if force or not os.path.exists(output_filepath):
                    print("Processing {}".format(flight_filepath))
                    extract_file(
                        region, provider, flight_filepath, output_filepath, epsilon
                    )


def extract_file(region, provider, input_filepath, output_filepath, epsilon):
    # TODO: Can't assume perfectly clean input data directories, so this
    #       needs to handle detecting that it's been asked to process
    #       an invalid file.
    # I'm not sure why my filesystem adds "._" files...
    if pathlib.Path(input_filepath).stem.startswith("."):
        return

    # TODO: Figure out how to get the RDP algorithm to use lat/lon
    #   for cross-track error calculations.
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

    if "STANFORD" == provider:
        result = extract_stanford_coords(input_filepath)
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
    # RDP doesn't dramatically reduce the number of points in each SPRI flight, since
    # they were already pretty sparse.
    sub_lon, sub_lat = proj.transform(
        np.array(sx), np.array(sy), direction=pyproj.enums.TransformDirection.INVERSE
    )

    print("Saving subsampled data to {}".format(output_filepath))
    with open(output_filepath, "w") as fp:
        fp.write("ps71_easting,ps71_northing\n")
        data = ["{},{}\n".format(pt[0], pt[1]) for pt in zip(sx, sy)]
        fp.writelines(data)


def extract_stanford_coords(filepath):
    # CSV with fields: [CBD,LAT,LON,THK,SRF]
    skip_lines = count_skip_lines(filepath)
    data = pd.read_csv(filepath, skiprows=skip_lines)

    lat_index = [col for col in data.columns if "LAT" in col][0]
    lon_index = [col for col in data.columns if "LON" in col][0]
    lat = data[lat_index]
    lon = data[lon_index]
    return np.array(lon), np.array(lat)


def extract_bas_respac(data_directory, index_directory, epsilon):
    # Import data, grouping it into seasons.
    bas_filepath = os.path.join(
        data_directory, "ANTARCTIC", "BAS", "BAS_RESPAC_Radar.xyz"
    )
    seasons = {}
    season = None
    curr_line = None
    with open(bas_filepath, "r") as fp:
        for line in fp:
            if line.startswith("/"):
                continue
            if "Line" in line:
                season = line.split()[1]
                if curr_line is not None:
                    seasons[season] = np.array(curr_line)
                curr_line = []
            else:
                tokens = line.split()

                (
                    current_record,
                    season,
                    lon,
                    lat,
                    xx,
                    yy,
                    wgs84_height,
                    tice,
                    srfelev,
                    bedelev,
                ) = tokens
                try:
                    curr_line.append((float(lon), float(lat)))
                except Exception:
                    # Some records don't have position data; just skip them.
                    continue

    # Split each season into segments that can be plotted as line segments.
    ps71 = pyproj.Proj("epsg:3031")
    for season, points in seasons.items():
        season_name = "BAS_19{}_19{}".format(season[0:2], season[2:4])
        print(season_name)
        season_dir = os.path.join(index_directory, "ANTARCTIC", "BAS", season_name)

        try:
            pathlib.Path(season_dir).mkdir(parents=True, exist_ok=True)
        except FileExistsError as ex:
            print("Could not create {}".format(season_dir))
            raise (ex)

        # break each season into segments that can be plotted with line segments
        # Find distance between consecutive points
        lon = points[:, 0]
        lat = points[:, 1]
        xx, yy = ps71.transform(lon, lat)
        dx = xx[1:] - xx[0:-1]
        dy = yy[1:] - yy[0:-1]
        dists = np.sqrt(dx * dx + dy * dy)
        dists = np.insert(dists, 0, 0)
        # Find indices of larger jumps and split points into segments
        (skips,) = np.where(dists > 1000)
        skips = np.insert(skips, 0, 0)
        skips = np.append(skips, len(points))
        segments = [
            points[skips[idx] : skips[idx + 1], :] for idx in range(len(skips) - 1)
        ]

        segment_count = 0
        for segment in segments:
            if len(segment) <= 1:
                continue
            segment_filepath = os.path.join(
                season_dir, "segment{:03d}.csv".format(segment_count)
            )
            segment_count += 1
            lon = segment[:, 0]
            lat = segment[:, 1]
            xx, yy = ps71.transform(lon, lat)
            sx, sy = subsample_tracks_rdp(xx, yy, epsilon)
            with open(segment_filepath, "w") as fp:
                fp.write("ps71_easting,ps71_northing\n")
                data = ["{},{}\n".format(pt[0], pt[1]) for pt in zip(sx, sy)]
                fp.writelines(data)


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

    # This is in the hopes that we'll have more data showing up as CSVs
    # For now, only does SPRI
    extract_flightlines(
        args.data_directory, args.index_directory, args.epsilon, args.force
    )

    # BAS's format for respac data is special and won't generalize.
    extract_bas_respac(args.data_directory, args.index_directory, args.epsilon)


if __name__ == "__main__":
    main()
