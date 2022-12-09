#! /usr/bin/env python3

"""
In order for qgis to be importable, I'm running this in a shell after:
~~~
OLD_PATH=$PATH
OLD_PYTHONPATH=$PYTHONPATH

QGIS_VERSION="QGIS-LTR"

export PATH=/Applications/$QGIS_VERSION.app/Contents/MacOS/bin:$PATH
export PYTHONPATH=/Applications/$QGIS_VERSION.app/Contents/Resources/python/:/Applications/$QGIS_VERSION.app/Contents/Resources/python/plugins
export QGIS_PREFIX_PATH=/Applications/$QGIS_VERSION.app/Contents/MacOS
export QT_QPA_PLATFORM_PLUGIN_PATH=/Applications/$QGIS_VERSION.app/Contents/PlugIns/platforms/
export DYLD_INSERT_LIBRARIES=/Applications/$QGIS_VERSION.app/Contents/MacOS/lib/libsqlite3.dylib
~~~

HOWEVER, doing this makes other python stuff break.
"""

import os
import random

import qgis
from qgis.core import (QgsApplication, QgsCoordinateReferenceSystem, QgsLayerDefinition,
                       QgsLayerTreeGroup, QgsMarkerSymbol, QgsProject, QgsVectorLayer)

###########
# Create root of the QIceRadar layer + hierarchy of data providers
# For now, starting with just BAS, since I have their radar data downloaded

# Each campaign in BEDMAP will be color-coded based on data availability
UNAVAILBLE = 0
UNKNOWN = 1
UNSUPPORTED = 2
SUPPORTED = 3  # Not plotted at all, since institution-specific code will handle that

# TODO: Split BEDMAP1 out into per-institution, where possible (based on available line picks)
# BAS ('66-'87): https://data.bas.ac.uk/metadata.php?id=GB/NERC/BAS/PDC/01357
#


# Map from BEDMAP campaign nomenclature to where the data lives.
# (At least for now, automating the generation of this lookup table isn't time efficient)
# TODO: right now, nothing uses the values here. We need to traverse data provider directories directly to support post-bedmap3 data.
available_campaigns = {
    ####################################
    ##              BAS               ##
    ####################################

    # Evans only available as bed elevation: https://data.bas.ac.uk/metadata.php?id=GB/NERC/BAS/PDC/01347
    # 'BAS_1994_Evans_AIR_BM2': '',
    # Dufek Massif data only available as bed elevation: https://data.bas.ac.uk/metadata.php?id=GB/NERC/BAS/PDC/01344
    # 'BAS_1998_Dufek_AIR_BM2': '',
    # Seems to be bed elevation only: https://data.bas.ac.uk/full-record.php?id=GB/NERC/BAS/PDC/01266
    # 'BAS_2001_Bailey-Slessor_AIR_BM2': '',
    # Again, bed elevations: https://data.bas.ac.uk/full-record.php?id=GB/NERC/BAS/PDC/01274
    # 'BAS_2001_MAMOG_AIR_BM2': '',
    # TORUS data only available as bed elevation: https://data.bas.ac.uk/metadata.php?id=GB/NERC/BAS/PDC/01277
    # 'BAS_2002_TORUS_AIR_BM2': '',
    'BAS_2004_BBAS_AIR_BM2': 'BAS/BBAS',
    'BAS_2005_WISE-ISODYN_AIR_BM2': 'BAS/WISE_ISODYN',
    'BAS_2006_GRADES-IMAGE_AIR_BM2': 'BAS/GRADES_IMAGE',
    'BAS_2007_AGAP_AIR_BM2': 'BAS/AGAP',
    # No source given; radar was DELORES, N. Ross listed as creator
    # 'BAS_2007_Lake-Ellsworth_GRN_BM3': '',
    # Radar was DELORES; created by Ed King; only released grid: https://dx.doi.org/10.5285/54757cbe-0b13-4385-8b31-4dfaa1dab55e
    # 'BAS_2007_Rutford_GRN_BM3': '',
    # Radar was DELORES; A. Smith & R. Bingham; no source.
    # 'BAS_2007_TIGRIS_GRN_BM2': '',
    # Again, no source given; radar was DELORES, N. Ross listed as creator
    # 'BAS_2008_Lake-Ellsworth_GRN_BM3': '',
    # Radar was DELORES; A. Smith & R. Bingham; no source.
    # 'BAS_2009_FERRIGNO_GRN_BM2': '',
    'BAS_2010_IMAFI_AIR_BM2': 'BAS/IMAFI',
    'BAS_2010_IMAFI_AIR_BM3': 'BAS/IMAFI',  # IMAFI appeared in both; unclear why
    # Another bed-elevation only: https://data.bas.ac.uk/full-record.php?id=GB/NERC/BAS/PDC/01356
    # 'BAS_2010_PIG_AIR_BM2': '',  # ???
    # No source given; survey was 1/2 aeromag, 1/2 radar
    # 'BAS_2011_Adelaide_AIR_BM3': '', # ???
    # Radar was DELORES; created by A. Smith; no source or reference given
    # 'BAS_2012_Castle_GRN_BM3': '',
    'BAS_2012_ICEGRAV_AIR_BM3': 'BAS/ICEGRAV',
    # Another PIG survey with DELORES; no source given; D. Vaughn & R. Bingham created data.
    # 'BAS_2013_ISTAR_GRN_BM3': '',
    'BAS_2015_FISS_AIR_BM3': 'BAS/FISS2015',
    # POLARGAP radargrams have lines not in BM3.
    'BAS_2015_POLARGAP_AIR_BM3': 'BAS/POLARGAP',
    'BAS_2016_FISS_AIR_BM3': 'BAS/FISS2016',
    # English-Coast netCDFs appeared alongside FISS data, rather than where the associated BEDMAP3 metadata pointed
    'BAS_2017_English-Coast_AIR_BM3': 'BAS/FISS2016',
    # ??? Looks like 2018 Thwaites was primarily CReSIS gravity data??
    # 'BAS_2018_Thwaites_AIR_BM3': '',
    # 2019 Thwaites radargrams are missing one line that appeared in BM3,
    # so keep plotting them with BM3 as well.
    # 'BAS_2019_Thwaites_AIR_BM3': 'BAS/ITGC_2019',

    ####################################
    ##              LDEO              ##
    ####################################
    'LDEO_2007_AGAP-GAMBIT_AIR_BM2': 'LDEO/AGAP_GAMBIT',

    ####################################
    ##              UTIG              ##
    ####################################
    # "UTIG_1991_CASERTZ_AIR_BM2":
    # "UTIG_1998_West-Marie-Byrd-Land_AIR_BM2":
    # "UTIG_1999_SOAR-LVS-WLK_AIR_BM2":
    # "UTIG_2000_Robb-Glacier_AIR_BM2":

    # The AGASEA data release is missing a bunch of transit/turn lines
    # that DO appear in BEDMAP.
    "UTIG_2004_AGASEA_AIR_BM2": "UTIG/AGASEA",

    # Looks partially, but not completely, in ICECAP release
    # "UTIG_2009_Darwin-Hatherton_AIR_BM3":

    # This is ALMOST a subset of 2010 ICECAP, but there are 3 ASE
    # radials that only appear in the BM2 data.
    # "UTIG_2008_ICECAP_AIR_BM2":
    # "UTIG_2010_ICECAP_AIR_BM3":

    # "UTIG_2013_GIMBLE_AIR_BM3":

    # EAGLE mostly matches BEDMAP. netCDF files are there, but the
    # extracted lines seem to be missing:
    # * most of PEL/JKB2n/Y18a
    # * all of PEL/JKB2n/Y20a
    "UTIG_2015_EAGLE_AIR_BM3": "UTIG/EAGLE",

    # OIA is mostly good. I know i'm missing 2 files and need to track them down.
    # Additionally, some of the files have issues:
    # * OIA/JKB2n/X60a has good data when plotted in jupyter, but the
    #   extracted path is simply [nan,nan]
    #   => the first 1180 traces have 'nan' for lat/lon
    # * OIA/JKB2n/X51a seems half missing, even though I've downloaded
    #   both granules. The turn on the southing end of the survey wasn't
    #   a turn -- F13T07a and F13T08a are both towards northing.
    "UTIG_2016_OLDICE_AIR_BM3": "UTIG/OIA",
}


def count_skip_lines(filepath):
    """
    Count how many comment lines are at the start of a CSV file.

    QGS's vector layer API doesn't appear to have a setting that says
    "ignore all lines starting with a '#'", even though the GUI seems
    to auto-detect that and fill in the number.
    """
    skip_lines = 0
    for line in open(filepath, 'r'):
        if line.startswith("#"):
            skip_lines += 1
        else:
            break
    return skip_lines


def layer_from_kml(layer_name, kml_filepath, color):
    # URI does require THREE slashes; there will be one already in filepath
    # TODO: Look into pathlib.Path.as_uri()
    kml_uri = "file://{}|layername={}|geometrytype=LineString25D".format(
        kml_filepath, layer_name)
    print("Trying to create layer from {}".format(kml_uri))
    kml_layer = QgsVectorLayer(kml_uri, layer_name, "ogr")
    # Using Lon/Lat rather than PS71 for consistency between arctic/antarctic
    kml_layer.setCrs(QgsCoordinateReferenceSystem.fromEpsgId(4326))

    print("kml layer: {}".format(kml_layer))
    print("type of layer: {}".format(type(kml_layer)))
    kml_layer.updateExtents()
    #kml_symbol = kml_layer.renderer().symbol()
    # kml_symbol.setColor(color)
    # print("kml symbol: {}".format(kml_symbol))
    # layer.renderer().setSymbol(symbol)
    return kml_layer


def layer_from_csv(layer_name, csv_filepath, color):
    # URI does require THREE slashes; there will be one already in filepath
    skip_lines = count_skip_lines(csv_filepath)
    # TODO: Look into pathlib.Path.as_uri()
    uri = "file://{}?type=csv&detectTypes=yes&skipLines={}&xField=ps71_easting&yField=ps71_northing&crs=EPSG:3031".format(
        csv_filepath, skip_lines)
    layer = QgsVectorLayer(uri, layer_name, "delimitedtext")
    symbol = QgsMarkerSymbol.createSimple({'name': 'circle',
                                           'color': color,
                                          'outline_style': 'no',
                                           'size': '1',
                                           'size_unit': 'Point',
                                           })

    layer.renderer().setSymbol(symbol)
    layer.updateExtents()
    return layer


def add_bedmap_layers(root_group, data_dir):
    bedmap_dir = os.path.join(data_dir, "ANTARCTIC", "BEDMAP")

    institutions = [ff for ff in os.listdir(bedmap_dir)]
    institutions.sort()

    for institution in institutions:
        institution_group = root_group.addGroup(institution)
        institution_group.setExpanded(False)
        institution_dir = os.path.join(bedmap_dir, institution)
        filenames = [ff for ff in os.listdir(
            institution_dir) if ff.endswith("csv")]
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

            filepath = os.path.join(institution_dir, filename)
            print("Trying to create a layer from {}".format(filepath))

            # TODO: per-campaign symbol colors!?
            # * unavailable - salmon: 251, 154, 153
            salmon = "251,154,153,255"
            # * unknown - grey 136,136,136
            grey = "136,136,136,255"
            # * unsupported - NYI
            # * available - not displayed (will be blue: 31,120,180, but that's for the individual institution plotting code to handle.
            blue = "31,120,138,255"
            layer = layer_from_csv(campaign, filepath, salmon)
            # TODO: I think it'll be more manageable for debugging if all points
            #     are unchecked by default
            # layer.setItemVisibilityChecked(False)
            QgsProject.instance().addMapLayer(layer, False)
            institution_group.addLayer(layer)


def add_kml_layers(provider: str, root_group, data_dir: str):
    """
    For now, all providers have the same structure:
    Campaign, then flight/line.
    This may change if/when we need to propery match granules to LDEO/CRESIS/etc.
    Data
    """
    # Use '.' to eliminate the annoying .DS_Store directory
    campaigns = [ff for ff in os.listdir(data_dir)
                 if os.path.isdir(os.path.join(data_dir, ff)) and not ff.startswith('.')]
    campaigns.sort()
    # Want them in reverse-alpabetical order so when inserted at pos 0
    # they will be above any bedmap layers.
    campaigns.reverse()

    # TODO: This needs to find the provider group first, and only add it if necessary
    provider_index = [idx for idx, child in enumerate(root_group.children())
                      if child.name() == provider]
    if len(provider_index) == 0:
        print("Could not find {} group in root's children: {}".format(
            provider, root_group.children()))
        provider_group = root_group.addGroup(provider)
        provider_group.setExpanded(False)
    else:
        print("Reusing BEDMAP's {} group!".format(provider))
        provider_group = root_group.children()[provider_index[0]]
        if type(provider_group) != QgsLayerTreeGroup:
            raise Exception(
                "Child named {} exists, but is not a group".format(provider))

    for campaign in campaigns:
        print("Processing campaign: {}".format(campaign))
        campaign_group = provider_group.insertGroup(0, campaign)
        campaign_group.setExpanded(False)
        campaign_dir = os.path.join(data_dir, campaign)
        filenames = [ff for ff in os.listdir(campaign_dir)
                     if ff.endswith("kml")]
        filenames.sort()
        for filename in filenames:
            if filename.startswith('.'):
                print("skipping: {}".format(filename))
                continue
            segment = filename.strip(".kml")
            filepath = os.path.join(campaign_dir, filename)
            flight_layer = layer_from_kml(segment, filepath, '31,120,180,255')
            # flight_layer.setItemVisibilityChecked(False)
            QgsProject.instance().addMapLayer(flight_layer, False)
            campaign_group.addLayer(flight_layer)
            renderer = flight_layer.renderer()
            print("After adding to the map, renderer: {}".format(renderer))


def add_provider_layers(provider: str, root_group, data_dir: str):
    """
    For now, all providers have the same structure:
    Campaign, then flight/line.
    This may change if/when we need to propery match granules to LDEO/CRESIS/etc.
    Data
    """
    # Use '.' to eliminate the annoying .DS_Store directory
    campaigns = [ff for ff in os.listdir(data_dir)
                 if os.path.isdir(os.path.join(data_dir, ff)) and not ff.startswith('.')]
    campaigns.sort()
    # Want them in reverse-alpabetical order so when inserted at pos 0
    # they will be above any bedmap layers.
    campaigns.reverse()

    # TODO: This needs to find the BAS group first, and only add it if necessary
    provider_index = [idx for idx, child in enumerate(root_group.children())
                      if child.name() == provider]
    if len(provider_index) == 0:
        print("Could not find {} group in root's children: {}".format(
            provider, root_group.children()))
        provider_group = root_group.addGroup(provider)
        provider_group.setExpanded(False)
    else:
        print("Reusing BEDMAP's {} group!".format(provider))
        provider_group = root_group.children()[provider_index[0]]
        if type(provider_group) != QgsLayerTreeGroup:
            raise Exception(
                "Child named {} exists, but is not a group".format(provider))

    for campaign in campaigns:
        print("Processing campaign: {}".format(campaign))
        campaign_group = provider_group.insertGroup(0, campaign)
        campaign_group.setExpanded(False)
        campaign_dir = os.path.join(data_dir, campaign)
        filenames = [ff for ff in os.listdir(campaign_dir)
                     if ff.endswith("csv")]
        filenames.sort()
        for filename in filenames:
            if filename.startswith('.'):
                print("skipping: {}".format(filename))
                continue
            segment = filename.strip(".csv")
            filepath = os.path.join(campaign_dir, filename)
            flight_layer = layer_from_csv(segment, filepath, '31,120,180,255')
            # flight_layer.setItemVisibilityChecked(False)
            QgsProject.instance().addMapLayer(flight_layer, False)
            campaign_group.addLayer(flight_layer)


# Tryign to run this within the Python Console.
# Unfortunately, it really didn't like that any better.
"""
print("Creating root")
root = QgsProject.instance().layerTreeRoot()
qiceradar_group = root.insertGroup(0, "QIceRadar Index")
index_directory = "/Users/lindzey/Documents/QIceRadar/data_index"
add_kml_layers("UTIG", qiceradar_group,
               os.path.join(index_directory, "ANTARCTIC", "UTIG"))
layer_file = os.path.join(index_directory, "testing.qlr")
print("Saving layer to: {}".format(layer_file))
QgsLayerDefinition.exportLayerDefinition(layer_file, [qiceradar_group])
"""


if __name__ == "__main__":
    # Initialize QGIS. Needs to be in main to stay in scope
    # qgs = QgsApplication([], False)
    qgs = QgsApplication([], True)
    qgs.initQgis()
    root = QgsProject.instance().layerTreeRoot()
    qiceradar_group = root.insertGroup(0, "QIceRadar Index")

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("index_directory",
                        help="Root directory for generated subsampled files")
    args = parser.parse_args()

    # Create Antarctic map!
    # add_bedmap_layers(qiceradar_group, args.index_directory)
    # add_provider_layers("BAS", qiceradar_group,
    #                   os.path.join(args.index_directory, "ANTARCTIC", "BAS"))
    # add_provider_layers("LDEO", qiceradar_group,
    #                    os.path.join(args.index_directory, "ANTARCTIC", "LDEO"))
    add_kml_layers("UTIG", qiceradar_group,
                   os.path.join(args.index_directory, "ANTARCTIC", "UTIG"))

    layer_file = os.path.join(args.index_directory, "testing.qlr")

    QgsLayerDefinition.exportLayerDefinition(layer_file, [qiceradar_group])
