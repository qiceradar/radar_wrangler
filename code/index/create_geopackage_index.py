#! /usr/bin/env python3
import os
import pathlib
import sqlite3
import time

import geopandas as gpd
import numpy as np
import pandas as pd
from bedmap_labels import available_campaigns
from radar_index_utils import count_skip_lines
from shapely.geometry import LineString, MultiPoint


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
    gpkg_filepath, campaign_dir, layer_name, region, campaign, institution, availability
):
    """
    QGIS can't handle having a separate layer for each flight or segment,
    so collect all granules for each season into a single layer/GeoDataFrame,
    with per-granule metadata providing info on where to download data.

    TODO: I haven't yet figured out how to track metadata from download
        through extraction and into database creation.
        This should probably eventually include:
        * download_uri -- address for wget
        * display_uri  -- file:///path/to/radaragram
        * campaign -- foreign key into separate table with detailed
            information about the season. (or maybe just let that live in
            the netCDFs provided?)
        * institution -- eventually another foreign key
        * instrumment -- eventually another foreign key into table with ifo
            about different instruments. (Maybe leave this attached per-radargram?)

    """
    geometry_names = []
    geometries = []
    granules = []
    segments = []
    t0 = time.time()
    for csv_filepath in pathlib.Path(campaign_dir).rglob("*.csv"):
        relative_path = pathlib.Path(csv_filepath).relative_to(campaign_dir)
        granule = None
        if institution == "BAS":
            # BAS CSVs are in BAS/{campaign}/{campaign}_{segment}.csv
            # Unfortunately, several of them have trailing underscores.
            # try:
            #     # For the radar lines
            #     segment = relative_path.stem.split('_')[-1]
            # except IndexError:
            #     # For the depths-only lines
            #     segment = relative_path.stem
            # Ick -- this is yet another way of parsing the BAS filenames
            # (download_bas uses regexes; this is simpler, but will break for GOG3)
            # TODO: try to refactor and pull that parsing function into single place?
            segment = relative_path.stem
            if segment.startswith("BAS_"):
                segment = segment[4:]
            prefix = f"{campaign}_"
            if segment.startswith(prefix):
                segment = segment[len(prefix) :]
        elif institution == "CRESIS":
            # CRESIS CSVs are in CRESIS/{campaign}/{segment}/Data_{segment}_{granule}.csv
            segment, _ = relative_path.parts
            filename = relative_path.stem
            granule = filename.split("_")[-1]
        elif institution in ["KOPRI", "UTIG"]:
            # UTIG CSVs are in UTIG/{campaign}/{segment}/{product}_{date}_{segment}_{granule}.csv
            # The KOPRI KRT1 data follows the same pattern
            # (This is the same as CRESIS, but keeping it separate in case we need product)
            if "SOAR_LVS" == campaign:
                segment = relative_path.stem
            else:
                try:
                    segment, _ = relative_path.parts
                    filename = relative_path.stem
                    granule = filename.split("_")[-1]
                except Exception as ex:
                    print(f"Can't process {relative_path}")
                    raise ex
        elif institution == "LDEO":
            # The AGAP_BANDIT CSVs are in
            # LDEO/AGAP_BANDIT/{segment}/{flight}_{segment}-{granule}_{product}.csv
            # Unfortunately, {segment}-{granule} is not necessarily unique;
            # they have overlaps for F39b and F51b on T10210, so we'll include
            # the flight in the segment name.
            filename = relative_path.stem
            segment = filename.split("-")[0]
            granule = filename.split("-")[1].split("_")[0]
        elif institution == "STANFORD":
            # Another ground-tracks-only dataset.abs
            segment = relative_path.stem
        else:
            print(f"institution {institution} not supported!")

        # QUESTION: Does this need to be unique? (e.g. guarantee only one F01 in the whole dataset?)
        if granule is None:
            geometry_name = "_".join([institution, campaign, segment])
        else:
            geometry_name = "_".join([institution, campaign, segment, granule])

        # Add a layer with these features to the GeoPackage
        xx, yy = load_xy(csv_filepath)
        if len(xx) < 2:
            print("Cannot create feature from {csv_filepath}; too few points")
        else:
            coords = np.array([[x1, y1] for x1, y1 in zip(xx, yy)])
            points = LineString(coords)
            geometry_names.append(geometry_name)
            granules.append(granule)
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
        for name in geometry_names:
            cmd = f'SELECT destination_path FROM granules WHERE name IS "{name}"'
            try:
                result = cursor.execute(cmd)
                rows = result.fetchall()
                relative_path = rows[0][0]
            except IndexError as ex:
                # This is expected if there is no corresponding entry in the
                # granules table.
                print(f"Unable to find {name} in geopackage granules table")
                print(f"{ex}")
                relative_path = ""
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
    # TODO: this will probably need to be a lookup somewhere, unless URIs are
    # embedded in the comments in the CSV
    gdf["uri"] = [None for _ in geometry_names]
    gdf["name"] = geometry_names
    if region == "ARCTIC":
        gdf.crs = "EPSG:3413"
    elif region == "ANTARCTIC":
        gdf.crs = "EPSG:3031"
    else:
        raise (Exception("Unrecognized region: {}".format(region)))

    # TODO: Create campaign table and add metadata
    t2 = time.time()
    # This takes > 1 sec/write, which seems excessive. It looks like some work
    # has been done speeding this up, but it's in Fiona 1.9/2.x
    gdf.to_file(gpkg_filepath, driver="GPKG", layer=layer_name, crs=gdf.crs)
    t3 = time.time()
    print(
        "{:0.4f} s loading geometry; {:0.4f} sec creating GeoDataFrame; {:0.4f} adding to GeoPackage".format(
            t1 - t0, t2 - t1, t3 - t2
        )
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
        raise (Exception("Unrecognized region: {}".format(region)))

    # TODO: Create campaign table and add metadata

    gdf.to_file(gpkg_filepath, driver="GPKG", layer=layer_name)


def add_bedmap_layers(data_dir, gpkg_filepath):
    bedmap_dir = os.path.join(data_dir, "ANTARCTIC", "BEDMAP")

    institutions = list(os.listdir(bedmap_dir))
    institutions.sort()

    for institution in institutions:
        institution_dir = os.path.join(bedmap_dir, institution)
        filenames = [ff for ff in os.listdir(institution_dir) if ff.endswith("csv")]

        # TODO: This sorts by *year*, rather than by campaign name
        filenames.sort()  # QUESTION: Why doesn't this seem to be working?
        for filename in filenames:
            if filename.startswith("BEDMAP1"):
                campaign = "BEDMAP1"
            else:
                ff = filename.strip(".csv")
                if ff in available_campaigns:
                    print("Skipping {}; full data is available".format(ff))
                    continue
                tokens = ff.split("_")
                # intentionally include the year
                campaign = "_".join(tokens[1:-2])

            csv_filepath = os.path.join(institution_dir, filename)
            print("Trying to create a layer from {}".format(csv_filepath))
            layer_name = "_".join([institution, campaign])

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


def add_radargram_layers(region, institution, data_dir, gpkg_filepath):
    data_dir = os.path.join(data_dir, region, institution)
    if not os.path.isdir(data_dir):
        print("No {} data from {}".format(region, institution))
        return
    campaigns = [
        dd for dd in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, dd))
    ]
    campaigns.sort()
    for campaign in campaigns:
        print("Processing {} radargram tracks".format(campaign))
        availability = "a"
        campaign_dir = os.path.join(data_dir, campaign)
        add_campaign_directory_gpkg(
            gpkg_filepath,
            campaign_dir,
            campaign,
            region,
            campaign,
            institution,
            availability,
        )


def add_icethk_layers(region, institution, data_dir, gpkg_filepath, availability="u"):
    data_dir = os.path.join(data_dir, region, institution)
    if not os.path.isdir(data_dir):
        print("No {} data from {}".format(region, institution))
        return
    campaigns = [
        dd for dd in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, dd))
    ]
    campaigns.sort()
    for campaign in campaigns:
        print("Processing {} ice thicknesses".format(campaign))
        availability = availability
        campaign_dir = os.path.join(data_dir, campaign)
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
    layer_name = "_".join([institution, campaign])

    # TODO: Stanford is a special case here, since radargrams are available but
    #   not yet in a format that I can support.
    availability = "a"  # Available
    add_campaign_directory_gpkg(
        gpkg_filepath, spri_dir, layer_name, region, campaign, institution, availability
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "radargram_index_directory",
        help="Root directory for generated subsampled files derived from radargrams",
    )
    parser.add_argument(
        "icethk_index_directory",
        help="Root directory for generated subsampled files derived from icethk-only",
    )
    parser.add_argument(
        "antarctic_index",
        help="Geopackage database to update with geometry for Antarctic radar lines",
    )
    parser.add_argument(
        "arctic_index",
        help="Geopackage database to update with geometry for Arctic radar lines",
    )
    args = parser.parse_args()

    for region in ["ANTARCTIC", "ARCTIC"]:
        if region == "ARCTIC":
            gpkg_file = args.arctic_index
        else:
            gpkg_file = args.antarctic_index

        # Add the vostok lines ... these are available, but I don't
        # yet support them, so am treating them like icethk lines
        if region == "ANTARCTIC":
            add_icethk_layers("ANTARCTIC", "UTIG", args.icethk_index_directory, gpkg_file, "a")

        if region == "ARCTIC":
            # TODO: Add Bedmachine coverage data?
            pass
        else:
            add_bedmap_layers(args.radargram_index_directory, gpkg_file)

        for provider in ["BAS", "CRESIS", "KOPRI", "LDEO", "UTIG"]:
            add_radargram_layers(
                region, provider, args.radargram_index_directory, gpkg_file
            )

        # TODO: For arctic, this may need to include UTIG
        for provider in ["BAS"]:
            add_icethk_layers(region, provider, args.icethk_index_directory, gpkg_file, "u")

        if region == "ANTARCTIC":
            add_spri_layers(args.icethk_index_directory, gpkg_file)
