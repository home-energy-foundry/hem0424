#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides objects to represent heat pumps and heat pump test data.
The calculations are based on the DAHPSE method developed for generating PCDB
entries for SAP 2012 and SAP 10. DAHPSE was based on a draft of
BS EN 15316-4-2:2017 and is described in the SAP calculation method CALCM-01.
"""

# Standard library imports
import sys
from copy import deepcopy
from enum import Enum, auto

# Third-party imports
import numpy as np
from numpy.polynomial.polynomial import polyfit

# Local imports
from core.units import Celcius2Kelvin, Kelvin2Celcius

# Constants
N_EXER = 3.0


# Data types

class SourceType(Enum):
    GROUND = auto()
    OUTSIDE_AIR = auto()
    EXHAUST_AIR_MEV = auto()
    EXHAUST_AIR_MVHR = auto()
    EXHAUST_AIR_MIXED = auto()
    WATER_GROUND = auto()
    WATER_SURFACE = auto()

    @classmethod
    def from_string(cls, strval):
        if strval == 'Ground':
            return cls.GROUND
        elif strval == 'OutsideAir':
            return cls.OUTSIDE_AIR
        elif strval == 'ExhaustAirMEV':
            return cls.EXHAUST_AIR_MEV
        elif strval == 'ExhaustAirMVHR':
            return cls.EXHAUST_AIR_MVHR
        elif strval == 'ExhaustAirMixed':
            return cls.EXHAUST_AIR_MIXED
        elif strval == 'WaterGround':
            return cls.WATER_GROUND
        elif strval == 'WaterSurface':
            return cls.WATER_SURFACE
        else:
            sys.exit('SourceType (' + str(strval) + ') not valid.')
            # TODO Exit just the current case instead of whole program entirely?

class SinkType(Enum):
    AIR = auto()
    WATER = auto()

    @classmethod
    def from_string(cls, strval):
        if strval == 'Air':
            return cls.AIR
        elif strval == 'Water':
            return cls.WATER
        else:
            sys.exit('SinkType (' + str(strval) + ') not valid.')
            # TODO Exit just the current case instead of whole program entirely?

class BackupCtrlType(Enum):
    NONE = auto()
    TOPUP = auto()
    SUBSTITUTE = auto()

    @classmethod
    def from_string(cls, strval):
        if strval == 'None':
            return cls.NONE
        elif strval == 'TopUp':
            return cls.TOPUP
        elif strval == 'Substitute':
            return cls.SUBSTITUTE
        else:
            sys.exit('BackupType (' + str(strval) + ') not valid.')
            # TODO Exit just the current case instead of whole program entirely?

class ServiceType(Enum):
    WATER = auto()
    SPACE = auto()


# Free functions

def carnot_cop(temp_source, temp_outlet, temp_diff_limit_low=None):
    """ Calculate Carnot CoP based on source and outlet temperatures (in Kelvin) """
    temp_diff = temp_outlet - temp_source
    if temp_diff_limit_low is not None:
        temp_diff = max (temp_diff, temp_diff_limit_low)
    return temp_outlet / temp_diff


# Classes

class HeatPumpTestData:
    """ An object to represent EN 14825 test data for a heat pump.

    This object stores the data and provides functions to look up values from
    the correct data records for the conditions being modelled.
    """

    __test_letters_non_bivalent = ['A', 'B', 'C', 'D']
    __test_letters_all = ['A','B','C','D','F']

    def __init__(self, hp_testdata_dict_list):
        """ Construct a HeatPumpTestData object

        Arguments:
        hp_testdata_dict_list
            -- list of dictionaries of heat pump test data, each with the following elements:
                - test_letter
                - capacity
                - cop
                - degradation_coeff
                - design_flow_temp (in Celsius)
                - temp_outlet (in Celsius)
                - temp_source (in Celsius)
                - temp_test (in Celsius)
        """
        def duplicates(a, b):
            """ Determine whether records a and b are duplicates """
            return (a['temp_test'] == b['temp_test'] \
                and a['design_flow_temp'] == b['design_flow_temp'])

        # Keys will be design flow temps, values will be lists of dicts containing the test data
        self.__testdata = {}

        # A separate list of design flow temps is required because it can be
        # sorted, whereas the dict above can't be (at least before Python 3.7)
        self.__dsgn_flow_temps = []
        # Dict to count duplicate records for each design flow temp
        dupl = {}

        # Read the test data records
        # Work on a deep copy of the input data structure in case the original
        # is used to init other objects (or the same object multiple times
        # e.g. during testing)
        for hp_testdata_dict in deepcopy(hp_testdata_dict_list):
            dsgn_flow_temp = hp_testdata_dict['design_flow_temp']

            # When a new design flow temp is encountered, add it to the lists/dicts
            if dsgn_flow_temp not in self.__dsgn_flow_temps:
                self.__dsgn_flow_temps.append(dsgn_flow_temp)
                self.__testdata[dsgn_flow_temp] = []
                dupl[dsgn_flow_temp] = 0

            # Check for duplicate records
            duplicate = False
            for d in self.__testdata[dsgn_flow_temp]:
                if duplicates(hp_testdata_dict, d):
                    duplicate = True
                    # Increment count of number of duplicates for this design flow temp
                    # Handle records with same inlet temp
                    # Cannot process a row at the same inlet temperature (div
                    # by zero error during interpolation), so we add a tiny
                    # amount to the temperature (to 10DP) for each duplicate
                    # found.
                    # TODO Why do we need to alter the duplicate record? Can we
                    #      not just eliminate it?
                    hp_testdata_dict['temp_test']   += 0.0000000001
                    hp_testdata_dict['temp_source'] += 0.0000000001
                    # TODO The adjustment to temp_source is in the python
                    #      implementation of DAHPSE but not in the spreadsheet
                    #      implementation. Given that temp_source can be the
                    #      same for all test records anyway, is this adjustment
                    #      needed?
            # This increment has to be after loop to avoid multiple-counting
            # when there are 3 or more duplicates. E.g. if there are already 2
            # records that are the same, then when adding a third that is the
            # same, we only want to increment the counter by 1 (for the record
            # we are adding) and not 2 (the number of existing records the new
            # record duplicates).
            if duplicate:
                dupl[dsgn_flow_temp] += 1

            # Add the test record to the data structure, under the appropriate design flow temp
            self.__testdata[dsgn_flow_temp].append(hp_testdata_dict)

        # Check the number of test records is as expected
        # - 1 or 2 design flow temps
        # - 4 or 5 distinct records for each flow temp
        # TODO Is there any reason the model couldn't handle more than 2 design
        #      flow temps or more than 5 test records if data is available?
        #      Could/should we relax the restrictions below?
        if len(self.__dsgn_flow_temps) < 1:
            sys.exit('No test data provided for heat pump performance')
        elif len(self.__dsgn_flow_temps) > 2:
            sys.exit('Test data for a maximum of 2 design flow temperatures may be provided')
        for dsgn_flow_temp, data in self.__testdata.items():
            if dupl[dsgn_flow_temp]:
                if (len(data) - dupl[dsgn_flow_temp]) != 4:
                    sys.exit('Expected 4 distinct records for each design flow temperature')
            elif len(data) != 5:
                sys.exit('Expected 5 records for each design flow temperature')

        # Check if test letters ABCDF are present as expected
        test_letter_array = []
        for temperature in self.__dsgn_flow_temps:
            for test_data in self.__testdata[temperature]:
                for test_letter in test_data['test_letter']:
                    test_letter_array.append(test_letter)
                if len(test_letter_array) == 5:
                    for test_letter_check in self.__test_letters_all:
                        if test_letter_check not in test_letter_array:
                            error_output = 'Expected test letter ' + test_letter_check + ' in ' + str(temperature) + ' degree temp data'
                            sys.exit(error_output)
                    test_letter_array = []

        # Sort the list of design flow temps
        self.__dsgn_flow_temps = sorted(self.__dsgn_flow_temps)

        # Sort the records in order of test temperature from low to high
        for dsgn_flow_temp, data in self.__testdata.items():
            data.sort(key=lambda sublist: sublist['temp_test'])

        # Calculate derived variables which are not time-dependent

        def ave_degradation_coeff():
            # The list average_deg_coeff will be in the same order as the
            # corresponding elements in self.__dsgn_flow_temps. This behaviour
            # is relied upon elsewhere.
            average_deg_coeff = []
            for dsgn_flow_temp in self.__dsgn_flow_temps:
                average_deg_coeff.append(
                    sum([
                        x['degradation_coeff']
                        for x in self.__testdata[dsgn_flow_temp]
                        if x['test_letter'] in self.__test_letters_non_bivalent
                        ]) \
                    / len(self.__test_letters_non_bivalent)
                    )
            return average_deg_coeff

        self.__average_deg_coeff = ave_degradation_coeff()

        def ave_capacity():
            # The list average_cap will be in the same order as the
            # corresponding elements in self.__dsgn_flow_temps. This behaviour
            # is relied upon elsewhere.
            average_cap = []
            for dsgn_flow_temp in self.__dsgn_flow_temps:
                average_cap.append(
                    sum([
                        x['capacity']
                        for x in self.__testdata[dsgn_flow_temp]
                        if x['test_letter'] in self.__test_letters_non_bivalent
                        ]) \
                    / len(self.__test_letters_non_bivalent)
                    )
            return average_cap

        self.__average_cap = ave_capacity()

        def init_temp_spread_test_conditions():
            """ List temp spread at test conditions for the design flow temps in the test data """
            dtheta_out_by_flow_temp = {35: 5.0, 55: 8.0, 65: 10.0}
            dtheta_out = []
            for dsgn_flow_temp in self.__dsgn_flow_temps:
                dtheta_out.append(dtheta_out_by_flow_temp[dsgn_flow_temp])
            return dtheta_out

        self.__temp_spread_test_conditions = init_temp_spread_test_conditions()

        def init_regression_coeffs():
            """ Calculate polynomial regression coefficients for test temperature vs. CoP """
            regression_coeffs = {}
            for dsgn_flow_temp in self.__dsgn_flow_temps:
                temp_test_list = [x['temp_test'] for x in self.__testdata[dsgn_flow_temp]]
                cop_list = [x['cop'] for x in self.__testdata[dsgn_flow_temp]]
                regression_coeffs[dsgn_flow_temp] = (list(polyfit(temp_test_list, cop_list, 2)))

            return regression_coeffs

        self.__regression_coeffs = init_regression_coeffs()

        # Calculate derived variables for each data record which are not time-dependent
        for dsgn_flow_temp in self.__dsgn_flow_temps:
            for data in self.__testdata[dsgn_flow_temp]:
                # Get the source and outlet temperatures from the test record
                temp_source = Celcius2Kelvin(data['temp_source'])
                temp_outlet = Celcius2Kelvin(data['temp_outlet'])

                # Calculate the Carnot CoP and add to the test record
                data['carnot_cop'] = carnot_cop(temp_source, temp_outlet)
                # Calculate the exergetic efficiency and add to the test record
                data['exergetic_eff'] = data['cop'] / data['carnot_cop']

            temp_source_cld = Celcius2Kelvin(self.__testdata[dsgn_flow_temp][0]['temp_source'])
            temp_outlet_cld = Celcius2Kelvin(self.__testdata[dsgn_flow_temp][0]['temp_outlet'])
            carnot_cop_cld = self.__testdata[dsgn_flow_temp][0]['carnot_cop']

            # Calculate derived variables that require values at coldest test temp as inputs
            for data in self.__testdata[dsgn_flow_temp]:
                # Get the source and outlet temperatures from the test record
                temp_source = Celcius2Kelvin(data['temp_source'])
                temp_outlet = Celcius2Kelvin(data['temp_outlet'])

                # Calculate the theoretical load ratio and add to the test record
                data['theoretical_load_ratio'] \
                    = ((data['carnot_cop'] / carnot_cop_cld) \
                    * (temp_outlet_cld * temp_source / (temp_source_cld * temp_outlet)) ** N_EXER)

    def average_degradation_coeff(self, flow_temp):
        """ Return average deg coeff for tests A-D, interpolated between design flow temps """
        if len(self.__dsgn_flow_temps) == 1:
            # If there is data for only one design flow temp, use that
            return self.__average_deg_coeff[0]

        flow_temp = Kelvin2Celcius(flow_temp)
        return np.interp(flow_temp, self.__dsgn_flow_temps, self.__average_deg_coeff)

    def average_capacity(self, flow_temp):
        """ Return average capacity for tests A-D, interpolated between design flow temps """
        if len(self.__dsgn_flow_temps) == 1:
            # If there is data for only one design flow temp, use that
            return self.__average_cap[0]

        flow_temp = Kelvin2Celcius(flow_temp)
        return np.interp(flow_temp, self.__dsgn_flow_temps, self.__average_cap)

    def temp_spread_test_conditions(self, flow_temp):
        """ Return temperature spread under test conditions, interpolated between design flow temps """
        if len(self.__dsgn_flow_temps) == 1:
            # If there is data for only one design flow temp, use that
            return self.__temp_spread_test_conditions[0]

        flow_temp = Kelvin2Celcius(flow_temp)
        return np.interp(flow_temp, self.__dsgn_flow_temps, self.__temp_spread_test_conditions)

    def __find_test_record_index(self, test_condition, dsgn_flow_temp):
        """ Find position of specified test condition in list """
        if test_condition == 'cld':
            # Coldest test condition is first in list
            return 0
        for index, test_record in enumerate(self.__testdata[dsgn_flow_temp]):
            if test_record['test_letter'] == test_condition:
                return index

    def __data_at_test_condition(self, data_item_name, test_condition, flow_temp):
        """ Return value at specified test condition, interpolated between design flow temps """
        # TODO What do we do if flow_temp is outside the range of design flow temps provided?

        if len(self.__dsgn_flow_temps) == 1:
            # If there is data for only one design flow temp, use that
            idx = self.__find_test_record_index(test_condition, self.__dsgn_flow_temps[0])
            return self.__testdata[self.__dsgn_flow_temps[0]][idx][data_item_name]

        # Interpolate between the values at each design flow temp
        data_list = []
        for dsgn_flow_temp in self.__dsgn_flow_temps:
            idx = self.__find_test_record_index(test_condition, dsgn_flow_temp)
            data_list.append(self.__testdata[dsgn_flow_temp][idx][data_item_name])

        flow_temp = Kelvin2Celcius(flow_temp)
        return np.interp(flow_temp, self.__dsgn_flow_temps, data_list)

    def carnot_cop_at_test_condition(self, test_condition, flow_temp):
        """
        Return Carnot CoP at specified test condition (A, B, C, D, F or cld),
        interpolated between design flow temps
        """
        return self.__data_at_test_condition('carnot_cop', test_condition, flow_temp)

    def outlet_temp_at_test_condition(self, test_condition, flow_temp):
        """
        Return outlet temp, in Kelvin, at specified test condition (A, B, C, D,
        F or cld), interpolated between design flow temps.
        """
        return Celcius2Kelvin(
            self.__data_at_test_condition('temp_outlet', test_condition, flow_temp)
            )

    def source_temp_at_test_condition(self, test_condition, flow_temp):
        """
        Return source temp, in Kelvin, at specified test condition (A, B, C, D,
        F or cld), interpolated between design flow temps.
        """
        return Celcius2Kelvin(
            self.__data_at_test_condition('temp_source', test_condition, flow_temp)
            )

    def capacity_at_test_condition(self, test_condition, flow_temp):
        """
        Return capacity, in kW, at specified test condition (A, B, C, D, F or
        cld), interpolated between design flow temps.
        """
        return self.__data_at_test_condition('capacity', test_condition, flow_temp)

    def lr_op_cond(self, flow_temp, temp_source, carnot_cop_op_cond):
        """ Return load ratio at operating conditions """
        lr_op_cond_list = []
        for dsgn_flow_temp in self.__dsgn_flow_temps:
            dsgn_flow_temp = Celcius2Kelvin(dsgn_flow_temp)
            temp_output_cld = self.outlet_temp_at_test_condition('cld', dsgn_flow_temp)
            temp_source_cld = self.source_temp_at_test_condition('cld', dsgn_flow_temp)
            carnot_cop_cld = self.carnot_cop_at_test_condition('cld', dsgn_flow_temp)

            lr_op_cond = (carnot_cop_op_cond / carnot_cop_cld) \
                       * ( temp_output_cld * temp_source
                         / (flow_temp * temp_source_cld)
                         ) \
                         ** N_EXER
            lr_op_cond_list.append(max(1.0, lr_op_cond))

        flow_temp = Kelvin2Celcius(flow_temp)
        return np.interp(flow_temp, self.__dsgn_flow_temps, lr_op_cond_list)

    def lr_eff_degcoeff_either_side_of_op_cond(self, flow_temp, exergy_lr_op_cond):
        """ Return test results either side of operating conditions.

        This function returns 6 results:
        - Exergy load ratio below operating conditions
        - Exergy load ratio above operating conditions
        - Exergy efficiency below operating conditions
        - Exergy efficiency above operating conditions
        - Degradation coeff below operating conditions
        - Degradation coeff above operating conditions

        Arguments:
        flow_temp         -- flow temperature, in Kelvin
        exergy_lr_op_cond -- exergy load ratio at operating conditions
        """
        load_ratios_below = []
        load_ratios_above = []
        efficiencies_below = []
        efficiencies_above = []
        degradation_coeffs_below = []
        degradation_coeffs_above = []

        # For each design flow temperature, find load ratios in test data
        # either side of load ratio calculated for operating conditions.
        # Note: Loop over sorted list of design flow temps and then index into
        #       self.__testdata, rather than looping over self.__testdata,
        #       which is unsorted and therefore may populate the lists in the
        #       wrong order.
        for dsgn_flow_temp in self.__dsgn_flow_temps:
            found = False
            dsgn_flow_temp_data = self.__testdata[dsgn_flow_temp]
            # Find the first load ratio in the test data that is greater than
            # or equal to than the load ratio at operating conditions - this
            # and the previous load ratio are the values either side of
            # operating conditions.
            for idx, test_record in enumerate(dsgn_flow_temp_data):
                # Note: Changed the condition below from ">=" to ">" because
                # otherwise when exergy_lr_op_cond == test_record['theoretical_load_ratio']
                # for the first record, idx == 0 which is not allowed
                if test_record['theoretical_load_ratio'] > exergy_lr_op_cond:
                    assert idx > 0
                    found = True
                    # Current value of idx will be used later, so break out of loop
                    break

            if not found:
                # Use the highest (list index -1) and second highest
                idx = -1

            # Look up correct load ratio and efficiency based on the idx found above
            load_ratios_below.append(dsgn_flow_temp_data[idx-1]['theoretical_load_ratio'])
            load_ratios_above.append(dsgn_flow_temp_data[idx]['theoretical_load_ratio'])
            efficiencies_below.append(dsgn_flow_temp_data[idx-1]['exergetic_eff'])
            efficiencies_above.append(dsgn_flow_temp_data[idx]['exergetic_eff'])
            degradation_coeffs_below.append(dsgn_flow_temp_data[idx-1]['degradation_coeff'])
            degradation_coeffs_above.append(dsgn_flow_temp_data[idx]['degradation_coeff'])

        if len(self.__dsgn_flow_temps) == 1:
            # If there is data for only one design flow temp, use that
            return load_ratios_below[0], load_ratios_above[0], \
                   efficiencies_below[0], efficiencies_above[0], \
                   degradation_coeffs_below[0], degradation_coeffs_above[0]

        # Interpolate between the values found for the different design flow temperatures
        flow_temp = Kelvin2Celcius(flow_temp)
        lr_below = np.interp(flow_temp, self.__dsgn_flow_temps, load_ratios_below)
        lr_above = np.interp(flow_temp, self.__dsgn_flow_temps, load_ratios_above)
        eff_below = np.interp(flow_temp, self.__dsgn_flow_temps, efficiencies_below)
        eff_above = np.interp(flow_temp, self.__dsgn_flow_temps, efficiencies_above)
        deg_below = np.interp(flow_temp, self.__dsgn_flow_temps, degradation_coeffs_below)
        deg_above = np.interp(flow_temp, self.__dsgn_flow_temps, degradation_coeffs_above)

        return lr_below, lr_above, eff_below, eff_above, deg_below, deg_above

    def cop_op_cond_if_not_air_source(
            self,
            temp_diff_limit_low,
            temp_ext,
            temp_source,
            temp_output,
            ):
        """ Calculate CoP at operating conditions when heat pump is not air-source

        Arguments:
        temp_diff_limit_low -- minimum temperature difference between source and sink
        temp_ext           -- external temperature, in Kelvin
        temp_source        -- source temperature, in Kelvin
        temp_output        -- output temperature, in Kelvin
        """
        # Need to use Celsius here because regression coeffs were calculated
        # using temperature in Celsius
        temp_ext = Kelvin2Celcius(temp_ext)

        # For each design flow temperature, calculate CoP at operating conditions
        # Note: Loop over sorted list of design flow temps and then index into
        #       self.__testdata, rather than looping over self.__testdata,
        #       which is unsorted and therefore may populate the lists in the
        #       wrong order.
        cop_op_cond = []
        for dsgn_flow_temp in self.__dsgn_flow_temps:
            dsgn_flow_temp_data = self.__testdata[dsgn_flow_temp]
            # Get the source and outlet temperatures from the coldest test record
            temp_outlet_cld = Celcius2Kelvin(dsgn_flow_temp_data[0]['temp_outlet'])
            temp_source_cld = Celcius2Kelvin(dsgn_flow_temp_data[0]['temp_source'])

            cop_operating_conditions \
                = ( self.__regression_coeffs[dsgn_flow_temp][0] \
                  + self.__regression_coeffs[dsgn_flow_temp][1] * temp_ext \
                  + self.__regression_coeffs[dsgn_flow_temp][2] * temp_ext ** 2 \
                  ) \
                * temp_output * (temp_outlet_cld - temp_source_cld) \
                / ( temp_outlet_cld * max( (temp_output - temp_source), temp_diff_limit_low))
            cop_op_cond.append(cop_operating_conditions)

        if len(self.__dsgn_flow_temps) == 1:
            # If there is data for only one design flow temp, use that
            return cop_op_cond[0]

        # Interpolate between the values found for the different design flow temperatures
        flow_temp = Kelvin2Celcius(temp_output)
        return np.interp(flow_temp, self.__dsgn_flow_temps, cop_op_cond)

    def capacity_op_cond_if_not_air_source(self, temp_output, temp_source, mod_ctrl):
        """ Calculate thermal capacity at operating conditions when heat pump is not air-source
        
        Arguments:
        temp_source -- source temperature, in Kelvin
        temp_output -- output temperature, in Kelvin
        mod_ctrl -- boolean specifying whether or not the heat has controls
                    capable of varying the output (as opposed to just on/off
                    control)
        """
        # In eqns below, method uses condition A rather than coldest. From
        # CALCM-01 - DAHPSE - V2.0_DRAFT13, section 4.4:
        # The Temperature Operation Limit (TOL) is defined in EN14825 as
        # “the lowest outdoor temperature at which the unit can still
        # deliver heating capacity and is declared by the manufacturer.
        # Below this temperature the heat pump will not be able to
        # deliver any heating capacity.”
        # The weather data used within this calculation method does not
        # feature a source temperature at or below the “TOL” test
        # temperature (which is -7°C to -10°C). Therefore, test data at
        # the TOL test condition is not used (Test condition “A” at -7°C
        # is sufficient).
        # TODO The above implies that the TOL test temperature data may
        #      be needed if we change the weather data from that used in
        #      DAHPSE for SAP 2012/10.2
        therm_cap_op_cond = []

        if mod_ctrl:
            # For each design flow temperature, calculate capacity at operating conditions
            # Note: Loop over sorted list of design flow temps and then index into
            #       self.__testdata, rather than looping over self.__testdata,
            #       which is unsorted and therefore may populate the lists in the
            #       wrong order.
            for dsgn_flow_temp in self.__dsgn_flow_temps:
                dsgn_flow_temp_data = self.__testdata[dsgn_flow_temp]
                # Get the source and outlet temperatures from the coldest test record
                temp_outlet_cld = Celcius2Kelvin(dsgn_flow_temp_data[0]['temp_outlet'])
                temp_source_cld = Celcius2Kelvin(dsgn_flow_temp_data[0]['temp_source'])
                # Get the thermal capacity from the coldest test record
                thermal_capacity_cld = dsgn_flow_temp_data[0]['capacity']

                thermal_capacity_op_cond \
                    = thermal_capacity_cld \
                    * ( (temp_outlet_cld * temp_source) \
                      / (temp_output * temp_source_cld) \
                      ) \
                    ** N_EXER
                therm_cap_op_cond.append(thermal_capacity_op_cond)
        else:
            # For each design flow temperature, calculate capacity at operating conditions
            # Note: Loop over sorted list of design flow temps and then index into
            #       self.__testdata, rather than looping over self.__testdata,
            #       which is unsorted and therefore may populate the lists in the
            #       wrong order.
            for dsgn_flow_temp in self.__dsgn_flow_temps:
                dsgn_flow_temp_data = self.__testdata[dsgn_flow_temp]
                # Get the source and outlet temperatures from the coldest test record
                temp_outlet_cld = Celcius2Kelvin(dsgn_flow_temp_data[0]['temp_outlet'])
                temp_source_cld = Celcius2Kelvin(dsgn_flow_temp_data[0]['temp_source'])
                # Get the thermal capacity from the coldest test record
                thermal_capacity_cld = dsgn_flow_temp_data[0]['capacity']

                D_idx = self.__find_test_record_index('D', dsgn_flow_temp)
                # Get the source and outlet temperatures for test condition D
                temp_outlet_D = Celcius2Kelvin(dsgn_flow_temp_data[D_idx]['temp_outlet'])
                temp_source_D = Celcius2Kelvin(dsgn_flow_temp_data[D_idx]['temp_source'])
                # Get the thermal capacity for test condition D
                thermal_capacity_D = dsgn_flow_temp_data[D_idx]['capacity']

                temp_diff_cld = temp_outlet_cld - temp_source_cld
                temp_diff_D = temp_outlet_D - temp_source_D
                temp_diff_op_cond = temp_output - temp_source

                thermal_capacity_op_cond \
                    = thermal_capacity_cld \
                    + (thermal_capacity_D - thermal_capacity_cld) \
                    * ( (temp_diff_cld - temp_diff_op_cond) \
                      / (temp_diff_cld - temp_diff_D) \
                      )
                therm_cap_op_cond.append(thermal_capacity_op_cond)

        # Interpolate between the values found for the different design flow temperatures
        flow_temp = Kelvin2Celcius(temp_output)
        return np.interp(flow_temp, self.__dsgn_flow_temps, therm_cap_op_cond)


class HeatPumpService:
    """ A base class for objects representing services (e.g. water heating) provided by a heat pump.

    This object encapsulates the name of the service, meaning that the system
    consuming the energy does not have to specify this on every call, and
    helping to enforce that each service has a unique name.

    Derived objects provide a place to handle parts of the calculation (e.g.
    distribution flow temperature) that may differ for different services.

    Separate subclasses need to be implemented for different types of service
    (e.g. HW and space heating). These should implement the following functions:
    - demand_energy(self, energy_demand)
    """

    def __init__(self, heat_pump, service_name, control=None):
        """ Construct a HeatPumpService object

        Arguments:
        heat_pump    -- reference to the HeatPump object providing the service
        service_name -- name of the service demanding energy from the heat pump
        control -- reference to a control object which must implement is_on() func
        """
        self.__hp = heat_pump
        self.__service_name = service_name
        self.__control = control

    def is_on(self):
        if self.__control is not None:
            service_on = self.__control.is_on()
        else:
            service_on = True
        return service_on



class HeatPumpServiceWater(HeatPumpService):
    """ An object to represent a water heating service provided by a heat pump to e.g. a cylinder.

    This object contains the parts of the heat pump calculation that are
    specific to providing hot water.
    """

    __TIME_CONSTANT_WATER = 1560

    def __init__(
            self,
            heat_pump,
            service_name,
            temp_hot_water,
            temp_return_feed,
            temp_limit_upper,
            cold_feed,
            control=None,
            ):
        """ Construct a BoilerServiceWater object

        Arguments:
        heat_pump -- reference to the HeatPump object providing the service
        service_name -- name of the service demanding energy from the heat pump
        temp_hot_water -- temperature of the hot water to be provided, in deg C
        temp_limit_upper -- upper operating limit for temperature, in deg C
        cold_feed -- reference to ColdWaterSource object
        control -- reference to a control object which must implement is_on() func
        """
        super().__init__(heat_pump, service_name, control)

        self.__temp_hot_water = Celcius2Kelvin(temp_hot_water)
        # TODO Should temp_return_feed be calculated per timestep?
        self.__temp_return_feed = Celcius2Kelvin(temp_return_feed)
        self.__temp_limit_upper = Celcius2Kelvin(temp_limit_upper)
        self.__cold_feed = cold_feed

    def demand_energy(self, energy_demand):
        """ Demand energy (in kWh) from the heat pump """
        temp_cold_water = Celcius2Kelvin(self.__cold_feed.temperature())

        service_on = self.is_on()
        if not service_on:
            energy_demand = 0.0

        return self.__hp._HeatPump__demand_energy(
            self.__service_name,
            ServiceType.WATER,
            energy_demand,
            self.__temp_hot_water,
            self.__temp_return_feed,
            self.__temp_limit_upper,
            self.__TIME_CONSTANT_WATER,
            service_on,
            temp_used_for_scaling = temp_cold_water,
            )


class HeatPumpServiceSpace(HeatPumpService):
    """ An object to represent a space heating service provided by a heat pump to e.g. radiators.

    This object contains the parts of the heat pump calculation that are
    specific to providing space heating.
    """

    __TIME_CONSTANT_SPACE = 1370

    def __init__(
            self,
            heat_pump,
            service_name,
            temp_limit_upper,
            temp_diff_emit_dsgn,
            control=None,
            ):
        """ Construct a BoilerServiceSpace object

        Arguments:
        heat_pump -- reference to the HeatPump object providing the service
        service_name -- name of the service demanding energy from the heat pump
        temp_limit_upper -- upper operating limit for temperature, in deg C
        temp_diff_emit_dsgn -- design temperature difference across the emitters, in deg C or K
        control -- reference to a control object which must implement is_on() func
        """
        super().__init__(heat_pump, service_name, control)

        self.__temp_limit_upper = Celcius2Kelvin(temp_limit_upper)
        self.__temp_diff_emit_dsgn = temp_diff_emit_dsgn

    def energy_output_max(self, temp_output):
        """ Calculate the maximum energy output of the HP, accounting for time
            spent on higher-priority services
        """
        self.__hp._HeatPump__energy_output_max(temp_output)

    def demand_energy(self, energy_demand, temp_flow, temp_return):
        """ Demand energy (in kWh) from the heat pump

        Arguments:
        energy_demand -- space heating energy demand, in kWh
        temp_flow -- flow temperature for emitters, in deg C
        temp_return -- return temperature for emitters, in deg C
        """
        service_on = self.is_on()
        if not service_on:
            energy_demand = 0.0

        return self.__hp._HeatPump__demand_energy(
            self.__service_name,
            ServiceType.SPACE,
            energy_demand,
            Celcius2Kelvin(temp_flow),
            Celcius2Kelvin(temp_return),
            self.__temp_limit_upper,
            self.__TIME_CONSTANT_SPACE,
            service_on,
            # TODO temp_spread_correction
            )


class HeatPump:
    """ An object to represent an electric heat pump """

    # From CALCM-01 - DAHPSE - V2.0_DRAFT13, section 4.5.3:
    # A minimum temperature difference of 6K between the source and sink
    # temperature is applied to prevent very high Carnot COPs entering the
    # calculation. This only arises when the temperature difference and heating
    # load is small and is unlikely to affect the calculated SPF.
    __temp_diff_limit_low = 6.0 # Kelvin

    # Fraction of the energy input dedicated to auxiliaries when on
    # TODO This is always zero for electric heat pumps, but if we want to deal
    #      with non-electric heat pumps then this will need to be altered.
    __f_aux = 0.0

    def __init__(
            self,
            hp_dict,
            energy_supply,
            energy_supply_conn_name_auxiliary,
            simulation_time,
            external_conditions,
            ):
        """ Construct a HeatPump object

        Arguments:
        hp_dict -- dictionary of heat pump characteristics, with the following elements:
            - test_data -- EN 14825 test data dictionary
            - SourceType -- string specifying heat source type, one of:
                - "Ground"
                - "OutsideAir"
                - "ExhaustAirMEV"
                - "ExhaustAirMVHR"
                - "ExhaustAirMixed"
                - "WaterGround"
                - "WaterSurface"
            - SinkType -- string specifying heat distribution type, one of:
                - "Air"
                - "Water"
            - BackupCtrlType -- string specifying control arrangement for backup
                                heater, one of:
                - "None" -- backup heater disabled or not present
                - "TopUp" -- when heat pump has insufficient capacity, backup
                             heater will supplement the heat pump
                - "Substitute" -- when heat pump has insufficient capacity, backup
                                  heater will provide all the heat required, and
                                  heat pump will switch off
            - modulating_control -- boolean specifying whether or not the heat
                                    has controls capable of varying the output
                                    (as opposed to just on/off control)
            - time_constant_onoff_operation
                -- a characteristic parameter of the heat pump, due to the
                   inertia of the on/off transient
            - temp_return_feed_max -- maximum allowable temperature of the
                                      return feed, in Celsius
            - temp_lower_operating_limit
                -- minimum source temperature at which the heat pump can operate,
                   in Celsius
            - min_temp_diff_flow_return_for_hp_to_operate
                -- minimum difference between flow and return temperatures
                   required for the HP to operate, in Celsius or Kelvin
            - var_flow_temp_ctrl_during_test
                -- boolean specifying whether or not variable flow temperature
                   control was enabled during the EN 14825 tests
            - power_heating_circ_pump -- power (kW) of central heating circulation pump
            - power_source_circ_pump
                -- power (kW) of source ciculation pump or fan circulation when not
                   implicit in CoP measurements
        energy_supply -- reference to EnergySupply object
        energy_supply_conn_name_auxiliary
            -- name to be used for EnergySupplyConnection object for auxiliary energy
        simulation_time -- reference to SimulationTime object
        external_conditions -- reference to ExternalConditions object

        Other variables:
        energy_supply_connections
            -- dictionary with service name strings as keys and corresponding
               EnergySupplyConnection objects as values
        energy_supply_connection_aux -- EnergySupplyConnection object for auxiliary energy
        test_data -- HeatPumpTestData object
        """
        self.__energy_supply = energy_supply
        self.__simulation_time = simulation_time
        self.__external_conditions = external_conditions

        self.__energy_supply_connections = {}
        self.__energy_supply_connection_aux \
            = self.__energy_supply.connection(energy_supply_conn_name_auxiliary)
        self.__test_data = HeatPumpTestData(hp_dict['test_data'])

        self.__service_results = []
        self.__total_time_running_current_timestep = 0.0

        # Assign hp_dict elements to member variables of this class
        self.__source_type = SourceType.from_string(hp_dict['SourceType'])
        self.__sink_type = SinkType.from_string(hp_dict['SinkType'])
        self.__backup_ctrl = BackupCtrlType.from_string(hp_dict['BackupCtrlType'])
        self.__modulating_ctrl = bool(hp_dict['modulating_control'])
        self.__time_constant_onoff_operation = float(hp_dict['time_constant_onoff_operation'])
        self.__temp_return_feed_max = Celcius2Kelvin(float(hp_dict['temp_return_feed_max']))
        self.__temp_lower_op_limit = Celcius2Kelvin(float(hp_dict['temp_lower_operating_limit']))
        self.__temp_diff_flow_return_min \
            = float(hp_dict['min_temp_diff_flow_return_for_hp_to_operate'])
        self.__var_flow_temp_ctrl_during_test = bool(hp_dict['var_flow_temp_ctrl_during_test'])
        self.__power_heating_circ_pump = hp_dict['power_heating_circ_pump']
        self.__power_source_circ_pump = hp_dict['power_source_circ_pump']

    def __create_service_connection(self, service_name):
        """ Return a HeatPumpService object """
        # Check that service_name is not already registered
        if service_name in self.__energy_supply_connections.keys():
            sys.exit("Error: Service name already used: "+service_name)
            # TODO Exit just the current case instead of whole program entirely?

        # Set up EnergySupplyConnection for this service
        self.__energy_supply_connections[service_name] = \
            self.__energy_supply.connection(service_name)

    def create_service_hot_water(
            self,
            service_name,
            temp_hot_water,
            temp_limit_upper,
            cold_feed,
            control=None,
            ):
        """ Return a HeatPumpServiceWater object and create an EnergySupplyConnection for it

        Arguments:
        service_name -- name of the service demanding energy from the boiler
        temp_hot_water -- temperature of the hot water to be provided, in deg C
        temp_limit_upper -- upper operating limit for temperature, in deg C
        cold_feed -- reference to ColdWaterSource object
        control -- reference to a control object which must implement is_on() func
        """
        self.__create_service_connection(service_name)
        return HeatPumpServiceWater(
            self,
            service_name,
            temp_hot_water,
            temp_limit_upper,
            cold_feed,
            control,
            )

    def create_service_space_heating(
            self,
            service_name,
            temp_limit_upper,
            temp_diff_emit_dsgn,
            control=None,
            ):
        """ Return a HeatPumpServiceSpace object and create an EnergySupplyConnection for it

        Arguments:
        service_name -- name of the service demanding energy from the heat pump
        temp_limit_upper -- upper operating limit for temperature, in deg C
        temp_diff_emit_dsgn -- design temperature difference across the emitters, in deg C or K
        control -- reference to a control object which must implement is_on() func
        """
        self.__create_service_connection(service_name)
        return HeatPumpServiceSpace(
            self,
            service_name,
            temp_limit_upper,
            temp_diff_emit_dsgn,
            control,
            )

    def __get_temp_source(self):
        """ Get source temp according to rules in CALCM-01 - DAHPSE - V2.0_DRAFT13, 3.1.1 """
        if self.__source_type == SourceType.GROUND:
            # Subject to max source temp of 8 degC and min of 0 degC
            temp_ext = self.__external_conditions.temperature()
            temp_source = max(0, min(8, temp_ext * 0.25806 + 2.8387))
        elif self.__source_type == SourceType.OUTSIDE_AIR:
            temp_source = self.__external_conditions.temperature()
        # elif self.__source_type == SourceType.EXHAUST_AIR_MEV:
        #     # TODO Get from internal air temp of zone?
        # elif self.__source_type == SourceType.EXHAUST_AIR_MVHR:
        #     # TODO Get from internal air temp of zone?
        # elif self.__source_type == SourceType.EXHAUST_AIR_MIXED:
        #     # TODO
        # elif self.__source_type == SourceType.WATER_GROUND:
        #     # TODO
        # elif self.__source_type == SourceType.WATER_SURFACE:
        #     # TODO
        else:
            # If we reach here, then earlier input validation has failed, or a
            # SourceType option is missing above.
            sys.exit('SourceType not valid.')

        return Celcius2Kelvin(temp_source)

    def __thermal_capacity_op_cond(self, temp_output, temp_source):
        """ Calculate the thermal capacity of the heat pump at operating conditions

        Based on CALCM-01 - DAHPSE - V2.0_DRAFT13, section 4.4
        """
        if not self.__source_type == SourceType.OUTSIDE_AIR \
        and not self.__var_flow_temp_ctrl_during_test:
            thermal_capacity_op_cond = self.__test_data.average_capacity(temp_output)
        else:
            thermal_capacity_op_cond \
                = self.__test_data.capacity_op_cond_if_not_air_source(
                    temp_output,
                    temp_source,
                    self.__modulating_ctrl,
                    )

        return thermal_capacity_op_cond

    def __energy_output_max(self, temp_output):
        """ Calculate the maximum energy output of the HP, accounting for time
            spent on higher-priority services

        Note: Call via a HeatPumpService object, not directly.
        """
        timestep = self.__simulation_time.timestep()
        time_available = timestep - self.__total_time_running_current_timestep
        temp_source = self.__get_temp_source()
        power_max = self.__thermal_capacity_op_cond(temp_output, temp_source)
        return power_max * time_available

    def __cop_deg_coeff_op_cond(
            self,
            service_type,
            temp_output, # Kelvin
            temp_source, # Kelvin
            temp_spread_correction,
            ):
        """ Calculate CoP and degradation coefficient at operating conditions """

        # TODO Make if/elif/else chain exhaustive?
        if not self.__source_type == SourceType.OUTSIDE_AIR \
        and not self.__var_flow_temp_ctrl_during_test:
            cop_op_cond \
                = temp_spread_correction \
                * self.__test_data.cop_op_cond_if_not_air_source(
                    self.__temp_diff_limit_low,
                    self.__external_conditions.temperature(),
                    temp_source,
                    temp_output,
                    )
            deg_coeff_op_cond = self.__test_data.average_degradation_coeff(temp_output)
        else:
            carnot_cop_op_cond = carnot_cop(temp_source, temp_output, self.__temp_diff_limit_low)
            # Get exergy load ratio at operating conditions and exergy load ratio,
            # exergy efficiency and degradation coeff at test conditions above and
            # below operating conditions
            lr_op_cond = self.__test_data.lr_op_cond(temp_output, temp_source, carnot_cop_op_cond)
            lr_below, lr_above, eff_below, eff_above, deg_coeff_below, deg_coeff_above \
                = self.__test_data.lr_eff_degcoeff_either_side_of_op_cond(temp_output, lr_op_cond)

            # CALCM-01 - DAHPSE - V2.0_DRAFT13, section 4.5.4
            # Get exergy efficiency by interpolating between figures above and
            # below operating conditions
            exer_eff_op_cond \
                = eff_below \
                + (eff_below - eff_above) \
                * (lr_op_cond - lr_below) \
                / (lr_below - lr_above)

            # CALCM-01 - DAHPSE - V2.0_DRAFT13, section 4.5.5
            # Note: DAHPSE method document section 4.5.5 doesn't have
            # temp_spread_correction in formula below. However, section 4.5.7
            # states that the correction factor is to be applied to the CoP.
            cop_op_cond = max(1.0, exer_eff_op_cond * carnot_cop_op_cond * temp_spread_correction)

            if self.__sink_type == SinkType.AIR and service_type != ServiceType.WATER:
                limit_upper = 0.25
            else:
                limit_lower = 1.0

            if self.__sink_type == SinkType.AIR and service_type != ServiceType.WATER:
                limit_lower = 0.0
            else:
                limit_lower = 0.9

            if lr_below == lr_above:
                deg_coeff_op_cond = deg_coeff_below
            else:
                deg_coeff_op_cond \
                    = deg_coeff_below \
                    + (deg_coeff_below - deg_coeff_above) \
                    * (lr_op_cond - lr_below) \
                    / (lr_below - lr_above)

            deg_coeff_op_cond = max(min(deg_coeff_op_cond, limit_upper), limit_lower)

        return cop_op_cond, deg_coeff_op_cond

    def __energy_output_limited(
            self,
            energy_output_required,
            temp_output,
            temp_used_for_scaling,
            temp_limit_upper
            ):
        """ Calculate energy output limited by upper temperature """
        if temp_output > temp_limit_upper:
        # If required output temp is above upper limit
            if temp_output == temp_used_for_scaling:
            # If flow and return temps are equal
                return energy_output_required
            else:
            # If flow and return temps are not equal
                if (temp_limit_upper - temp_used_for_scaling) >= self.__temp_diff_flow_return_min:
                # If max. achievable temp diff is at least the min required
                # for the HP to operate.
                    return \
                          energy_output_required \
                        * (temp_limit_upper - temp_used_for_scaling) \
                        / (temp_output - temp_used_for_scaling)
                else:
                # If max. achievable temp diff is less than the min required
                # for the HP to operate.
                    return 0.0
        else:
        # If required output temp is below upper limit
            return energy_output_required

    def __demand_energy(
            self,
            service_name,
            service_type,
            energy_output_required,
            temp_output, # Kelvin
            temp_return_feed, # Kelvin
            temp_limit_upper, # Kelvin
            time_constant_for_service,
            service_on, # bool - is service allowed to run?
            temp_spread_correction=1.0,
            temp_used_for_scaling=None,
            ):
        """ Calculate energy required by heat pump to satisfy demand for the service indicated.

        Note: Call via a HeatPumpService object, not directly.
        """
        if temp_used_for_scaling is None:
            temp_used_for_scaling = temp_return_feed

        timestep = self.__simulation_time.timestep()

        energy_output_limited = self.__energy_output_limited(
            energy_output_required,
            temp_output,
            temp_used_for_scaling,
            temp_limit_upper,
            )

        temp_source = self.__get_temp_source() # Kelvin
        # From here onwards, output temp to be used is subject to the upper limit
        temp_output = min(temp_output, temp_limit_upper) # Kelvin

        # Get thermal capacity, CoP and degradation coeff at operating conditions
        thermal_capacity_op_cond = self.__thermal_capacity_op_cond(temp_output, temp_source)
        cop_op_cond, deg_coeff_op_cond \
            = self.__cop_deg_coeff_op_cond(temp_output, temp_source, temp_spread_correction)

        # Calculate running time of HP
        time_running_current_service = min( \
            energy_output_limited / thermal_capacity_op_cond,
            timestep - self.__total_time_running_current_timestep
            )
        self.__total_time_running_current_timestep += time_running_current_service

        # Calculate load ratio
        load_ratio = time_running_current_service / timestep
        if self.__modulating_ctrl:
            # Note: min modulation rates are always for 35 and 55
            # TODO What if we only have the rate at one of these temps (e.g. a low-
            #      temperature heat pump that does not go up to 55degC output)?
            load_ratio_continuous_min \
                = (min(max(temp_output, 35.0), 55.0) - 35.0) \
                / (55.0 - 35.0) \
                * self.__min_modulation_rate_35 \
                + (1.0 - (min(max(temp_output, 35.0), 55.0) - 35.0)) \
                / (55.0 - 35.0) \
                * self.__min_modulation_rate_55
        else:
            # On/off heat pump cannot modulate below maximum power
            load_ratio_continuous_min = 1.0

        # Determine whether or not HP is operating in on/off mode
        hp_operating_in_onoff_mode = (load_ratio > 0.0 and load_ratio < load_ratio_continuous_min)

        compressor_power_full_load = thermal_capacity_op_cond / cop_op_cond

        # CALCM-01 - DAHPSE - V2.0_DRAFT13, section 4.5.10, step 1:
        compressor_power_min_load \
            = compressor_power_full_load * load_ratio_continuous_min
        # CALCM-01 - DAHPSE - V2.0_DRAFT13, section 4.5.10, step 2:
        # TODO The value calculated here is only used in some code branches
        #      later. In future, rearrange this function so that this is only
        #      calculated when needed.
        if load_ratio >= load_ratio_continuous_min:
            power_used_due_to_inertia_effects = 0.0
        else:
            power_used_due_to_inertia_effects \
                = compressor_power_min_load \
                * self.__time_constant_onoff_operation \
                * load_ratio \
                * (1.0 - load_ratio) \
                / time_constant_for_service

        # Evaluate boolean conditions that may trigger backup heater
        # TODO Consider moving some of these checks earlier or to HeatPumpService
        #      classes. May be able to skip a lot of the calculation.
        below_min_ext_temp = (temp_source <= self.__temp_lower_op_limit)
        inadequate_capacity = (energy_output_required > thermal_capacity_op_cond * timestep)
        above_temp_return_feed_max = (temp_return_feed > self.__temp_return_feed_max)

        use_backup_heater_only \
            = self.__backup_ctrl != BackupCtrlType.NONE \
              and ( below_min_ext_temp or above_temp_return_feed_max
                 or (inadequate_capacity and self.__backup_ctrl == BackupCtrlType.SUBSTITUTE))
        # TODO For hybrid HPs: Replace inadequate_capacity in use_backup_heater_only
        #      condition with (inadequate_capacity or HP not cost effective)

        # Calculate energy delivered by HP and energy input
        if use_backup_heater_only or not service_on:
            energy_delivered_HP = 0.0
            energy_input_HP = 0.0
        else:
            # Backup heater not providing entire energy requirement
            energy_delivered_HP = thermal_capacity_op_cond * time_running_current_service

            if hp_operating_in_onoff_mode:
                # TODO Why does the divisor below differ for DHW from warm air HPs?
                if service_type == ServiceType.WATER and self.__sink_type == SinkType.AIR:
                    energy_input_HP_divisor \
                        = 1.0 \
                        - deg_coeff_op_cond \
                        * (1.0 - load_ratio / load_ratio_continuous_min)
                else:
                    energy_input_HP_divisor = 1.0

                # TODO In the eqn below, should compressor_power_full_load actually
                #      be compressor_power_min_load? In this code branch the HP is
                #      operating in on/off mode, so presumably cycling between off
                #      and min load rather than full load.
                # Note: Energy_ancillary_when_off should also be included in the
                # energy input for on/off operation, but at this stage we have
                # not calculated whether a lower-priority service will run
                # instead, so this will need to be calculated later and
                # (energy_ancillary_when_off / eqn_denom) added to the energy
                # input
                energy_input_HP \
                    = ( ( compressor_power_full_load * (1.0 + self.__f_aux) \
                        + power_used_due_to_inertia_effects \
                        ) \
                      * time_running_current_service \
                      ) \
                    / energy_input_HP_divisor
            else:
                # If not operating in on/off mode
                energy_input_HP = energy_delivered_HP / cop_op_cond

        # Calculate energy delivered by backup heater
        # TODO Add a power limit for the backup heater, or call another heating
        #      system object. For now, assume no power limit.
        if self.__backup_ctrl == BackupCtrlType.NONE or not service_on:
            energy_delivered_backup = 0.0
        elif self.__backup_ctrl == BackupCtrlType.TOPUP \
        or self.__backup_ctrl == BackupCtrlType.SUBSTITUTE:
            energy_delivered_backup = max(energy_output_required - energy_delivered_HP, 0.0)
        else:
            sys.exit('Invalid BackupCtrlType')

        # Calculate energy input to backup heater
        # TODO Account for backup heater efficiency, or call another heating
        #      system object. For now, assume 100% efficiency
        energy_input_backup = energy_delivered_backup

        # Calculate total energy delivered and input
        energy_delivered_total = energy_delivered_HP + energy_delivered_backup
        energy_input_total = energy_input_HP + energy_input_backup

        # Save results that are needed later (in the timestep_end function)
        self.__service_results.append({
            'service_name': service_name,
            'service_type': service_type,
            'service_on': service_on,
            'time_running': time_running_current_service,
            'deg_coeff_op_cond': deg_coeff_op_cond,
            'compressor_power_min_load': compressor_power_min_load,
            'load_ratio_continuous_min': load_ratio_continuous_min,
            'load_ratio': load_ratio,
            'use_backup_heater_only': use_backup_heater_only,
            'hp_operating_in_onoff_mode': hp_operating_in_onoff_mode,
            'energy_input_HP_divisor': energy_input_HP_divisor,
            })

        # Feed/return results to other modules
        self.__energy_supply_connections[service_name].demand_energy(energy_input_total)
        return energy_delivered_total

    def __calc_ancillary_energy(self, timestep, time_remaining_current_timestep):
        """ Calculate ancillary energy for each service """
        for service_no, service_data in self.__service_results.enumerate():
            # Unpack results of previous calculations for this service
            service_name = service_data['service_name']
            service_type = service_data['service_type']
            service_on = service_data['service_on']
            time_running_current_service = service_data['time_running']
            deg_coeff_op_cond = service_data['deg_coeff_op_cond']
            compressor_power_min_load = service_data['compressor_power_min_load']
            load_ratio_continuous_min = service_data['load_ratio_continuous_min']
            load_ratio = service_data['load_ratio']
            use_backup_heater_only = service_data['use_backup_heater_only']
            hp_operating_in_onoff_mode = service_data['hp_operating_in_onoff_mode']
            energy_input_HP_divisor = service_data['energy_input_HP_divisor']

            time_running_subsequent_services \
                = sum([ \
                    data['time_running'] \
                    for data in self.__service_results[service_no + 1 :] \
                    ])

            if service_on \
            and time_running_current_service > 0.0 and not time_running_subsequent_services > 0.0 \
            and not (self.__sink_type == SinkType.AIR and service_type == ServiceType.WATER):
                energy_ancillary_when_off \
                    = (1.0 - deg_coeff_op_cond) \
                    * (compressor_power_min_load / load_ratio_continuous_min) \
                    * max(
                        ( time_remaining_current_timestep \
                        - load_ratio / load_ratio_continuous_min * timestep
                        ),
                        0.0
                        )
            else:
                energy_ancillary_when_off = 0.0

            if not use_backup_heater_only and hp_operating_in_onoff_mode:
                energy_input_HP = energy_ancillary_when_off / energy_input_HP_divisor
            else:
                energy_input_HP = 0.0

            self.__energy_supply_connections[service_name].demand_energy(energy_input_HP)

    def __calc_auxiliary_energy(self, timestep, time_remaining_current_timestep):
        # Energy used by pumps
        # TODO This could be calculated separately for each service and included
        #      in those totals, rather than auxiliary
        energy_aux \
            = self.__total_time_running_current_timestep \
            * (self.__power_heating_circ_pump + self.__power_source_circ_pump)

        # Retrieve control settings for this timestep
        for service_data in self.__service_results:
            if service_data['service_type'] == ServiceType.SPACE:
                heating_profile_on = service_data['service_on']
            elif service_data['service_type'] == ServiceType.WATER:
                water_profile_on = service_data['service_on']
            else:
                sys.exit('ServiceType not recognised')

        # Energy used in standby and crankcase heater mode
        # TODO Crankcase heater mode appears to be relevant only when HP is
        #      available to provide space heating. Therefore, it could be added
        #      to space heating energy consumption instead of auxiliary
        # TODO Standby power is only relevant when at least one service is
        #      available. Therefore, it could be split between the available
        #      services rather than treated as auxiliary
        if heating_profile_on and water_profile_on:
            energy_aux \
               += time_remaining_current_timestep \
                * (self.__power_standby + self.__power_crankcase_heater_mode)
        elif not heating_profile_on and water_profile_on:
            energy_aux += time_remaining_current_timestep * self.__power_standby
        # Energy used in off mode
        elif not heating_profile_on and not water_profile_on:
            energy_aux += timestep * self.__power_off_mode
        else:
            sys.exit('No aux energy calc defined for space heating on and water heating off')

        self.__energy_supply_connection_aux.demand_energy(energy_aux)

    def timestep_end(self):
        """ Calculations to be done at the end of each timestep """
        timestep = self.__simulation_time.timestep()
        time_remaining_current_timestep = timestep - self.__total_time_running_current_timestep

        self.__calc_ancillary_energy(timestep, time_remaining_current_timestep)
        self.__calc_auxiliary_energy(timestep, time_remaining_current_timestep)

        # Variables below need to be reset at the end of each timestep.
        self.__total_time_running_current_timestep = 0.0
        self.__service_results = []
