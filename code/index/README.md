This directory contains scripts involved in creating the index layer.

## Attribute Bedmap points

We have made an effort to detangle points that are in the BEDMAP1 layer and also in other BEDMAP2/3 files, or are available elsewhere. The goal is to properly attribute these transects to the extent possible, as well as to clearly show which points are still unknown.

Some of the parameters in this script were chosen based on exploration using detangle_bedmap_general.ipynb.

1) ./detangle_bedmap.py ~/RadarData

This script attempts to find the indices of points in BEDMAP1 that corespond to:
* AWI, BAS, NIPR, UTIG ice thicknesses that also appear in BM2/BM3's per-campaign CSVs.
* BAS RESPAC data: https://data.bas.ac.uk/full-record.php?id=GB/NERC/BAS/PDC/01357
* SPRI (using Stanford's published points): https://github.com/radioglaciology/radarfilmstudio/tree/master/antarctica_original_positioning

There are a number of known-outstanding surveys to be detangled:
* SPRI -- I have not yet found complete flight lines; the Stanford ones are patchy + missing entire flights.
* Russian -- emailed Popov, waiting for data

## Extract flight paths

This step extracts a subsampled representation of all known radar tracks, taking whatever raw format they are provided in and creating uniform CSV files with columns: [ps71_easting,ps71_northing]

TODO: If we stick with using a GeoPackage, it might make sense to combine this step with creating the GeoPackage itself, rather than storing intermediate CSVs. However, they're useful for debugging during development, and it allows us to keep the very slow subsampling separate from developing the database.

1) ./extract_bedmap_tracks.py ~/RadarData ~/RadarData/targ --force

Subsample bedmap data to 200m along-track spacing (RDP algorithm doesn't work well with the full-season datasets in Bedmap).

Uses the `duplicate_segments` variable from bedmap_labels.py to filter out some of the points from BEDMAP1's layer that also appear in other BEDMAP2/3 layers or are extracted from directly available radargram or flight tracks.

2)  ./extract_radargram_tracks.py ~/RadarData ~/RadarData/targ --force

Single script that pulls CSV files for position out of all available radargrams.
This is slow, since it runs the RDP algorithm on each track, so we want to separate it from the index layer creation.

Arguments:
  * data_directory: root RadarData folder, containing ARCTIC/ANTARCTIC directories
  * index_directory: root of filesystem where subsampled files will be created
  * --epsilon: Maximum cross-track error in RDP subsampling algorithm.
  * --force: Recreate output files even if they already exist.

3)  ./extract_icethk_tracks.py ~/RadarData ~/RadarData/targ/icethk --force



## Layer Creation

I am currently experimenting with using a single GeoPackage as the database that holds all tracks for the index. However, since importing the GeoPackage directly in to QGIS only seems to allow one level of nesting, there needs to be a separate qlr file that styles the layers and organizes them.


1) create_geopackage_index.py
  * Generates qiceradar_index.gpkg

  * Uses (manually updated) `available_campaigns` variable from bedmap_labels.py to not create layers for BEDMAP2/3 campaigns that are directly downloaded as radargrams to avoid duplication.

2) style_geopackage_index.py
  * Generates qice_radar_index.qlr
  * Uses the 'available' attribute attached to each geometry to determine which color the points should be.


## Misc

There are also a handful of `example_*.py` scripts showing minimum working
examples for various related tasks within QGIS.


I also played with using KML to handle nesting:
* make_utig_kml.py
  * Takes output of extract_utig_tracks.py and creates one kml per PST,
    where each granule is a separate LineString.
