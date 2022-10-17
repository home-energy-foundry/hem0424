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

class TestEmitters(unittest.TestCase):
    """ Unit tests for InstantElecHeater class """

    def setUp(self):
        """ Create InstantElecHeater object to be tested """
        self.simtime = SimulationTime(0, 2, 0.25)

        # Create simple HeatSource object implementing required interface to run tests
        class HeatSource:
            def thermal_capacity_max(self, temp_flow):
                return 10.0
            def demand_energy(self, energy_req_from_heating_system, temp_flow_achievable):
                return max(0, min(2.5, energy_req_from_heating_system))
        heat_source = HeatSource()

        # Create simple Zone object implementing required interface to run tests
        class Zone:
            def temp_internal_air(self):
                return 20.0
        zone = Zone()

        self.emitters = Emitters(0.14, 0.08, 1.2, 10.0, heat_source, zone, self.simtime)

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

