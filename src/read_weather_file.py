#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module reads in an energy + weather file.
"""

import csv
from enum import Enum

COLUMN_LONGITUDE = 6
COLUMN_LATITUDE = 7
COLUMN_AIR_TEMP = 6
COLUMN_DIR_RAD = 14
COLUMN_HOR_RAD = 15
COLUMN_GROUND_REFLECT = 32

def weather_data_to_dict(weather_file):
    """ Read in weather file, return dictionary"""
    air_temperatures = []
    diff_hor_rad = []
    dir_beam_rad = []
    ground_solar_reflc = []

    with open(weather_file) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter = ',')
        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                longitude = row[COLUMN_LONGITUDE]
                latitude = row[COLUMN_LATITUDE]
            elif line_count >= 8:
                air_temperatures.append(row[COLUMN_AIR_TEMP])
                dir_beam_rad.append(row[COLUMN_DIR_RAD])
                diff_hor_rad.append(row[COLUMN_HOR_RAD])
                ground_solar_reflc.append(row[COLUMN_GROUND_REFLECT])
            line_count = line_count + 1

    external_conditions = {
        "air_temperatures": air_temperatures,
        "diffuse_horizontal_radiation": diff_hor_rad,
        "direct_beam_radiation": dir_beam_rad.append,
        "solar_reflectivity_of_ground": ground_solar_reflc,
        "longitude": longitude,
        "latitude": latitude
        }

    return external_conditions
