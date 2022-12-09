#! /usr/bin/env python3

"""
Test script demonstrating how KML-backed layer doesn't seem to have
a renderer, which means I can't figure out how to programmatically
change its symbology.

Submitted as code for question:
https://gis.stackexchange.com/questions/447166/programmatically-set-symbology-for-kml-based-vector-layer-in-qgis

"""

import numpy as np
import os
import simplekml

import qgis
from qgis.core import (QgsApplication, QgsCoordinateReferenceSystem, QgsLayerDefinition,
                       QgsMarkerSymbol, QgsProject, QgsVectorLayer)


if __name__ == "__main__":
    # Initialize QGIS.
    qgs = QgsApplication([], False)
    qgs.initQgis()
    root = QgsProject.instance().layerTreeRoot()
    group = root.insertGroup(0, "Index")

    # Create input files
    coords = np.random.randint(0, 25000, (5, 2))
    cwd = os.getcwd()

    csv_filepath = os.path.join(cwd, "test_coords.csv")
    with open(csv_filepath, "w") as fp:
        fp.write("X,Y\n")
        fp.writelines(["{},{}\n".format(x, y) for x, y in coords])

    kml = simplekml.Kml()
    kml.newlinestring(name="test", coords=coords)
    kml_filepath = os.path.join(cwd, "test_coords.kml")
    kml.save(kml_filepath)

    # Create CSV layer
    csv_uri = "file://{}?type=csv&detectTypes=yes&xField=X&yField=y&crs=EPSG:3031".format(
        csv_filepath)
    csv_layer = QgsVectorLayer(csv_uri, "CSV test layer", "delimitedtext")
    csv_symbol = QgsMarkerSymbol.createSimple({'name': 'circle',
                                               'color': '255,0,0,255',
                                               'outline_style': 'no',
                                               'size': '10',
                                               'size_unit': 'Point',
                                               })
    csv_renderer = csv_layer.renderer()
    print("CSV renderer: {}".format(csv_renderer))
    csv_renderer.setSymbol(csv_symbol)
    csv_layer.updateExtents()
    QgsProject.instance().addMapLayer(csv_layer, False)
    group.addLayer(csv_layer)

    # Create KML layer
    kml_uri = "file://{}|layername=test_coords|geometrytype=LineString25D".format(
        kml_filepath)
    kml_layer = QgsVectorLayer(kml_uri, "KML test layer", "ogr")
    kml_layer.setCrs(QgsCoordinateReferenceSystem.fromEpsgId(3031))

    kml_renderer = kml_layer.renderer()
    print("KML renderer: {}".format(kml_renderer))
    # kml_renderer is None, so I can't use it to set symbology
    kml_layer.updateExtents()
    QgsProject.instance().addMapLayer(kml_layer, False)
    group.addLayer(kml_layer)

    # Save as a qlr file that can be opened in QGIS
    QgsLayerDefinition.exportLayerDefinition("testing.qlr", [group])
