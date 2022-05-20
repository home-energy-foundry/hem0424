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

# Third-party imports
import numpy as np

# Local imports
from core.units import Celcius2Kelvin

# Constants
N_EXER = 3.0


def carnot_cop(temp_source, temp_outlet):
    """ Calculate Carnot CoP based on source and outlet temperatures (in Kelvin) """
    return temp_outlet / (temp_outlet - temp_source)


class HeatPumpTestData:
    """ An object to represent EN 14825 test data for a heat pump.

    This object stores the data and provides functions to look up values from
    the correct data records for the conditions being modelled.
    """

    def __init__(self, hp_testdata_dict_list):
        """ Construct a HeatPumpTestData object

        Arguments:
        hp_testdata_dict_list
            -- list of dictionaries of heat pump test data, each with the following elements:
                - test_letter
                - capacity
                - cop
                - degradation_coeff
                - design_flow_temp
                - temp_outlet
                - temp_source
                - temp_test
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

        # Sort the list of design flow temps
        self.__dsgn_flow_temps = sorted(self.__dsgn_flow_temps)

        # Sort the records in order of test temperature from low to high
        for dsgn_flow_temp, data in self.__testdata.items():
            data.sort(key=lambda sublist: sublist['temp_test'])

        # TODO Calculate derived variables which are not time-dependent
        for dsgn_flow_temp in self.__dsgn_flow_temps:
            for data in self.__testdata[dsgn_flow_temp]:
                # Get the source and outlet temperatures from the test record
                temp_source = Celcius2Kelvin(data['temp_source'])
                temp_outlet = Celcius2Kelvin(data['temp_outlet'])

                # Calculate the Carnot CoP and add to the test record
                data['carnot_cop'] = carnot_cop(temp_source, temp_outlet)

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

    def __data_coldest_conditions(self, data_item_name, flow_temp):
        # TODO What do we do if flow_temp is outside the range of design flow temps provided?

        if len(self.__dsgn_flow_temps) == 1:
            # If there is data for only one design flow temp, use that
            return self.__testdata[self.__dsgn_flow_temps[0]][0][data_item_name]

        # Interpolate between the outlet temps at each design flow temp
        data_list = []
        for dsgn_flow_temp in self.__dsgn_flow_temps:
            data_list.append(self.__testdata[dsgn_flow_temp][0][data_item_name])

        return np.interp(flow_temp, self.__dsgn_flow_temps, data_list)

    def carnot_cop_coldest_conditions(self, flow_temp):
        """ Return Carnot CoP at coldest test condition, interpolated between design flow temps """
        return self.__data_coldest_conditions('carnot_cop', flow_temp)

    def outlet_temp_coldest_conditions(self, flow_temp):
        """
        Return outlet temp, in Kelvin, at coldest test condition, interpolated
        between design flow temps.
        """
        return Celcius2Kelvin(self.__data_coldest_conditions('temp_outlet', flow_temp))

    def source_temp_coldest_conditions(self, flow_temp):
        """
        Return source temp, in Kelvin, at coldest test condition, interpolated
        between design flow temps.
        """
        return Celcius2Kelvin(self.__data_coldest_conditions('temp_source', flow_temp))


class HeatPumpService:
    """ An object to represent a service (e.g. water heating) provided by a heat pump.

    This object encapsulates the name of the service, meaning that the system
    consuming the energy does not have to specify this on every call, and
    helping to enforce that each service has a unique name.

    This object also provides a place to handle parts of the calculation (e.g.
    distribution flow temperature) that may differ for different services.

    TODO Separate subclasses for different types of service (HW and space heating)?
    """

    def __init__(self, heat_pump, service_name):
        """ Construct a HeatPumpService object

        Arguments:
        heat_pump    -- reference to the HeatPump object providing the service
        service_name -- name of the service demanding energy from the heat pump
        """
        self.__hp = heat_pump
        self.__service_name = service_name

    def demand_energy(self, energy_demand):
        """ Demand energy (in kWh) from the heat pump """
        # TODO Calculate required flow temperature
        # TODO Call self.__hp._HeatPump__demand_energy func
        return 0.0 # TODO Return energy supplied


class HeatPump:
    """ An object to represent an electric heat pump """

    def __init__(self, hp_dict, energy_supply, simulation_time):
        """ Construct a HeatPump object

        Arguments:
        hp_dict -- dictionary of heat pump characteristics, with the following elements:
            - test_data -- EN 14825 test data dictionary
            TODO List other elements and their definitions
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

        # TODO Assign hp_dict elements to member variables of this class

    def service(self, service_name):
        """ Return a HeatPumpService object """
        # Check that service_name is not already registered
        if service_name in self.__energy_supply_connections.keys():
            sys.exit("Error: Service name already used: "+service_name)
            # TODO Exit just the current case instead of whole program entirely?

        # Set up EnergySupplyConnection for this service
        self.__energy_supply_connections[service_name] = \
            self.__energy_supply.connection(service_name)

        return HeatPumpService(self, service_name)

    def __demand_energy(self, service_name, required_output, required_flow_temp):
        """ Calculate energy required by heat pump to satisfy demand for the service indicated.

        Note: Call via a HeatPumpService object, not directly.
        """
        # TODO Call self.__energy_supply_connections[service_name].demand_energy(energy_demand)
        pass # TODO Implement this function
