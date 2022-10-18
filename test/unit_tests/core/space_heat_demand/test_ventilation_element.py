#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains unit tests for the building_element module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.external_conditions import ExternalConditions
from core.simulation_time import SimulationTime
from core.energy_supply.energy_supply import EnergySupply
from core.space_heat_demand.ventilation_element import \
    VentilationElementInfiltration, WholeHouseExtractVentilation, \
    MechnicalVentilationHeatRecovery

class TestVentilationElementInfiltration(unittest.TestCase):
    """ Unit tests for VentilationElementInfiltration class """

    def setUp(self):
        """ Create VentilationElementInfiltration objects to be tested """
        self.simtime = SimulationTime(0, 8, 1)
        air_temps = [0.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 17.5]
        wind_speeds = [3.7, 3.8, 3.9, 4.0, 4.1, 4.2, 4.3, 4.4]
        ec = ExternalConditions(self.simtime,
                                air_temps,
                                wind_speeds,
                                None,
                                None,
                                None,
                                None,
                                None,
                                None,
                                0, # Start day
                                None,
                                None,
                                None,
                                None,
                                None,
                                None
                                )
        self.ve_inf = VentilationElementInfiltration(1.0, 
                                                    "sheltered",
                                                    "house",
                                                    4.5,
                                                    "50Pa",
                                                    40.0,
                                                    75.0,
                                                    2.0,
                                                    2.0,
                                                    2.0,
                                                    1.0,
                                                    0.0,
                                                    0.0,
                                                    0.0,
                                                    3.0,
                                                    6.0,
                                                    0.0,
                                                    ec,)

    def test_inf_openings(self):
        """ Test that correct infiltration rate for openings
         is returned when queried """
        self.assertEqual(
            self.ve_inf._VentilationElementInfiltration__inf_openings,
            4.0,
            "incorrect infiltration rate for openings returned"
            )

    def test_divisor(self):
        """ Test that correct Q50 divisor is returned when queried """
        self.assertEqual(
            self.ve_inf._VentilationElementInfiltration__divisor,
            29.4,
            "incorrect Q50 divisor returned"
            )

    def test_shelter_factor(self):
        """ Test that correct shelter factor is returned when queried """
        self.assertEqual(
            self.ve_inf._VentilationElementInfiltration__shelter_factor,
            0.85,
            "incorrect shelter factor returned"
            )

    def test_infiltration(self):
        """ Test that correct infiltration rate is returned when queried """
        self.assertAlmostEqual(
            self.ve_inf._VentilationElementInfiltration__infiltration,
            3.553061,
            6,
            "incorrect infiltration rate returned"
            )

    def test_h_ve(self):
        """ Test that correct heat transfer coeffient (h_ve) is returned when queried """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertAlmostEqual(
                    self.ve_inf.h_ve(75.0),
                    [82.9330531547619, 85.17448702380952, 87.41592089285714, 89.65735476190476,
                     91.89878863095237, 94.14022249999998, 96.3816563690476, 98.62309023809523][t_idx],
                    7,
                    "incorrect heat transfer coeffient (h_ve) returned"
                    )

    def test_temp_supply(self):
        """ Test that the correct external temperature is returned when queried """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i = t_idx):
                self.assertEqual(
                    self.ve_inf.temp_supply(),
                    t_idx * 2.5,
                    "incorrect ext temp returned",
                    )


class TestMechnicalVentilationHeatRecovery(unittest.TestCase):
    """ Unit tests for MechnicalVentilationHeatRecovery class """

    def setUp(self):
        """ Create MechnicalVentilationHeatRecovery object to be tested """
        self.simtime = SimulationTime(0, 8, 1)
        air_temps = [0.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 17.5]
        wind_speeds = [3.7, 3.8, 3.9, 4.0, 4.1, 4.2, 4.3, 4.4]
        ec = ExternalConditions(self.simtime,
                                air_temps,
                                wind_speeds,
                                None,
                                None,
                                None,
                                None,
                                None,
                                None,
                                0, # Start day
                                None,
                                None,
                                None,
                                None,
                                None,
                                None
                                )
        self.energysupply = EnergySupply("electricity", self.simtime)
        energysupplyconn = self.energysupply.connection("MVHR")
        self.mvhr \
            = MechnicalVentilationHeatRecovery(0.5, 2.0, 0.66, energysupplyconn, ec, self.simtime)

    def test_h_ve(self):
        """ Test that correct heat transfer coeffient (h_ve) is returned when queried """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertAlmostEqual(
                    self.mvhr.h_ve(75.0),
                    4.28975166666666,
                    msg="incorrect heat transfer coeffient (h_ve) returned"
                    )

    def test_fans(self):
        """ Test that correct fan gains and energy use are calculated """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertAlmostEqual(
                    self.mvhr.fans(75.0),
                    0.010416666666666666,
                    msg="incorrect fan gains for MVHR",
                    )
                self.assertAlmostEqual(
                    self.energysupply.results_by_end_user()['MVHR'][t_idx],
                    0.020833333333333333,
                    msg="incorrect fan energy use for MVHR",
                    )

    def test_temp_supply(self):
        """ Test that the correct external temperature is returned when queried """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i = t_idx):
                self.assertEqual(
                    self.mvhr.temp_supply(),
                    t_idx * 2.5,
                    "incorrect supply temp returned",
                    )


class TestWholeHouseExtractVentilation(unittest.TestCase):
    """ Unit tests for WholeHouseExtractVentilation class """

    def setUp(self):
        """ Create WholeHouseExtractVentilation object to be tested """
        self.simtime = SimulationTime(0, 8, 1)
        air_temps = [0.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 17.5]
        wind_speeds = [3.7, 3.8, 3.9, 4.0, 4.1, 4.2, 4.3, 4.4]
        ec = ExternalConditions(self.simtime,
                                air_temps,
                                wind_speeds,
                                None,
                                None,
                                None,
                                None,
                                None,
                                None,
                                0, # Start day
                                None,
                                None,
                                None,
                                None,
                                None,
                                None
                                )
        self.energysupply = EnergySupply("electricity", self.simtime)
        energysupplyconn = self.energysupply.connection("WHEV")
        self.whev = WholeHouseExtractVentilation(0.5, 2.0, energysupplyconn, ec, self.simtime)

    def test_h_ve(self):
        """ Test that correct heat transfer coeffient (h_ve) is returned when queried """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertAlmostEqual(
                    self.whev.h_ve(75.0),
                    12.616916666666667,
                    msg="incorrect heat transfer coeffient (h_ve) returned"
                    )

    def test_fans(self):
        """ Test that correct fan gains and energy use are calculated """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertAlmostEqual(
                    self.whev.fans(75.0),
                    0.0,
                    msg="incorrect fan gains for WHEV",
                    )
                self.assertAlmostEqual(
                    self.energysupply.results_by_end_user()['WHEV'][t_idx],
                    0.020833333333333333,
                    msg="incorrect fan energy use for WHEV",
                    )

    def test_temp_supply(self):
        """ Test that the correct external temperature is returned when queried """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i = t_idx):
                self.assertEqual(
                    self.whev.temp_supply(),
                    t_idx * 2.5,
                    "incorrect supply temp returned",
                    )
