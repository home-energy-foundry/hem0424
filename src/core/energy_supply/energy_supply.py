#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains objects that represent energy supplies such as mains gas,
mains electricity or other fuels (e.g. LPG, wood pellets).
"""

# Standard library inputs
import sys
from numpy.random.mtrand import beta


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

    def supply_energy(self, amount_produced):
        """ Forwards the amount of energy produced (in kWh) to the relevant EnergySupply object """
        self.__energy_supply._EnergySupply__supply_energy(self.__end_user_name, amount_produced)

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
        self.__beta_factor = self.__init_demand_list() #this would be multiple columns if multiple beta factors
        self.__supply_surplus = self.__init_demand_list()
        self.__demand_not_met = self.__init_demand_list()

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

        t_idx = self.__simulation_time.index()
        self.__demand_total[t_idx] = self.__demand_total[t_idx] + amount_demanded
        self.__demand_by_end_user[end_user_name][t_idx] \
            = self.__demand_by_end_user[end_user_name][t_idx] \
            + amount_demanded

    def __supply_energy(self, end_user_name, amount_produced):
        """ Record energy produced (in kWh) for the end user specified.

        Note: this is energy generated so it is subtracted from demand.
        Treat as negative
        """
        #energy produced in kWh as 'negative demand'
        amount_produced = amount_produced * -1
        self.__demand_energy(end_user_name, amount_produced)

    def results_total(self):
        """ Return list of the total demand on this energy source for each timestep """
        return self.__demand_total

    def results_by_end_user(self):
        """ Return the demand from each end user on this energy source for each timestep.

        Returns dictionary of lists, where dictionary keys are names of end users.
        """
        return self.__demand_by_end_user
    
    def get_demand_not_met(self):
        return self.__demand_not_met
    def get_supply_surplus(self):
        return self.__supply_surplus
    def get_beta_factor(self):
        return self.__beta_factor
    
    def calc_demand_after_generation(self):
        
        """
        calculate how much of that supply can be offset against demand. 
        And then calculate what demand and supply is left after offsetting, which are the amount exported imported
        """
        
        supplies=[]
        demands=[]
        t_idx = self.__simulation_time.index()
        for user in self.__demand_by_end_user.keys():
            demand = self.__demand_by_end_user[user][t_idx]
            if demand < 0.0:
                """if energy is negative that means its actually a supply, we need to separate the two"""
                """if we had multiple different supplies they would have to be separated here"""
                supplies.append(demand)
            else:
                demands.append(demand)
        
        """PV elec consumed within dwelling in absence of battery storage or diverter (Wh)
        if there were multiple sources they would each have their own beta factors"""
        supply_consumed = sum(supplies) * self.__beta_factor[t_idx]
        """Surplus PV elec generation (kWh) - ie amount to be exported to the grid or batteries"""
        supply_surplus = sum(supplies) * (1 - self.__beta_factor[t_idx])
        """Elec demand not met by PV (kWh) - ie amount to be imported from the grid or batteries"""
        demand_not_met = sum(demands) - supply_consumed
        
        self.__supply_surplus[t_idx] += supply_surplus
        self.__demand_not_met[t_idx] += demand_not_met
        
        return supply_surplus, demand_not_met
    
    def calc_beta_factor(self):
        """
        calculates beta factor for the current timestep
        Beta factor will at some stage need to be generalised to include Wind and Hydro
        """
        
        supplies=[]
        demands=[]
        t_idx = self.__simulation_time.index()

        for user in self.__demand_by_end_user.keys():
            demand = self.__demand_by_end_user[user][t_idx]
            if demand < 0.0:
                """if energy is negative that means its actually a supply, we need to separate the two for beta factor calc"""
                """if we had multiple different supplies they would have to be separated here"""
                supplies.append(-demand)
            else:
                demands.append(demand)
            
        beta_factor = self.beta_factor_function(sum(supplies),sum(demands),'PV')
        
        self.__beta_factor[t_idx] += beta_factor
        
        return beta_factor
        
    def beta_factor_function(self,supply,demand,function):
        """
        wrapper that applies relevant function to obtain 
        beta factor from energy supply+demand at a given timestep
        """
        
        if supply == 0.0:
            beta_factor = 1.0
            return beta_factor
        
        if demand == 0.0:
            beta_factor = 0.0
            return beta_factor
        
        
        demand_ratio = float(supply) / float(demand)
        if function=='PV':
            """TODO: come up with better fit curve for PV"""
            beta_factor = min(0.6748 *pow(demand_ratio,-0.703),1.0)
        elif function=='wind':
            """example"""
            beta_factor=1.0
        else:
            beta_factor=1.0

        return beta_factor
