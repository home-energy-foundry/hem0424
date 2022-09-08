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
        air_temp_day_Jan = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 7.5,
                            10.0, 12.5, 15.0, 19.5, 17.0, 15.0, 12.0, 10.0, 7.0, 5.0, 3.0, 1.0
                           ]
        air_temp_day_Feb = [x + 1.0 for x in air_temp_day_Jan]
        air_temp_day_Mar = [x + 2.0 for x in air_temp_day_Jan]
        air_temp_day_Apr = [x + 3.0 for x in air_temp_day_Jan]
        air_temp_day_May = [x + 4.0 for x in air_temp_day_Jan]
        air_temp_day_Jun = [x + 5.0 for x in air_temp_day_Jan]
        air_temp_day_Jul = [x + 6.0 for x in air_temp_day_Jan]
        air_temp_day_Aug = [x + 6.0 for x in air_temp_day_Jan]
        air_temp_day_Sep = [x + 5.0 for x in air_temp_day_Jan]
        air_temp_day_Oct = [x + 4.0 for x in air_temp_day_Jan]
        air_temp_day_Nov = [x + 3.0 for x in air_temp_day_Jan]
        air_temp_day_Dec = [x + 2.0 for x in air_temp_day_Jan]

        self.airtemp = []
        self.airtemp.extend(air_temp_day_Jan * 31)
        self.airtemp.extend(air_temp_day_Feb * 28)
        self.airtemp.extend(air_temp_day_Mar * 31)
        self.airtemp.extend(air_temp_day_Apr * 30)
        self.airtemp.extend(air_temp_day_May * 31)
        self.airtemp.extend(air_temp_day_Jun * 30)
        self.airtemp.extend(air_temp_day_Jul * 31)
        self.airtemp.extend(air_temp_day_Aug * 31)
        self.airtemp.extend(air_temp_day_Sep * 30)
        self.airtemp.extend(air_temp_day_Oct * 31)
        self.airtemp.extend(air_temp_day_Nov * 30)
        self.airtemp.extend(air_temp_day_Dec * 31)

        self.extcond = ExternalConditions(self.simtime, self.airtemp)

    def test_air_temp(self):
        """ Test that ExternalConditions object returns correct air temperatures """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.extcond.air_temp(),
                    self.airtemp[t_idx],
                    "incorrect air temp returned",
                    )

    def test_air_temp_annual(self):
        """ Test that ExternalConditions object returns correct annual air temperature """
        self.assertAlmostEqual(
            self.extcond.air_temp_annual(),
            10.1801369863014,
            msg="incorrect annual air temp returned"
            )

    def test_air_temp_monthly(self):
        """ Test that ExternalConditions object returns correct monthly air temperature """
        results = []
        for t_idx, _, _ in self.simtime:
            month_idx = self.simtime.current_month()
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.extcond.air_temp_monthly(),
                    [6.75, 7.75, 8.75, 9.75, 10.75, 11.75,
                     12.75, 12.75, 11.75, 10.75, 9.75, 8.75,
                    ][month_idx],
                    "incorrect monthly air temp returned",
                    )
