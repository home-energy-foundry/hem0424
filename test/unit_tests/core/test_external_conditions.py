#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains unit tests for the external_conditions module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.external_conditions import ExternalConditions

class TestExternalConditions(unittest.TestCase):
    """ Unit tests for ExternalConditions class """

    def setUp(self):
        """ Create ExternalConditions object to be tested """
        self.simtime = SimulationTime(0, 8, 1)
        self.airtemp = [0.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 20.0]
        self.groundtemp = [8.0, 8.7, 9.4, 10.1, 10.8, 10.5, 11.0, 12.7]
        self.diffuse_horizontal_radiation = [333, 610, 572, 420, 0, 10, 90, 275]
        self.direct_beam_radiation = [420, 750, 425, 500, 0, 40, 0, 388]
        self.solar_reflectivity_of_ground = [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2]
        self.latitude = 51.42
        self.longitude = -0.75
        self.timezone = 0
        self.start_day = 100
        self.end_day = 100
        self.january_first = 1
        self.daylight_savings = "not applicable"
        self.leap_day_included = False
        self.extcond = ExternalConditions(self.simtime, 
                                          self.airtemp, 
                                          self.groundtemp,
                                          self.diffuse_horizontal_radiation,
                                          self.direct_beam_radiation,
                                          self.solar_reflectivity_of_ground,
                                          self.latitude,
                                          self.longitude,
                                          self.timezone,
                                          self.start_day,
                                          self.end_day,
                                          self.january_first,
                                          self.daylight_savings,
                                          self.leap_day_included
                                        )

    def test_air_temp(self):
        """ Test that ExternalConditions object returns correct air temperatures """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.extcond.air_temp(),
                    self.airtemp[t_idx],
                    "incorrect air temp returned",
                    )

    def test_ground_temp(self):
        """ Test that ExternalConditions object returns correct ground temperatures """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.extcond.ground_temp(),
                    self.groundtemp[t_idx],
                    "incorrect ground temp returned",
                    )

    def diffuse_horizontal_radiation(self):
        """ Test that ExternalConditions object returns correct diffuse_horizontal_radiation """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.extcond.diffuse_horizontal_radiation(),
                    self.diffuse_horizontal_radiation[t_idx],
                    "incorrect diffuse_horizontal_radiation returned",
                    )
                
    def direct_beam_radiation(self):
        """ Test that ExternalConditions object returns correct direct_beam_radiation """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.extcond.direct_beam_radiation(),
                    self.direct_beam_radiation[t_idx],
                    "incorrect direct_beam_radiation returned",
                    )
                
    def solar_reflectivity_of_ground(self):
        """ Test that ExternalConditions object returns correct solar_reflectivity_of_ground """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.extcond.solar_reflectivity_of_ground(),
                    self.solar_reflectivity_of_ground[t_idx],
                    "incorrect solar_reflectivity_of_ground returned",
                    )