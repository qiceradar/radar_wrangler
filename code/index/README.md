This directory contains scripts involved in creating the index layer.


extract_radar_tracks.py:
* Single script that pulls CSV files for position out of all available radargrams
* arguments:
  * data_directory: root RadarDat folder, containing ARCTIC/ANTARCTIC directories
  * index_directory: root of filesystem where subsampled files will be created
  * --epsilon: Maximum cross-track error in RDP subsampling algorithm.
  * --force: Recreate output files even if they already exist.
* This is slow, since it runs the RDP algorithm on each track, so we
  want to separate it from the KML and index layer creation.


* extract_bedmap_tracks.py
  * subsample bedmap data to 200m along-track, save as (much) smaller CSV. These CSVs serve as the data source for some of the layers in the index.


* make_utig_kml.py
  * Takes output of extract_utig_tracks.py and creates one kml per PST,
    where each granule is a separate LineString.


There are also a handful of `example_*.py` scripts showing minimum working
examples for various related tasks within QGIS.