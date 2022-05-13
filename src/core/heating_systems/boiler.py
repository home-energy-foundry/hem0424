#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides objects to represent boilers. The calculations are based
on the hourly method developed for calculating efficiency improvements for
different classes of boiler controls in SAP 10 Appendix D2.2 (described in the
SAP 10 technical paper S10TP-12). This in turn was based on a combination of
the DAHPSE method for heat pumps (itself based on a draft of
BS EN 15316-4-2:2017 and described in the SAP calculation method CALCM-01) and
the Energy Balance Validation (EBV) method (described in the SAP 2009 technical
paper STP09/B02).
"""

# Standard library imports
import sys


class BoilerService:
    """ An object to represent a service (e.g. water heating) provided by a boiler.

    This object encapsulates the name of the service, meaning that the system
    consuming the energy does not have to specify this on every call, and
    helping to enforce that each service has a unique name.

    This object also provides a place to handle parts of the calculation (e.g.
    distribution flow temperature) that may differ for different services.

    TODO Separate subclasses for different types of service (HW and space heating)?
    """

    def __init__(self, boiler, service_name):
        """ Construct a BoilerService object

        Arguments:
        boiler       -- reference to the Boiler object providing the service
        service_name -- name of the service demanding energy from the boiler
        """
        self.__boiler = boiler
        self.__service_name = service_name

    def demand_energy(self, energy_demand):
        """ Demand energy (in kWh) from the boiler """
        # TODO Calculate required flow temperature
        # TODO Call self.__boiler._Boiler__demand_energy func
        return 0.0 # TODO Return energy supplied


class Boiler:
    """ An object to represent a boiler """

    def __init__(self, boiler_dict, energy_supply, simulation_time):
        """ Construct a Boiler object

        Arguments:
        boiler_dict -- dictionary of boiler characteristics, with the following elements:
            TODO List elements and their definitions
        energy_supply -- reference to EnergySupply object
        simulation_time -- reference to SimulationTime object

        Other variables:
        energy_supply_connections
            -- dictionary with service name strings as keys and corresponding
               EnergySupplyConnection objects as values
        """
        self.__energy_supply = energy_supply
        self.__simulation_time = simulation_time

        self.__energy_supply_connections = {}

        # TODO Assign boiler_dict elements to member variables of this class

    def service(self, service_name):
        """ Return a BoilerService object """
        # Check that service_name is not already registered
        if service_name in self.__energy_supply_connections.keys():
            sys.exit("Error: Service name already used: "+service_name)
            # TODO Exit just the current case instead of whole program entirely?

        # Set up EnergySupplyConnection for this service
        self.__energy_supply_connections[service_name] = \
            self.__energy_supply.connection(service_name)

        return BoilerService(self, service_name)

    def __demand_energy(self, service_name, required_output, required_flow_temp):
        """ Calculate energy required by boiler to satisfy demand for the service indicated.

        Note: Call via a BoilerService object, not directly.
        """
        # TODO Call self.__energy_supply_connections[service_name].demand_energy(energy_demand)
        pass # TODO Implement this function
