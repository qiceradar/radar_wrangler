#! /usr/bin/env zsh
# (Using zsh for mac)

QICERADAR_DATA=/Volumes/RadarData
LDEO_DIR=${QICERADAR_DATA}/LDEO/AGAP_GAMBIT
mkdir -p $LDEO_DIR
cd $LDEO_DIR

wget -c -r -d -nH --cut-dirs=5 http://wonder.ldeo.columbia.edu/data/AGAP/DataLevel_1/RADAR/DecimatedSAR_netcdf/index.html
