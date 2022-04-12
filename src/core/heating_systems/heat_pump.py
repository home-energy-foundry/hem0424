#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides objects to represent heat pumps and heat pump test data.
The calculations are based on the DAHPSE method developed for generating PCDB
entries for SAP 2012 and SAP 10. DAHPSE was based on a draft of
BS EN 15316-4-2:2017 and is described in the SAP calculation method CALCM-01.
"""

# Standard library imports
import sys


class HeatPumpTestData:
    """ An object to represent EN 14825 test data for a heat pump.

    This object stores the data and provides functions to look up values from
    the correct data records for the conditions being modelled.
    """

    def __init__(self, hp_testdata_dict):
        """ Construct a HeatPumpTestData object

        Arguments:
        hp_testdata_dict -- dictionary of heat pump test data, with the following elements:
            TODO List elements and their definitions
        """
        pass # TODO Implement this function


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
