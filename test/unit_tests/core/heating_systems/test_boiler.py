#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains unit tests for the boiler module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.external_conditions import ExternalConditions
from core.heating_systems.boiler import Boiler, BoilerServiceWaterCombi
from core.water_heat_demand.cold_water_source import ColdWaterSource
from core.energy_supply.energy_supply import EnergySupply
from core.material_properties import WATER, MaterialProperties


class TestBoiler(unittest.TestCase):
    """ Unit tests for Boiler class """

    def setUp(self):
        """ Create Boiler object to be tested """
        boiler_dict = {"type": "Boiler",
                       "rated_power": 16.85,
                       "EnergySupply": "mains_gas",
                       "efficiency_full_load": 0.868,
                       "efficiency_part_load": 0.952,
                       "boiler_location": "internal",
                       "modulation_load" : 1
                      }
        self.simtime                = SimulationTime(0, 2, 1)
        self.energysupply           = EnergySupply("mains_gas", self.simtime)
        self.energy_output_required = [2, 10]
        self.temp_return_feed       = [51.05, 60.00]
        airtemp                     = [0.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 20.0]
        extcond                     = ExternalConditions(self.simtime, airtemp)
        self.boiler                 = Boiler(boiler_dict, self.energysupply, extcond, self.simtime)
        self.boiler._Boiler__create_service_connection("boiler test")

    def test_energy_output_provided(self):
        """ Test that Boiler object returns correct energy and fuel demand """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertAlmostEqual(
                    self.boiler._Boiler__demand_energy("boiler test", 
                                                       self.energy_output_required[t_idx],
                                                       self.temp_return_feed[t_idx]),
                    [0.1186944, 0.5934718][t_idx],
                    msg="incorrect energy_output_provided"
                    )
                self.assertAlmostEqual(
                    self.energysupply.results_by_end_user()["boiler test"][t_idx],
                    [0.1474993, 0.6984658][t_idx],
                    msg="incorrect fuel demand"
                    )

    def test_effvsreturntemp(self):
        """ Test that Boiler object returns correct theoretical efficiencies """
        self.return_temp = [30, 60]
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.boiler.effvsreturntemp(self.return_temp[t_idx], 0),
                    [0.967, 0.8769][t_idx],
                    "incorrect theoretical boiler efficiency returned",
                    )

    def test_high_value_correction(self):
        """ Test that Boiler object corrects for high boiler efficiencies """
        self.assertEqual(
            self.boiler.high_value_correction_full_load(0.980),
            0.963175,
            "incorrect high_value_correction",
            )
        self.assertEqual(
            self.boiler.high_value_correction_part_load(1.081),
            1.056505,
            "incorrect high_value_correction",
            )

    def test_net2gross(self):
        """ Test that Boiler object selects correct net2gross conversion factor """
        self.__fuel_code = "mains_gas"
        self.assertEqual(
            self.boiler.net_to_gross(),
            0.901,
            "incorrect net_to_gross",
            )

class TestBoilerServiceWaterCombi(unittest.TestCase):
    """ Unit tests for Boiler class """

    def setUp(self):
        """ Create Boiler object to be tested """
        boiler_dict = {"type": "Boiler",
                       "rated_power": 16.85,
                       "EnergySupply": "mains_gas",
                       "efficiency_full_load": 0.868,
                       "efficiency_part_load": 0.952,
                       "boiler_location": "internal",
                       "modulation_load" : 1
                      }
        boilerservicewatercombi_dict = {
                        "separate_DHW_tests": "M&L",
                        "fuel_energy_1": 7.099,
                        "rejected_energy_1": 0.0004,
                        "storage_loss_factor_1": 0.98328,
                        "fuel_energy_2": 13.078,
                        "rejected_energy_2": 0.0004,
                        "storage_loss_factor_2": 0.91574,
                        "rejected_factor_3": 0,
                        "daily_HW_usage" : 132.5802
                      }
        self.simtime                = SimulationTime(0, 2, 1)
        self.energysupply           = EnergySupply("mains_gas", self.simtime)
        self.energy_output_required = [10, 2]
        self.temp_return_feed       = [51.05, 60.00]
        airtemp                     = [0.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 20.0]
        extcond                     = ExternalConditions(self.simtime, airtemp)
        self.boiler                 = Boiler(boiler_dict, self.energysupply, extcond, self.simtime)
        self.boiler._Boiler__create_service_connection("boiler test")

        coldwatertemps   = [1.0, 1.2]
        coldfeed         = ColdWaterSource(coldwatertemps, self.simtime)
        return_temp      = 60
        self.boiler_service_water     = BoilerServiceWaterCombi(
            boilerservicewatercombi_dict, \
            self.boiler, \
            "boiler test", \
            return_temp, \
            coldfeed, \
            self.simtime)
        
    def test_boiler_service_water(self):
        """ Test that Boiler object returns correct hot water energy demand """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertAlmostEqual(
                    self.boiler_service_water.demand_hot_water(self.energy_output_required[t_idx]),
                    [0.0429757, 0.0103791][t_idx],
                    msg="incorrect energy_output_provided"
                    )
