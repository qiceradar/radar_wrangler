#! /usr/bin/env bash

# The PANGAEA entries for these files provide a text file listing every line;
# we download those manually and them extract a single-column file containing
# just the filenames.

set -x

# Example filename: antr1996_9602092101_EMR600_19960209_00.nc
cat AWI_EMR_ANT1995-96.tab | grep -o 'antr[^ ]*\.nc' > dataset_995486_files.txt

# Example filename: 19972001_stp10.kml
cat AWI_EMR_ANT1996-97.tab | grep -o '[0-9]*_stp10*\.nc' > dataset_974229_files.txt
cat AWI_EMR_ANT1997-98.tab | grep -o '[0-9]*_stp10*\.nc' > dataset_974295_files.txt
cat AWI_EMR_ANT1998-99.tab | grep -o '[0-9]*_stp10*\.nc' > dataset_974402_files.txt
cat AWI_EMR_ANT2000-01.tab | grep -o '[0-9]*_stp10*\.nc' > dataset_974431_files.txt
cat AWI_EMR_ANT2001-02.tab | grep -o '[0-9]*_stp10*\.nc' > dataset_974432_files.txt
cat AWI_EMR_ANT2002-03.tab | grep -o '[0-9]*_stp10*\.nc' > dataset_982598_files.txt
cat AWI_EMR_ANT2005-06.tab | grep -o '[0-9]*_stp10*\.nc' > dataset_974441_files.txt
cat AWI_EMR_ANT2007-08.tab | grep -o '[0-9]*_stp10*\.nc' > dataset_974448_files.txt
cat AWI_EMR_ANT2008-09.tab | grep -o '[0-9]*_stp10*\.nc' > dataset_974453_files.txt
cat AWI_EMR_ANT2010-11_EPICA.tab | grep -o '[0-9]*_stp10*\.nc' > dataset_974319_files.txt
cat AWI_EMR_ANT2015-16.tab | grep -o '[0-9]*_stp7*\.nc' > dataset_987347_files.txt

# Example filename: Data_20170121_08_008_standard.nc
cat AWI_UWB_ANT2016-17_V2.tab | grep -o 'Data_.*_standard\.nc' > dataset_984741_files.txt
cat AWI_UWB_ANT2018-19_JuRaS.tab | grep -o 'Data_.*_standard\.nc' > dataset_976759_files.txt
cat AWI_UWB_ANT2018-19.tab | grep -o 'Data_.*_standard\.nc' > dataset_982515_files.txt

cat AWI_UWB_ANT2023-24_CHARISO.tab | grep -o 'Data_.*_standard\.nc' > dataset_990049_files.txt
cat AWI_UWB_ANT2024.tab | grep -o 'Data_.*_standard\.nc' > dataset_981128_files.txt
cat AWI_UWB_ANT2024-25_CHARISO.tab | grep -o 'Data_.*_standard\.nc' > dataset_981465_files.txt