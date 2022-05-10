#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains unit tests for the heat_pump module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.heating_systems.heat_pump import HeatPumpTestData


# Before defining the code to run the tests, we define the data to be parsed
# and the sorted/processed data structure it should be transformed into. Note
# that the data for design flow temp of 55 has an extra record (test letter F2)
# to test that the code can handle more than 2 records with the same temp_test
# value properly. This probably won't occur in practice.
data_unsorted = [
    {
        "test_letter": "A",
        "capacity": 8.4,
        "cop": 4.6,
        "degradation_coeff": 0.90,
        "design_flow_temp": 35,
        "temp_outlet": 34,
        "temp_source": 0,
        "temp_test": -7
    },
    {
        "test_letter": "B",
        "capacity": 8.3,
        "cop": 4.9,
        "degradation_coeff": 0.90,
        "design_flow_temp": 35,
        "temp_outlet": 30,
        "temp_source": 0,
        "temp_test": 2
    },
    {
        "test_letter": "C",
        "capacity": 8.3,
        "cop": 5.1,
        "degradation_coeff": 0.90,
        "design_flow_temp": 35,
        "temp_outlet": 27,
        "temp_source": 0,
        "temp_test": 7
    },
    {
        "test_letter": "D",
        "capacity": 8.2,
        "cop": 5.4,
        "degradation_coeff": 0.95,
        "design_flow_temp": 35,
        "temp_outlet": 24,
        "temp_source": 0,
        "temp_test": 12
    },
    {
        "test_letter": "F",
        "capacity": 8.4,
        "cop": 4.6,
        "degradation_coeff": 0.90,
        "design_flow_temp": 35,
        "temp_outlet": 34,
        "temp_source": 0,
        "temp_test": -7
    },
    {
        "test_letter": "A",
        "capacity": 8.8,
        "cop": 3.2,
        "degradation_coeff": 0.90,
        "design_flow_temp": 55,
        "temp_outlet": 52,
        "temp_source": 0,
        "temp_test": -7
    },
    {
        "test_letter": "B",
        "capacity": 8.6,
        "cop": 3.6,
        "degradation_coeff": 0.90,
        "design_flow_temp": 55,
        "temp_outlet": 42,
        "temp_source": 0,
        "temp_test": 2
    },
    {
        "test_letter": "C",
        "capacity": 8.5,
        "cop": 3.9,
        "degradation_coeff": 0.98,
        "design_flow_temp": 55,
        "temp_outlet": 36,
        "temp_source": 0,
        "temp_test": 7
    },
    {
        "test_letter": "D",
        "capacity": 8.5,
        "cop": 4.3,
        "degradation_coeff": 0.98,
        "design_flow_temp": 55,
        "temp_outlet": 30,
        "temp_source": 0,
        "temp_test": 12
    },
    {
        "test_letter": "F",
        "capacity": 8.8,
        "cop": 3.2,
        "degradation_coeff": 0.90,
        "design_flow_temp": 55,
        "temp_outlet": 52,
        "temp_source": 0,
        "temp_test": -7
    },
    {
        "test_letter": "F2",
        "capacity": 8.8,
        "cop": 3.2,
        "degradation_coeff": 0.90,
        "design_flow_temp": 55,
        "temp_outlet": 52,
        "temp_source": 0,
        "temp_test": -7
    }
]
data_sorted = {
    35: [
        {
            "test_letter": "A",
            "capacity": 8.4,
            "cop": 4.6,
            "degradation_coeff": 0.90,
            "design_flow_temp": 35,
            "temp_outlet": 34,
            "temp_source": 0,
            "temp_test": -7
        },
        {
            "test_letter": "F",
            "capacity": 8.4,
            "cop": 4.6,
            "degradation_coeff": 0.90,
            "design_flow_temp": 35,
            "temp_outlet": 34,
            "temp_source": 0.0000000001,
            "temp_test": -6.9999999999
        },
        {
            "test_letter": "B",
            "capacity": 8.3,
            "cop": 4.9,
            "degradation_coeff": 0.90,
            "design_flow_temp": 35,
            "temp_outlet": 30,
            "temp_source": 0,
            "temp_test": 2
        },
        {
            "test_letter": "C",
            "capacity": 8.3,
            "cop": 5.1,
            "degradation_coeff": 0.90,
            "design_flow_temp": 35,
            "temp_outlet": 27,
            "temp_source": 0,
            "temp_test": 7
        },
        {
            "test_letter": "D",
            "capacity": 8.2,
            "cop": 5.4,
            "degradation_coeff": 0.95,
            "design_flow_temp": 35,
            "temp_outlet": 24,
            "temp_source": 0,
            "temp_test": 12
        }
    ],
    55: [
        {
            "test_letter": "A",
            "capacity": 8.8,
            "cop": 3.2,
            "degradation_coeff": 0.90,
            "design_flow_temp": 55,
            "temp_outlet": 52,
            "temp_source": 0,
            "temp_test": -7
        },
        {
            "test_letter": "F",
            "capacity": 8.8,
            "cop": 3.2,
            "degradation_coeff": 0.90,
            "design_flow_temp": 55,
            "temp_outlet": 52,
            "temp_source": 0.0000000001,
            "temp_test": -6.9999999999
        },
        {
            "test_letter": "F2",
            "capacity": 8.8,
            "cop": 3.2,
            "degradation_coeff": 0.90,
            "design_flow_temp": 55,
            "temp_outlet": 52,
            "temp_source": 0.0000000002,
            "temp_test": -6.9999999998
        },
        {
            "test_letter": "B",
            "capacity": 8.6,
            "cop": 3.6,
            "degradation_coeff": 0.90,
            "design_flow_temp": 55,
            "temp_outlet": 42,
            "temp_source": 0,
            "temp_test": 2
        },
        {
            "test_letter": "C",
            "capacity": 8.5,
            "cop": 3.9,
            "degradation_coeff": 0.98,
            "design_flow_temp": 55,
            "temp_outlet": 36,
            "temp_source": 0,
            "temp_test": 7
        },
        {
            "test_letter": "D",
            "capacity": 8.5,
            "cop": 4.3,
            "degradation_coeff": 0.98,
            "design_flow_temp": 55,
            "temp_outlet": 30,
            "temp_source": 0,
            "temp_test": 12
        }
    ]
}

class TestHeatPumpTestData(unittest.TestCase):
    """ Unit tests for HeatPumpTestData class """

    def setUp(self):
        """ Create HeatPumpTestData object to be tested """
        self.hp_testdata = HeatPumpTestData(data_unsorted)

    def test_init(self):
        """ Test that internal data structures have been populated correctly.

        This includes parsing and sorting the test data records, and producing
        sorted list of the design flow temperatures for which the data records
        apply.
        """
        self.assertEqual(
            self.hp_testdata._HeatPumpTestData__dsgn_flow_temps,
            [35, 55],
            "list of design flow temps populated incorrectly"
            )
        self.assertEqual(
            self.hp_testdata._HeatPumpTestData__testdata,
            data_sorted,
            "list of test data records populated incorrectly"
            )
        # TODO Should also test that invalid data is handled correctly. This
        #      will require the init function to throw exceptions rather than
        #      exit the process as it does now.

