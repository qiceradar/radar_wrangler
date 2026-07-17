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

## Generating the indices

I download all available radaragrams to an external hard drive, extract their flight paths, then create a geopackage file with those points organized and styled hopefully-logically.

Run these commands in the `code` directory and activate the `uv` environment:
`source .venv/bin/activate`

### Create empty .gpkg file

Initialize our geopackage database from the default empty database,
then add the non-geometry tables that will be used to track metadata
about the radargrams.

Some of these tables function as enums:
* institutions (e.g. "AWI", "BAS", etc...): who generated the data
* data_formats (e.g. cresis_mat, utig_netcdf): specify how to parse the data
* download_methods (e.g. nsidc,  ): specify how to download the data

* Campaigns
* Granules

`python initialize_gpkg.py ../data/empty.gpkg ../indices/test_antarctica.gpkg`

* Input: `data/empty.gpkg`
* Output: [specified database]

### Add manually-generated metadata to the index

`python populate_campaigns.py --antarctic ../indices/test_antarctica.gpkg`

* Args: --antarctic / --arctic is required
* Inputs: (implicit) metadata about campaigns. Currently:
  * data/awi_campaigns.yaml
  * data/bas_campaigns.yaml
  * data/cresis_campaigns.yaml
  * data/kopri_campaigns.yaml
  * data/utig_campaigns.yaml
* Outputs: updates to specified database

### Download radargrams

All of these scripts check for whether a destination file already exists before downloading it, so they can be stopped and restarted as necessary.

They all require an argument specifying the root of your data directory; I use an external 4TB SSD for Antarctica.

Many of the download scripts directly parse available files from the server; others require a list to have been generated.

They all update the `granules` table in the geopackage file with information about how to download the data.
* name (fully specified and unique for each granule)
* institution
* campaign
* segment
* granule
* data_product (e.g. IR2HI1B; usually indicates processing applied)
* data_format
* download_method
* url
* destination_path (relative to input RADAR_DATA directory)
* filesize (bytes)

If you are trying to add support for a new season to an existing database file,
you'll have to add it to the appropriate file in `data/{institution}_campaigns.yaml`
and re-run `populate_campaigns.py`

#### Texas Data Repository (TDR)

Manual preparation: edit code to add additional season:DOI mappings
(e.g. `dois["COLDEX_2023"] = "doi:10.18738/T8/XPMLCC"`);
the script will find all included files from the initial DOI.

`python download_tdr.py /path/to/RADAR_DATA ../indices/test_antarctica.gpkg`

#### Pangaea

This download script supports the data that was part of AWI's recent (2024/2025/2026) release (bibliography: https://doi.pangaea.de/10.1594/PANGAEA.972094)
There are a handful of older radar releases that don't follow the same organization and that we don't support yet.

Manual preparation to add a new DOI:
* Go to the landing page for each DOI, and download the index of all files under the link "Download dataset as tab-delimited text"; save to `data/AWI`.
* Add a line to `data/AWI/convert_file_list.sh` to extract a list of files (one per line) from the input file
* re-run `convert_file_list.sh`, check that the generated `dataset_{id}_files.txt` file correctly lists each file, one per line.
* Add a mapping from season:ID in `code/download_awi_pangaea.py` (e.g. `datasets["ANT_95_96"] = 995486`)
* If the filename doesn't follow an existing pattern, add a new regex and a branch to the statement extracting flight and granule from filename.

`python download_awi_pangaea.py /path/to/RADAR_DATA ../indices/test_antarctica.gpkg`


## Data Organization

Radargrams are downloaded to a directory under:

`[data_dir]/{arctic, antarctic}/{institution}/{campaign}/`

Below that, it is institution specific.

We preserve the filenames chosen by the providers.


## To add support for a new campaign:

* update or create {institution}_campaigns.yaml
  * if created new .yaml, update populate_campaigns.py to include that file

* write or update download_{institution}_{datacenter}.py

## Campaigns table

Most radar data is released with a single DOI pointing to an entire season or campaign.

The campaigns table includes per-DOI metadata, including:
* name -- we try to use however the institution has labeled their data, whether by year or project.
* institution -- the institution who collected the data. In the case of collaborations, we try to go with BEDMAP3's organization.
* data_citation -- any published use of these data MUST include this citation
* science_citation -- a handful of other possibly-relevant papers; many data centers provide these in addition to the data release citation, in which case we include (max ~3) in our index. Other data providers do not include any guidance for this, in which case the field is blank.

Please contact us if you have suggested updates to this metadata!


## Institutions

### AWI
### BAS
### CRESIS

###  KOPRI
Only some seasons are available.

* KRT1 (16/17) - 9TB file on Zenodo; we do not assist with downloading this file.
* ASE3 (20/21) - hosted at the Texas Data Repository (so handled by download_tdr.py)
* ASE4 (22/23) - also at TDR

KRT2 - was dense survey over one of the David Glacier active lakes; I've found the very raw files online, but nothing processed enough to use.

ASE5 - still embargoed

### LDEO
### NASA
### NPI
### UTIG

Most of their post-2008 data is available:

* GIMBLE (13/14, 14/15) - hosted at TDR; download_tdr.py
* COLDEX (22/23, 23/24) - hosted at TDR; download_tdr.py


## Data Formats Table

This specifies which functions to use to load data / which message to show the user explaining why we cannot automate download.

All data with the same format does not necessarily follow the exact same conventions,
but they're similar enough to group them together into the same set of functions.

### ice_thickness

There are some datasets that have only been released as ice thickness data.
We want to show the locations of that data, so we ingest those lines and plot as unavailable.

### awi_netcdf

### bas_netcdf

There's a lot of complexity in parsing these data since they changed formats throughout the seasons.

### utig_netcdf

Most of the UTIG data uses the same netCDF format.

### cresis_mat

Older CReSIS data has been released as pre-HDF5 matlab files

### cresis_netcdf

Newer CReSIS data is released as netcdf files

## Download Methods Table

These datasets are scattered across a number of different data centers, many of which require custom code to access the data.

### curl

### wget

### nsidc

These data require the user to provide an EarthData login; QIceRadar guides the user through specifying one.

### usapdc_email

Some data is technically available, but requires an email exchange with USAP-DC to arrange for download.
In this case, QIceRadar cannot automate downloat, and instead will display a dialog pointing the user to how to start that process.

### usapdc_captcha

Other data at USAP-DC is protected by a captcha; I have not yet figured out how to help the user get around that in an automated way, so we point the user to the site with instructions for where to copy the downloaded files so QIceRadar can find them.

### aad_oia

### aad_eagle


