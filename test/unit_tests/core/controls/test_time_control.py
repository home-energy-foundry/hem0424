#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains unit tests for the Time Control module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.controls.time_control import OnOffTimeControl

class Test_OnOffTimeControl(unittest.TestCase):
    """ Unit tests for OnOffTimeControl class """

    def setUp(self):
        """ Create TimeControl object to be tested """
        self.simtime     = SimulationTime(0, 8, 1)
        self.schedule    = [True, False, True, True, False, True, False, False]
        self.timecontrol = OnOffTimeControl(self.schedule, self.simtime, 0, 1)

    def test_is_on(self):
        """ Test that OnOffTimeControl object returns correct schedule"""
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.timecontrol.is_on(),
                    self.schedule[t_idx],
                    "incorrect schedule returned",
                    )
