The code in this directory does the initial download for creating an index to the data. This is only for generating the data product that we provide; users should not need to run these scripts. Unfortunately, the process is still very manual.

The download step will populate our geopackage index with:
* granules
  * granule name  # Name that will be displayed when using QGIS's "Identify Features" tool, so it should include institution + campaign
  * download_url   # fully-specified url to access data
  * download_method  # 'wget' for simple passwordless access;
  * destination_filepath  # path relative to the QIceRadar data root directory, including filename
  * data_format  # e.g. "bas", "utig_netcdf"
  * filesize   # in bytes, used in download confirmation dialog
  * campaign
  * institution
* campaigns
  * institution
  * science_citation
  * data_citation

A later index step will add the per-campaign tables containing geometry:
* [campaign]
  * geometry

# Requirements:

(This is not a complete list; I haven't yet tried re-running all of this on a freshly installed OS.)

pip3 install --user requests
pip3 install --user bs4

# Initial Index Setup

We use a geopackage database to track geometry and metadata about each radargram.

Start with the empty template package downloaded from:
http://www.geopackage.org/data/empty.gpkg

Then run:

`python3 initialize_gpkg.py empty.gpkg qiceradar_antarctic_index.gpkg`
`python3 initialize_gpkg.py empty.gpkg qiceradar_arctic_index.gpkg`

This will set up the "campaigns" and "granules" tables that will be incrementally filled in with relevant info by the download scripts.

# Download

Each institution is different, but I've tried to standardize the scripts to take command-line arguments specifying:
* base directory for all downloaded data
* antarctic geopackage index
* arctic geopackage index

## BAS

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

`python3 download_bas.py ~/RadarData qiceradar_antarctic_index.gpkg qiceradar_arctic_index.gpkg`


## UTIG

UTIG's data is spread across multiple data centers, including:
* Texas Data Repository -- more recent releases
* NSIDC -- any of their NASA funded work
* AAD - much of ICECAP; unfortunately, only available as single large zip file
* USAP-DC; AGASEA + LVS; not automatable (access by email / captcha)

### TDR

TDR is the simplest:
`python3 download_utig_tdr.py ~/RadarData qiceradar_antarctic_index.gpkg qiceradar_arctic_index.gpkg`

### NSIDC

NSIDC is a two-step process that requres authentication; generating the list of files (slow), then downloading them:

**Autentication**

NASA's Earthdata requires a login to download. I prefer bearer token to avoid saving passwords in plain text (in case users have re-used passwords).
  * go to: https://urs.earthdata.nasa.gov/profile and log in
  * click "Generate Token"
  * Create ~/.netrc file containing a single line (replace [token] with your token)
      machine urs.earthdata.nasa.gov user token password [token]
  * make ~/.netrc only readable by the user: `chmod 600 ~/.netrc`  (on Linux or MacOS; TODO: how to do this on windows?)
  * NB: tokens expire after 1 year; will need to prompt users to re-generate if necessary.

**Generate index**:

`python3 generate_utig_nsidc_index.py`

**Download data**:

TODO: Update this script to update the index.
`python3 download_utig_nsidc.py ~/RadarData qiceradar_antarctic_index.gpkg`

# Add Geometry

See the README in ../index to finish adding transect geometry to the geopackage.

The short version is:

`python3 ../index/create_geopackage_index.py ~/RadarData/targ ~/RadarData/targ/icethk qiceradar_antarctic_index.gpkg qiceradar_arctic_index.gpkg`

Then set up environment variables to use the QGIS version of python,
and style the geopackage.

`python3 ../index/style_geopackage_index.py ANTARCTIC ~/Documents/QIceRadar/code/radar_wrangler/code/download/qiceradar_antarctic_index.gpkg ./qiceradar_antarctic_index.qlr`

NB: the script requires the full path to the geopackage file, not the relative filepath.

-------------------------------


Each institution has its own script for now because they make their data available in different ways.

As I work my way through them, I'm getting a better sense of what
the final workflow should look like. In order:
* bas
* bedmap
  * uses BeautifulSoup to parse website for links
* awi
* ldeo_agap_gambit
* cresis
  * First try at splitting url-scraping from download; but should use CSV and not pkl.
* {download, generate}_utig_nsidc
  * Examples of authentication

Eventually, they should all:
* Generate an index specifying download URLs that can be used for a `download_all_[institution].py` script or used to download a single line.
* Take data_directory as a command-line argument. This should be the root RadarData directory.
* Save files into a standardized path:
  * region: ARCTIC/ANTARCTIC
  * institution: AWI/BAS/CRESIS/etc.
  * campaign: POLARGAP/AGASEA/etc.
    * Should match what's in BEDMAP3
    * Usually a per-year designator, occasionally multiple per year
    * Exception is UTIG, where campaigns run across multiple years.
  * segment:
    * depending on institution, may be flight (e.g. BAS), line (e.g. LDEO), PST (UTIG) (There may be too many PSTs for this to scale.)
  * There may be multiple granules for a single segment; all of those files wind up in the same directory.
  * QUESTION: Where does "product" wind up in this hierarchy? CReSIS puts it just below campaign. In some ways, I'd prefer it to be the lowest-level directory, but I'm not sure if everybody's products align across granule lines.

## Antarctic

* BEDMAP:
  * These files are used as a starting point for the index layer.
  * `download_all_bedmap.py` downloads CSVs for ice thickness used in each BEDMAP compilation. Bedmap2 and 3 break this out into individual institutions.

* AWI: seems to be hit-or-miss, with more available in Greenland.
  * Datasets:
    * Radar profiles across ice-shelf channels at the Roi Baudouin Ice Shelf https://doi.pangaea.de/10.1594/PANGAEA.907146?format=html#download Reinhart Drews 2019
      * Data is in *.npy format
      * Example code provided
      * Does not appear to include picks?
    * Another Roi Baudouin (UWB) 2018: https://doi.pangaea.de/10.1594/PANGAEA.942989?format=html#download
      * Data is in *.mat format
    *  Shear Margins for NEGIS https://doi.pangaea.de/10.1594/PANGAEA.928569?format=html#download 2018
    * 2018 EGRIP-NOR https://doi.pangaea.de/10.1594/PANGAEA.914258?format=html#download
    * Nioghalvfjerdsbrae (Greenland) 2018 https://doi.pangaea.de/10.1594/PANGAEA.949391?format=html#download
    * Nioghalvfjerdsbrae (Greenland) 1998 https://doi.pangaea.de/10.1594/PANGAEA.949619
  * Unfortunately, every dataset seems to have a different directory structure. And for the Antarctic ones at least, different file formats.
  * download_all_awi.py attempts to save datafiles, grouped into directories by DOI.
  * There may be one season on CRESIS's site? https://data.cresis.ku.edu/data/rds/2016_Greenland_Polar6/

* BAS: `wget` works. Nice and simple.
  * Index files for a new season can be downloaded (manually) from rammada:
    * click the "Folder" dropdown next to "netcdf"
    * Select "All Actions"
    * Select "CSV"; download into data/BAS/netcdf_indices; renaming file to [survey].csv
  *  `download_all_bas.sh` will downline every segment listed in the index files (data/BAS/*.csv)
  * TODO: The BEDMAP script may show a way to automatically traverse the directories, rather than manually creating the index.
  * TODO: This only includes data since ~2004, and only airborne. Are other data hiding somewhere else?

* CRESIS:
  * Data available in multiple places...though most of the surveys they operated show up under other institutions in the BEDMAP database.
    * https://data.cresis.ku.edu/ seems to only have the matlab file formats
      * much more complete dataset
      * Organized into seasons/platforms
      * offers multiple quality levels -- do users typically want to flip between them? Or is it enough to download the "best"?
      * They also offer low/high gain datasets, as well as combined. I'll stick with the "combined" for now.
    * NSIDC has the ICEBRIDGE L1B products in netCDF format, and provides a download script.
      * https://nsidc.org/data/irmcr1b/versions/2 is 2012-2018; presumably only ICEbridge.
      * user guide: https://nsidc.org/sites/default/files/irmcr1b-v002-userguide_1.pdf
      * source citation (not in the files themselves): `@misc{Paden, J., J. Li, C. Leuschen, F. Rodriguez-Morales, and R. Hale._2014, title={IceBridge MCoRDS L1B Geolocated Radar Echo Strength Profiles, Version 2}, url={https://nsidc.org/data/IRMCR1B/versions/2}, DOI={10.5067/90S1XZRBAX5N}, publisher={NASA National Snow and Ice Data Center Distributed Active Archive Center}, author={Paden, J., J. Li, C. Leuschen, F. Rodriguez-Morales, and R. Hale.}, year={2014} }`
  * From their README: "The standard L1B files are, in order of increasing quality, CSARP_qlook, CSARP_csarpcombined, CSARP_standard, and CSARP_mvdr directories. Each directory will contain a complete set of echograms so downloading a single directory (usually the highest quality available) is what we recommend." => However, there are caveats for mvdr (and music) about radiometric fidelity + possibility of filtering out signal.
  * Each day's data is divided into "segments", where settings are the same. Segments are divided into ~50km long "frames". Frames may overlap slightly, so I shouldn't do any concatenation for easier viewing. File naming is YYYYMMDD_SS_FFF.
  * netCDF fields:

* INGV:
  * Data portal is under construction: https://ires.ingv.it/index.php/en/
  * Haven't found any radargrams yet.

* KOPRI:
  * Only their first season has been released: https://zenodo.org/record/3874655
    * Unfortunately, Zenodo does not support HTTP range requesets, so I can't use unzip-http to grab individual files.
  * For now, manually downloaded into KOPRI/KRT1
  * netCDF files split transects into ~100 MB "granules"

* LDEO:
  * AGAP_GAMBIT: officially lives at USAP-DC https://www.usap-dc.org/view/dataset/601285, but they don't handle large files well
    * Also available at http://wonder.ldeo.columbia.edu/data/AGAP/DataLevel_1/RADAR/DecimatedSAR_netcdf/index.html, from which wget works
    * `download_ldeo_agap_gambit.sh` will download the whole data directory structure.
  * ROSETTA -- haven't found radargrams yet. Kirsti provided a single sample line.
  * Recovery Lakes -- Haven't found yet.

* STANFORD/SPRI:
  * Dusty says the data is probably a few years from being cleaned up enough to be compatible with this project.
  * They have published a shapefile with links to some of the film images: https://purl.stanford.edu/xy581jd9710
  * I downloaded the original positioning data for the flights from: https://purl.stanford.edu/sq529nv6867 (Scroll down to the bottom of the list for a zip file)
    * They do not all have same format: (CBD,LAT,LON,THK,SRF) vs. (LAT,LON,CBD,THK)
    * They aren't necessarily in sequential order (CBD values are not monotonic)
    * A more complete dataset is here: https://github.com/radioglaciology/radarfilmstudio in the antarctica_original_positioning directory.
      * As of 24 Dec 2022 (5bb1da7), it includes 7 additional flights and more points for many other flights
      * Spot-checking indicates that this does NOT correspond one-to-one with the points in the previous dataset (The coordinates for CBD values don't match.)

* UTIG
  * Lake Vostok
    * Available at USAP-DC: https://www.usap-dc.org/view/dataset/601300
    * However, all downloads are protected via a captcha, so I had to click through manually. All available files were saved to RadarData/UTIG/LVS/.
    * To check they all downloaded: ```for ff in `ls vostok_radar_nav_lines`; do gg=`sed s/nav/segy.gz/ < ${ff}`; ls $gg > /dev/null; done```(`ls` will print an error for missing files)
    * To unzip all in terminal: ```for ff in `ls *.gz`; do gg=`echo $ff | sed s/.gz//`; if [ ! -f $gg ]; then echo "need to unzip $ff -> $gg"; dtrx $ff; fi; done``` (may need `pip install dtrx`)
  * AGASEA
    * https://www.usap-dc.org/view/dataset/601436
    * Available via Google Drive download from USAP-DC. This link seems to have them all, bundled in 5-10 GB chunks: https://drive.google.com/drive/folders/1BH36_FVb2fFyZl_aZlUgYwgL8QFYZml5
    * netCDF, with fields: latitude, longitude, elevation, fast-time, data_hi_gain, data_low_gain
  * EAGLE
    * Some available from AAD: https://data.aad.gov.au/datasets/science/AAS_4346_EAGLE_ICECAP_LEVEL2_RADAR_DATA
      - seem to have moved: https://data.aad.gov.au/metadata/AAS_4346_ICECAP_OIA_RADARGRAMS
      -  doi:10.26179/5bcff4afc287d    (but I haven't had luck getting that to resolve to the data; instead, search AAD site for 4346)
    * These are large-file downloads (8G-11G), but the download speed was 10-200 kB/sec, which is a problem.
    * netCDF with fields: lat, lon, altitude, pitch, roll, heading, time, fasttime, amplitude_low_gain, amplitude_high_gain
  * ICECAP
    * hicars1: https://n5eil01u.ecs.nsidc.org/ICEBRIDGE/IR1HI1B.001/
    * hicars2: https://n5eil01u.ecs.nsidc.org/ICEBRIDGE/IR2HI1B.001/
      * NASA's Earthdata requires a login to download. I prefer bearer token to avoid saving passwords in plain text (in case users have re-used passwords)
      * go to: https://urs.earthdata.nasa.gov/profile and log in
      * click "Generate Token"
      * Create ~/.netrc file containing a single line (replace [token] with your token)
          machine urs.earthdata.nasa.gov user token password [token]
      * make ~/.netrc only readable by the user: `chmod 600 ~/.netrc`
      * NB: tokens expire after 1 year; will need to prompt users to re-generate if necessary.
    * OIA: https://data.aad.gov.au/s3/bucket/datasets/science/AAS_4346_ICECAP_OIA_RADARGRAMS/ICECAP_OIA.SR2HI1B/ (unlike EAGLE, it's possible to download individual lines.)
      * I tried to scrape the page for links, but it renders in javascript. Was faster to just click the links and download. Now that I have them all, will be easy to construct URL, since it matched filenames.
      * They've changed their download procedure to require an email address:
        - dataset landing page: https://data.aad.gov.au/metadata/AAS_4346_ICECAP_OIA_RADARGRAMS
        - download page: https://data.aad.gov.au/dataset/5256/download (then there's the step of checking your email!) (Q: Why is this a different project number than the landing page?)
        - I'll need to have my users manually enter their Access Key and Secret Key for S3 access. Hopefully these persist?
        - They support loading raster images directly into QGIS ... interesting!
  * SOAR -- only some of the surveys have tracks available; others are only grids.



## Arctic

* CReSIS
  * https://data.cresis.ku.edu/ seems to only have the matlab file formats

* UTIG
  * Devon Ice Cap: https://zenodo.org/record/5795105
    * includes full radargrams
  * GOG3: https://data.bas.ac.uk/full-record.php?id=GB/NERC/BAS/PDC/00919
    * ice thickness only
  * GOG1 & GOG2 are as-yet unreleased, though made it into a Bamber DEM and into BedMachine.
