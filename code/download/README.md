Each institution has its own script for now because they make their data available in different ways.

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
    * NSIDC has L1B products in netCDF format, and provides a download script.
      * https://nsidc.org/data/irmcr1b/versions/2 is 2012-2018; presumably only ICEbridge.
      * user guide: https://nsidc.org/sites/default/files/irmcr1b-v002-userguide_1.pdf
  * From their README: "The standard L1B files are, in order of increasing quality, CSARP_qlook, CSARP_csarpcombined, CSARP_standard, and CSARP_mvdr directories. Each directory will contain a complete set of echograms so downloading a single directory (usually the highest quality available) is what we recommend." => However, there are caveats for mvdr (and music) about radiometric fidelity + possibility of filtering out signal.
  * Each day's data is divided into "segments", where settings are the same. Segments are divided into ~50km long "frames". Frames may overlap slightly, so I shouldn't do any concatenation for easier viewing. File naming is YYYYMMDD_SS_FFF.

* KOPRI:
  * Only their first season has been released: https://zenodo.org/record/3874655
  * For now, manually downloaded into KOPRI/KRT1
  * netCDF files split transects into ~100 MB "granules"

* LDEO:
  * AGAP_GAMBIT: officially lives at USAP-DC https://www.usap-dc.org/view/dataset/601285, but they don't handle large files well
    * Also available at http://wonder.ldeo.columbia.edu/data/AGAP/DataLevel_1/RADAR/DecimatedSAR_netcdf/index.html, from which wget works
    * `download_ldeo_agap_gambit.sh` will download the whole data directory structure.
  * ROSETTA: available as single large 200G. For now, downloaded manually:
    *  http://wonder.ldeo.columbia.edu/data/ROSETTA-Ice/Radar/RS_Process_Example/Rosetta_Data.zip

* UTIG
  * Lake Vostok
    * Available at USAP-DC: https://www.usap-dc.org/view/dataset/601300
    * However, all downloads are protected via a captcha, so I had to click through manually. All available files were saved to RadarData/UTIG/LVS/.
    * To check they all downloaded: ```for ff in `ls vostok_radar_nav_lines`; do gg=`sed s/nav/segy.gz/ < ${ff}`; ls $gg > /dev/null; done```(`ls` will print an error for missing files)
    * To unzip all in terminal: ```for ff in `ls *.gz`; do gg=`echo $ff | sed s/.gz//`; if [ ! -f $gg ]; then echo "need to unzip $ff -> $gg"; dtrx $ff; fi; done``` (may need `pip install dtrx`)
