#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains unit tests for the schedule module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.schedule import expand_schedule

class TestSchedule(unittest.TestCase):
    """ Unit tests for schedule module """

    def setUp(self):
        """ Define schedules to be used in tests """

        # Concise boolean schedule input (e.g. for heating time control) to be
        # expanded into full schedule
        self.schedule = {
            "main": [
                {"value": "weekday", "repeat": 5},
                "weekend",
                "weekend",
                ],
            "weekday": [
                {"value": False, "repeat": 7},
                {"value": True, "repeat": 2},
                {"value": False, "repeat": 7},
                {"value": True, "repeat": 7},
                False,
                ],
            "weekend": [
                {"value": False, "repeat": 7},
                {"value": True, "repeat": 16},
                False,
                ],
            }

        # Expanded boolean schedule (one item per hour)
        self.schedule_expanded = [
            # Weekday schedule (Mon)
            False, False, False, False, False, False, False, True,
            True, False, False, False, False, False, False, False,
            True, True, True, True, True, True, True, False,
            # Weekday schedule (Tue)
            False, False, False, False, False, False, False, True,
            True, False, False, False, False, False, False, False,
            True, True, True, True, True, True, True, False,
            # Weekday schedule (Wed)
            False, False, False, False, False, False, False, True,
            True, False, False, False, False, False, False, False,
            True, True, True, True, True, True, True, False,
            # Weekday schedule (Thu)
            False, False, False, False, False, False, False, True,
            True, False, False, False, False, False, False, False,
            True, True, True, True, True, True, True, False,
            # Weekday schedule (Fri)
            False, False, False, False, False, False, False, True,
            True, False, False, False, False, False, False, False,
            True, True, True, True, True, True, True, False,
            # Weekend schedule (Sat)
            False, False, False, False, False, False, False, True,
            True, True, True, True, True, True, True, True,
            True, True, True, True, True, True, True, False,
            # Weekend schedule (Sun)
            False, False, False, False, False, False, False, True,
            True, True, True, True, True, True, True, True,
            True, True, True, True, True, True, True, False,
            ]

    def test_process_schedule(self):
        """ Test that schedule is expanded correctly """
        self.maxDiff = None
        # Run the concise schedule through the expand_schedule function and
        # check it matches the expanded schedule as expected
        self.assertEqual(
            expand_schedule(bool, self.schedule, "main"),
            self.schedule_expanded,
            "incorrect schedule expansion"
            )
