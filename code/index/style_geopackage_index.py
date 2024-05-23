#! /usr/bin/env python3

"""
In order for qgis to be importable, I'm running this in a shell after:
~~~
OLD_PATH=$PATH
OLD_PYTHONPATH=$PYTHONPATH

QGIS_VERSION="QGIS-LTR"

export PATH=/Applications/${QGIS_VERSION}.app/Contents/MacOS/bin:${PATH}
export PYTHONPATH=/Applications/${QGIS_VERSION}.app/Contents/Resources/python/:/Applications/${QGIS_VERSION}.app/Contents/Resources/python/plugins:${OLD_PYTHONPATH}
export QGIS_PREFIX_PATH=/Applications/${QGIS_VERSION}.app/Contents/MacOS
export QT_QPA_PLATFORM_PLUGIN_PATH=/Applications/${QGIS_VERSION}.app/Contents/PlugIns/platforms/
export DYLD_INSERT_LIBRARIES=/Applications/${QGIS_VERSION}.app/Contents/MacOS/lib/libsqlite3.dylib
~~~

HOWEVER, doing this makes other python stuff break.
"""

import sqlite3

from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsLayerDefinition,
    QgsLineSymbol,
    QgsMarkerSymbol,
    QgsProject,
    QgsSingleSymbolRenderer,
    QgsVectorLayer,
)


def style_gpkg_geometries(region: str, root_group, gpkg_filepath):
    institutions = set()
    campaigns = set()
    campaign_availability = {}
    with sqlite3.connect(gpkg_filepath) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM {}".format("gpkg_geometry_columns"))
        for row in cursor:
            campaigns.add(row["table_name"])  # I think this is also the primary key

        for campaign in campaigns:
            cursor = conn.execute("SELECT * FROM '{}'".format(campaign))
            # NOTE: With the current database design, these tables only have one row.
            for row in cursor:
                institutions.add(row["institution"])
                campaign_availability[campaign] = (
                    row["institution"],
                    row["availability"],
                )

    print("{} granules from {} institutions".format(len(campaigns), len(institutions)))

    # Create per-institution groups
    institutions = list(institutions)
    institutions.sort()
    institution_groups = {}
    for institution in institutions:
        institution_groups[institution] = root_group.addGroup(institution)
        institution_groups[institution].setExpanded(False)

    # Consider namedtuple for this list of lists?
    # Dict mapping institution to list of [supported, available, unavailable] campaign names
    institution_campaigns = {inst: [[], [], []] for inst in institutions}
    for campaign, (institution, availability) in campaign_availability.items():
        if availability == "s":
            institution_campaigns[institution][0].append(campaign)
        elif availability == "a":
            institution_campaigns[institution][1].append(campaign)
        elif availability == "u":
            institution_campaigns[institution][2].append(campaign)

    for institution, (
        supported,
        available,
        unavailable,
    ) in institution_campaigns.items():
        supported.sort()
        for campaign in supported:
            add_campaign(
                region, gpkg_filepath, institution_groups[institution], campaign, "s"
            )
        available.sort()
        for campaign in available:
            add_campaign(
                region, gpkg_filepath, institution_groups[institution], campaign, "a"
            )
        unavailable.sort()
        for campaign in unavailable:
            add_campaign(
                region, gpkg_filepath, institution_groups[institution], campaign, "u"
            )


def add_campaign(region: str, gpkg_filepath, group, campaign, availability):
    # Figure out whether it's points or lines
    geometry = None
    with sqlite3.connect(gpkg_filepath) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM {}".format("gpkg_geometry_columns"))
        for row in cursor:
            if row["table_name"] == campaign:
                geometry = row["geometry_type_name"]
                break
    if geometry not in ["LINESTRING", "MULTIPOINT"]:
        print(
            "Unrecognized geometry {} for campaign {}; cannot style".format(
                geometry, campaign
            )
        )
        return

    # TODO: Look into pathlib.Path.as_uri()
    uri = "file://{}|layername={}".format(gpkg_filepath, campaign)
    layer = QgsVectorLayer(uri, campaign, "ogr")
    # Add campaigns to the institution
    colors = {
        # Sometimes, it's useful to just have all black
        # "s": "0,0,0",
        # "a": "0,0,0",
        # "u": "0,0,0",
        "s": "31,120,188,255",  # blue for available and supported
        "a": "136,136,136,255",  # grey for unsupported
        "u": "251,154,153,255",  # Salmon for unavailable data
    }
    if geometry == "MULTIPOINT":
        # BEDMAP1 points are NOT in order, so we can't connect them with lines
        symbol = QgsMarkerSymbol.createSimple(
            {
                "name": "circle",
                "color": colors[availability],
                "outline_style": "no",
                "size": "1",
                "size_unit": "Point",
            }
        )
    elif geometry == "LINESTRING":
        # All other datasets have been subsampled and will display better
        # as lines.
        # It's easier to use the Dict API since those keywords show up when
        # exporting a styled layer to qlr format, and can be directly copied
        # into the code.
        # symbol = QgsLineSymbol()
        # symbol.setWidth(1)
        # symbol.setColor(QColor(colors[availability]))
        # symbol.setWidthUnit(QgsUnitTypes.RenderPoints)
        symbol = QgsLineSymbol.createSimple(
            {
                "line_color": colors[availability],
                "line_style": "solid",
                "line_width": "1",
                "line_width_unit": "Point",
            }
        )
    else:
        print("ERROR -- unrecognized geometry, should have returned earlier")
        return

    renderer = QgsSingleSymbolRenderer(symbol)
    layer.setRenderer(renderer)
    if region.lower() == "arctic":
        crs = QgsCoordinateReferenceSystem("EPSG:3413")
    elif region.lower() == "antarctic":
        crs = QgsCoordinateReferenceSystem("EPSG:3031")
    else:
        raise Exception("Unrecognized region: {}".format(region))
    layer.setCrs(crs)

    layer.updateExtents()
    QgsProject.instance().addMapLayer(layer, False)
    group.addLayer(layer)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("region", help="ARCTIC or ANTARCTIC")
    parser.add_argument("gpkg_filepath", help="Full path to input GeoPackage file")
    parser.add_argument("qlr_filepath", help="Full path to output qlr file")
    args = parser.parse_args()

    # Initialize QGIS. Needs to be in main to stay in scope
    # qgs = QgsApplication([], False)
    print("Initializing QGIS")
    qgs = QgsApplication([], True)
    qgs.initQgis()
    root = QgsProject.instance().layerTreeRoot()
    qiceradar_group = root.insertGroup(0, f"{args.region} QIceRadar Index")
    print("...initialized.")

    # Create Antarctic map!
    style_gpkg_geometries(args.region, qiceradar_group, args.gpkg_filepath)

    QgsLayerDefinition.exportLayerDefinition(args.qlr_filepath, [qiceradar_group])
