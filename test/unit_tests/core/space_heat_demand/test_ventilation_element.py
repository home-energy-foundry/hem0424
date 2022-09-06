#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains unit tests for the building_element module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.external_conditions import ExternalConditions
from core.simulation_time import SimulationTime
from core.space_heat_demand.ventilation_element import VentilationElementInfiltration

class TestVentilationElementInfiltration(unittest.TestCase):
    """ Unit tests for VentilationElementInfiltration class """

    def setUp(self):
        """ Create VentilationElementInfiltration objects to be tested """
        self.simtime = SimulationTime(0, 8, 1)
        air_temps = [0.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 17.5]
        wind_speeds = [3.7, 3.8, 3.9, 4.0, 4.1, 4.2, 4.3, 4.4]
        self.ec = ExternalConditions(self.simtime, air_temps, None, wind_speeds)
        self.ve_inf = VentilationElementInfiltration(1.0, 
                                                    "sheltered",
                                                    "house",
                                                    4.5,
                                                    "Q50",
                                                    40.0,
                                                    75.0,
                                                    2.0,
                                                    2.0,
                                                    2.0,
                                                    1.0,
                                                    0.0,
                                                    0.0,
                                                    0.0,
                                                    3.0,
                                                    6.0,
                                                    0.0,
                                                    self.ec,)

    def test_inf_openings(self):
        """ Test that correct infiltration rate for openings
         is returned when queried """
        self.assertEqual(
            self.ve_inf._VentilationElementInfiltration__inf_openings,
            4.0,
            "incorrect infiltration rate for openings returned"
            )

    def test_divisor(self):
        """ Test that correct Q50 divisor is returned when queried """
        self.assertEqual(
            self.ve_inf._VentilationElementInfiltration__divisor,
            29.4,
            "incorrect Q50 divisor returned"
            )

    def test_shelter_factor(self):
        """ Test that correct shelter factor is returned when queried """
        self.assertEqual(
            self.ve_inf._VentilationElementInfiltration__shelter_factor,
            0.85,
            "incorrect shelter factor returned"
            )

    def test_infiltration(self):
        """ Test that correct infiltration rate is returned when queried """
        self.assertAlmostEqual(
            self.ve_inf._VentilationElementInfiltration__infiltration,
            3.553061,
            6,
            "incorrect infiltration rate returned"
            )

    def test_h_ve(self):
        """ Test that correct heat transfer coeffient (h_ve) is returned when queried """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertAlmostEqual(
                    self.ve_inf.h_ve(),
                    [0.0829331, 0.0851745, 0.0874159, 0.0896574, 0.0918988, 0.0941402, 0.0963817, 0.0986231][t_idx],
                    7,
                    "incorrect heat transfer coeffient (h_ve) returned"
                    )

    def test_temp_supply(self):
        """ Test that the correct external temperature is returned when queried """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i = t_idx):
                self.assertEqual(
                    self.ve_inf.temp_supply(),
                    t_idx * 2.5,
                    "incorrect ext temp returned",
                    )

