#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module reads in weather data from CIBSE csv file.
"""

import csv
from enum import Enum

COLUMN_LONGITUDE = 1
COLUMN_LATITUDE = 3
COLUMN_AIR_TEMP = 6 # dry bulb temp
COLUMN_WIND_SPEED = 11
COLUMN_DIR_RAD = 12 # global irradiation (horizantal plane)
COLUMN_HOR_RAD = 13 # diffuse irradiation (horizantal plane)
#COLUMN_GROUND_REFLECT = 32

def CIBSE_weather_data_to_dict(weather_file):
    """ Read in weather file, return dictionary"""
    air_temperatures = []
    wind_speeds = []
    diff_hor_rad = []
    dir_beam_rad = []
    ground_solar_reflc = []

    with open(weather_file) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter = ',')
        line_count = 0
        for row in csv_reader:
            if line_count == 5:
                longitude = float(row[COLUMN_LONGITUDE])
                latitude = float(row[COLUMN_LATITUDE])
            elif line_count >= 32:
                air_temperatures.append(float(row[COLUMN_AIR_TEMP]))
                wind_speeds.append(float(row[COLUMN_WIND_SPEED]))
                dir_beam_rad.append(float(row[COLUMN_DIR_RAD]))
                diff_hor_rad.append(float(row[COLUMN_HOR_RAD]))
                ground_solar_reflc.append(float(0.2))
            line_count = line_count + 1

    external_conditions = {
        "air_temperatures": air_temperatures,
        "wind_speeds": wind_speeds,
        "diffuse_horizontal_radiation": diff_hor_rad,
        "direct_beam_radiation": dir_beam_rad,
        "solar_reflectivity_of_ground": ground_solar_reflc,
        "longitude": longitude,
        "latitude": latitude
        }

    return external_conditions

