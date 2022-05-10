#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains unit tests for units module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.units import Celcius2Kelvin, Kelvin2Celcius

class TestUnits(unittest.TestCase):
    """ Unit tests for free functions in units module """

    def test_temp_conversions(self):
        """ Test temperature conversions between Celcius and Kelvin """
        self.assertEqual(Celcius2Kelvin(20.0), 293.15, 'incorrect conversion of C to K')
        self.assertEqual(Kelvin2Celcius(5.0), -268.15, 'incorrect conversion of K to C')

        # Test round-trip conversion for range of temperatures
        for i in range (-10, 80):
            with self.subTest(i=i):
                self.assertEqual(
                    Kelvin2Celcius(Celcius2Kelvin(i)),
                    i,
                    'round trip temperature conversion (C to K to C) failed to return orig value'
                    )

if __name__ == '__main__':
    unittest.main()
