#! /usr/bin/env python3

import os
import pathlib

import numpy as np
import pandas as pd
import pyproj

from radar_index_utils import count_skip_lines, subsample_tracks_rdp


def extract_flightlines(
    data_directory: pathlib.Path,
    index_directory: pathlib.Path,
    epsilon: float,
    force: bool,
):
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
        # Odd one out -- since SEGY files do not include nav, it makes more
        # sense to put this here, even though we do have radargrams for them.
        ("ANTARCTIC", "UTIG", "LVS/vostok_radar_nav_lines", "LVS"),
    ]

    for region, provider, data_dir, campaign in icethicknesses:
        input_dir = data_directory / region / provider / data_dir
        print(input_dir)

        # Downloaded data format was a bunch of CSVs
        if provider == "STANFORD":
            filepaths = [
                ff for ff in input_dir.glob("*.csv") if not ff.name.startswith(".")
            ]
        elif provider == "UTIG" and campaign == "LVS":
            filepaths = [
                ff for ff in input_dir.glob("*.nav") if not ff.name.startswith(".")
            ]
        else:
            print(f"Cannot extract campaign {campaign}")
            return
        for filepath in filepaths:
            segment = filepath.stem
            output_filepath = (
                index_directory / region / provider / campaign / (segment + ".csv")
            )

            if force or not os.path.exists(output_filepath):
                print(f"Processing {filepath} -> {output_filepath}")
                extract_file(region, provider, filepath, output_filepath, epsilon)
            else:
                print(f"Skipping {filepath}")


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
        print(f"Unrecognized region {region} -- cannot downsample.")
        return

    if "STANFORD" == provider:
        result = extract_stanford_coords(input_filepath)
    elif "UTIG" == provider and "LVS" in str(input_filepath):
        result = extract_lvs_coords(input_filepath)
    else:
        print(f"Unsupported data provider: {provider}. Skipping {input_filepath}")
        return

    if result is None:
        print(f"Unable to extract data from: {input_filepath}")
        return

    # Only create output directory if we have something to put there.
    # Otherwise, will create directories for non-radargram directories
    # in RadarData.
    output_dir = pathlib.Path(output_filepath).parent
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
    sx, sy = subsample_tracks_rdp(xx, yy, epsilon)
    # RDP doesn't dramatically reduce the number of points in each SPRI flight, since
    # they were already pretty sparse.
    sub_lon, sub_lat = proj.transform(
        np.array(sx), np.array(sy), direction=pyproj.enums.TransformDirection.INVERSE
    )

    print(f"Saving subsampled data to {output_filepath}")
    with open(output_filepath, "w") as fp:
        fp.write("ps71_easting,ps71_northing\n")
        data = [f"{pt[0]},{pt[1]}\n" for pt in zip(sx, sy)]
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


# I haven't yet figured out how to extract this data from the segy
# files (and hope to not support them), so just doing paths
# for now.
def extract_lvs_coords(filepath):
    # tab-separated file with fields: [line, trace, lon, lat, alt]
    data = pd.read_csv(filepath)
    field_names = ["line", "trace", "LON", "LAT", "ALT"]
    data = pd.read_csv(filepath, sep="\s+", names=field_names)  # noqa: W605
    lat = data["LAT"]
    lon = data["LON"]
    return np.array(lon), np.array(lat)


def extract_bas_respac(
    data_directory: pathlib.Path,
    index_directory: pathlib.Path,
    epsilon: float,
    force: bool,
):
    # Import data, grouping it into seasons.
    bas_filepath = data_directory / "ANTARCTIC" / "BAS" / "BAS_RESPAC_Radar.xyz"

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
                    _current_record,
                    season,
                    lon,
                    lat,
                    xx,
                    yy,
                    _wgs84_height,
                    _tice,
                    _srfelev,
                    _bedelev,
                ) = tokens
                try:
                    curr_line.append((float(lon), float(lat)))
                except Exception:
                    # Some records don't have position data; just skip them.
                    continue

    # Split each season into segments that can be plotted as line segments.
    ps71 = pyproj.Proj("epsg:3031")
    for season, points in seasons.items():
        season_name = f"BAS_19{season[0:2]}_19{season[2:4]}"
        print(season_name)
        season_dir = index_directory / "ANTARCTIC" / "BAS" / season_name

        try:
            season_dir.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            print(f"Could not create {season_dir}")
            raise

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
            segment_filepath = season_dir / f"segment{segment_count:03d}.csv"
            if force or not segment_filepath.exists():
                segment_count += 1
                lon = segment[:, 0]
                lat = segment[:, 1]
                xx, yy = ps71.transform(lon, lat)
                sx, sy = subsample_tracks_rdp(xx, yy, epsilon)
                with open(segment_filepath, "w") as fp:
                    fp.write("ps71_easting,ps71_northing\n")
                    data = [f"{pt[0]},{pt[1]}\n" for pt in zip(sx, sy)]
                    fp.writelines(data)
            else:
                print(f"Skipping {segment_filepath}")


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
    data_dir = pathlib.Path(args.data_directory)
    index_dir = pathlib.Path(args.index_directory)
    # These DON'T go to the icethk dir, since vostok has radargrams too
    extract_flightlines(data_dir, index_dir, args.epsilon, args.force)

    # BAS's format for respac data is special and won't generalize.
    extract_bas_respac(data_dir, index_dir / "icethk", args.epsilon, args.force)


if __name__ == "__main__":
    main()
