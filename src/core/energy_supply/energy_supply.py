#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains objects that represent energy supplies such as mains gas,
mains electricity or other fuels (e.g. LPG, wood pellets).
"""

# Standard library inputs
import sys


class EnergySupplyConnection:
    """ An object to represent the connection of a system that consumes energy to the energy supply

    This object encapsulates the name of the connection, meaning that the
    system consuming the energy does not have to specify these on every call,
    and helping to enforce that each connection to a single supply has a unique
    name.
    """

    def __init__(self, energy_supply, end_user_name):
        """ Construct an EnergySupplyConnection object

        Arguments:
        energy_supply -- reference to the EnergySupply object that the connection is to
        end_user_name -- name of the system (and end use, where applicable)
                         consuming energy from this connection
        """
        self.__energy_supply = energy_supply
        self.__end_user_name = end_user_name

    def demand_energy(self, amount_demanded):
        """ Forwards the amount of energy demanded (in kWh) to the relevant EnergySupply object """
        self.__energy_supply._EnergySupply__demand_energy(self.__end_user_name, amount_demanded)


class EnergySupply:
    """ An object to represent an energy supply, and to report energy consumption """
    # TODO Do we need a subclass for electricity supply specifically, to
    #      account for generators? Or do we just handle it in this object and
    #      have an empty list of generators when not electricity?

    def __init__(self, fuel_type, simulation_time):
        """ Construct an EnergySupply object

        Arguments:
        fuel_type          -- string denoting type of fuel
                              TODO Consider replacing with fuel_type object
        simulation_time    -- reference to SimulationTime object

        Other variables:
        demand_total       -- list to hold total demand on this energy supply at each timestep
        demand_by_end_user -- dictionary of lists to hold demand from each end user on this
                              energy supply at each timestep
        """
        self.__fuel_type          = fuel_type
        self.__simulation_time    = simulation_time
        self.__demand_total       = self.__init_demand_list()
        self.__demand_by_end_user = {}

    def __init_demand_list(self):
        """ Initialise zeroed list of demand figures (one list entry for each timestep) """
        # TODO Consider moving this function to SimulationTime object if it
        #      turns out to be more generally useful.
        return [0] * self.__simulation_time.total_steps()

    def connection(self, end_user_name):
        """ Return an EnergySupplyConnection object and initialise list for the end user demand """
        # Check that end_user_name is not already registered/connected
        if end_user_name in self.__demand_by_end_user.keys():
            sys.exit("Error: End user name already used: "+end_user_name)
            # TODO Exit just the current case instead of whole program entirely?

        self.__demand_by_end_user[end_user_name] = self.__init_demand_list()
        return EnergySupplyConnection(self, end_user_name)

    def __demand_energy(self, end_user_name, amount_demanded):
        """ Record energy demand (in kWh) for the end user specified.

        Note: Call via an EnergySupplyConnection object, not directly.
        """
        # Check that end_user_name is already connected/registered
        if end_user_name not in self.__demand_by_end_user.keys():
            sys.exit("Error: End user name ("+end_user_name+
                     ") not already registered by calling connection function.")
            # TODO Exit just the current case instead of whole program entirely?

        t_idx = self.__simulation_time.current_hour()
        self.__demand_total[t_idx] = self.__demand_total[t_idx] + amount_demanded
        self.__demand_by_end_user[end_user_name][t_idx] \
            = self.__demand_by_end_user[end_user_name][t_idx] \
            + amount_demanded

    def results_total(self):
        """ Return list of the total demand on this energy source for each timestep """
        return self.__demand_total

    def results_by_end_user(self):
        """ Return the demand from each end user on this energy source for each timestep.

        Returns dictionary of lists, where dictionary keys are names of end users.
        """
        return self.__demand_by_end_user
