#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains unit tests for the Ductwork module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.ductwork import Ductwork

class TestDuctwork(unittest.TestCase):
    """ Unit tests for Ductwork class """

    def setUp(self):
        """ Create Ductwork objects to be tested """
        self.ductwork = Ductwork(0.025, 0.027, 0.4, 0.2, 0.15, "false" ,"intake", "inside")
        self.simtime = SimulationTime(0, 8, 1)

    def test_D_ins(self):
        """ Test that correct D_ins value is returned when queried """
        self.assertAlmostEqual(
            self.ductwork._Ductwork__D_ins,
            0.327,
            3,
            "incorrect D_ins returned"
            )

    def test_R1(self):
        """ Test that correct R1 value is returned when queried """
        self.assertAlmostEqual(
            self.ductwork._Ductwork__R1,
            0.82144,
            5,
            "incorrect R1 returned"
            )

    def test_R2(self):
        """ Test that correct R2 value is returned when queried """
        self.assertAlmostEqual(
            self.ductwork._Ductwork__R2,
            2.04600,
            5,
            "incorrect R2 returned"
            )

    def test_R3(self):
        """ Test that correct R3 value is returned when queried """
        self.assertAlmostEqual(
            self.ductwork._Ductwork__R3,
            0.09734,
            5,
            "incorrect R3 returned"
            )

    def test_heat_loss(self):
        """ Test that correct heat loss (q value) is returned when queried """
        T_o = [20.0, 19.5, 19.0, 18.5, 19.0, 19.5, 20.0, 20.5]
        T_i = [5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0]
        for t_idx, _, _ in self.simtime:
            with self.subTest(i = t_idx):
                self.assertAlmostEqual(
                    self.ductwork.heat_loss(T_i[t_idx], T_o[t_idx]),
                    [-2.02375, -1.82138, -1.61900, -1.41663, -1.34917, -1.28171, -1.21425, -1.14679][t_idx],
                    5,
                    "incorrect heat loss returned",
                    )

