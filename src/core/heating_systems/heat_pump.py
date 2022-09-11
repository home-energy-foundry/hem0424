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


# Free functions

def carnot_cop(temp_source, temp_outlet):
    """ Calculate Carnot CoP based on source and outlet temperatures (in Kelvin) """
    return temp_outlet / (temp_outlet - temp_source)


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

    def __data_at_test_condition(self, data_item_name, test_condition, flow_temp):
        """ Return value at specified test condition, interpolated between design flow temps """
        # TODO What do we do if flow_temp is outside the range of design flow temps provided?

        def find_test_record_index(dsgn_flow_temp):
            """ Find position of specified test condition in list """
            if test_condition == 'cld':
                # Coldest test condition is first in list
                return 0
            for index, test_record in enumerate(self.__testdata[dsgn_flow_temp]):
                if test_record['test_letter'] == test_condition:
                    return index

        if len(self.__dsgn_flow_temps) == 1:
            # If there is data for only one design flow temp, use that
            idx = find_test_record_index(self.__dsgn_flow_temps[0])
            return self.__testdata[self.__dsgn_flow_temps[0]][idx][data_item_name]

        # Interpolate between the values at each design flow temp
        data_list = []
        for dsgn_flow_temp in self.__dsgn_flow_temps:
            idx = find_test_record_index(dsgn_flow_temp)
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
                if test_record['theoretical_load_ratio'] >= exergy_lr_op_cond:
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
            min_temp_diff_emit,
            temp_ext,
            temp_source,
            temp_output,
            ):
        """ Calculate CoP at operating conditions when heat pump is not air-source

        Arguments:
        min_temp_diff_emit -- minimum temperature difference above the room
                              temperature for emitters to operate, in
                              Celcius/Kelvin
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
                / ( temp_outlet_cld * max( (temp_output - temp_source), min_temp_diff_emit))
            cop_op_cond.append(cop_operating_conditions)

        if len(self.__dsgn_flow_temps) == 1:
            # If there is data for only one design flow temp, use that
            return cop_op_cond[0]

        # Interpolate between the values found for the different design flow temperatures
        flow_temp = Kelvin2Celcius(temp_output)
        return np.interp(flow_temp, self.__dsgn_flow_temps, cop_op_cond)


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

    def __init__(self, heat_pump, service_name):
        """ Construct a HeatPumpService object

        Arguments:
        heat_pump    -- reference to the HeatPump object providing the service
        service_name -- name of the service demanding energy from the heat pump
        """
        self.__hp = heat_pump
        self.__service_name = service_name


class HeatPumpServiceWater(HeatPumpService):
    """ An object to represent a water heating service provided by a heat pump to e.g. a cylinder.

    This object contains the parts of the heat pump calculation that are
    specific to providing hot water.
    """

    def __init__(self, heat_pump, service_name, temp_hot_water, temp_limit_upper, cold_feed):
        """ Construct a BoilerServiceWater object

        Arguments:
        heat_pump -- reference to the HeatPump object providing the service
        service_name -- name of the service demanding energy from the heat pump
        temp_hot_water -- temperature of the hot water to be provided, in deg C
        temp_limit_upper -- upper operating limit for temperature, in deg C
        cold_feed -- reference to ColdWaterSource object
        """
        super().__init__(heat_pump, service_name)

        self.__temp_hot_water = temp_hot_water
        self.__temp_limit_upper = temp_limit_upper
        self.__cold_feed = cold_feed

    def demand_energy(self, energy_demand):
        """ Demand energy (in kWh) from the heat pump """
        temp_cold_water = self.__cold_feed.temperature()

        return self.__hp._HeatPump__demand_energy(
            self.__service_name,
            energy_demand,
            self.__temp_hot_water,
            temp_cold_water,
            self.__temp_limit_upper,
            )


class HeatPump:
    """ An object to represent an electric heat pump """

    def __init__(self, hp_dict, energy_supply, simulation_time):
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
        energy_supply -- reference to EnergySupply object
        simulation_time -- reference to SimulationTime object

        Other variables:
        energy_supply_connections
            -- dictionary with service name strings as keys and corresponding
               EnergySupplyConnection objects as values
        test_data -- HeatPumpTestData object
        """
        self.__energy_supply = energy_supply
        self.__simulation_time = simulation_time

        self.__energy_supply_connections = {}
        self.__test_data = HeatPumpTestData(hp_dict['test_data'])

        # Assign hp_dict elements to member variables of this class
        self.__source_type = SourceType.from_string(hp_dict['SourceType'])
        self.__sink_type = SinkType.from_string(hp_dict['SinkType'])

    def service(self, service_name, service_type):
        """ Return a HeatPumpService object """
        # Check that service_name is not already registered
        if service_name in self.__energy_supply_connections.keys():
            sys.exit("Error: Service name already used: "+service_name)
            # TODO Exit just the current case instead of whole program entirely?

        # Set up EnergySupplyConnection for this service
        self.__energy_supply_connections[service_name] = \
            self.__energy_supply.connection(service_name)

        if service_type == 'W': # Hot water cylinder/tank
            return HeatPumpServiceWater(self, service_name)
        else:
            sys.exit(service_name + ': service type (' + str(service_type) + ') not recognised.')

    def __demand_energy(
            self,
            service_name,
            energy_output_required,
            temp_flow_required,
            temp_return_feed,
            temp_limit_upper,
            ):
        """ Calculate energy required by heat pump to satisfy demand for the service indicated.

        Note: Call via a HeatPumpService object, not directly.
        """
        # TODO Call self.__energy_supply_connections[service_name].demand_energy(energy_demand)
        pass # TODO Implement this function
