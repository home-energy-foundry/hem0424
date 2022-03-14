#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides the high-level control flow for the core calculation, and
initialises the relevant objects in the core model.
"""

class InstantElecHeater:
    """ Class to represent instantaneous electric heaters """

    def __init__(self, rated_power, energy_supply_conn, simulation_time, control=None):
        """ Construct an InstantElecHeater object

        Arguments:
        rated_power        -- in kW
        energy_supply_conn -- reference to EnergySupplyConnection object
        simulation_time    -- reference to SimulationTime object
        control            -- reference to a control object which must implement is_on() func
        """
        self.__pwr                = rated_power
        self.__energy_supply_conn = energy_supply_conn
        self.__simulation_time    = simulation_time
        self.__control            = control

    def demand_energy(self, energy_demand):
        """ Demand energy (in kWh) from the heater """

        # Account for time control where present. If no control present, assume
        # system is always active (except for basic thermostatic control, which
        # is implicit in demand calculation).
        # TODO Account for manual (or smart) control where heater may be left
        #      on for longer than it would be under a simple thermostatic
        #      control?
        if self.__control is None or self.__control.is_on():
            # Energy that heater is able to supply is limited by power rating
            energy_supplied = min(energy_demand, self.__pwr * self.__simulation_time.timestep())
        else:
            energy_supplied = 0.0

        self.__energy_supply_conn.demand_energy(energy_supplied)
        return energy_supplied
