#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains unit tests for the energy_supply module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.energy_supply.energy_supply import EnergySupply, EnergySupplyConnection

class TestEnergySupply(unittest.TestCase):
    """ Unit tests for EnergySupply class """

    def setUp(self):
        """ Create EnergySupply object to be tested """
        self.simtime            = SimulationTime(0, 8, 1)
        self.energysupply       = EnergySupply("gas", self.simtime)
        """ Set up two different energy supply connections """
        self.energysupplyconn_1 = self.energysupply.connection("shower")
        self.energysupplyconn_2 = self.energysupply.connection("bath")

    def test_connection(self):
        """ Test the correct end user name is assigned when creating the
        two different connections.
        """
        self.assertEqual(
            self.energysupplyconn_1._EnergySupplyConnection__end_user_name,
            "shower",
            "end user name for connection 1 not returned"
            )
        self.assertEqual(
            self.energysupplyconn_2._EnergySupplyConnection__end_user_name,
            "bath",
            "end user name for connection 2 not returned"
            )

        """ Test the energy supply is created as expected for the two
        different connections.
        """
        self.assertIs(
            self.energysupply,
            self.energysupplyconn_1._EnergySupplyConnection__energy_supply,
            "energy supply for connection 1 not returned"
            )
        self.assertIs(
            self.energysupply,
            self.energysupplyconn_2._EnergySupplyConnection__energy_supply,
            "energy supply for connection 2 not returned"
            )

    def test_results_total(self):
        """ Check the correct list of the total demand on this energy
        source for each timestep is returned.
        """
        demandtotal = [50.0, 120.0, 190.0, 260.0, 330.0, 400.0, 470.0, 540.0]
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.energysupplyconn_1.demand_energy((t_idx+1.0)*50.0)
                self.energysupplyconn_2.demand_energy((t_idx)*20.0)
                self.assertEqual(
                    self.energysupply.results_total()[t_idx],
                    demandtotal[t_idx],
                    "incorrect total demand energy returned",
                    )

    def test_results_by_end_user(self):
        """ Check the correct list of the total demand on this energy
        source for each timestep is returned for each connection.
        """
        demandtotal_1 = [50.0, 100.0, 150.0, 200.0, 250.0, 300.0, 350.0, 400.0]
        demandtotal_2 = [0.0, 20.0, 40.0, 60.0, 80.0, 100.0, 120.0, 140.0]
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.energysupplyconn_1.demand_energy((t_idx+1.0)*50.0)
                self.energysupplyconn_2.demand_energy((t_idx)*20.0)
                self.assertEqual(
                    self.energysupply.results_by_end_user()["shower"][t_idx],
                    demandtotal_1[t_idx],
                    "incorrect demand by end user returned",
                    )
                self.assertEqual(
                    self.energysupply.results_by_end_user()["bath"][t_idx],
                    demandtotal_2[t_idx],
                    "incorrect demand by end user returned",
                    )
    def test_beta_factor(self):
        """check beta factor and surplus supply/demand are calculated correctly"""
        energysupplyconn_3 = self.energysupply.connection("PV")
    
    
        #demandtotal_1 = [50.0, 100.0, 150.0, 200.0, 250.0, 300.0, 350.0, 400.0]
        #demandtotal_2 = [0.0, 20.0, 40.0, 60.0, 80.0, 100.0, 120.0, 140.0]
        #supplytotal_1 = [0.0, 40.0, 80.0, 120.0, 160.0, 200.0, 240.0, 280.0]
        betafactor = [  1.0,
                        1.0,
                        1.0,
                        0.9933657509923902,
                        0.9595470767450086,
                        0.9390126041156721,
                        0.9252170469746361,
                        0.9153096727481128,
                        1.0]

        surplus = [0.0, 
                   0.0, 
                   0.0,
                  -0.9951373511414674,
                  -8.090584650998277, 
                  -15.246848971081972,
                  -22.434885907609157,
                  -29.641614538160514]

        demandnotmet = [50.0,
                        170.0, 
                        290.0, 
                        409.00486264885853, 
                        521.9094153490017, 
                        634.7531510289181, 
                        747.5651140923908, 
                        860.3583854618395]

        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.energysupplyconn_1.demand_energy((t_idx+1.0)*50.0)
                self.energysupplyconn_2.demand_energy((t_idx)*20.0)
                energysupplyconn_3.supply_energy((t_idx)*50.0)
                
                self.energysupply.calc_beta_factor()
                self.energysupply.calc_demand_after_generation()
    
                self.assertEqual(
                    self.energysupply.get_beta_factor()[t_idx],
                    betafactor[t_idx],
                    "incorrect beta factor returned",
                    )
                self.assertEqual(
                    self.energysupply.get_supply_surplus()[t_idx],
                    surplus[t_idx],
                    "incorrect surplus by end user returned",
                    )
                self.assertEqual(
                    self.energysupply.get_demand_not_met()[t_idx],
                    demandnotmet[t_idx],
                    "incorrect surplus by end user returned",
                    )
    