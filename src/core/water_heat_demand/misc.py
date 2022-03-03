#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains miscellaneous free functions related to water heat demand.
"""

def frac_hot_water(temp_target, temp_hot, temp_cold):
    """ Calculate the fraction of hot water required when mixing hot and cold
    water to achieve a target temperature

    Arguments:
    temp_target -- temperature to be achieved, in any units
    temp_hot    -- temperature of hot water to be mixed, in same units as temp_target
    temp_cold   -- temperature of cold water to be mixed, in same units as temp_target
    """
    return (temp_target - temp_cold) / (temp_hot - temp_cold)
