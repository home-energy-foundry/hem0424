#!/usr/bin/env python3

"""
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
        control          = OnOffTimeControl(
                               [True, False, False, False, True, True, True, True],
                               self.simtime,
                               0,
                               1
                               )
        self.energysupply = EnergySupply("electricity", self.simtime)
        energysupplyconn = self.energysupply.connection("immersion")
        imheater         = ImmersionHeater(50.0, energysupplyconn, self.simtime, control)
        heat_source_dict = {imheater: (0.1, 0.33)}
        self.storagetank = StorageTank(150.0, 1.68, 52.0, 55.0, coldfeed, self.simtime, heat_source_dict)

    def test_demand_hot_water(self):
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.storagetank.demand_hot_water([10.0, 10.0, 15.0, 20.0, 20.0, 20.0, 20.0, 20.0]
                                                  [t_idx])
                #print(self.storagetank._StorageTank__temp_n)
                self.assertListEqual(
                    self.storagetank._StorageTank__temp_n,
                    [[43.5117037037037, 54.595555555555556, 54.595555555555556, 54.595555555555556],
                     [34.923351362284535, 51.44088940589104, 54.19530534979424, 54.19530534979424],
                     [25.428671888696492, 44.86111831060492, 52.763271736704276, 53.79920588690749],
                     [17.778914378539547, 34.731511258769736, 48.38455458241966, 52.883165319588585],
                     [55, 55, 55, 55],
                     [32.955654320987655, 54.595555555555556, 54.595555555555556, 54.595555555555556],
                     [55, 55, 55, 55],
                     [33.53623703703703, 54.595555555555556, 54.595555555555556, 54.595555555555556]][t_idx],
                    "incorrect temperatures returned"
                    )
                #print(self.energysupply.results_by_end_user()["immersion"][t_idx])
                self.assertEqual(
                    self.energysupply.results_by_end_user()["immersion"][t_idx],
                    [0.0,
                     0.0,
                     0.0,
                     0.0,
                     3.9189973050595626,
                     0.0,
                     2.0255553251028573,
                     0.0][t_idx],
                    "incorrect energy supplied returned",
                    )

class Test_ImmersionHeater(unittest.TestCase):
    """ Unit tests for ImmersionHeater class """

    def setUp(self):
        """ Create ImmersionHeater object to be tested """
        self.simtime          = SimulationTime(0, 4, 1)
        energysupply          = EnergySupply("mains_gas", self.simtime)
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
