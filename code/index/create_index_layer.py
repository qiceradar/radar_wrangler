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

from radar_index_utils import count_skip_lines

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
    ##            CRESIS              ##
    ####################################
    'CRESIS_2009_AntarcticaTO_AIR_BM3.csv': 'CRESIS/2009_Antarctica_TO',
    # This one has swath data in Bedmap -- one of the surveys was tight enough
    # to get almost full coverage.
    'CRESIS_2009_Thwaites_AIR_BM3.csv': 'CRESIS/2009_Antarctica_TO',
    'CRESIS_2013_Siple-Coast_AIR_BM3.csv': 'CRESIS/2013_Antarctica_Basler',


    ####################################
    ##            KOPRI               ##
    ####################################
    # Unfortunately, the KOPRI/KRT1 survey release didn't include Campbell glacier (which is in the bedmap release)
    # It's also missing all of the Nansen lines.
    # 'KOPRI_2017_KRT1_AIR_BM3.csv': '',
	# 'KOPRI_2018_KRT2_AIR_BM3.csv': '',

    ####################################
    ##              LDEO              ##
    ####################################
    # CRESIS also released some of this data via data.cresis.ku.edu, but it was missing a few transects
    'LDEO_2007_AGAP-GAMBIT_AIR_BM2': 'LDEO/AGAP_GAMBIT',

    # According to Studinger, the Recovery Lakes survey was part of the
    # AGAP-GAMBIT one, but the lines weren't released in the same dataset.
    # 'LDEO_2007_Recovery-Lakes_AIR_BM2.csv': '',
    # 'LDEO_2015_ROSETTA_AIR_BM3.csv': '',


    ####################################
    ##              NASA              ##
    ####################################

    # TODO: Should I download these data from NSIDC, rather than treating
    #       them like the rest of the cresis data?

    # Some of the lines are missing in the CRESIS data, but I think those
    # are all due to my throwing out granules with single bad Longitude coords.
    #'NASA_2002_ICEBRIDGE_AIR_BM2.csv': 'CRESIS/2002_Antarctica_P3Chile',
    'NASA_2004_ICEBRIDGE_AIR_BM2.csv': 'CRESIS/2004_Antarctica_P3Chile',
    # There's one line that doesn't appear in the CRESIS data,
    # and a polar orbit flight that's not in the NASA layer
    'NASA_2009_ICEBRIDGE_AIR_BM2.csv': 'CRESIS/2009_Antarctica_DC8',
    # Exactly the same as 2009 -- a few lines missing in each direction
    'NASA_2010_ICEBRIDGE_AIR_BM2.csv': 'CRESIS/2010_Antarctica_DC8',
    # It looks like this was accidentally a copy of the 2002_ICEBRIDGE??
    #'NASA_2011_ICEBRIDGE_AIR_BM2.csv': '',
    'NASA_2013_ICEBRIDGE_AIR_BM3.csv': 'CRESIS/2013_Antarctica_P3',
    'NASA_2014_ICEBRIDGE_AIR_BM3.csv': 'CRESIS/2014_Antarctica_DC8',
    'NASA_2016_ICEBRIDGE_AIR_BM3.csv': 'CRESIS/2016_Antarctica_DC8',
    'NASA_2017_ICEBRIDGE_AIR_BM3.csv': ('CRESIS/2017_Antarctica_P3', 'CRESIS/2017_Antarctica_Basler'),
    'NASA_2018_ICEBRIDGE_AIR_BM3.csv': 'CRESIS/2018_Antarctica_DC8',
    'NASA_2019_ICEBRIDGE_AIR_BM3.csv': 'CRESIS/2019_Antarctica_GV',

    ####################################
    ##              NIPR              ##
    ####################################
    # 'NIPR_1992_JARE33_GRN_BM3.csv': '',
    # 'NIPR_1996_JARE37_GRN_BM3.csv': '',
    'NIPR_1999_JARE40_GRN_BM2.csv': 'NIPR_1999_JARE40_GRN_BM3',	# Exact same points appear in both BM2 and BM3
	# 'NIPR_1999_JARE40_GRN_BM3.csv': '',
    'NIPR_2007_JARE49_GRN_BM2.csv': 'NIPR_2007_JARE49_GRN_BM3', # BM3 has denser bed picks for same lines
    # 'NIPR_2007_JARE49_GRN_BM3.csv': '',
    'NIPR_2007_JASE_GRN_BM2.csv': 'NIPR_2007_JASE_GRN_BM3',  # BM3 has denser bed picks for same lines
    # 'NIPR_2007_JASE_GRN_BM3.csv': '',
    # 'NIPR_2012_JARE54_GRN_BM3.csv': '',
    # 'NIPR_2018_JARE60_GRN_BM3.csv': '',
    # 'NIPR_2017_JARE59_GRN_BM3.csv': '',


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
    # The data released at NSIDC is missing a few transects, so we want to keep plotting this.
    # "UTIG_2008_ICECAP_AIR_BM2": "UTIG/ICECAP",
    # "UTIG_2010_ICECAP_AIR_BM3": "UTIG/ICECAP",

    # 4 Gimble lines made it into the ICECAP release, but I haven't
    # found anything else.
    # "UTIG_2013_GIMBLE_AIR_BM3":

    # EAGLE mostly matches BEDMAP. netCDF files are there, but the
    # extracted lines seem to be missing:
    # * most of PEL/JKB2n/Y18a
    # * all of PEL/JKB2n/Y20a
    "UTIG_2015_EAGLE_AIR_BM3": "UTIG/EAGLE",

    # Additionally, some of the files have issues:
    # * OIA/JKB2n/X60a has good data when plotted in jupyter, but the
    #   extracted path is simply [nan,nan]
    #   => the first 1180 traces have 'nan' for lat/lon
    # * OIA/JKB2n/X51a seems half missing, even though I've downloaded
    #   both granules. The turn on the southing end of the survey wasn't
    #   a turn -- F13T07a and F13T08a are both towards northing.
    "UTIG_2016_OLDICE_AIR_BM3": "UTIG/OIA",
}


def layer_from_kml(layer_name, kml_filepath, color):
    # URI does require THREE slashes; there will be one already in filepath
    # TODO: Look into pathlib.Path.as_uri()
    kml_uri = "file://{}|layername={}|geometrytype=LineString25D".format(
        kml_filepath, layer_name)
    kml_layer = QgsVectorLayer(kml_uri, layer_name, "ogr")
    # Using Lon/Lat rather than PS71 for consistency between arctic/antarctic
    kml_layer.setCrs(QgsCoordinateReferenceSystem.fromEpsgId(4326))

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

def layer_from_spri_csv(layer_name, csv_filepath, color):
    # URI does require THREE slashes; there will be one already in filepath
    skip_lines = count_skip_lines(csv_filepath)
    # TODO: Look into pathlib.Path.as_uri()
    uri = "file://{}?type=csv&detectTypes=yes&skipLines={}&xField=LON&yField=LAT&crs=EPSG:4326".format(
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
            blue = "31,120,188,255"
            layer = layer_from_csv(campaign, filepath, salmon)
            # TODO: I think it'll be more manageable for debugging if all points
            #     are unchecked by default
            # layer.setItemVisibilityChecked(False)
            QgsProject.instance().addMapLayer(layer, False)
            institution_group.addLayer(layer)

def add_spri_layers(root_group, spri_dir):
    stanford_index = [idx for idx, child in enumerate(root_group.children())
                      if child.name() == "STANFORD"]
    if len(stanford_index) == 0:
        print("Could not find STANFORD group in root's children: {}".format(
            root_group.children()))
        stanford_group = root_group.addGroup(provider)
        stanford_group.setExpanded(False)
    else:
        print("Reusing BEDMAP's {} group!".format(provider))
        stanford_group = root_group.children()[stanford_index[0]]
        if type(stanford_group) != QgsLayerTreeGroup:
            raise Exception(
                "Child named {} exists, but is not a group".format(provider))

    flights = [ff for ff in os.listdir(spri_dir)
               if ff.endswith("csv") and not ff.startswith('.')]
    flights.sort()

    for flight in flights:
        filepath = os.path.join(spri_dir, flight)
        print("trying to add layer from {}".format(filepath))

        # TODO: per-campaign symbol colors!?
        # * unavailable - salmon: 251, 154, 153
        salmon = "251,154,153,255"
        # * unknown - grey 136,136,136
        grey = "136,136,136,255"
        # * unsupported - NYI
        # * available - not displayed (will be blue: 31,120,180, but that's for the individual institution plotting code to handle.
        blue = "31,120,188,255"
        layer = layer_from_spri_csv(flight.split()[0], filepath, grey)
        QgsProject.instance().addMapLayer(layer, False)
        stanford_group.addLayer(layer)


def add_kml_campaigns(provider: str, root_group, index_dir: str):
    """
    For now, all providers have the same structure:
    Campaign, then flight/line.
    This may change if/when we need to propery match granules to LDEO/CRESIS/etc.
    Data
    """
    provider_dir = os.path.join(index_dir, "ANTARCTIC", provider)
    # Use '.' to eliminate the annoying .DS_Store directory
    campaigns = [ff for ff in os.listdir(provider_dir) if ff.endswith("kml")]
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
        campaign_name = campaign.strip(".kml")
        filepath = os.path.join(provider_dir, campaign)
        campaign_layer = layer_from_kml(campaign_name, filepath, '31,120,180,255')
        QgsProject.instance().addMapLayer(campaign_layer, False)
        provider_group.insertLayer(0, campaign_layer)
        #provider_group.addLayer(campaign_layer)
        renderer = campaign_layer.renderer()


# Trying to run this within the Python Console to see if the
# KML layer's renderer will be instantiated there.
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
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("index_directory",
                        help="Root directory for generated subsampled files")
    # TODO: These need to be properly handled eventually, but I'm not subsampling them yet.
    parser.add_argument("spri_directory",
                        help="directory where the SPRI csv files live. ")
    args = parser.parse_args()

    # Initialize QGIS. Needs to be in main to stay in scope
    # qgs = QgsApplication([], False)
    qgs = QgsApplication([], True)
    qgs.initQgis()
    root = QgsProject.instance().layerTreeRoot()
    qiceradar_group = root.insertGroup(0, "QIceRadar Index")

    # Create Antarctic map!
    add_bedmap_layers(qiceradar_group, args.index_directory)
    for provider in ["BAS", "CRESIS", "KOPRI", "LDEO", "UTIG"]:
        add_kml_campaigns(provider, qiceradar_group, args.index_directory)
    add_spri_layers(qiceradar_group, args.spri_directory)

    layer_file = os.path.join(args.index_directory, "qiceradar_index.qlr")

    QgsLayerDefinition.exportLayerDefinition(layer_file, [qiceradar_group])
