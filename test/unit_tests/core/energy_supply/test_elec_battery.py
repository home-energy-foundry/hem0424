#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains unit tests for the elec_battery module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.energy_supply.elec_battery import ElectricBattery

class TestElectricBattery(unittest.TestCase):
    """ Unit tests for ElectricBattery class """

    def setUp(self):
        """ Create ElectricBattery object to be tested """
        self.elec_battery = ElectricBattery(2000, 0.8)

    def test_charge_discharge_battery(self):
        """ Test the charge_discharge_battery function including for
            overcharging and overdischarging.
        """
        #Demand on battery exceeds limit
        self.elec_battery = ElectricBattery(2000, 0.8)
        self.assertAlmostEqual(self.elec_battery.charge_discharge_battery(-100), 0)

        #Normal supply cases
        self.assertAlmostEqual(self.elec_battery.charge_discharge_battery(10), 10)
        self.elec_battery = ElectricBattery(2000, 0.8)
        self.assertAlmostEqual(self.elec_battery.charge_discharge_battery(100), 100)

        #Supply to battery exceeds limit
        self.elec_battery = ElectricBattery(2000, 0.8)
        self.assertAlmostEqual(self.elec_battery.charge_discharge_battery(1000000), 2000/(0.8**0.5))
