# RadarWrangler

The QIceRadar project has 2 primary software components:
1. [RadarWrangler](https://github.com/qiceradar/radar_wrangler): set of tools to generate the index (this repo)
2. [qiceradar_plugin](https://github.com/qiceradar/qiceradR_plugin): QGIS plugin that downloads radargrams on request and displays them in geographical context.

RadarWrangler's output is the QGIS layer that serves as the data index for the QGIS plugin.

The rest of this README is aimed at developers.
If you just want to use the tool, head over to the
[qiceradar_plugin](https://github.com/qiceradar/qiceradR_plugin) documentation
for instructions on downloading the index and getting started using it.

## Structure of RadarWrangler repo

* code
  * download_*.py: scripts for downloading available data
  * index: create QGIS layer that serves as index for QIceRadar


* data: input/configuration files
  * BAS:
    * [survey].csv: (manually) downloaded from rammada, maps flight name to URL
  *

* data_exploration: jupyter notebooks exploring available data

## TL;DR

The rest of this document describes the steps below in more detail,
but here are the actual commands to run to generate the index,
assuming the root data directory is at `~/RadarData`.

This does not include the various often-manual index-generation steps,
because their result is committed into the repository
(but see relevant sections for instructions.)

Run these commands in the `code` directory after activating the `uv` environment:
`source .venv/bin/activate`


```
# Set up .gpkg with non-geometry tables
python initialize_gpkg.py ~/RadarData ../indices/test_antarctica.gpkg

# Populate database with metadata about the campaigns
python populate_campaigns.py --antarctic ../indices/test_antarctica.gpkg

# Download AWI's data and add granule metadata to database
`python download_awi_pangaea.py ~/RadarData ../indices/test_antarctica.gpkg`

# Download BAS's data + update database with metadata
python3 download_bas.py --antarctic ~/RadarData ../indices/test_antarctica.gpk
# Download CReSIS data then fill in CReSIS granule metadata from the index
python download_cresis_ku.py --antarctic ~/RadarData
python populate_cresis_granules.py --antarctic ../indices/test_antarctica.gpkg

# Download KOPRI data and some of UTIG's transects; add granule metadata to index
python download_tdr.py ~/RadarData ../indices/test_antarctica.gpkg

# Download UTIG's data from NSIDC:
python download_utig_nsidc.py ~/RadarData ../indices/test_antarctica.gpkg

# Download UTIG's data from AADC:
python3 download_utig_aad_oia_eagle.py ~/RadarData ../indices/test_antarctica.gpkg

# Manually download and extract:
# * UTIG/LVS (captchas): https://www.usap-dc.org/view/dataset/601300
# * UTIG/AGASEA (email exchange): https://www.usap-dc.org/view/dataset/601436
# * KOPRI/KRT1 (9G tarball from Zenodo): https://zenodo.org/records/3874655
# Then run:
python3 populate_kopri_krt1_granules.py ~/RadarData ../indices/test_antarctica.gpkg
python3 populate_utig_agasea_granules.py ~/RadarData ../indices/test_antarctica.gpkg
python3 populate_soar_lvs_granules.py ~/RadarData ../indices/test_antarctica.gpkg
```


## Generating the indices

I download all available radaragrams to an external hard drive (creating ~/RadarData as a symlink to that external drive), extract their flight paths, then create a geopackage file with those points organized and styled hopefully-logically.


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
and re-run `populate_campaigns.py` before the download script.

#### Pangaea: AWI

This download script supports the data that was part of AWI's recent (2024/2025/2026) release (bibliography: https://doi.pangaea.de/10.1594/PANGAEA.972094)
There are a handful of older radar releases that don't follow the same organization and that we don't support yet.

Manual preparation to add a new DOI:
* Go to the landing page for each DOI, and download the index of all files under the link "Download dataset as tab-delimited text"; save to `data/AWI`.
* Add a line to `data/AWI/convert_file_list.sh` to extract a list of files (one per line) from the input file
* re-run `convert_file_list.sh`, check that the generated `dataset_{id}_files.txt` file correctly lists each file, one per line.
* Add a mapping from season:ID in `code/download_awi_pangaea.py` (e.g. `datasets["ANT_95_96"] = 995486`)
* If the filename doesn't follow an existing pattern, add a new regex and a branch to the statement extracting flight and granule from filename.

`python download_awi_pangaea.py /path/to/RADAR_DATA ../indices/test_antarctica.gpkg`

This download script can time out if it takes Pangaea a long time to load a file from tape, so re-run until all lines report as already downloaded.

#### Rammada: BAS


BAS has a data portal: https://www.bas.ac.uk/project/nagdp/
I used that to find all openly-available Antarctic surveys. Click on a line, then click "Metadata" to be taken to the rammada page.

Individual surveys are hosted at rammada; I have not figured out how to automate scraping the download links, so manually download the indices:

* Go to the landing page
* click the "Folder" dropdown next to "netcdf"
* Select "All Actions"
* Select "CSV"; download into data/BAS/netcdf_indices; renaming file to [survey].csv
* Relevant columns are "name" and "url"

Landing pages for different Antarctic surveys with full radargrams available:
* AGAP: https://ramadda.data.bas.ac.uk/repository/entry/show?entryid=a1abf071-85fc-4118-ad37-7f186b72c847
* BBAS: https://ramadda.data.bas.ac.uk/repository/entry/show?entryid=db8bdbad-6893-4a77-9d12-a9bcb7325b70
* FISS2015: https://ramadda.data.bas.ac.uk/repository/entry/show?entryid=3507901f-d03e-45a6-8d9b-59cf98a03e1d
* FISS2016: https://ramadda.data.bas.ac.uk/repository/entry/show?entryid=0cb61583-3985-4875-b141-5743e68abe35
* GRADES_IMAGE: https://ramadda.data.bas.ac.uk/repository/entry/show?entryid=c7ea5697-87e3-4529-a0dd-089a2ed638fb
* ICEGRAV: https://ramadda.data.bas.ac.uk/repository/entry/show?entryid=c6324118-94a2-4e03-8715-b24b82322a57
* IMAFI: https://ramadda.data.bas.ac.uk/repository/entry/show?entryid=f32b298b-7906-4360-9e34-16739af73bb7
* ITGC_2019: https://ramadda.data.bas.ac.uk/repository/entry/show?entryid=e7aba676-1fdc-4c9a-b125-1ebe6124e5dc
* POLARGAP: https://ramadda.data.bas.ac.uk/repository/entry/show?entryid=e8a29fa7-a245-4a04-8b56-098defa134b9
* WISE_ISODYN: https://ramadda.data.bas.ac.uk/repository/entry/show?entryid=70adab3d-3632-400d-9aa1-ddf2d62a11b3

For Arctic surveys:
* GOG3 (ice thickness only): https://ramadda.data.bas.ac.uk/repository/entry/show?entryid=d31550de-13c2-4779-aa10-9e0a43bbeb1a

Download:

```
python3 download_bas.py --antarctic /path/to/RADAR_DATA ../indices/test_antarctica.gpkg
```

#### CReSIS -- Kansas servers

The most complete set of data collected by CReSIS is available on their own servers.
However, it doesn't have good metadata for proper citations -- they do not mint DOIs, though some of the data is also posted
elsewhere with DOI assigned.

Additionally, they host a copy of the COLDEX data that was collected using UTIG's radar;
that data (processed by UTIG) is also available at TDR.
Rather than decide which is the canonical format, we simply index all versions.

(As of August 2026, they have a "coming soon" for info on e.g. how to cite the COLDEX data)

On lines where multiple processed versions are available, we download the "best" version, based on these priorities:
1. CSARP_mvdr
2. CSARP_standard
3. CSARP_csarp-combined
4. CSARP_qlook

(We currently only support displaying one product per line)

The only way I've found to get a complete list of available data is to
crawl their site, which takes quite a while. So we also split this one
up into an indexing and a downloading step (so the downloading can be
re-started without having to re-index).

Saves a .csv to data/CResis/cresile_granules.csv:

`python generate_cresis_ku_index.py`

Download all granules from that .csv:

`python download_cresis_ku.py --antarctic ~/RadarData`

Add granule information to database:

`python populate_cresis_granules.py --antarctic ../indices/test_antarctica.gpkg`


#### National Snow and Ice Data Center: some UTIG

**Authentication**

NASA's Earthdata requires a login to download. I prefer bearer token to avoid saving passwords in plain text (in case users have re-used passwords).
  * go to: https://urs.earthdata.nasa.gov/profile and log in
  * click "Generate Token"
  * Create ~/.netrc file containing a single line (replace [token] with your token)
      machine urs.earthdata.nasa.gov user token password [token]
  * make ~/.netrc only readable by the user: `chmod 600 ~/.netrc`  (on Linux or MacOS; TODO: how to do this on windows?)
  * NB: tokens expire after 1 year; will need to prompt users to re-generate if necessary.


** Create Indices**

https://nsidc.org/data/explore-data
I searched for known instrument codes for HiCARS: IR1HI1b
This takes you to the dataset

https://nsidc.org/data/ir1hi1b/versions/1
* click "Data Access Tool"
* click "Order via Earth Data Search"; "OK" for redirection
* click "Download Now"
* Follow login prompts
* click "Download All"
* Then, click "Download Script", which will have a list of all files
* Saved this list to nsidc_download_urls_hicars1.txt

Then, do the same for the dataset at https://nsidc.org/data/IR2HI1B/versions/1, copying it to nsidc_download_urls_hicars2.txt

Reformat that list of URLs into a CSV with most of the relevant granule metadata:
`python generate_utig_nsidc_index.py`

This creates `data/UTIG/utig_nsidc_index.csv`.


To actually download the data:
`python download_utig_nsidc.py ~/RadarData ../indices/test_antarctica.gpkg`

#### Texas Data Repository (TDR): some UTIG, some KOPRI

Manual preparation: edit code to add additional season:DOI mappings
(e.g. `dois["COLDEX_2023"] = "doi:10.18738/T8/XPMLCC"`);
the script will find all included files from the initial DOI.

`python download_tdr.py /path/to/RADAR_DATA ../indices/test_antarctica.gpkg`

#### Australian Antarctic Data Centre (AADC): some UTIG

First, obtain access keys for the data by entering your email in the form:
EAGLE: https://data.aad.gov.au/dataset/4780/download
OIA: https://data.aad.gov.au/dataset/5256/download

FOr the download, I put them in bash variables:
```
export EAGLE_ACCESS_KEY=[your access key]
export EAGLE_SECRET_KEY=[your secret key]

export OIA_ACCESS_KEY=[your access key]
export OIA_SECRET_KEY=[your secret key]
```

Then run:
`python3 download_utig_aad_oia_eagle.py ~/RadarData ../indices/test_antarctica.gpkg`

#### USAP_DC: some UTIG, some LDEO

Each dataset hosted on USAP-DC is different.

**AGASEA**

The 2004-2005 AGASEA survey is hosted at https://www.usap-dc.org/view/dataset/601436

However, downloading it requires an email exchange with USAP-DC, which (in 2022) resulted in files being up loaded to Google Drive, and a link being shared.

Following the instructions in their "Contact Us" link, I sent an email
to "info@usap-dc.org" with the subject "Request for large dataset 601436" and that got to the right place.

Do that, unzip the files, and copy them to:
`${RADAR_DATA}/ANTARCTIC/UTIG/AGASEA/{DRP,X,Y}##{a,b,c}/{DRP,X,Y}##{a,b,c}_##.nc`

Then run:

`python3 populate_utig_agasea_granules.py ~/RadarData ../indices/test_antarctica.gpkg `

**LVS**

The 2000-2001 SOAR Lake Vostok survey is available at https://www.usap-dc.org/view/dataset/601300

Downloading it requires solving a captcha for each line; there's an option to download all 10G as a zip file, but it timed out every time I tried.

Download lines, unzip, and copy to:

`${RADAR_DATA}/ANTARCTIC/UTIG/LVS/{X,Y}##{a,b,c}.segy`

Then run:
`python3 populate_soar_lvs_granules.py ~/RadarData ../indices/test_antarctica.gpkg `

#### Zenodo: some KOPRI

The KOPRI KRT1 survey of the David active lakes is hosted at Zenodo: https://zenodo.org/records/3874655

Unfortunately, it is a 9.4G tgz file, and content-range is not supported, so we cannot support downloads of individual lines.

Download it, and unzip the tarball so that the files are at e.g.

`${RADAR_DATA}`/ANTARCTIC/KOPRI/KRT1/KHERA1B_2017019_DVG_IBH0c_X23a_002.nc`

Then run:

`python3 populate_kopri_krt1_granules.py ~/RadarData ../indices/test_antarctica.gpkg `

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

They released most of their data, with the bilbliography here:
https://doi.pangaea.de/10.1594/PANGAEA.972094

They have an online data portal that allows exploring their data:

### BAS


### CRESIS

data.cresis.ku.edu has everything (including some data that they host for other institutions)

###  KOPRI
Only some seasons are available.

* KRT1 (16/17) - 9TB file on Zenodo; we do not assist with downloading this file.
* KRT2 (17/18) - ??
* ASE2 (18/19) - ??
* ASE3 (20/21) - hosted at the Texas Data Repository (so handled by download_tdr.py)
* ASE4 (22/23) - also at TDR
* ASE5 (25/26) - not yet released.

KRT2 - was dense survey over one of the David Glacier active lakes; I've found the very raw files online, but nothing processed enough to use.
ASE2 - They flew, but I don't know if they got any data.
ASE5 - still embargoed.

### LDEO

ROSETTA -- https://www.usap-dc.org/view/dataset/601789 (only png files are directly downloadable; the other lines require email coordination with USAP-DC. As of 2026, they are working towards having their data processed and hosted by CReSIS as part of the Open Polar Radar project.

AGAP GAMBIT -- Used to be available from http://wonder.ldeo.columbia.edu/data/AGAP/DataLevel_1/RADAR/DecimatedSAR_netcdf/index.html

### NASA

### NPI


### SOAR? (I'm not sure how to attribute Vostok)

In theory, this is downloadable from USAP-DC.
However, each individual line is protected by a captcha where you have to click cars.
In theory, there's an option to select all files and download them, b
ut when I try that it stalls for a long time and before the download
can start, the captcha "Verification expired. Check the checkbox again".
It did manage to start the download once, but then failed after 1G (out of 9)
was transferred.

----

I have NO IDEA what to do for citations. The USAP-DC entry says:
"Cite as: Studinger, M. S., & Bell, R. (2020) "SOAR-Lake Vostok Survey airborne radar data" U.S. Antarctic Program (USAP) Data Center. doi: https://doi.org/10.1594/IEDA/306568. "

Meanwhile, the README in the downloaded files says:
"LAKE VOSTOK AEROGEOPHYSICAL SURVEY DATA DISTRIBUTION, 26 OCT 2001

University of Texas Institute for Geophysics
John A. and Katherine G. Jackson School of Geosciences
The University of Texas at Austin

The accompanying files are our results from the aerogeophysical surveys
we conducted over Lake Vostok during 2000/2001.  This work was supported
by NSF/OPP grant #9911617 to UTIG.  These files include profiles and maps of
surface elevation, ice thickness, bed elevation, and gravity. The
kinematic carrier phase GPS solutions used in the reduction of these
data are also included. The first publication of any maps should list
J. Holt, D. Morse, T. Richter, S. Kempf, M. Peters, and D. Blankenship
as authors, in that order.  Other publications using these data should
suitably acknowledge these same participants as well as UTIG staff and
NSF/OPP award #991167.
"

In BEDMAP2 (https://bedmap.scar.org/), it was categorized as UTIG.

downloadable from USAP-DC, but protected by a captcha.

Instruct users to download data and put it in expected location.
TODO: Create a "manual" download method, where we pop up per-campaign instructions?

Also have to download *separate* nav files.
vostok_radar_nav_lines.zip

Columns are:
[transect, trace, lon, lat, elev]

Can use segpy:

```
from segpy.reader import create_reader

input_file =  open("/Users/lindzey/RadarData/ANTARCTIC/SOAR/Vostok/X01a.segy", 'rb')

dataset = create_reader(input_file, endian='>')

print(seg_y_dataset.num_traces())
# Each trace can have a different number of samples; doesn't seem to accept an iterable as the argument
seg_y_dataset.num_trace_samples(0)
> 4096
seg_y_dataset.trace_samples(0)

```


### UTIG

Most of their post-2006 data is available; earlier surveys are not.
It is spread across multiple data centers (based on source of funding), including:
* Texas Data Repository -- more recent releases (COLDEX, GIMBLE)
* NSIDC -- any of their NASA funded work (early ICECAP, OIB)
* AAD - much of ICECAP; unfortunately, only available as single large zip file
* USAP-DC -- AGASEA + LVS; not automatable (access by email / captcha)



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

These data require the user to provide an EarthData login; QIceRadar guides the user through specifying one. For the download scripts:





### usapdc_email

Some data is technically available, but requires an email exchange with USAP-DC to arrange for download.
In this case, QIceRadar cannot automate downloat, and instead will display a dialog pointing the user to how to start that process.

### usapdc_captcha

Other data at USAP-DC is protected by a captcha; I have not yet figured out how to help the user get around that in an automated way, so we point the user to the site with instructions for where to copy the downloaded files so QIceRadar can find them.

### aad_oia

### aad_eagle


