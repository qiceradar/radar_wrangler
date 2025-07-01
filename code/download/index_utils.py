"""
Utilities for reading and writing the CSV index of granules.
"""

import csv

from dataclasses import dataclass


@dataclass
class Granule:
    granule_name: str  # Must be unique; primary key in database
    region: str  # ANTARCTIC or ARCTIC
    institution: str
    campaign: str
    segment: str  # either flight or PST
    granule: str  # represents a number, but the leading zeroes matter
    data_product: str  # e.g. CSARP_standard, ER2HI1B, IR1HI1B, KHERA1B, etc.
    data_format: str  # e.g. utig_netcdf
    # path (including filename) relative to QIceRadar base data directory where data will be saved
    relative_filepath: str
    download_url: str  # download link
    download_method: str  # e.g. curl, wget, nsidc


def write_granule_list(index_filepath: str, cresis_granules: list[Granule]) -> None:
    with open(index_filepath, 'w', newline='') as fp:
        fields = [field.name for field in Granule.__dataclass_fields__.values()]
        csv_writer = csv.DictWriter(fp, fieldnames=fields)
        csv_writer.writeheader()

        for granule in cresis_granules:
            csv_writer.writerow(granule.__dict__)


def read_granule_list(index_filepath: str) -> list[Granule]:
    print(f"read_granule_list: {index_filepath}")
    granules = []
    with open(index_filepath, 'r', newline='') as fp:
        csv_reader = csv.DictReader(fp)
        granules = [Granule(**row) for row in csv_reader]
    return granules
