#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains unit tests for the pipework module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.pipework import Pipework

class TestPipework(unittest.TestCase):
    """ Unit tests for Pipework class """

    def setUp(self):
        """ Create Pipework object to be tested """
        self.simtime = SimulationTime(0, 8, 1)
        self.pipework = Pipework(1000, 0.01, 0.012, 1.0, 400, 0.035, 0.014, 10.0, 0.95)

    def test_R1(self):
        """ Test that correct R1 is returned when queried """
        self.assertAlmostEqual(self.pipework._Pipework__R1, 0.0318310, 7, msg="incorrect R1 returned")

    def test_R2(self):
        """ Test that correct R2 is returned when queried """
        self.assertAlmostEqual(self.pipework._Pipework__R2, 0.0000725, 7, msg="incorrect R2 returned")

    def test_R3(self):
        """ Test that correct R3 is returned when queried """
        self.assertAlmostEqual(self.pipework._Pipework__R3, 5.4748064, 7, msg="incorrect R3 returned")

    def test_Rc(self):
        """ Test that correct Rc is returned when queried """
        self.assertAlmostEqual(self.pipework._Pipework__Rc, 0.7957747, 7, msg="incorrect Rc returned")

    def test_heat_loss(self):
        """ Test that correct heat_loss is returned when queried """
        T_s = 40.0
        T_i = [60.0, 59.0, 58.0, 57.0, 56.0, 57.0, 58.0, 57.0]
        T_o = [15.0, 15.0, 16.0, 16.0, 17.0, 18.0, 19.0, 19.0]
        for t_idx, _, _ in self.simtime:
            with self.subTest(i = t_idx):
                self.assertAlmostEqual(self.pipework.heat_loss(T_s, T_i[t_idx], T_o[t_idx]),
                                 [7.4896702, 7.3232331, 6.9914049, 6.8249428, 6.4929912, 6.4939647, 6.4949393, 6.3284024][t_idx],
                                 7,
                                 msg="incorrect heat loss returned")
