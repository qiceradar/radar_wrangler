This directory contains scripts involved in creating the index layer.

All scripts should take 2 arguments:
* data_directory: root RadarDat folder, containing ARCTIC/ANTARCTIC directories
* index_directory: root of filesystem where subsampled files will be created
* --force: Recreate output files even if they already exist.
  (The more computationally intensive scripts will usually skip these.)

* extract_bedmap_tracks.py
  * subsample bedmap data to 200m along-track, save as (much) smaller CSV. These CSVs serve as the data source for some of the layers in the index.

* extract_bas_tracks.py

* extract_ldeo_tracks.py
  * Currently only handles AGAP-GAMBIT




* extract_utig_tracks.py
  * Reads UTIG netCDF files and extracts the lon/lat paths into
    corresponding CSV files
  * This is slow, since it runs the RDP algorithm on each track, so we
    want to separate it from the KML and index layer creation, which I'm
    continuing to iterate on.
  * Does NOT handle the LVS data, which was provided as segy files.
* make_utig_kml.py
  * Takes output of extract_utig_tracks.py and creates one kml per PST,
    where each granule is a separate LineString.

There are also a handful of `example_*.py` scripts showing minimum working
examples for various related tasks within QGIS.