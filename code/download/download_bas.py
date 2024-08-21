#! /usr/bin/env python3

import csv
import os
import os.path
import pathlib
import re
import sqlite3
import subprocess
import tempfile

# I really don't love mixing data and code, but I'm feeling lazy,
# and don't want to have to deal with additional config files.
data_citations = {}
data_citations[
    "AGAP"
] = "Corr, H., Ferraccioli, F., Jordan, T., & Robinson, C. (2021). Processed airborne radio-echo sounding data from the AGAP survey covering Antarctica's Gamburtsev Province, East Antarctica (2007/2009) (Version 1.0) [Data set]. NERC EDS UK Polar Data Centre. https://doi.org/10.5285/A1ABF071-85FC-4118-AD37-7F186B72C847"
data_citations[
    "BBAS"
] = "Corr, H., Ferraccioli, F., & Vaughan, D. (2021). Processed airborne radio-echo sounding data from the BBAS survey covering the Pine Island Glacier basin, West Antarctica (2004/2005) (Version 1.0) [Data set]. NERC EDS UK Polar Data Centre. https://doi.org/10.5285/DB8BDBAD-6893-4A77-9D12-A9BCB7325B70"
data_citations[
    "FISS2015"
] = "Nicholls, K., Robinson, C., Corr, H., & Jordan, T. (2021). Processed airborne radio-echo sounding data from the FISS 2015 survey covering the Foundation Ice Stream, Bungenstock Ice Rise, and the Filchner Ice Shelf system, West Antarctica (2015/2016) (Version 1.0) [Data set]. NERC EDS UK Polar Data Centre. https://doi.org/10.5285/3507901F-D03E-45A6-8D9B-59CF98A03E1D"

data_citations[
    "FISS2016"
] = "Corr, H., Robinson, C., Jordan, T., Nicholls, K., & Brisbourne, A. (2021). Processed airborne radio-echo sounding data from the FISS 2016 surveys covering the Filchner and Halley Ice Shelves, and the English Coast (western Palmer Land), West Antarctica (2016/2017) (Version 1.0) [Data set]. NERC EDS UK Polar Data Centre. https://doi.org/10.5285/0CB61583-3985-4875-B141-5743E68ABE35"
data_citations[
    "GRADES_IMAGE"
] = "Corr, H. (2021). Processed airborne radio-echo sounding data from the GRADES-IMAGE survey covering the Evans and Rutford Ice Streams, and ice rises in the Ronne Ice Shelf, West Antarctica (2006/2007) (Version 1.0) [Data set]. NERC EDS UK Polar Data Centre. https://doi.org/10.5285/C7EA5697-87E3-4529-A0DD-089A2ED638FB"
data_citations[
    "ICEGRAV"
] = "Ferraccioli, F., Corr, H., Jordan, T., Forsberg, R., Matsuoka, K., Diez, A., Olesen, A., Ghidella, M., Zakrajsek, A., Robinson, C., & King, O. (2021). Processed airborne radio-echo sounding data from the ICEGRAV survey covering the Recovery Catchment and interior Dronning Maud Land, East Antarctica (2012/2013) (Version 1.0) [Data set]. NERC EDS UK Polar Data Centre. https://doi.org/10.5285/C6324118-94A2-4E03-8715-B24B82322A57"
data_citations[
    "IMAFI"
] = "Ross, N., Bingham, R., Ferraccioli, F., Jordan, T., Le Brocq, A., Rippin, D., & Siegert, M. (2021). Processed airborne radio-echo sounding data from the IMAFI survey covering the Institute and Moller ice streams and the Patriot Hills, West Antarctica (2010/2011) (Version 1.0) [Data set]. NERC EDS UK Polar Data Centre. https://doi.org/10.5285/F32B298B-7906-4360-9E34-16739AF73BB7"
data_citations[
    "ITGC_2019"
] = "Jordan, T., & Robinson, C. (2021). Processed airborne radio-echo sounding data for the Thwaites Glacier 2019 survey, West Antarctica (2019/2020) (Version 1.0) [Data set]. NERC EDS UK Polar Data Centre. https://doi.org/10.5285/E7ABA676-1FDC-4C9A-B125-1EBE6124E5DC"
data_citations[
    "POLARGAP"
] = "Ferraccioli, F., Forsberg, R., Matsuoka, K., Olesen, A., Jordan, T., Corr, H., Robinson, C., & Kohler, J. (2021). Processed airborne radio-echo sounding data from the POLARGAP survey covering the South Pole, and Foundation and Recovery Glaciers, East Antarctica (2015/2016) (Version 1.0) [Data set]. NERC EDS UK Polar Data Centre. https://doi.org/10.5285/E8A29FA7-A245-4A04-8B56-098DEFA134B9"
data_citations[
    "WISE_ISODYN"
] = "Ferraccioli, F., Corr, H., Jordan, T., Robinson, C., Armadillo, E., Bozzo, E., & Caneva, G. (2021). Processed airborne radio-echo sounding data from the WISE-ISODYN survey across the Wilkes Subglacial Basin, East Antarctica (2005/2006) (Version 1.0) [Data set]. NERC EDS UK Polar Data Centre. https://doi.org/10.5285/70ADAB3D-3632-400D-9AA1-DDF2D62A11B3"

data_citations[
    "GOG3"
] = "Benham, T., Christoffersen, P., Dowdeswell, J., Siegert, M., Blankenship, D., Young, D., Kempf, S., & Palmer, S. (2020). Airborne geophysical data from the Queen Elizabeth Islands, Canadian Arctic, 2014 (Version 1.0) [Data set]. UK Polar Data Centre, Natural Environment Research Council, UK Research & Innovation. https://doi.org/10.5285/D31550DE-13C2-4779-AA10-9E0A43BBEB1A"

# Unlike some places, BAS doesn't explicitly request science citations
# for using the data, though they do provide them for reference.
science_citations = {}
science_citations["AGAP"] = (
    "Bell, Ferraccioli, Creyts, Braaten, Corr, Das, Damaske, Frearson, Jordan, Rose, Studinger, Wolovick (2011). Widespread Persistent Thickening of the East Antarctic Ice Sheet by Freezing from the Base. Science 331; doi: 10.1126/science.1200109 \n\n"
    "Ferraccioli, F., C. Finn, T. A. Jordan, R. E. Bell, L. M. Anderson and D. Damaske (2011). East Antarctic rifting triggers uplift of the Gamburtsev Mountains. Nature 479: 388-392, doi: 10.1038/nature10566. \n\n"
    "Rose, K.C., Ferraccioli, F., Jamieson, S.S., Bell, R.E., Corr, H., Creyts, T.T., Braaten, D., Jordan, T.A., Fretwell, P.T. and Damaske, D. (2013). Early east Antarctic Ice Sheet growth recorded in the landscape of the Gamburtsev Subglacial Mountains. Earth and Planetary Science Letters, 375, pp.1-12. doi: 10.1016/j.epsl.2013.03.053 \n\n"
)
science_citations[
    "BBAS"
] = "Vaughan, D.G., Corr, H.F.J., Ferraccioli, F., Frearson, N., O'Hare, A., Mach, D., Holt, J.W., Blankenship, D., Morse, D.L. & Young, D.A. 2006. New boundary conditions for the West Antarctic ice sheet: Subglacial topography beneath Pine Island Glacier. Geophysical Research Letters. 33. L09501, doi:10.1029/2005GL025588."
science_citations["FISS2015"] = ""  # Not listed at the landing page
science_citations["FISS2016"] = ""  # Not listed at the landing page
science_citations["GRADES_IMAGE"] = (
    "Ashmore, D.W., Bingham, R.G., Hindmarsh, R.C., Corr, H.F. and Joughin, I.R., 2014. The relationship between sticky spots and radar reflectivity beneath an active West Antarctic ice stream. Annals of Glaciology, 55(67), pp.29-38. https://doi.org/10.3189/2014AoG67A052 \n\n"
    "Jeofry, H., Ross, N., Corr, H.F., Li, J., Morlighem, M., Gogineni, P. and Siegert, M.J., 2018. A new bed elevation model for the Weddell Sea sector of the West Antarctic Ice Sheet. Earth System Science Data, 10(2), pp.711-725.doi: https://doi.org/10.5194/essd-10-711-2018"
)
science_citations["ICEGRAV"] = (
    "Diez A., K. Matsuoka, F. Ferraccioli, T.A. Jordan, H.F.J. Corr, J. Kohler, A. Olesen, and R. Forsberg (2018) Basal settings control fast ice flow in the Recovery/Slessor/Bailey Region, East Antarctica. Geophys. Res. Lett., 45, doi:10.1002/2017GL076601 \n\n"
    "Forsberg, R., Olesen, A. V., Ferraccioli, F., Jordan, T. A., Matsuoka, K., Zakrajsek, A., Greenbaum, J. S. (2018) Exploring the Recovery Lakes region and interior Dronning Maud Land, East Antarctica, with airborne gravity, magnetic and radar measurements. Geological Society, London, Special Publications, 461(1), 23-34. doi: 10.1144/SP461.17"
)
science_citations["IMAFI"] = (
    "Ross, N., Bingham, R. G., Corr, H. F. J., Ferraccioli, F., Jordan, T. A., Le Brocq, A., Rippin, D. M., Young, D., Blankenship, D. D., and Siegert, M. J. (2012): Steep reverse bed slope at the grounding line of the Weddell Sea sector in West Antarctica, Nature Geoscience, 5, 393-396, 2012. doi: https://doi.org/10.1038/NGEO1468 \n\n"
    "Jordan, T.A., Ferraccioli, F., Ross, N., Corr, H.F.J., Leat, P.T., Bingham, R.C., Rippin, D.M., Le Brocq, A & Siegert, M.J. 2010. Inland extent of the Weddell Sea Rift imaged by new aerogeophysical data. Tectonophysics, 585, 137-160. https://doi.org/10.1016/j.tecto.2012.09.010 \n\n"
    "Jeofry, H., Ross, N., Corr, H.F., Li, J., Morlighem, M., Gogineni, P. and Siegert, M.J., 2018. A new bed elevation model for the Weddell Sea sector of the West Antarctic Ice Sheet. Earth System Science Data, 10(2), pp.711-725.doi: https://doi.org/10.5194/essd-10-711-2018"
)
science_citations["ITGC_2019"] = ""  # Not listed at the landing page
science_citations["POLARGAP"] = (
    "Jordan, T.A., Martin, C., Ferraccioli, F., Matsuoka, K., Corr, H., Forsberg, R., Olesen, A. and Siegert, M., 2018. Anomalously high geothermal flux near the South Pole. Scientific reports, 8(1), pp.1-8. https://doi.org/10.1038/s41598-018-35182-0 \n\n"
    "Paxman, G.J., Jamieson, S.S., Ferraccioli, F., Jordan, T.A., Bentley, M.J., Ross, N., Forsberg, R., Matsuoka, K., Steinhage, D., Eagles, G. and Casal, T.G., 2019. Subglacial Geology and Geomorphology of the Pensacola Pole Basin, East Antarctica. Geochemistry, Geophysics, Geosystems, 20(6), pp.2786-2807. https://doi.org/10.1029/2018GC008126 \n\n"
    "Winter, K., Ross, N., Ferraccioli, F., Jordan, T.A., Corr, H.F., Forsberg, R., Matsuoka, K., Olesen, A.V. and Casal, T.G., 2018. Topographic steering of enhanced ice flow at the bottleneck between East and West Antarctica. Geophysical Research Letters, 45(10), pp.4899-4907. https://doi.org/10.1029/2018GL077504 \n\n"
    "Diez, A., Matsuoka, K., Jordan, T.A., Kohler, J., Ferraccioli, F., Corr, H.F., Olesen, A.V., Forsberg, R. and Casal, T.G., 2019. Patchy lakes and topographic origin for fast flow in the Recovery Glacier system, East Antarctica. Journal of Geophysical Research: Earth Surface, 124(2), pp.287-304. https://doi.org/10.1029/2018JF004799"
)
science_citations["WISE_ISODYN"] = ""  # Not listed at the landing page


def download_all_bas(qiceradar_dir: str, antarctic_index: str, arctic_index: str):
    """
    Ensures that all BAS data has been downloaded to the specified root
    directory, and updates the input index database with url and path info.
    """
    institution = "BAS"
    index_dir = "../../data/BAS"

    campaign_indices = {
        ff.split(".")[0]: f"{index_dir}/{ff}"
        for ff in os.listdir(index_dir)
        if ff.endswith(".csv")
    }

    for campaign, filepath in campaign_indices.items():
        if campaign in ["GOG3"]:
            region = "ARCTIC"
            connection = sqlite3.connect(arctic_index)
        else:
            region = "ANTARCTIC"
            connection = sqlite3.connect(antarctic_index)
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")

        campaign_dir = f"{region}/{institution}/{campaign}"
        dest_dir = f"{qiceradar_dir}/{campaign_dir}"
        print(
            f"Saving campaign {campaign} from institution {institution} to {dest_dir}"
        )
        try:
            pp = pathlib.Path(dest_dir)
            pp.mkdir(parents=True, exist_ok=True)
        except FileExistsError as ex:
            raise Exception(
                "Could not create {} for {}'s campaign {}: {}.".format(
                    dest_dir, institution, campaign, ex
                )
            )

        # Science citation is optional; data and doi required
        try:
            science_citation = science_citations[campaign]
        except KeyError:
            science_citation = ""
        cursor.execute(
            "INSERT OR REPLACE INTO campaigns VALUES(?, ?, ?, ?)",
            [
                campaign,
                institution,
                data_citations[campaign],
                science_citation,
            ],
        )
        connection.commit()

        with open(filepath) as csvfile:
            csv_reader = csv.DictReader(csvfile)
            for flight in csv_reader:
                # print("{} {}: {}".format(
                #     campaign, flight['name'], flight['url']))
                # TODO: Consider checking filesize for complete download, rather than checking file exists?
                #    However, that would require somehow having the metadata for expected file size, and IIRC, that may differ slightly
                #    on different filesystems.
                #    => `wget -c` may be the answer to this! Let wget check sizes.
                relative_filepath = f"{campaign_dir}/{flight['name']}"
                dest_filepath = f"{qiceradar_dir}/{relative_filepath}"
                # Save data about this granule to the database
                # TODO:
                # filepath (wheere it should be saved within the QIceRadar directory structure)
                # url (where we'll download it from)
                # download_method: 'wget' in this case.

                # format is {campaign}_{segment}.nc
                # This is the problem -- need to be more robust to their file names.
                # The challenge is we have an unpredictable number of underscores.
                # e.g.: WISE_ISODYN_W09.nc, WISE_ISODYN_10_.nc, and WISE_IDOSYN_10B_A.nc
                # and BBAS_B27.nc
                # Whatever I do, GOG3 will break it: IR2HI2_2014130_GRANT_JKB2k_X2Aa_icethk
                if campaign in ["AGAP", "BBAS", "FISS2015", "FISS2016", "ICEGRAV", "IMAFI", "POLARGAP"]:
                    expr = r"(?P<campaig>[A-Z0-9]+)_(?P<flight>[A-Za-z0-9_]+).nc"
                elif campaign in ["GRADES_IMAGE", "ITGC_2019", "WISE_ISODYN"]:
                    expr = r"(?P<campaign>[A-Z0-9]+_[A-Z0-9]+)_(?P<flight>[A-Za-z0-9_]+).nc"
                else:
                    print(f"NYI: trying to parse filename from BAS campaign {campaign}")
                    continue
                mm = re.match(expr, flight["name"])
                if mm is None:
                    print(f"Unable to parse flight: {flight['name']}")
                    continue
                segment = mm.group('flight')
                granule_name = pathlib.Path(
                    f"{institution}_{campaign}_{segment}"
                ).with_suffix("")
                # TODO: the BAS formats are COMPLICATED. each campaign is different.
                #       I haven't decided yet whether I want to name them differently,
                #       or handle it in the BAS parser. I'm leaning towards the later.
                # NB: GOG3 was released by BAS, but was UTIG's radar.
                if campaign in ["GOG3"]:
                    data_format = "ice_thickness"
                else:
                    data_format = "bas_netcdf"
                download_method = "wget"
                filesize = -1
                if os.path.exists(dest_filepath):
                    filesize = os.path.getsize(dest_filepath)
                    print(
                        "Skipping {}: file already exists with size {}".format(
                            flight["name"], filesize
                        )
                    )
                else:
                    try:
                        # Create a temporary file to avoid having to clean up partial downloads.
                        # This may not be ideal if the temporary file is created in a different filesystem than the
                        # output file belongs in. (I expect to eventually be downloading data to an external drive/NAS)
                        # TODO: create the temporary file in the same directory? or in the RadarData directory?
                        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                            # wget_cmd = ["wget", "--no-clobber", "--quiet", "--output-document", dest_filepath, flight['url']]
                            # If saving to a temp file, get rid of --no-clobber, since the file will already have been created.
                            wget_cmd = [
                                "wget",
                                "--quiet",
                                "--output-document",
                                temp_file.name,
                                "{}".format(flight["url"]),
                            ]

                            subprocess.check_call(wget_cmd)
                            # TODO: for plugin download, replace this with
                            #       `shutil.move` for cross-platform compatibility
                            move_cmd = ["mv", temp_file.name, dest_filepath]
                            subprocess.check_call(move_cmd)
                            print("Got {}!".format(flight["name"]))
                            filesize = os.path.getsize(dest_filepath)

                    except subprocess.CalledProcessError as ex:
                        print("Failed to download {}: {}".format(flight["name"], ex))
                cursor.execute(
                    "INSERT OR REPLACE INTO granules VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        str(granule_name),
                        institution,
                        campaign,
                        segment,
                        "",  # granule
                        "",  # product (multiple products included in single file)
                        data_format,
                        download_method,
                        flight["url"],
                        str(relative_filepath),
                        str(filesize),
                    ],
                )
                connection.commit()
    connection.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "data_directory", help="Root directory for all QIceRadar-managed radargrams."
    )
    parser.add_argument(
        "antarctic_index",
        help="Geopackage database to update with metadata about Antarctic campaigns and granules",
    )
    parser.add_argument(
        "arctic_index",
        help="Geopackage database to update with metadata about Arctic campaigns and granules",
    )
    args = parser.parse_args()
    download_all_bas(args.data_directory, args.antarctic_index, args.arctic_index)
