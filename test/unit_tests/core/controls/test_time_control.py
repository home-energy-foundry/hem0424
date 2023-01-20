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
from core.controls.time_control import OnOffTimeControl, SetpointTimeControl

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


class Test_SetpointTimeControl(unittest.TestCase):
    """ Unit tests for SetpointTimeControl class """

    def setUp(self):
        """ Create TimeControl object to be tested """
        self.simtime     = SimulationTime(0, 8, 1)
        self.schedule    = [21.0, None, 21.0, 21.0, None, 21.0, 25.0, 15.0]
        self.timecontrol = SetpointTimeControl(self.schedule, self.simtime, 0, 1)
        self.timecontrol_min \
            = SetpointTimeControl(self.schedule, self.simtime, 0, 1, 16.0, None)
        self.timecontrol_max \
            = SetpointTimeControl(self.schedule, self.simtime, 0, 1, None, 24.0)
        self.timecontrol_minmax \
            = SetpointTimeControl(self.schedule, self.simtime, 0, 1, 16.0, 24.0, False)

    def test_is_on(self):
        """ Test that SetpointTimeControl object is always on """
        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.timecontrol.is_on(),
                    [True, False, True, True, False, True, True, True][t_idx],
                    "incorrect is_on value returned for control with no min or max set",
                    )
                self.assertEqual(
                    self.timecontrol_min.is_on(),
                    True, # Should always be True for this type of control
                    "incorrect is_on value returned for control with min set",
                    )
                self.assertEqual(
                    self.timecontrol_max.is_on(),
                    True, # Should always be True for this type of control
                    "incorrect is_on value returned for control with max set",
                    )
                self.assertEqual(
                    self.timecontrol_minmax.is_on(),
                    True, # Should always be True for this type of control
                    "incorrect is_on value returned for control with min and max set",
                    )

    def test_setpnt(self):
        """ Test that SetpointTimeControl object returns correct schedule"""
        results_min    = [21.0, 16.0, 21.0, 21.0, 16.0, 21.0, 25.0, 16.0]
        results_max    = [21.0, 24.0, 21.0, 21.0, 24.0, 21.0, 24.0, 15.0]
        results_minmax = [21.0, 16.0, 21.0, 21.0, 16.0, 21.0, 24.0, 16.0]

        for t_idx, _, _ in self.simtime:
            with self.subTest(i=t_idx):
                self.assertEqual(
                    self.timecontrol.setpnt(),
                    self.schedule[t_idx],
                    "incorrect schedule returned for control with no min or max set",
                    )
                self.assertEqual(
                    self.timecontrol_min.setpnt(),
                    results_min[t_idx],
                    "incorrect schedule returned for control with min set",
                    )
                self.assertEqual(
                    self.timecontrol_max.setpnt(),
                    results_max[t_idx],
                    "incorrect schedule returned for control with max set",
                    )
                self.assertEqual(
                    self.timecontrol_minmax.setpnt(),
                    results_minmax[t_idx],
                    "incorrect schedule returned for control with min and max set",
                    )
