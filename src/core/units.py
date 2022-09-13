#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains common unit conversions for use by other modules.
"""

J_per_kWh = 3600000
W_per_kW = 1000
minutes_per_hour = 60
seconds_per_hour = 3600
hours_per_day = 24

def Celcius2Kelvin(temp_C):
    assert temp_C >= -273.15
    return temp_C + 273.15

def Kelvin2Celcius(temp_K):
    assert temp_K >= 0
    return temp_K - 273.15
