#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains unit tests for the Storage Tank module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.material_properties import WATER, MaterialProperties
from core.heating_systems.storage_tank import StorageTank, ImmersionHeater
from core.water_heat_demand.cold_water_source import ColdWaterSource
from core.energy_supply.energy_supply import EnergySupply, EnergySupplyConnection
from core.controls.time_control import OnOffTimeControl

class Test_StorageTank(unittest.TestCase):
    """ Unit tests for StorageTank class """

    def setUp(self):
        """ Create StorageTank object to be tested """
        coldwatertemps   = [1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4]
        self.simtime     = SimulationTime(0, 8, 1)
        coldfeed         = ColdWaterSource(coldwatertemps, self.simtime, 0, 1)
        self.storagetank = StorageTank(150.0, 0.9, 55.0, coldfeed, WATER)
        control          = OnOffTimeControl(
                               [True, False, False, False, True, True, True, True],
                               self.simtime,
                               0,
                               1
                               )
        energysupply     = EnergySupply("gas", self.simtime)
        energysupplyconn = energysupply.connection("shower")
        imheater         = ImmersionHeater(50.0, energysupplyconn, self.simtime, control)
        heatsource       = self.storagetank.add_heat_source(imheater, 0.9)

    def test_demand_hot_water(self):
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.storagetank.demand_hot_water([10.0, 10.0, 15.0, 20.0, 20.0, 20.0, 20.0, 20.0][t_idx])
                self.assertEqual(
                    self.storagetank._StorageTank__vol_hot,
                    [125.0, 115.0, 100.0, 80.0, 150.0, 130.0, 110.0, 150.0][t_idx],
                    "incorrect hot water volume returned"
                    )

class Test_ImmersionHeater(unittest.TestCase):
    """ Unit tests for ImmersionHeater class """

    def setUp(self):
        """ Create ImmersionHeater object to be tested """
        self.simtime          = SimulationTime(0, 4, 1)
        energysupply          = EnergySupply("gas", self.simtime)
        energysupplyconn      = energysupply.connection("shower")
        control               = OnOffTimeControl([True, True, False, True], self.simtime, 0, 1)
        self.immersionheater  = ImmersionHeater(50, energysupplyconn, self.simtime, control)

    def test_demand_energy(self):
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.immersionheater.demand_energy([40.0, 100.0, 30.0, 20.0][t_idx]),
                    [40.0, 50.0, 0.0, 20.0][t_idx],
                    "incorrect energy supplied returned",
                    )
