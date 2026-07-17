#! /usr/bin/env bash
set -x
cat AWI_EMR_ANT1995-96.tab | grep -o 'antr[^ ]*\.nc' > dataset_995486_files.txt

