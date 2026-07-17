#! /usr/bin/env python3
import os
import pathlib
import re
import sqlite3
import sys
import time

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, MultiPoint

from bedmap_labels import available_campaigns
from radar_index_utils import count_skip_lines


def load_xy(filepath):
    """
    Extract xy coords from CSV file with ps71_easting and ps71_northing fields.
    """
    skip_lines = count_skip_lines(filepath)
    data = pd.read_csv(filepath, skiprows=skip_lines)

    x_index = [col for col in data.columns if "ps71_easting" in col][0]
    y_index = [col for col in data.columns if "ps71_northing" in col][0]
    xx = data[x_index]
    yy = data[y_index]
    good_idxs = [
        idx
        for idx, x, y in zip(np.arange(len(xx)), xx, yy)
        if not (np.isnan(x) or np.isnan(y))
    ]
    xx = xx[good_idxs]
    yy = yy[good_idxs]
    return xx, yy


def add_campaign_directory_gpkg(
    gpkg_filepath: pathlib.Path,
    campaign_dir: pathlib.Path,
    layer_name: str,
    region: str,
    campaign: str,
    institution: str,
    availability: str,
):
    """
    QGIS can't handle having a separate layer for each flight or segment,
    so collect all granules for each season into a single layer/GeoDataFrame,
    with per-granule metadata providing info on where to download data.
    """
    geometry_names = []
    geometries = []
    granules: list[str] = []
    segments: list[str] = []
    t0 = time.time()
    # This is ugly ... figure out segment/granule from filename
    for csv_filepath in [
        pp for pp in campaign_dir.rglob("*.csv") if not pp.stem.startswith(".")
    ]:
        granule = None
        if institution == "AWI":
            filename = csv_filepath.stem

            # Logic copied from download_awi_pangaea
            # For the MCoRDS data
            # CSVs are in AWI/campaign/DATA_{segment}_{granule}_standard.csv
            mcords_expr = (
                "Data_(?P<segment>[0-9]{8}_[0-9]{2})_(?P<granule>[0-9]{3})_standard"
            )
            # Filenames for the 1995/96 EMR data
            # antr1996_9602102402_EMR600_19960210_00.nc
            emr95_expr = "antr[0-9]{4}_(?P<ymd>[0-9]{6})(?P<hs>[0-9]{4})_(?P<emr>EMR[0-9]{2,3})_[0-9]{8}_(?P<granule>[0-9]{2})"
            # Filenames for the 1996/97 EMR data. And 97/98.
            # It appears that the 5th digit indicates system: 2 for EMR600, 3 for EMR60
            # 19973209_stp10.nc
            emr_expr = "(?P<flight>[0-9]{8})_stp[0-9]{1,2}"

            mcords_match = re.match(mcords_expr, filename)
            emr95_match = re.match(emr95_expr, filename)
            emr_match = re.match(emr_expr, filename)

            if mcords_match is not None:
                segment = mcords_match.group("segment")
                granule = mcords_match.group("granule")
            elif emr95_match is not None:
                segment = emr95_match.group("ymd") + "_" + emr95_match.group("emr")
                granule = emr95_match.group("hs")
            elif emr_match is not None:
                segment = emr_match.group("flight")
            else:
                print(f"Unable to extract segment from filename {filename}")
                raise Exception

        elif institution == "BAS":
            # BAS CSVs are in BAS/{campaign}/{campaign}_{segment}.csv
            # Unfortunately, several of them have trailing underscores.
            segment = csv_filepath.stem
            if segment.startswith("BAS_"):
                segment = segment.removeprefix("BAS_")
            prefix = f"{campaign}_"
            if segment.startswith(prefix):
                segment = segment.removeprefix(prefix)
        elif institution == "CRESIS":
            # CRESIS CSVs are in CRESIS/{campaign}/{segment}/Data_{segment}_{granule}.csv
            segment = csv_filepath.parent.name
            filename = csv_filepath.stem
            granule = filename.split("_")[-1]
        elif institution in ["KOPRI", "UTIG"]:
            # UTIG CSVs are in UTIG/{campaign}/{segment}/{product}_{date}_{segment}_{granule}.csv
            # The KOPRI KRT1 data follows the same pattern
            # (This is the same as CRESIS, but keeping it separate in case we need product)
            if "LVS" == campaign:
                segment = csv_filepath.stem
            elif "AGASEA" == campaign:
                transect, granule = csv_filepath.stem.split("_")
                segment = f"THW_SJB_{transect}"
            elif "KRT1" == campaign:
                filename = csv_filepath.stem
                expr = "KHERA1B_(?P<year>[0-9]{4})(?P<doy>[0-9]{3})_(?P<project>[a-zA-Z0-9]*)_(?P<set>[a-zA-Z0-9]*)_(?P<transect>[a-zA-Z0-9]*)_(?P<granule>[0-9]{3})"
                mm = re.match(expr, filename)
                # Since this is unzipped from a tarball, it doesn't have the
                # directory structure grouping netCDFs for each granule by PST.
                segment = f"{mm['project']}_{mm['set']}_{mm['transect']}"
                granule = mm["granule"]
            else:
                try:
                    segment = csv_filepath.parent.name
                    filename = csv_filepath.stem
                    granule = filename.split("_")[-1]
                except Exception as ex:
                    print(f"Can't process {csv_filepath}")
                    raise
        elif institution == "LDEO":
            # The AGAP_BANDIT CSVs are in
            # LDEO/AGAP_BANDIT/{segment}/{flight}_{segment}-{granule}_{product}.csv
            # Unfortunately, {segment}-{granule} is not necessarily unique;
            # they have overlaps for F39b and F51b on T10210, so we'll include
            # the flight in the segment name.
            filename = csv_filepath.stem
            segment = filename.split("-")[0]
            granule = filename.split("-")[1].split("_")[0]
        elif institution == "STANFORD":
            # Another ground-tracks-only dataset.
            segment = csv_filepath.stem
        else:
            print(f"institution {institution} not supported!")

        # QUESTION: Does this need to be unique? (e.g. guarantee only one F01 in the whole dataset?)
        if granule is None:
            geometry_name = f"{institution}_{campaign}_{segment}"
        else:
            geometry_name = f"{institution}_{campaign}_{segment}_{granule}"

        # Add a layer with these features to the GeoPackage
        try:
            xx, yy = load_xy(csv_filepath)
        except Exception as ex:
            print(f"Could not load XY from {csv_filepath}")
            print(f"{ex}")
            continue
        if len(xx) < 2:
            print(f"Cannot create feature from {csv_filepath}; too few points")
        else:
            coords = np.array([[x1, y1] for x1, y1 in zip(xx, yy)])
            points = LineString(coords)
            geometry_names.append(geometry_name)
            granules.append(str(granule))
            segments.append(segment)
            geometries.append(points)
    t1 = time.time()

    # Look up relative path to all granules.
    # We want this info in the survey table to QGIS can easily access it.
    # (For categorized styling of features within a layer, we can do
    # operations on attributes within that table, so having filepath as
    # an attribute is useful.)
    with sqlite3.connect(gpkg_filepath) as connection:
        cursor = connection.cursor()
        relative_paths = []
        for geometry_name in geometry_names:
            cmd = (
                f'SELECT destination_path FROM granules WHERE name IS "{geometry_name}"'
            )
            try:
                result = cursor.execute(cmd)
                rows = result.fetchall()
                relative_path = rows[0][0]
            except IndexError as ex:
                # This is expected if there is no corresponding entry in the
                # granules table.
                print(f"Unable to find {geometry_name} in geopackage granules table")
                print(f"{ex}")
                relative_path = ""
                raise
            except TypeError as ex:
                print(f"Error in executing command: {cmd} \n {ex}")
                relative_path = ""
            except sqlite3.OperationalError as ex:
                print(f"Error in executing command: {cmd} \n {ex}")
                relative_path = ""

            relative_paths.append(relative_path)

    gdf = gpd.GeoDataFrame(geometries, columns=["geometry"])
    gdf["institution"] = [institution for _ in geometry_names]
    gdf["region"] = [region.lower() for _ in geometry_names]
    gdf["campaign"] = [campaign for _ in geometry_names]
    gdf["segment"] = segments
    gdf["granule"] = granules
    gdf["relative_path"] = relative_paths
    # TODO: Way to make this an enum?
    gdf["availability"] = [availability for _ in geometry_names]
    # This info is stored in the granules table, rather than with the geometry
    gdf["uri"] = [None for _ in geometry_names]
    gdf["name"] = geometry_names
    if region == "ARCTIC":
        gdf.crs = "EPSG:3413"
    elif region == "ANTARCTIC":
        gdf.crs = "EPSG:3031"
    else:
        raise (Exception(f"Unrecognized region: {region}"))

    t2 = time.time()
    # This takes > 1 sec/write, which seems excessive. It looks like some work
    # has been done speeding this up, but it's in Fiona 1.9/2.x
    # 2025-06-25: It looks like geopandas has added support for pyogrio;
    # this got rid of the crs argument. However, it also looks like attributes
    # aren't being handled properly? Maybe they need to be provided as "metadata"?
    # gdf.to_file(gpkg_filepath, driver="GPKG", layer=layer_name, crs=gdf.crs)
    gdf.to_file(gpkg_filepath, driver="GPKG", layer=layer_name)
    t3 = time.time()
    print(
        f"{(t1 - t0):0.4f} s loading geometry; {(t2 - t1):0.4f} sec creating GeoDataFrame; {(t3 - t2):0.4f} adding to GeoPackage"
    )


# QUESTION: Should I be passing around pathlib.Path objects, rather than strings?
def add_csv_gpkg(
    gpkg_filepath: str,
    csv_filepath: str,
    layer_name: str,
    granule: str,
    segment: str,
    region: str,
    campaign: str,
    institution: str,
    uri: str,
    availability: str,
):
    """ "
    Add data in the CSV to the Geopackage, and create a QGIS layer with
    that as the data backend.

    This is used for the BEDMAP data, and anywhere else that a full campaign
    worth of radar tracks is included in a single CSV file.

    We can't just directly drag the Geopackage into QGIS because:
    1) I don't see how to group layers within the GeoPackage file
    2) Programmatically styling the geopackage is awkward. I've only
      figured out how to do it when running in the QGIS console.

    * layer_name: needs to be unique
    * gpkg_filepath: GeoPackage
    * availability: 's'upported, 'a'vailable (but not supported), 'u'navailable
    """
    # Add a layer with these features to the GeoPackage
    xx, yy = load_xy(csv_filepath)
    coords = np.array([[x1, y1] for x1, y1 in zip(xx, yy)])

    # points = LineString(coords)
    points = MultiPoint(coords)
    geometries = [points]
    gdf = gpd.GeoDataFrame(geometries, columns=["geometry"])
    gdf["name"] = layer_name
    gdf["uri"] = uri
    gdf["institution"] = institution
    gdf["region"] = region.lower()
    gdf["granule"] = granule
    gdf["segment"] = segment
    gdf["campaign"] = campaign
    # TODO: Way to make this an enum?
    gdf["availability"] = availability
    if region.lower() == "arctic":
        gdf.crs = "EPSG:3413"
    elif region.lower() == "antarctic":
        gdf.crs = "EPSG:3031"
    else:
        raise (Exception(f"Unrecognized region: {region}"))

    # TODO: Create campaign table and add metadata

    gdf.to_file(gpkg_filepath, driver="GPKG", layer=layer_name)


def add_bedmap_layers(data_dir, gpkg_filepath):
    bedmap_dir = os.path.join(data_dir, "ANTARCTIC", "BEDMAP")

    institutions = [dd for dd in os.listdir(bedmap_dir) if not dd.startswith(".")]
    institutions.sort()

    for institution in institutions:
        institution_dir = os.path.join(bedmap_dir, institution)
        print(
            f"Adding Bedmap layers for institution {institution}; dir = {institution_dir}"
        )
        filenames = [
            ff
            for ff in os.listdir(institution_dir)
            if ff.endswith("csv") and not ff.startswith(".")
        ]

        # TODO: This sorts by *year*, rather than by campaign name
        filenames.sort()  # QUESTION: Why doesn't this seem to be working?
        for filename in filenames:
            if filename.startswith("BEDMAP1"):
                campaign = "BEDMAP1"
            else:
                ff = filename.strip(".csv")
                if ff in available_campaigns:
                    print(f"Skipping {ff}; full data is available")
                    continue
                tokens = ff.split("_")
                # intentionally include the year
                campaign = "_".join(tokens[1:-2])

            csv_filepath = os.path.join(institution_dir, filename)
            print(f"Trying to create a layer from {csv_filepath}")
            layer_name = f"{institution}_{campaign}"

            granule = None
            segment = None
            uri = None
            availability = "u"  # Unavailable
            add_csv_gpkg(
                gpkg_filepath,
                csv_filepath,
                layer_name,
                granule,
                segment,
                region,
                campaign,
                institution,
                uri,
                availability,
            )


def add_radargram_layers(
    region: str, institution: str, data_dir: pathlib.Path, gpkg_filepath: pathlib.Path
):
    institution_dir = data_dir / region / institution
    if not institution_dir.is_dir():
        print(f"No {region} data from {institution}. dir={institution_dir}")
        return
    campaigns = [dd for dd in institution_dir.iterdir() if dd.is_dir()]
    campaigns.sort()
    for campaign_dir in campaigns:
        print(f"Processing {campaign_dir.name} radargram tracks")
        availability = "a"
        campaign = campaign_dir.name
        add_campaign_directory_gpkg(
            gpkg_filepath,
            campaign_dir,
            campaign,
            region,
            campaign,
            institution,
            availability,
        )


def add_icethk_layers(
    region: str,
    institution: str,
    track_dir: pathlib.Path,
    gpkg_filepath: pathlib.Path,
    availability: str = "u",
):
    data_dir = track_dir / region / institution
    if not data_dir.is_dir():
        print(f"No {region} icethk data from {institution}")
        return
    campaigns = [dd for dd in data_dir.iterdir() if dd.is_dir()]
    campaigns.sort()
    for campaign_dir in campaigns:
        campaign = campaign_dir.name
        print(f"Processing {campaign} ice thicknesses")
        add_campaign_directory_gpkg(
            gpkg_filepath,
            campaign_dir,
            campaign,
            region,
            campaign,
            institution,
            availability,
        )


def add_spri_layers(index_dir, gpkg_filepath):
    institution = "STANFORD"
    campaign = "SPRI_NSF_TUD"
    spri_dir = os.path.join(index_dir, "ANTARCTIC", institution, campaign)
    print(spri_dir)
    layer_name = f"{institution}_{campaign}"

    # TODO: Stanford is a special case here, since radargrams are available but
    #   not yet in a format that I can support.
    availability = "a"  # Available
    add_campaign_directory_gpkg(
        gpkg_filepath, spri_dir, layer_name, region, campaign, institution, availability
    )


def main(antarctic: bool, track_dir, gpkg_filepath):
    # Add the vostok lines ... these are available, but I don't
    # yet support them, so am treating them like icethk lines

    # for provider in ["AWI", "BAS", "CRESIS", "KOPRI", "LDEO", "UTIG"]:
    # DO NOT COMMIT. Jumping to where errors are ...revolutionise2
    for provider in ["AWI"]:
        add_radargram_layers(region, provider, track_dir, gpkg_file)

    return

    # TODO: For arctic, this may need to include UTIG
    for provider in ["BAS"]:
        add_icethk_layers(region, provider, track_dir, gpkg_file, "u")

    if antarctic:
        add_spri_layers(track_dir, gpkg_file)

    # ------- confirmed to work ----------
    if antarctic:
        add_icethk_layers("ANTARCTIC", "UTIG", track_dir / "icethk", gpkg_filepath, "a")

    if antarctic:
        add_bedmap_layers(track_dir, gpkg_file)
    else:
        # TODO: Add Bedmachine coverage data?
        pass


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("--antarctic", action="store_true")
    parser.add_argument("--arctic", action="store_true")

    parser.add_argument(
        "track_dir",
        help="Root directory for generated subsampled files derived from radargrams",
    )
    parser.add_argument(
        "index",
        help="Geopackage database to update with geometry for radar lines",
    )
    args = parser.parse_args()

    antarctic = False
    if args.antarctic:
        antarctic = True
        region = "ANTARCTIC"
    elif args.arctic:
        antarctic = False
        region = "ARCTIC"
    else:
        print("ERROR: Must specify either --antarctic or --arctic")
        sys.exit(-1)

    gpkg_file = pathlib.Path(args.index)
    track_dir = pathlib.Path(args.track_dir)

    main(antarctic, track_dir, gpkg_file)
