#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains unit tests for the simulation_time module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime

class TestSimulationTime(unittest.TestCase):
    """ Unit tests for SimulationTime class """

    def setUp(self):
        """ Create SimulationTime object to be tested """
        self.simtime = SimulationTime(2, 10, 1)

    def test_timestep(self):
        """ Test that SimulationTime object returns correct timestep """
        self.assertEqual(self.simtime.timestep(), 1, "incorrect timestep returned")

    def test_total_steps(self):
        """ Test that total steps has been calculated correctly """
        self.assertEqual(self.simtime.total_steps(), 8, "incorrect total steps")

    def test_iteration(self):
        """ Test that SimulationTime object works as an iterator """
        # Call to iter() should return reference to same object
        simtime_iter = iter(self.simtime)
        self.assertIs(simtime_iter, self.simtime)

        # Check figures returned in each iteration
        for i in range(0, 8):
            with self.subTest(i=i):
                # Check that call to next() returns correct index and current time
                self.assertEqual(next(simtime_iter), (i, i + 2, 1), "incorrect loop vars returned")

                # Check that individual functions also return correct index and current time
                self.assertEqual(
                    self.simtime.current(),
                    2 + i * self.simtime.timestep(),
                    "incorrect current time returned"
                    )
                self.assertEqual(self.simtime.index(), i, "incorrect ordinal index returned")

        # Once all timesteps have been iterated over, next increment should raise exception
        with self.assertRaises(StopIteration):
            next(simtime_iter)
