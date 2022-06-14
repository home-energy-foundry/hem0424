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
            "carnot_cop": 9.033823529411764,
            "cop": 4.6,
            "degradation_coeff": 0.90,
            "design_flow_temp": 35,
            "exergetic_eff": 0.5091974605241738,
            "temp_outlet": 34,
            "temp_source": 0,
            "temp_test": -7,
            "theoretical_load_ratio": 1.0,
        },
        {
            "test_letter": "F",
            "capacity": 8.4,
            "carnot_cop": 9.033823529438331,
            "cop": 4.6,
            "degradation_coeff": 0.90,
            "design_flow_temp": 35,
            "exergetic_eff": 0.5091974605226763,
            "temp_outlet": 34,
            "temp_source": 0.0000000001,
            "temp_test": -6.9999999999,
            "theoretical_load_ratio": 1.0000000000040385,
        },
        {
            "test_letter": "B",
            "capacity": 8.3,
            "carnot_cop": 10.104999999999999,
            "cop": 4.9,
            "degradation_coeff": 0.90,
            "design_flow_temp": 35,
            "exergetic_eff": 0.48490846115784275,
            "temp_outlet": 30,
            "temp_source": 0,
            "temp_test": 2,
            "theoretical_load_ratio": 1.1634388356892613,
        },
        {
            "test_letter": "C",
            "capacity": 8.3,
            "carnot_cop": 11.116666666666665,
            "cop": 5.1,
            "degradation_coeff": 0.90,
            "design_flow_temp": 35,
            "exergetic_eff": 0.4587706146926537,
            "temp_outlet": 27,
            "temp_source": 0,
            "temp_test": 7,
            "theoretical_load_ratio": 1.3186802349509577,
        },
        {
            "test_letter": "D",
            "capacity": 8.2,
            "carnot_cop": 12.38125,
            "cop": 5.4,
            "degradation_coeff": 0.95,
            "design_flow_temp": 35,
            "exergetic_eff": 0.43614336193841496,
            "temp_outlet": 24,
            "temp_source": 0,
            "temp_test": 12,
            "theoretical_load_ratio": 1.513621351820552,
        }
    ],
    55: [
        {
            "test_letter": "A",
            "capacity": 8.8,
            "carnot_cop": 6.252884615384615,
            "cop": 3.2,
            "degradation_coeff": 0.90,
            "design_flow_temp": 55,
            "exergetic_eff": 0.5117638013224666,
            "temp_outlet": 52,
            "temp_source": 0,
            "temp_test": -7,
            "theoretical_load_ratio": 1.0,
        },
        {
            "test_letter": "F",
            "capacity": 8.8,
            "carnot_cop": 6.252884615396638,
            "cop": 3.2,
            "degradation_coeff": 0.90,
            "design_flow_temp": 55,
            "exergetic_eff": 0.5117638013214826,
            "temp_outlet": 52,
            "temp_source": 0.0000000001,
            "temp_test": -6.9999999999,
            "theoretical_load_ratio": 1.0000000000030207,
        },
        {
            "test_letter": "F2",
            "capacity": 8.8,
            "carnot_cop": 6.252884615408662,
            "cop": 3.2,
            "degradation_coeff": 0.90,
            "design_flow_temp": 55,
            "exergetic_eff": 0.5117638013204985,
            "temp_outlet": 52,
            "temp_source": 0.0000000002,
            "temp_test": -6.9999999998,
            "theoretical_load_ratio": 1.0000000000060418,
        },
        {
            "test_letter": "B",
            "capacity": 8.6,
            "carnot_cop": 7.503571428571428,
            "cop": 3.6,
            "degradation_coeff": 0.90,
            "design_flow_temp": 55,
            "exergetic_eff": 0.4797715373631604,
            "temp_outlet": 42,
            "temp_source": 0,
            "temp_test": 2,
            "theoretical_load_ratio": 1.3179136223360988,
        },
        {
            "test_letter": "C",
            "capacity": 8.5,
            "carnot_cop": 8.587499999999999,
            "cop": 3.9,
            "degradation_coeff": 0.98,
            "design_flow_temp": 55,
            "exergetic_eff": 0.4541484716157206,
            "temp_outlet": 36,
            "temp_source": 0,
            "temp_test": 7,
            "theoretical_load_ratio": 1.5978273764295179,
        },
        {
            "test_letter": "D",
            "capacity": 8.5,
            "carnot_cop": 10.104999999999999,
            "cop": 4.3,
            "degradation_coeff": 0.98,
            "design_flow_temp": 55,
            "exergetic_eff": 0.4255319148936171,
            "temp_outlet": 30,
            "temp_source": 0,
            "temp_test": 12,
            "theoretical_load_ratio": 1.9940427298329144,
        }
    ]
}

class TestHeatPumpTestData(unittest.TestCase):
    """ Unit tests for HeatPumpTestData class """
    # TODO Test handling of case where test data for only 1 design flow temp has been provided

    def setUp(self):
        """ Create HeatPumpTestData object to be tested """
        self.hp_testdata = HeatPumpTestData(data_unsorted)

    def test_init(self):
        """ Test that internal data structures have been populated correctly.

        This includes parsing and sorting the test data records, and producing
        sorted list of the design flow temperatures for which the data records
        apply.
        """
        self.maxDiff = None
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

    def test_init_regression_coeffs(self):
        """ Test that regression coefficients have been populated correctly """
        self.maxDiff = None
        self.assertEqual(
            self.hp_testdata._HeatPumpTestData__regression_coeffs,
            {
                35: [4.810017281274474, 0.03677543129969711, 0.0009914765238219576],
                55: [3.4857982546529755, 0.050636568790103566, 0.001410495558351414]
            },
            "list of regression coefficients populated incorrectly"
            )

    def test_average_degradation_coeff(self):
        """ Test that correct average degradation coeff is returned for the flow temp """
        results = [0.9125, 0.919375, 0.92625, 0.933125, 0.94]

        for i, flow_temp in enumerate([35, 40, 45, 50, 55]):
            with self.subTest(i=i):
                self.assertAlmostEqual(
                    self.hp_testdata.average_degradation_coeff(flow_temp),
                    results[i],
                    msg="incorrect average degradation coefficient returned"
                    )

    def test_average_capacity(self):
        """ Test that correct average capacity is returned for the flow temp """
        results = [8.3, 8.375, 8.45, 8.525, 8.6]

        for i, flow_temp in enumerate([35, 40, 45, 50, 55]):
            with self.subTest(i=i):
                self.assertAlmostEqual(
                    self.hp_testdata.average_capacity(flow_temp),
                    results[i],
                    msg="incorrect average capacity returned"
                    )

    def test_temp_spread_test_conditions(self):
        """ Test that correct temp spread at test conditions is returned for the flow temp """ 
        results = [5.0, 5.75, 6.5, 7.25, 8.0]
        
        for i, flow_temp in enumerate([35, 40, 45, 50, 55]):
            with self.subTest(i=i):
                self.assertEqual(
                    self.hp_testdata.temp_spread_test_conditions(flow_temp),
                    results[i],
                    msg="incorrect temp spread at test conditions returned"
                    )

    def test_carnot_cop_at_test_condition(self):
        """ Test that correct Carnot CoP is returned for the flow temp and test condition """
        # TODO Test conditions other than just coldest
        i = -1
        for flow_temp, test_condition, result in [
            [35, 'cld', 9.033823529411764],
            [40, 'cld', 8.338588800904978],
            [45, 'cld', 7.643354072398189],
            [50, 'cld', 6.948119343891403],
            [55, 'cld', 6.252884615384615],
            [45, 'A', 7.643354072398189],
            [45, 'B', 8.804285714285713],
            [45, 'C', 9.852083333333333],
            [45, 'D', 11.243125],
            [45, 'F', 7.643354072417485],
            ]:
            # TODO Note that the result above for condition F is different to
            #      that for condition A, despite the source and outlet temps in
            #      the inputs being the same for both, because of the adjustment
            #      to the source temp applied in the HeatPumpTestData __init__
            #      function when duplicate records are found. This may not be
            #      the desired behaviour (see the TODO comment in that function)
            #      but in that case the problem is not with the function that
            #      is being tested here, so for now we set the result so that
            #      the test passes.
            i += 1
            with self.subTest(i=i):
                self.assertEqual(
                    self.hp_testdata.carnot_cop_at_test_condition(test_condition, flow_temp),
                    result,
                    "incorrect Carnot CoP at condition "+test_condition+" returned"
                    )

    def test_outlet_temp_at_test_condition(self):
        """ Test that correct outlet temp is returned for the flow temp and test condition """
        # TODO Test conditions other than just coldest
        i = -1
        for flow_temp, test_condition, result in [
            [35, 'cld', 307.15],
            [40, 'cld', 311.65],
            [45, 'cld', 316.15],
            [50, 'cld', 320.65],
            [55, 'cld', 325.15],
            [45, 'A', 316.15],
            [45, 'B', 309.15],
            [45, 'C', 304.65],
            [45, 'D', 300.15],
            [45, 'F', 316.15],
            ]:
            i += 1
            with self.subTest(i=i):
                self.assertEqual(
                    self.hp_testdata.outlet_temp_at_test_condition(test_condition, flow_temp),
                    result,
                    "incorrect outlet temp at condition "+test_condition+" returned"
                    )

    def test_source_temp_at_test_condition(self):
        """ Test that correct source temp is returned for the flow temp and test condition """
        # TODO Test conditions other than just coldest
        i = -1
        for flow_temp, test_condition, result in [
            [35, 'cld', 273.15],
            [40, 'cld', 273.15],
            [45, 'cld', 273.15],
            [50, 'cld', 273.15],
            [55, 'cld', 273.15],
            [45, 'A', 273.15],
            [45, 'B', 273.15],
            [45, 'C', 273.15],
            [45, 'D', 273.15],
            [45, 'F', 273.15000000009996],
            ]:
            # TODO Note that the result above for condition F is different to
            #      that for condition A, despite the source and outlet temps in
            #      the inputs being the same for both, because of the adjustment
            #      to the source temp applied in the HeatPumpTestData __init__
            #      function when duplicate records are found. This may not be
            #      the desired behaviour (see the TODO comment in that function)
            #      but in that case the problem is not with the function that
            #      is being tested here, so for now we set the result so that
            #      the test passes.
            i += 1
            with self.subTest(i=i):
                self.assertEqual(
                    self.hp_testdata.source_temp_at_test_condition(test_condition, flow_temp),
                    result,
                    "incorrect source temp at condition "+test_condition+" returned"
                    )

    def test_capacity_at_test_condition(self):
        """ Test that correct capacity is returned for the flow temp and test condition """
        i = -1
        for flow_temp, test_condition, result in [
            [35, 'cld', 8.4],
            [40, 'cld', 8.5],
            [45, 'cld', 8.6],
            [50, 'cld', 8.7],
            [55, 'cld', 8.8],
            [45, 'A', 8.6],
            [45, 'B', 8.45],
            [45, 'C', 8.4],
            [45, 'D', 8.35],
            [45, 'F', 8.6],
            ]:
            i += 1
            with self.subTest(i=i):
                self.assertAlmostEqual(
                    self.hp_testdata.capacity_at_test_condition(test_condition, flow_temp),
                    result,
                    msg="incorrect capacity at condition "+test_condition+" returned"
                    )

    def test_lr_eff_degcoeff_either_side_of_op_cond(self):
        """ Test that correct test results either side of operating conditions are returned """
        results_lr_below = [
            1.1634388356892613, 1.1225791267684564, 1.0817194178476517, 1.0408597089268468,
            1.0000000000060418,
            1.3186802349509577, 1.318488581797243, 1.3182969286435282, 1.3181052754898135,
            1.3179136223360988,
            ]
        results_lr_above = [
            1.3186802349509577, 1.318488581797243, 1.3182969286435282, 1.3181052754898135,
            1.3179136223360988,
            1.513621351820552, 1.5346728579727933, 1.555724364125035, 1.5767758702772765,
            1.5978273764295179,
            ]
        results_eff_below = [
            0.48490846115784275, 0.49162229619850667, 0.49833613123917064, 0.5050499662798346,
            0.5117638013204985,
            0.4587706146926537, 0.4640208453602804, 0.4692710760279071, 0.4745213066955337,
            0.4797715373631604,
            ]
        results_eff_above = [
            0.4587706146926537, 0.4640208453602804, 0.4692710760279071, 0.4745213066955337,
            0.4797715373631604,
            0.43614336193841496, 0.44064463935774134, 0.4451459167770678, 0.4496471941963942,
            0.4541484716157206,
            ]
        results_deg_below = [0.9] * 10
        results_deg_above = \
            [0.9, 0.9, 0.9, 0.9, 0.9, 0.95, 0.9575, 0.965, 0.9724999999999999, 0.98]

        i = -1
        for exergy_lr_op_cond in [1.2, 1.4]:
            for flow_temp in [35, 40, 45, 50, 55]:
                i += 1
                with self.subTest(i=i):
                    lr_below, lr_above, eff_below, eff_above, deg_below, deg_above = \
                        self.hp_testdata.lr_eff_degcoeff_either_side_of_op_cond(
                            flow_temp,
                            exergy_lr_op_cond,
                            )
                    self.assertEqual(
                        lr_below,
                        results_lr_below[i],
                        "incorrect load ratio below operating conditions returned",
                        )
                    self.assertEqual(
                        lr_above,
                        results_lr_above[i],
                        "incorrect load ratio above operating conditions returned",
                        )
                    self.assertEqual(
                        eff_below,
                        results_eff_below[i],
                        "incorrect efficiency below operating conditions returned",
                        )
                    self.assertEqual(
                        eff_above,
                        results_eff_above[i],
                        "incorrect efficiency above operating conditions returned",
                        )
                    self.assertEqual(
                        deg_below,
                        results_deg_below[i],
                        "incorrect degradation coeff below operating conditions returned",
                        )
                    self.assertEqual(
                        deg_above,
                        results_deg_above[i],
                        "incorrect degradation coeff above operating conditions returned",
                        )

    def test_cop_op_cond_if_not_air_source(self):
        """ Test that correct CoP at operating conditions (not air source) is returned """
        results = [
            8.070540309266503,
            10.616403014723252,
            5.539815752185454,
            8.039050079300951,
            4.460426809129295,
            ]

        i = -1
        for flow_temp, min_temp_diff_emit, temp_ext, temp_source, temp_output in [
            [35.0, 8.0, 0.00, 283.15, 303.15],
            [40.0, 7.0, -5.0, 293.15, 308.15],
            [45.0, 6.0, 5.00, 278.15, 310.65],
            [50.0, 5.0, 10.0, 288.15, 313.15],
            [55.0, 4.0, 7.50, 273.15, 318.15],
            ]:
            i += 1
            with self.subTest(i=i):
                self.assertEqual(
                    self.hp_testdata.cop_op_cond_if_not_air_source(
                        flow_temp,
                        min_temp_diff_emit,
                        temp_ext,
                        temp_source,
                        temp_output,
                        ),
                    results[i],
                    "incorrect CoP at operating conditions (not air source) returned",
                    )

