#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains unit tests for the heat network module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.external_conditions import ExternalConditions
from core.heating_systems.heat_network import HeatNetwork, HeatNetworkServiceWaterDirect, \
HeatNetworkServiceWaterStorage, HeatNetworkServiceSpace
from core.water_heat_demand.cold_water_source import ColdWaterSource
from core.energy_supply.energy_supply import EnergySupply
from core.material_properties import WATER, MaterialProperties


class TestHeatNetwork(unittest.TestCase):
    """ Unit tests for HeatNetwork class """

    def setUp(self):
        """ Create HeatNetwork object to be tested """
        heat_network_dict = {"type": "HeatNetwork",
                             "EnergySupply": "custom"
                             }
        self.simtime = SimulationTime(0, 2, 1)
        self.energysupply = EnergySupply("custom", self.simtime)
        energy_supply_conn_name_auxiliary = 'heat_network_auxiliary'

        # Set up ExternalConditions object
        windspeed = [3.7, 3.8, 3.9, 4.0, 4.1, 4.2, 4.3, 4.4]
        airtemp = [0.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 20.0]
        diffuse_horizontal_radiation = [333, 610, 572, 420, 0, 10, 90, 275]
        direct_beam_radiation = [420, 750, 425, 500, 0, 40, 0, 388]
        solar_reflectivity_of_ground = [0.2] * 8760
        latitude = 51.42
        longitude = -0.75
        timezone = 0
        start_day = 0
        end_day = 0
        time_series_step = 1
        january_first = 1
        daylight_savings = "not applicable"
        leap_day_included = False
        direct_beam_conversion_needed = False
        shading_segments = [
            {"number": 1, "start": 180, "end": 135},
            {"number": 2, "start": 135, "end": 90},
            {"number": 3, "start": 90, "end": 45},
            {"number": 4, "start": 45, "end": 0},
            {"number": 5, "start": 0, "end": -45},
            {"number": 6, "start": -45, "end": -90},
            {"number": 7, "start": -90, "end": -135},
            {"number": 8, "start": -135, "end": -180}
        ]
        extcond = ExternalConditions(
            self.simtime,
            airtemp,
            windspeed,
            diffuse_horizontal_radiation,
            direct_beam_radiation,
            solar_reflectivity_of_ground,
            latitude,
            longitude,
            timezone,
            start_day,
            end_day,
            time_series_step,
            january_first,
            daylight_savings,
            leap_day_included,
            direct_beam_conversion_needed,
            shading_segments
            )

        # Set up HeatNetwork object
        self.heat_network = HeatNetwork(
            heat_network_dict,
            self.energysupply,
            energy_supply_conn_name_auxiliary,
            self.simtime,
            extcond
            )

        # Create a service connection
        self.heat_network._HeatNetwork__create_service_connection("heat_network_test")

    def test_energy_output_provided(self):
        """ Test that HeatNetwork object returns correct energy and fuel demand """
        energy_output_required = [2.0, 10.0]
        temp_return = [50.0, 60.0]
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertAlmostEqual(
                    self.heat_network._HeatNetwork__demand_energy(
                                        "heat_network_test",
                                        energy_output_required[t_idx],
                                        temp_return),
                    [2.0, 10.0][t_idx],
                    msg="incorrect energy_output_provided"
                    )
                self.assertAlmostEqual(
                    self.energysupply.results_by_end_user()["heat_network_test"][t_idx],
                    [2.0, 10.0][t_idx],
                    msg="incorrect fuel demand"
                    )

    def test_HIU_loss(self):
        """ Test that HeatNetwork object returns correct HIU loss """
        daily_loss = 0.24
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertAlmostEqual(
                    self.heat_network.HIU_loss(daily_loss),
                    0.01,
                    msg="incorrect HIU loss returned"
                    )


class TestHeatNetworkServiceWaterDirect(unittest.TestCase):
    """ Unit tests for HeatNetworkServiceWaterDirect class """

    def setUp(self):
        """ Create HeatNetworkServiceWaterDirect object to be tested """
        heat_network_dict = {"type": "HeatNetwork",
                             "EnergySupply": "custom"
                             }
        self.simtime = SimulationTime(0, 2, 1)
        self.energysupply = EnergySupply("custom", self.simtime)
        self.energy_output_required = [2.0, 10.0]
        self.temp_return_feed = [51.05, 60.00]
        energy_supply_conn_name_auxiliary = 'heat_network_auxiliary'

        # Set up external conditions
        self.windspeed = [3.7, 3.8, 3.9, 4.0, 4.1, 4.2, 4.3, 4.4]
        self.airtemp = [0.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 20.0]
        self.diffuse_horizontal_radiation = [333, 610, 572, 420, 0, 10, 90, 275]
        self.direct_beam_radiation = [420, 750, 425, 500, 0, 40, 0, 388]
        self.solar_reflectivity_of_ground = [0.2] * 8760
        self.latitude = 51.42
        self.longitude = -0.75
        self.timezone = 0
        self.start_day = 0
        self.end_day = 0
        self.time_series_step = 1
        self.january_first = 1
        self.daylight_savings = "not applicable"
        self.leap_day_included = False
        self.direct_beam_conversion_needed = False
        self.shading_segments = [
            {"number": 1, "start": 180, "end": 135},
            {"number": 2, "start": 135, "end": 90},
            {"number": 3, "start": 90, "end": 45},
            {"number": 4, "start": 45, "end": 0},
            {"number": 5, "start": 0, "end": -45},
            {"number": 6, "start": -45, "end": -90},
            {"number": 7, "start": -90, "end": -135},
            {"number": 8, "start": -135, "end": -180}
        ]
        extcond = ExternalConditions(
            self.simtime,
            self.airtemp,
            self.windspeed,
            self.diffuse_horizontal_radiation,
            self.direct_beam_radiation,
            self.solar_reflectivity_of_ground,
            self.latitude,
            self.longitude,
            self.timezone,
            self.start_day,
            self.end_day,
            self.time_series_step,
            self.january_first,
            self.daylight_savings,
            self.leap_day_included,
            self.direct_beam_conversion_needed,
            self.shading_segments
            )

        # Set up HeatNetwork
        self.heat_network = HeatNetwork(
            heat_network_dict,
            self.energysupply,
            energy_supply_conn_name_auxiliary,
            self.simtime,
            extcond
            )

        self.heat_network._HeatNetwork__create_service_connection("heat_network_test")

        # Set up HeatNetworkServiceWaterDirect
        coldwatertemps = [1.0, 1.2]
        coldfeed = ColdWaterSource(coldwatertemps, self.simtime, 0, 1)
        return_temp = 60
        self.heat_network_service_water_direct = HeatNetworkServiceWaterDirect(
            self.heat_network,
            "heat_network_test", 
            return_temp,
            coldfeed,
            self.simtime
            )

    def test_heat_network_service_water(self):
        """ Test that HeatNetwork object returns correct hot water energy demand """
        volume_demanded = [50.0, 100.0]
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertAlmostEqual(
                    self.heat_network_service_water_direct.demand_hot_water(volume_demanded[t_idx]),
                    [3.429, 6.834][t_idx],
                    3,
                    msg="incorrect energy_output_provided"
                    )


class TestHeatNetworkServiceWaterStorage(unittest.TestCase):
    """ Unit tests for HeatNetworkServiceWaterStorage class """

    def setUp(self):
        """ Create HeatNetworkServiceWaterStorage object to be tested """
        heat_network_dict = {"type": "HeatNetwork",
                             "EnergySupply": "custom"
                             }
        self.simtime = SimulationTime(0, 2, 1)
        self.energysupply = EnergySupply("custom", self.simtime)
        self.energy_output_required = [2.0, 10.0]
        self.temp_return_feed = [51.05, 60.00]
        energy_supply_conn_name_auxiliary = 'heat_network_auxiliary'

        # Set up external conditions
        self.windspeed = [3.7, 3.8, 3.9, 4.0, 4.1, 4.2, 4.3, 4.4]
        self.airtemp = [0.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 20.0]
        self.diffuse_horizontal_radiation = [333, 610, 572, 420, 0, 10, 90, 275]
        self.direct_beam_radiation = [420, 750, 425, 500, 0, 40, 0, 388]
        self.solar_reflectivity_of_ground = [0.2] * 8760
        self.latitude = 51.42
        self.longitude = -0.75
        self.timezone = 0
        self.start_day = 0
        self.end_day = 0
        self.time_series_step = 1
        self.january_first = 1
        self.daylight_savings = "not applicable"
        self.leap_day_included = False
        self.direct_beam_conversion_needed = False
        self.shading_segments = [
            {"number": 1, "start": 180, "end": 135},
            {"number": 2, "start": 135, "end": 90},
            {"number": 3, "start": 90, "end": 45},
            {"number": 4, "start": 45, "end": 0},
            {"number": 5, "start": 0, "end": -45},
            {"number": 6, "start": -45, "end": -90},
            {"number": 7, "start": -90, "end": -135},
            {"number": 8, "start": -135, "end": -180}
        ]
        extcond = ExternalConditions(
            self.simtime,
            self.airtemp,
            self.windspeed,
            self.diffuse_horizontal_radiation,
            self.direct_beam_radiation,
            self.solar_reflectivity_of_ground,
            self.latitude,
            self.longitude,
            self.timezone,
            self.start_day,
            self.end_day,
            self.time_series_step,
            self.january_first,
            self.daylight_savings,
            self.leap_day_included,
            self.direct_beam_conversion_needed,
            self.shading_segments
            )

        # Set up HeatNetwork
        self.heat_network = HeatNetwork(
            heat_network_dict,
            self.energysupply,
            energy_supply_conn_name_auxiliary,
            self.simtime,
            extcond
            )

        self.heat_network._HeatNetwork__create_service_connection("heat_network_test")

        # Set up HeatNetworkServiceWaterStorage
        coldwatertemps = [1.0, 1.2]
        coldfeed = ColdWaterSource(coldwatertemps, self.simtime, 0, 1)
        return_temp = 60
        self.heat_network_service_water_storage= HeatNetworkServiceWaterStorage(
            self.heat_network,
            "heat_network_test"
            )

    def test_heat_network_service_water_storage(self):
        """ Test that HeatNetwork object returns correct energy demand for the storage tank """
        # TODO update results
        energy_demanded = [10.0, 2.0]
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertAlmostEqual(
                    self.heat_network_service_water_storage.demand_energy(energy_demanded[t_idx]),
                    [10.0, 2.0][t_idx],
                    msg="incorrect energy_output_provided"
                    )


class TestHeatNetworkServiceSpace(unittest.TestCase):
    """ Unit tests for HeatNetworkServiceSpace class """

    def setUp(self):
        """ Create HeatNetworkServiceSpace object to be tested """
        heat_network_dict = {"type": "HeatNetwork",
                             "EnergySupply": "custom"
                             }
        self.simtime = SimulationTime(0, 2, 1)
        self.energysupply = EnergySupply("mains_gas", self.simtime)
        energy_supply_conn_name_auxiliary = 'Boiler_auxiliary'

        # Set up ExternalConditions
        self.airtemp = [0.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 20.0]
        self.windspeed = [3.7, 3.8, 3.9, 4.0, 4.1, 4.2, 4.3, 4.4]
        self.airtemp = [0.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 20.0]
        self.diffuse_horizontal_radiation = [333, 610, 572, 420, 0, 10, 90, 275]
        self.direct_beam_radiation = [420, 750, 425, 500, 0, 40, 0, 388]
        self.solar_reflectivity_of_ground = [0.2] * 8760
        self.latitude = 51.42
        self.longitude = -0.75
        self.timezone = 0
        self.start_day = 0
        self.end_day = 0
        self.time_series_step = 1
        self.january_first = 1
        self.daylight_savings = "not applicable"
        self.leap_day_included = False
        self.direct_beam_conversion_needed = False
        self.shading_segments = [
            {"number": 1, "start": 180, "end": 135},
            {"number": 2, "start": 135, "end": 90},
            {"number": 3, "start": 90, "end": 45},
            {"number": 4, "start": 45, "end": 0},
            {"number": 5, "start": 0, "end": -45},
            {"number": 6, "start": -45, "end": -90},
            {"number": 7, "start": -90, "end": -135},
            {"number": 8, "start": -135, "end": -180}
        ]
        extcond = ExternalConditions(
            self.simtime,
            self.airtemp,
            self.windspeed,
            self.diffuse_horizontal_radiation,
            self.direct_beam_radiation,
            self.solar_reflectivity_of_ground,
            self.latitude,
            self.longitude,
            self.timezone,
            self.start_day,
            self.end_day,
            self.time_series_step,
            self.january_first,
            self.daylight_savings,
            self.leap_day_included,
            self.direct_beam_conversion_needed,
            self.shading_segments
            )

        # Set up HeatNetwork
        self.heat_network = HeatNetwork(
            heat_network_dict,
            self.energysupply,
            energy_supply_conn_name_auxiliary,
            self.simtime,
            extcond
            )

        self.heat_network._HeatNetwork__create_service_connection("heat_network_test")

        # Set up HeatNetworkServiceSpace
        self.heat_network_service_space = HeatNetworkServiceSpace(
            self.heat_network,
            "heat_network_test",
            False
            )

    def test_heat_network_service_space(self):
        """ Test that HeatNetworkServiceSpace object returns correct space heating energy demand """
        energy_demanded = [10.0, 2.0]
        temp_flow = [55.0, 65.0]
        temp_return = [50.0, 60.0]
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertAlmostEqual(
                    self.heat_network_service_space.demand_energy(
                        energy_demanded[t_idx],
                        temp_flow[t_idx],
                        temp_return[t_idx]),
                    [10.0, 2.0][t_idx],
                    msg="incorrect energy_output_provided"
                    )