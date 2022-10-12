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
        self.pipework = Pipework(0.025, 0.027, 1.0, 0.035, 0.038, 'false', 'water')

    def test_R1(self):
        """ Test that correct R1 is returned when queried """
        self.assertAlmostEqual(self.pipework._Pipework__R1, 0.00849, 5, msg="incorrect R1 returned")

    def test_R2(self):
        """ Test that correct R2 is returned when queried """
        self.assertAlmostEqual(self.pipework._Pipework__R2, 6.43829, 5, msg="incorrect R2 returned")

    def test_R3(self):
        """ Test that correct R3 is returned when queried """
        self.assertAlmostEqual(self.pipework._Pipework__R3, 0.30904, 5, msg="incorrect R3 returned")

    def test_heat_loss(self):
        """ Test that correct heat_loss is returned when queried """
        T_i = [50.0, 51.0, 52.0, 52.0, 51.0, 50.0, 51.0, 52.0]
        T_o = [15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 21.0, 21.0]
        for t_idx, _, _ in self.simtime:
            with self.subTest(i = t_idx):
                self.assertAlmostEqual(self.pipework.heat_loss(T_i[t_idx], T_o[t_idx]),
                                 [5.18072, 5.18072, 5.18072, 5.03270, 4.73666, 4.44062, 4.44062, 4.58864][t_idx],
                                 5,
                                 msg="incorrect heat loss returned")

    def test_temp_drop(self):
        """ Test that correct temperature drop is returned when queried """
        T_i = [50.0, 51.0, 52.0, 52.0, 51.0, 50.0, 51.0, 52.0]
        T_o = [15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 21.0, 21.0]
        for t_idx, _, _ in self.simtime:
            with self.subTest(i = t_idx):
                self.assertAlmostEqual(self.pipework.temperature_drop(T_i[t_idx], T_o[t_idx]),
                                 [35.0, 35.0, 35.0, 34.0, 32.0, 30.0, 30.0, 31.0][t_idx],
                                 5,
                                 msg="incorrect temperature drop returned")

    def test_cool_down_loss(self):
        """ Test that correct cool down loss is returned when queried """
        T_i = [50.0, 51.0, 52.0, 52.0, 51.0, 50.0, 51.0, 52.0]
        T_o = [15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 21.0, 21.0]
        for t_idx, _, _ in self.simtime:
            with self.subTest(i = t_idx):
                self.assertAlmostEqual(self.pipework.cool_down_loss(T_i[t_idx], T_o[t_idx]),
                                 [0.01997, 0.01997, 0.01997, 0.01940, 0.01826, 0.01712, 0.01712, 0.01769][t_idx],
                                 5,
                                 msg="incorrect cool down loss returned")

    def test_water_demand_to_kWh(self):
        """ Test that correct water demand to kWh is returned when queried """
        litres_demand = [5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0]
        demand_temp = [40.0, 35.0, 37.0, 39.0, 40.0, 38.0, 39.0, 40.0]
        cold_temp = [5.0, 4.0, 5.0, 6.0, 5.0, 4.0, 3.0, 4.0]
        for t_idx, _, _ in self.simtime:
            with self.subTest(i = t_idx):
                self.assertAlmostEqual(self.pipework.water_demand_to_kWh(litres_demand[t_idx], demand_temp[t_idx], cold_temp[t_idx]),
                               [0.20339, 0.36029, 0.55787, 0.76707, 1.01694, 1.18547, 1.46440, 1.67360][t_idx],
                               5,
                               msg="incorrect water demand to kWh returned")
