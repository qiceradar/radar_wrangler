
# Map from BEDMAP campaign nomenclature to where the data lives.
# (At least for now, automating the generation of this lookup table isn't time efficient)
# Any filename that appears in this table will NOT be added as a bedmap layer;
# instead, it is assumed that it will be added in a layer that's based on other extracted data.
available_campaigns = {
    ####################################
    ##              BAS               ##
    ####################################

    # Evans only available as bed elevation: https://data.bas.ac.uk/metadata.php?id=GB/NERC/BAS/PDC/01347
    # 'BAS_1994_Evans_AIR_BM2': '',
    # Dufek Massif data only available as bed elevation: https://data.bas.ac.uk/metadata.php?id=GB/NERC/BAS/PDC/01344
    # 'BAS_1998_Dufek_AIR_BM2': '',
    # Seems to be bed elevation only: https://data.bas.ac.uk/full-record.php?id=GB/NERC/BAS/PDC/01266
    # 'BAS_2001_Bailey-Slessor_AIR_BM2': '',
    # Again, bed elevations: https://data.bas.ac.uk/full-record.php?id=GB/NERC/BAS/PDC/01274
    # 'BAS_2001_MAMOG_AIR_BM2': '',
    # TORUS data only available as bed elevation: https://data.bas.ac.uk/metadata.php?id=GB/NERC/BAS/PDC/01277
    # 'BAS_2002_TORUS_AIR_BM2': '',
    'BAS_2004_BBAS_AIR_BM2': 'BAS/BBAS',
    'BAS_2005_WISE-ISODYN_AIR_BM2': 'BAS/WISE_ISODYN',
    'BAS_2006_GRADES-IMAGE_AIR_BM2': 'BAS/GRADES_IMAGE',
    'BAS_2007_AGAP_AIR_BM2': 'BAS/AGAP',
    # No source given; radar was DELORES, N. Ross listed as creator
    # 'BAS_2007_Lake-Ellsworth_GRN_BM3': '',
    # Radar was DELORES; created by Ed King; only released grid: https://dx.doi.org/10.5285/54757cbe-0b13-4385-8b31-4dfaa1dab55e
    # 'BAS_2007_Rutford_GRN_BM3': '',
    # Radar was DELORES; A. Smith & R. Bingham; no source.
    # 'BAS_2007_TIGRIS_GRN_BM2': '',
    # Again, no source given; radar was DELORES, N. Ross listed as creator
    # 'BAS_2008_Lake-Ellsworth_GRN_BM3': '',
    # Radar was DELORES; A. Smith & R. Bingham; no source.
    # 'BAS_2009_FERRIGNO_GRN_BM2': '',
    'BAS_2010_IMAFI_AIR_BM2': 'BAS/IMAFI',
    'BAS_2010_IMAFI_AIR_BM3': 'BAS/IMAFI',  # IMAFI appeared in both; unclear why
    # Another bed-elevation only: https://data.bas.ac.uk/full-record.php?id=GB/NERC/BAS/PDC/01356
    # 'BAS_2010_PIG_AIR_BM2': '',  # ???
    # No source given; survey was 1/2 aeromag, 1/2 radar
    # 'BAS_2011_Adelaide_AIR_BM3': '', # ???
    # Radar was DELORES; created by A. Smith; no source or reference given
    # 'BAS_2012_Castle_GRN_BM3': '',
    'BAS_2012_ICEGRAV_AIR_BM3': 'BAS/ICEGRAV',
    # Another PIG survey with DELORES; no source given; D. Vaughn & R. Bingham created data.
    # 'BAS_2013_ISTAR_GRN_BM3': '',
    'BAS_2015_FISS_AIR_BM3': 'BAS/FISS2015',
    # POLARGAP radargrams have lines not in BM3.
    'BAS_2015_POLARGAP_AIR_BM3': 'BAS/POLARGAP',
    'BAS_2016_FISS_AIR_BM3': 'BAS/FISS2016',
    # English-Coast netCDFs appeared alongside FISS data, rather than where the associated BEDMAP3 metadata pointed
    'BAS_2017_English-Coast_AIR_BM3': 'BAS/FISS2016',
    # ??? Looks like 2018 Thwaites was primarily CReSIS gravity data??
    # 'BAS_2018_Thwaites_AIR_BM3': '',
    # 2019 Thwaites radargrams are missing one line that appeared in BM3,
    # so keep plotting them with BM3 as well.
    # 'BAS_2019_Thwaites_AIR_BM3': 'BAS/ITGC_2019',

    ####################################
    ##            CRESIS              ##
    ####################################
    'CRESIS_2009_AntarcticaTO_AIR_BM3.csv': 'CRESIS/2009_Antarctica_TO',
    # This one has swath data in Bedmap -- one of the surveys was tight enough
    # to get almost full coverage.
    'CRESIS_2009_Thwaites_AIR_BM3.csv': 'CRESIS/2009_Antarctica_TO',
    'CRESIS_2013_Siple-Coast_AIR_BM3.csv': 'CRESIS/2013_Antarctica_Basler',


    ####################################
    ##            KOPRI               ##
    ####################################
    # Unfortunately, the KOPRI/KRT1 survey release didn't include Campbell glacier (which is in the bedmap release)
    # It's also missing all of the Nansen lines.
    # 'KOPRI_2017_KRT1_AIR_BM3.csv': '',
	# 'KOPRI_2018_KRT2_AIR_BM3.csv': '',

    ####################################
    ##              LDEO              ##
    ####################################
    # CRESIS also released some of this data via data.cresis.ku.edu, but it was missing a few transects
    'LDEO_2007_AGAP-GAMBIT_AIR_BM2': 'LDEO/AGAP_GAMBIT',

    # According to Studinger, the Recovery Lakes survey was part of the
    # AGAP-GAMBIT one, but the lines weren't released in the same dataset.
    # 'LDEO_2007_Recovery-Lakes_AIR_BM2.csv': '',
    # 'LDEO_2015_ROSETTA_AIR_BM3.csv': '',


    ####################################
    ##              NASA              ##
    ####################################

    # TODO: Should I download these data from NSIDC, rather than treating
    #       them like the rest of the cresis data?

    # Some of the lines are missing in the CRESIS data, but I think those
    # are all due to my throwing out granules with single bad Longitude coords.
    #'NASA_2002_ICEBRIDGE_AIR_BM2.csv': 'CRESIS/2002_Antarctica_P3Chile',
    'NASA_2004_ICEBRIDGE_AIR_BM2.csv': 'CRESIS/2004_Antarctica_P3Chile',
    # There's one line that doesn't appear in the CRESIS data,
    # and a polar orbit flight that's not in the NASA layer
    'NASA_2009_ICEBRIDGE_AIR_BM2.csv': 'CRESIS/2009_Antarctica_DC8',
    # Exactly the same as 2009 -- a few lines missing in each direction
    'NASA_2010_ICEBRIDGE_AIR_BM2.csv': 'CRESIS/2010_Antarctica_DC8',
    # It looks like this was accidentally a copy of the 2002_ICEBRIDGE??
    #'NASA_2011_ICEBRIDGE_AIR_BM2.csv': '',
    'NASA_2013_ICEBRIDGE_AIR_BM3.csv': 'CRESIS/2013_Antarctica_P3',
    'NASA_2014_ICEBRIDGE_AIR_BM3.csv': 'CRESIS/2014_Antarctica_DC8',
    'NASA_2016_ICEBRIDGE_AIR_BM3.csv': 'CRESIS/2016_Antarctica_DC8',
    'NASA_2017_ICEBRIDGE_AIR_BM3.csv': ('CRESIS/2017_Antarctica_P3', 'CRESIS/2017_Antarctica_Basler'),
    'NASA_2018_ICEBRIDGE_AIR_BM3.csv': 'CRESIS/2018_Antarctica_DC8',
    'NASA_2019_ICEBRIDGE_AIR_BM3.csv': 'CRESIS/2019_Antarctica_GV',

    ####################################
    ##              NIPR              ##
    ####################################
    # 'NIPR_1992_JARE33_GRN_BM3.csv': '',
    # 'NIPR_1996_JARE37_GRN_BM3.csv': '',
    'NIPR_1999_JARE40_GRN_BM2.csv': 'NIPR_1999_JARE40_GRN_BM3',	# Exact same points appear in both BM2 and BM3
	# 'NIPR_1999_JARE40_GRN_BM3.csv': '',
    'NIPR_2007_JARE49_GRN_BM2.csv': 'NIPR_2007_JARE49_GRN_BM3', # BM3 has denser bed picks for same lines
    # 'NIPR_2007_JARE49_GRN_BM3.csv': '',
    'NIPR_2007_JASE_GRN_BM2.csv': 'NIPR_2007_JASE_GRN_BM3',  # BM3 has denser bed picks for same lines
    # 'NIPR_2007_JASE_GRN_BM3.csv': '',
    # 'NIPR_2012_JARE54_GRN_BM3.csv': '',
    # 'NIPR_2018_JARE60_GRN_BM3.csv': '',
    # 'NIPR_2017_JARE59_GRN_BM3.csv': '',

    ####################################
    ##            STANFORD            ##
    ####################################
    'STANFORD_1971_SPRI-NSF-TUD_AIR_BM3.csv': "AVAILABLE",  # this is a subset of the SPRI tracks posted by Stanford.


    ####################################
    ##              UTIG              ##
    ####################################
    # "UTIG_1991_CASERTZ_AIR_BM2":
    # "UTIG_1998_West-Marie-Byrd-Land_AIR_BM2":
    # "UTIG_1999_SOAR-LVS-WLK_AIR_BM2":
    # "UTIG_2000_Robb-Glacier_AIR_BM2":

    # The AGASEA data release is missing a bunch of transit/turn lines
    # that DO appear in BEDMAP.
    "UTIG_2004_AGASEA_AIR_BM2.csv": "UTIG/AGASEA",

    # Looks partially, but not completely, in ICECAP release
    # "UTIG_2009_Darwin-Hatherton_AIR_BM3.csv":

    # This is ALMOST a subset of 2010 ICECAP, but there are 3 ASE
    # radials that only appear in the BM2 data.
    # The data released at NSIDC is missing a few transects, so we want to keep plotting this.
    # "UTIG_2008_ICECAP_AIR_BM2.csv": "UTIG/ICECAP",
    # "UTIG_2010_ICECAP_AIR_BM3.csv": "UTIG/ICECAP",

    # 4 Gimble lines made it into the ICECAP release, but I haven't
    # found anything else.
    # "UTIG_2013_GIMBLE_AIR_BM3.csv":

    # EAGLE mostly matches BEDMAP. netCDF files are there, but the
    # extracted lines seem to be missing:
    # * most of PEL/JKB2n/Y18a
    # * all of PEL/JKB2n/Y20a
    "UTIG_2015_EAGLE_AIR_BM3.csv": "UTIG/EAGLE",

    # Additionally, some of the files have issues:
    # * OIA/JKB2n/X60a has good data when plotted in jupyter, but the
    #   extracted path is simply [nan,nan]
    #   => the first 1180 traces have 'nan' for lat/lon
    # * OIA/JKB2n/X51a seems half missing, even though I've downloaded
    #   both granules. The turn on the southing end of the survey wasn't
    #   a turn -- F13T07a and F13T08a are both towards northing.
    "UTIG_2016_OLDICE_AIR_BM3.csv": "UTIG/OIA",
}