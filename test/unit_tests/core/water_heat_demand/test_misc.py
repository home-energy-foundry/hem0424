#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains unit tests for the misc module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.water_heat_demand.misc import frac_hot_water

class TestMisc(unittest.TestCase):
    """ Unit tests for functions in the misc.py file """
    def test_frac_hot_water(self):
        self.assertEqual(
            frac_hot_water(40, 55, 5),
            0.7,
            "incorrect fraction of hot water returned",
            )