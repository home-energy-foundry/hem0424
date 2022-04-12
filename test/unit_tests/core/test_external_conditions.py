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
