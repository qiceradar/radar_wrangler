# RadarWrangler

The QIceRadar project has 2 primary software components:
1. [RadarWrangler](https://github.com/qiceradar/radar_wrangler): set of tools to generate the index (this repo)
2. [qiceradar_plugin](https://github.com/qiceradar/qiceradR_plugin): QGIS plugin that downloads radargrams on request and displays them in geographical context. 

RadarWrangler's output is the QGIS layer that serves as the data index for the QGIS plugin.

## Structure of RadarWrangler repo

* code
  * data_exploration: jupyter notebooks exploring available data
  * download: download available data
  * index: create QGIS layer that serves as index for QIceRadar


* data: input/configuration files
  * BAS:
    * [survey].csv: (manually) downloaded from rammada, maps flight name to URL
  *

## Per-Institution documentation

Each institution collecting data uses a different file format and hosting scheme.

### BAS
