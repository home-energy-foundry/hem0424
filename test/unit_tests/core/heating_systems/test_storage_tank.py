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
        coldwatertemps = [10.0, 10.1, 10.2, 10.5, 10.6, 11.0, 11.5, 12.1]
        self.simtime     = SimulationTime(0, 8, 1)
        coldfeed         = ColdWaterSource(coldwatertemps, self.simtime, 0, 1)
        self.storagetank = StorageTank(150.0, 1.68, 55.0, coldfeed, self.simtime, WATER)
        control          = OnOffTimeControl(
                               [True, False, False, False, True, True, True, True],
                               self.simtime,
                               0,
                               1
                               )
        self.energysupply = EnergySupply("elec", self.simtime)
        energysupplyconn = self.energysupply.connection("immersion")
        imheater         = ImmersionHeater(50.0, energysupplyconn, self.simtime, control)
        heatsource       = self.storagetank.add_heat_source(imheater, 0.9)

    def test_demand_hot_water(self):
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.storagetank.demand_hot_water([10.0, 10.0, 15.0, 20.0, 20.0, 20.0, 20.0, 20.0]
                                                  [t_idx])
                #print(self.storagetank._StorageTank__temp_n)
                self.assertListEqual(
                    self.storagetank._StorageTank__temp_n,
                    [[55, 55, 55, 55],
                     [43.538093827160495, 54.595555555555556, 54.595555555555556, 54.595555555555556],
                     [30.827117778420643, 50.07409375884502, 54.19530534979424, 54.19530534979424],
                     [20.483675222718627, 40.07251184772483, 51.73330420939261, 53.79920588690749],
                     [55, 55, 55, 55],
                     [55, 55, 55, 55],
                     [55, 55, 55, 55],
                     [55, 55, 55, 55]][t_idx],
                    "incorrect temperatures returned"
                    )
                #print(self.energysupply.results_by_end_user()["immersion"][t_idx])
                self.assertEqual(
                    self.energysupply.results_by_end_user()["immersion"][t_idx],
                    [0.5586414814814873,
                     0.0,
                     0.0,
                     0.0,
                     3.3824624299642423,
                     1.0235303703703664,
                     1.0119081481481444,
                     0.9979614814814752][t_idx],
                    "incorrect energy supplied returned",
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
