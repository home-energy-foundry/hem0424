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
from core.space_heat_demand.building_element import \
    BuildingElementOpaque, BuildingElementGround, BuildingElementTransparent, \
    BuildingElementAdjacentZTC

class TestBuildingElementOpaque(unittest.TestCase):
    """ Unit tests for BuildingElementOpaque class """

    def setUp(self):
        """ Create BuildingElementOpaque objects to be tested """
        self.simtime = SimulationTime(0, 4, 1)
        ec = ExternalConditions(self.simtime, [0.0, 5.0, 10.0, 15.0], None)

        # Create an object for each mass distribution class
        be_I = BuildingElementOpaque(20.0, 0.30, 0.40, 0.50, 0.20, 0.60, 0.25, 19000.0, "I", 0, ec)
        be_E = BuildingElementOpaque(22.5, 0.31, 0.41, 0.51, 0.21, 0.61, 0.50, 18000.0, "E", 45, ec)
        be_IE = BuildingElementOpaque(25.0, 0.32, 0.42, 0.52, 0.22, 0.62, 0.75, 17000.0, "IE", 90, ec)
        be_D = BuildingElementOpaque(27.5, 0.33, 0.43, 0.53, 0.23, 0.63, 0.80, 16000.0, "D", 135, ec)
        be_M = BuildingElementOpaque(30.0, 0.34, 0.44, 0.54, 0.24, 0.64, 0.40, 15000.0, "M", 180, ec)

        # Put objects in a list that can be iterated over
        self.test_be_objs = [be_I, be_E, be_IE, be_D, be_M]

    def test_no_of_nodes(self):
        """ Test that number of nodes (total and inside) have been calculated correctly """
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertEqual(be.no_of_nodes(), 5, "incorrect number of nodes")
                self.assertEqual(be.no_of_inside_nodes(), 3, "incorrect number of inside nodes")

    def test_area(self):
        """ Test that correct area is returned when queried """
        # Define increment between test cases
        area_inc = 2.5

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.area, 20.0 + i * area_inc, msg="incorrect area returned")

    def test_h_ci(self):
        """ Test that correct h_ci is returned when queried """
        # Define increment between test cases
        h_ci_inc = 0.01

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.h_ci, 0.3 + i * h_ci_inc, msg="incorrect h_ci returned")

    def test_h_ri(self):
        """ Test that correct h_ri is returned when queried """
        # Define increment between test cases
        h_ri_inc = 0.01

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.h_ri, 0.4 + i * h_ri_inc, msg="incorrect h_ri returned")

    def test_h_ce(self):
        """ Test that correct h_ce is returned when queried """
        # Define increment between test cases
        h_ce_inc = 0.01

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.h_ce, 0.5 + i * h_ce_inc, msg="incorrect h_ce returned")

    def test_h_re(self):
        """ Test that correct h_re is returned when queried """
        # Define increment between test cases
        h_re_inc = 0.01

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.h_re, 0.2 + i * h_re_inc, msg="incorrect h_re returned")

    def test_a_sol(self):
        """ Test that correct a_sol is returned when queried """
        # Define increment between test cases
        a_sol_inc = 0.01

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.a_sol, 0.6 + i * a_sol_inc, msg="incorrect a_sol returned")

    def test_therm_rad_to_sky(self):
        """ Test that correct therm_rad_to_sky is returned when queried """
        results = [2.2, 1.971708332, 1.21, 0.370509922, 0.0]

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(
                    be.therm_rad_to_sky,
                    results[i],
                    msg="incorrect therm_rad_to_sky returned",
                    )

    def test_h_pli(self):
        """ Test that correct h_pli list is returned when queried """
        results = [
            [24.0, 12.0, 12.0, 24.0],
            [12.0, 6.0, 6.0, 12.0],
            [8.0, 4.0, 4.0, 8.0],
            [7.5, 3.75, 3.75, 7.5],
            [15.0, 7.5, 7.5, 15.0],
            ]
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertEqual(be.h_pli, results[i], "incorrect h_pli list returned")

    def test_k_pli(self):
        """ Test that correct k_pli list is returned when queried """
        results = [
            [0.0, 0.0, 0.0, 0.0, 19000.0],
            [18000.0, 0.0, 0.0, 0.0, 0.0],
            [8500.0, 0.0, 0.0, 0.0, 8500.0],
            [2000.0, 4000.0, 4000.0, 4000.0, 2000.0],
            [0.0, 0.0, 15000.0, 0.0, 0.0],
            ]
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertEqual(be.k_pli, results[i], "incorrect k_pli list returned")

    def test_temp_ext(self):
        """ Test that the correct external temperature is returned when queried """
        for i, be in enumerate(self.test_be_objs):
            for t_idx, _, _ in self.simtime:
                with self.subTest(i = i * t_idx):
                    self.assertEqual(be.temp_ext(), t_idx * 5.0, "incorrect ext temp returned")

class TestBuildingElementAdjacentZTC(unittest.TestCase):
    """ Unit tests for BuildingElementAdjacentZTC class """

    def setUp(self):
        """ Create BuildingElementAdjacentZTC objects to be tested """
        self.simtime = SimulationTime(0, 4, 1)
        ec = ExternalConditions(self.simtime, [0.0, 5.0, 10.0, 15.0], None)

        # Create an object for each mass distribution class
        be_I = BuildingElementAdjacentZTC(20.0, 0.30, 0.40, 0.25, 19000.0, "I", ec)
        be_E = BuildingElementAdjacentZTC(22.5, 0.31, 0.41, 0.50, 18000.0, "E", ec)
        be_IE = BuildingElementAdjacentZTC(25.0, 0.32, 0.42, 0.75, 17000.0, "IE", ec)
        be_D = BuildingElementAdjacentZTC(27.5, 0.33, 0.43, 0.80, 16000.0, "D", ec)
        be_M = BuildingElementAdjacentZTC(30.0, 0.34, 0.44, 0.40, 15000.0, "M", ec)

        # Put objects in a list that can be iterated over
        self.test_be_objs = [be_I, be_E, be_IE, be_D, be_M]

    def test_no_of_nodes(self):
        """ Test that number of nodes (total and inside) have been calculated correctly """
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertEqual(be.no_of_nodes(), 5, "incorrect number of nodes")
                self.assertEqual(be.no_of_inside_nodes(), 3, "incorrect number of inside nodes")

    def test_area(self):
        """ Test that correct area is returned when queried """
        # Define increment between test cases
        area_inc = 2.5

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.area, 20.0 + i * area_inc, msg="incorrect area returned")

    def test_h_ci(self):
        """ Test that correct h_ci is returned when queried """
        # Define increment between test cases
        h_ci_inc = 0.01

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.h_ci, 0.3 + i * h_ci_inc, msg="incorrect h_ci returned")

    def test_h_ri(self):
        """ Test that correct h_ri is returned when queried """
        # Define increment between test cases
        h_ri_inc = 0.01

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.h_ri, 0.4 + i * h_ri_inc, msg="incorrect h_ri returned")

    def test_h_ce(self):
        """ Test that correct h_ce is returned when queried """
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.h_ce, 0.0, msg="incorrect h_ce returned")

    def test_h_re(self):
        """ Test that correct h_re is returned when queried """
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.h_re, 0.0, msg="incorrect h_re returned")

    def test_a_sol(self):
        """ Test that correct a_sol is returned when queried """
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.a_sol, 0.0, msg="incorrect a_sol returned")

    def test_therm_rad_to_sky(self):
        """ Test that correct therm_rad_to_sky is returned when queried """
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(
                    be.therm_rad_to_sky,
                    0.0,
                    msg="incorrect therm_rad_to_sky returned",
                    )

    def test_h_pli(self):
        """ Test that correct h_pli list is returned when queried """
        results = [
            [24.0, 12.0, 12.0, 24.0],
            [12.0, 6.0, 6.0, 12.0],
            [8.0, 4.0, 4.0, 8.0],
            [7.5, 3.75, 3.75, 7.5],
            [15.0, 7.5, 7.5, 15.0],
            ]
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertEqual(be.h_pli, results[i], "incorrect h_pli list returned")

    def test_k_pli(self):
        """ Test that correct k_pli list is returned when queried """
        results = [
            [0.0, 0.0, 0.0, 0.0, 19000.0],
            [18000.0, 0.0, 0.0, 0.0, 0.0],
            [8500.0, 0.0, 0.0, 0.0, 8500.0],
            [2000.0, 4000.0, 4000.0, 4000.0, 2000.0],
            [0.0, 0.0, 15000.0, 0.0, 0.0],
            ]
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertEqual(be.k_pli, results[i], "incorrect k_pli list returned")

    # No test for temp_ext - not relevant as the external wall bounds ZTC not the external environment

class TestBuildingElementGround(unittest.TestCase):
    """ Unit tests for BuildingElementGround class """

    def setUp(self):
        """ Create BuildingElementGround objects to be tested """
        self.simtime = SimulationTime(0, 4, 1)
        ec = ExternalConditions(self.simtime, None, [8.0, 9.0, 10.0, 11.0])

        # Create an object for each mass distribution class
        be_I = BuildingElementGround(20.0, 0.30, 0.40, 0.50, 0.20, 0.25, 0.5, 19000.0, 24000.0, "I", ec)
        be_E = BuildingElementGround(22.5, 0.31, 0.41, 0.51, 0.21, 0.50, 0.5, 18000.0, 24000.0, "E", ec)
        be_IE = BuildingElementGround(25.0, 0.32, 0.42, 0.52, 0.22, 0.75, 0.5, 17000.0, 24000.0, "IE", ec)
        be_D = BuildingElementGround(27.5, 0.33, 0.43, 0.53, 0.23, 0.80, 0.5, 16000.0, 24000.0, "D", ec)
        be_M = BuildingElementGround(30.0, 0.34, 0.44, 0.54, 0.24, 0.40, 0.5, 15000.0, 24000.0, "M", ec)

        # Put objects in a list that can be iterated over
        self.test_be_objs = [be_I, be_E, be_IE, be_D, be_M]

    def test_no_of_nodes(self):
        """ Test that number of nodes (total and inside) have been calculated correctly """
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertEqual(be.no_of_nodes(), 5, "incorrect number of nodes")
                self.assertEqual(be.no_of_inside_nodes(), 3, "incorrect number of inside nodes")

    def test_area(self):
        """ Test that correct area is returned when queried """
        # Define increment between test cases
        area_inc = 2.5

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.area, 20.0 + i * area_inc, msg="incorrect area returned")

    def test_h_ci(self):
        """ Test that correct h_ci is returned when queried """
        # Define increment between test cases
        h_ci_inc = 0.01

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.h_ci, 0.3 + i * h_ci_inc, msg="incorrect h_ci returned")

    def test_h_ri(self):
        """ Test that correct h_ri is returned when queried """
        # Define increment between test cases
        h_ri_inc = 0.01

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.h_ri, 0.4 + i * h_ri_inc, msg="incorrect h_ri returned")

    def test_h_ce(self):
        """ Test that correct h_ce is returned when queried """
        # Define increment between test cases
        h_ce_inc = 0.01

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.h_ce, 0.5 + i * h_ce_inc, msg="incorrect h_ce returned")

    def test_h_re(self):
        """ Test that correct h_re is returned when queried """
        # Define increment between test cases
        h_re_inc = 0.01

        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.h_re, 0.2 + i * h_re_inc, msg="incorrect h_re returned")

    def test_a_sol(self):
        """ Test that correct a_sol is returned when queried """
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(be.a_sol, 0.0, msg="incorrect a_sol returned")

    def test_therm_rad_to_sky(self):
        """ Test that correct therm_rad_to_sky is returned when queried """
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertAlmostEqual(
                    be.therm_rad_to_sky,
                    0.0,
                    msg="incorrect therm_rad_to_sky returned",
                    )

    def test_h_pli(self):
        """ Test that correct h_pli list is returned when queried """
        results = [
            [4.0, 3.2, 8.0, 16.0],
            [4.0, 2.6666666666666665, 4.0, 8.0],
            [4.0, 2.2857142857142856, 2.6666666666666665, 5.333333333333333],
            [4.0, 2.2222222222222223, 2.5, 5.0],
            [4.0, 2.857142857142857, 5.0, 10.0],
            ]
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertEqual(be.h_pli, results[i], "incorrect h_pli list returned")

    def test_k_pli(self):
        """ Test that correct k_pli list is returned when queried """
        results = [
            [0.0, 24000.0, 0.0, 0.0, 19000.0],
            [0.0, 24000.0, 18000.0, 0.0, 0.0],
            [0.0, 24000.0, 8500.0, 0.0, 8500.0],
            [0.0, 24000.0, 4000.0, 8000.0, 4000.0],
            [0.0, 24000.0, 0.0, 15000.0, 0.0],
            ]
        for i, be in enumerate(self.test_be_objs):
            with self.subTest(i=i):
                self.assertEqual(be.k_pli, results[i], "incorrect k_pli list returned")

    def test_temp_ext(self):
        """ Test that the correct external temperature is returned when queried """
        for i, be in enumerate(self.test_be_objs):
            for t_idx, _, _ in self.simtime:
                with self.subTest(i = i * t_idx):
                    self.assertEqual(be.temp_ext(), t_idx + 8.0, "incorrect ext temp returned")

class TestBuildingElementTransparent(unittest.TestCase):
    """ Unit tests for BuildingElementTransparent class """

    def setUp(self):
        """ Create BuildingElementTransparent object to be tested """
        self.simtime = SimulationTime(0, 4, 1)
        ec = ExternalConditions(self.simtime, [0.0, 5.0, 10.0, 15.0], None)

        self.be = BuildingElementTransparent(5.0, 0.35, 0.45, 0.30, 0.25, 0.4, 90, ec)

    def test_no_of_nodes(self):
        """ Test that number of nodes (total and inside) have been calculated correctly """
        self.assertEqual(self.be.no_of_nodes(), 2, "incorrect number of nodes")
        self.assertEqual(self.be.no_of_inside_nodes(), 0, "incorrect number of inside nodes")

    def test_area(self):
        """ Test that correct area is returned when queried """
        self.assertEqual(self.be.area, 5.0, "incorrect area returned")

    def test_h_ci(self):
        """ Test that correct h_ci is returned when queried """
        self.assertEqual(self.be.h_ci, 0.35, "incorrect h_ci returned")

    def test_h_ri(self):
        """ Test that correct h_ri is returned when queried """
        self.assertEqual(self.be.h_ri, 0.45, "incorrect h_ri returned")

    def test_h_ce(self):
        """ Test that correct h_ce is returned when queried """
        self.assertEqual(self.be.h_ce, 0.30, "incorrect h_ce returned")

    def test_h_re(self):
        """ Test that correct h_re is returned when queried """
        self.assertEqual(self.be.h_re, 0.25, "incorrect h_re returned")

    def test_a_sol(self):
        """ Test that correct a_sol is returned when queried """
        self.assertEqual(self.be.a_sol, 0.0, "non-zero a_sol returned")

    def test_therm_rad_to_sky(self):
        """ Test that correct therm_rad_to_sky is returned when queried """
        self.assertEqual(self.be.therm_rad_to_sky, 1.375, "incorrect therm_rad_to_sky returned")

    def test_h_pli(self):
        """ Test that correct h_pli list is returned when queried """
        self.assertEqual(self.be.h_pli, [2.5], "incorrect h_pli list returned")

    def test_k_pli(self):
        """ Test that correct k_pli list is returned when queried """
        self.assertEqual(self.be.k_pli, [0.0, 0.0], "non-zero k_pli list returned")

    def test_temp_ext(self):
        """ Test that the correct external temperature is returned when queried """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i = t_idx):
                self.assertEqual(
                    self.be.temp_ext(),
                    t_idx * 5.0,
                    "incorrect ext temp returned",
                    )

