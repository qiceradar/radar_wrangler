#! /usr/bin/env python3

import geopandas as gpd
import numpy as np
import os
import pandas as pd
import pathlib
from shapely.geometry import Point, LineString, MultiPoint
import time

from radar_index_utils import count_skip_lines
from bedmap_labels import available_campaigns


def load_xy(filepath):
    '''
    Extract xy coords from CSV file with ps71_easting and ps71_northing fields.
    '''
    skip_lines = count_skip_lines(filepath)
    data = pd.read_csv(filepath, skiprows=skip_lines)

    x_index = [col for col in data.columns if 'ps71_easting' in col][0]
    y_index = [col for col in data.columns if 'ps71_northing' in col][0]
    xx = data[x_index]
    yy = data[y_index]
    good_idxs = [idx for idx, x, y in zip(
        np.arange(len(xx)), xx, yy) if not (np.isnan(x) or np.isnan(y))]
    xx = xx[good_idxs]
    yy = yy[good_idxs]
    return xx, yy

def add_campaign_directory_gpkg(gpkg_filepath, campaign_dir, layer_name,
                                campaign, institution, availability):
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
    names = []
    geometries = []
    granules = []
    segments = []
    t0 = time.time()
    for csv_filepath in pathlib.Path(campaign_dir).rglob("*.csv"):
        rel_path = pathlib.Path(csv_filepath).relative_to(campaign_dir)
        if len(rel_path.parts) == 2:
            segment, _ = rel_path.parts
            granule = rel_path.stem
        elif len(rel_path.parts) == 1:
            segment = rel_path.stem
            granule = segment

        # QUESTION: Does this need to be unique? (e.g. guarantee only one F01 in the whole dataset?)
        geometry_name = "_".join([institution, campaign, granule])
        names.append(geometry_name)
        granules.append(granule)
        segments.append(segment)

        # Add a layer with these features to the GeoPackage
        xx, yy = load_xy(csv_filepath)
        coords = np.array([[x1, y1] for x1, y1 in zip(xx, yy)])
        points = LineString(coords)
        geometries.append(points)
    t1 = time.time()

    gdf = gpd.GeoDataFrame(geometries, columns=['geometry'])
    gdf['institution'] = [institution for _ in names]
    gdf['campaign'] = [campaign for _ in names]
    gdf['segment'] = segments
    gdf['granule'] = granules
    # TODO: Way to make this an enum?
    gdf['availability'] = [availability for _ in names]
    # TODO: this will probably need to be a lookup somewhere, unless URIs are
    # embedded in the comments in the CSV
    gdf['uri'] = [None for _ in names]
    gdf['name'] = names
    # QUESTION: Setting the CRS here doesn't seem to propagate to QGIS; instead,
    #    I have to set it explicitly when creting the QGIS layer from this table.
    gdf.crs = 'EPSG:3031'

    # TODO: Create campaign table and add metadata
    t2 = time.time()
    # This takes > 1 sec/write, which seems excessive. It looks like some work
    # has been done speeding this up, but it's in Fiona 1.9/2.x
    gdf.to_file(gpkg_filepath, driver='GPKG', layer=layer_name, crs=gdf.crs)
    t3 = time.time()
    print("{:0.4f} s loading geometry; {:0.4f} sec creating GeoDataFrame; {:0.4f} adding to GeoPackage".format(t1-t0, t2-t1, t3-t2))

# QUESTION: Should I be passing around pathlib.Path objects, rather than strings?
def add_csv_gpkg(gpkg_filepath: str,
                 csv_filepath: str,
                 layer_name: str, granule: str, segment: str, campaign: str,
                 institution: str, uri: str, availability: str):
    """"
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

    #points = LineString(coords)
    points = MultiPoint(coords)
    geometries = [points]
    gdf = gpd.GeoDataFrame(geometries, columns=['geometry'])
    gdf['name'] = layer_name
    gdf['uri'] = uri
    gdf['institution'] = institution
    gdf['granule'] = granule
    gdf['segment'] = segment
    gdf['campaign'] = campaign
    # TODO: Way to make this an enum?
    gdf['availability'] = availability
    gdf.crs = 'EPSG:3031'

    # TODO: Create campaign table and add metadata

    gdf.to_file(gpkg_filepath, driver='GPKG', layer=layer_name)


def add_bedmap_layers(data_dir, gpkg_filepath):
    bedmap_dir = os.path.join(data_dir, "ANTARCTIC", "BEDMAP")

    institutions = [ff for ff in os.listdir(bedmap_dir)]
    institutions.sort()

    for institution in institutions:
        institution_dir = os.path.join(bedmap_dir, institution)
        filenames = [ff for ff in os.listdir(institution_dir)
                     if ff.endswith("csv")]

        # TODO: This sorts by *year*, rather than by campaign name
        filenames.sort()  # QUESTION: Why doesn't this seem to be working?
        for filename in filenames:
            if filename.startswith('BEDMAP1'):
                campaign = "BEDMAP1"
            else:
                ff = filename.strip('.csv')
                if ff in available_campaigns:
                    print("Skipping {}; full data is available".format(ff))
                    continue
                tokens = ff.split('_')
                # intentionally include the year
                campaign = "_".join(tokens[1:-2])

            csv_filepath = os.path.join(institution_dir, filename)
            print("Trying to create a layer from {}".format(csv_filepath))
            layer_name = '_'.join([institution, campaign])

            granule = None
            segment = None
            uri = None
            availability = 'u'  # Unavailable
            add_csv_gpkg(gpkg_filepath, csv_filepath, layer_name,
                            granule, segment, campaign, institution,
                            uri, availability)

def add_radargram_layers(institution, data_dir, gpkg_filepath):
    region = "ANTARCTIC"
    data_dir = os.path.join(data_dir, region, institution)
    if not os.path.isdir(data_dir):
        print("No {} data from {}".format(region, institution))
        return
    campaigns = [dd for dd in os.listdir(data_dir)
                if os.path.isdir(os.path.join(data_dir, dd))]
    campaigns.sort()
    for campaign in campaigns:
        print("Processing {}".format(campaign))
        availability = 's'  # Supported
        campaign_dir = os.path.join(data_dir, campaign)
        add_campaign_directory_gpkg(gpkg_filepath, campaign_dir, campaign,
                                    campaign, institution, availability)


def add_spri_layers(index_dir, gpkg_filepath):
    institution = "STANFORD"
    campaign = "SPRI_NSF_TUD"
    spri_dir = os.path.join(index_dir, "ANTARCTIC", institution, campaign)
    print(spri_dir)
    layer_name = "_".join([institution, campaign])

    # TODO: Stanford is a special case here, since radargrams are available but
    #   not yet in a format that I can support.
    availability = 'a'  # Available
    add_campaign_directory_gpkg(gpkg_filepath, spri_dir, layer_name,
                                campaign, institution, availability)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("radargram_index_directory",
                        help="Root directory for generated subsampled files derived from radargrams")
    parser.add_argument("icethk_index_directory",
                        help="Root directory for generated subsampled files derived from icethk-only")
    args = parser.parse_args()

    gpkg_file = os.path.join(args.radargram_index_directory, "qiceradar_index.gpkg")

    # Create Antarctic map!
    #add_bedmap_layers(args.radargram_index_directory, gpkg_file)
    for provider in ["BAS", "CRESIS", "KOPRI" , "LDEO", "UTIG"]:
        add_radargram_layers(provider, args.radargram_index_directory, gpkg_file)
    #add_spri_layers(args.icethk_index_directory, gpkg_file)