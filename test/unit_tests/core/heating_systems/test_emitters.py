#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains unit tests for the Instant Electric Heater module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.heating_systems.emitters import Emitters
from core.external_conditions import ExternalConditions

class TestEmitters(unittest.TestCase):
    """ Unit tests for InstantElecHeater class """

    def setUp(self):
        """ Create InstantElecHeater object to be tested """
        self.simtime = SimulationTime(0, 2, 0.25)

        # Create simple HeatSource object implementing required interface to run tests
        class HeatSource:
            def energy_output_max(self, temp_flow):
                return 10.0
            def demand_energy(self, energy_req_from_heating_system, temp_flow, temp_return):
                return max(0, min(2.5, energy_req_from_heating_system))
        heat_source = HeatSource()

        # Create simple Zone object implementing required interface to run tests
        class Zone:
            def temp_internal_air(self):
                return 20.0

        zone = Zone()
        self.airtemp = [0.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 20.0]
        self.windspeed = [3.7, 3.8, 3.9, 4.0, 4.1, 4.2, 4.3, 4.4]
        energy_supply_conn_name_auxiliary = 'Boiler_auxiliary'
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
        ext_cond = ExternalConditions(
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
        
        self.emitters = Emitters(0.14, 0.08, 1.2, 10.0, 0.4, heat_source, zone, ext_cond, 2, 55.0, self.simtime)

    def test_demand_energy(self):
        """ Test that Emitter object returns correct energy supplied """
        energy_demand_list = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0]
        energy_demand = 0.0
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                energy_demand += energy_demand_list[t_idx]
                energy_provided = self.emitters.demand_energy(energy_demand)
                energy_demand -= energy_provided
                self.assertEqual(
                    energy_provided,
                    [0.26481930394248643, 0.8298460545452833, 1.301166517644123, 1.561584597997277,
                     1.3663790053799807, 0.9752088626903335, 0.7086536127948441, 0.5233452308830262]
                    [t_idx],
                    'incorrect energy provided by emitters',
                    )
                self.assertEqual(
                    self.emitters._Emitters__temp_emitter_prev,
                    [35.96557640041081, 47.89524743937307, 56.45834374191505, 58.92751500769138,
                     49.16766496926295, 42.20188737861771, 37.14007585865454, 33.4018956380615]
                    [t_idx],
                    'incorrect emitter temperature calculated'
                    )

