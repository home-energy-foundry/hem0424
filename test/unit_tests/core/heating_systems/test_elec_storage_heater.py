#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains unit tests for the Electric Storage Heater module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.energy_supply.energy_supply import EnergySupplyConnection, EnergySupply
from core.heating_systems.elec_storage_heater import ElecStorageHeater
from core.controls.time_control import OnOffTimeControl

class TestElecStorageHeater(unittest.TestCase):
    """ Unit tests for ElecStorageHeater class """

    def setUp(self):
        """ Create ElecStorageHeater object to be tested """

        class Zone:
            def temp_internal_air(self):
                return 20.0

        zone = Zone()

        self.simtime     = SimulationTime(0, 4, 1)
        energysupply     = EnergySupply("electricity", self.simtime)
        energysupplyconn = energysupply.connection("main")
        control          = OnOffTimeControl([True, True, False, True], self.simtime, 0, 1)

        data = {"rated_power": 4.0,
                "rated_power_instant": 0.75,
                "flue_type": "fan-assisted",
                "temp_dis_safe": 60.0,
                "thermal_mass": 0.01278,
                "frac_convective": 0.7,
                "U_ins": 0.3,
                "mass_core": 130.0,
                "c_pcore": 920.0,
                "temp_core_target": 450.0,
                "A_core": 4.0,
                "c_wall": 8.0,
                "n_wall": 0.9,
                "thermal_mass_wall": 23.0,
                "fan_pwr": 11.0,
                "n_units": 2}

        self.inselecheater = ElecStorageHeater(data['rated_power'],
                                               data['rated_power_instant'],
                                               data['flue_type'],
                                               data['temp_dis_safe'],
                                               data['thermal_mass'],
                                               data['frac_convective'],
                                               data['U_ins'],
                                               data['mass_core'],
                                               data['c_pcore'],
                                               data['temp_core_target'],
                                               data['A_core'],
                                               data['c_wall'],
                                               data['n_wall'],
                                               data['thermal_mass_wall'],
                                               data['fan_pwr'],
                                               data['n_units'],
                                               zone,
                                               energysupplyconn,
                                               self.simtime,
                                               control)

    def test_demand_energy(self):
        """ Test that ElecStorageHeater object returns correct energy supplied """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    round(self.inselecheater.demand_energy([40.0, 100.0, 30.0, 20.0][t_idx]), 2),
                    [2.82, 3.92, 4.84, 5.61][t_idx],
                    "incorrect energy supplied returned",
                    )
