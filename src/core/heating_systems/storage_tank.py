#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides objects to model heat storage vessels e.g. hot water
cylinder with immersion heater.
"""

# Local imports
from core.material_properties import WATER


class StorageTank:
    """ An object to represent a hot water storage tank/cylinder

    Models the case where hot water is drawn off and replaced by fresh cold
    water which is then heated in the tank by a heat source. Assumes the water
    is stratified by temperature.

    Implements function demand_hot_water(volume_demanded) which all hot water
    source objects must implement.
    """

    def __init__(self, volume, initial_hot_fraction, temp_hot, cold_feed, contents=WATER):
        """ Construct a StorageTank object

        Arguments:
        volume               -- total volume of the tank, in litres
        initial_hot_fraction -- fraction of the tank contents that are "hot" at
                                the start of the calculation
        temp_hot             -- temperature of the hot water, in deg C
        cold_feed            -- reference to ColdWaterSource object
        contents             -- reference to MaterialProperties object

        Other variables:
        vol_hot              -- volume of water in the tank that is hot, in litres
        heat_sources         -- list (initialised to empty) of heat sources
        """
        self.__vol_max      = volume
        self.__vol_hot      = volume * initial_hot_fraction
        self.__temp_hot     = temp_hot
        self.__cold_feed    = cold_feed
        self.__contents     = contents
        self.__heat_sources = []

    def add_heat_source(self, heat_source, proportion_of_tank_heated):
        """ Add a reference to heat source object and specify position in tank.

        Heat source object must implement the demand_energy(energy_demand) function.
        """
        # TODO Add proportion to list. Account for thermostat position for each
        #      heat source individually?
        self.__heat_sources.append(heat_source)

    def demand_hot_water(self, volume_demanded):
        """ Draw off hot water from the tank

        Arguments:
        volume_demanded -- volume of hot water required, in litres
        """
        # TODO Should demand be in terms of volume or energy? Or option for both?
        #      In terms of volume is simpler because cold water temperature
        #      (and therefore baseline energy) is variable.
        # TODO Account for case where tank cannot provide enough hot water?
        # TODO Account for standing loss

        self.__vol_hot = self.__vol_hot - volume_demanded

        energy_content_kWh_per_litre = self.__contents.volumetric_energy_content_kWh_per_litre(
            self.__temp_hot,
            self.__cold_feed.temperature()
            )

        # Demand heat from heat source(s) if cold water has reached the thermostat
        thermostat_position = 2.0 / 3.0
        # TODO Parameterise this ^^^.
        #      May need to calculate max energy demand possible (i.e. whole tank cold)
        #      and multiply by thermostat position for each heat source to get max.
        #      energy that can be provided by each heat source.
        if self.__vol_hot < (self.__vol_max * thermostat_position):
            energy_demand = (self.__vol_max - self.__vol_hot) * energy_content_kWh_per_litre

            # Demand heat from heat source(s) and subtract supplied heat from
            # energy demand (resulting in energy_demand equalling unsatisfied
            # energy demand)
            for heat_source in self.__heat_sources:
                energy_demand = energy_demand - heat_source.demand_energy(energy_demand)

            # Amount of hot water in tank is now max volume minus volume that
            # heat sources could not heat
            self.__vol_hot = self.__vol_max - (energy_demand / energy_content_kWh_per_litre)


class ImmersionHeater:
    """ An object to represent an immersion heater """

    def __init__(self, rated_power, energy_supply_conn, simulation_time, control=None):
        """ Construct an ImmersionHeater object

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
        if self.__control is None or self.__control.is_on():
            # Energy that heater is able to supply is limited by power rating
            energy_supplied = min(energy_demand, self.__pwr * self.__simulation_time.timestep())
        else:
            energy_supplied = 0.0

        self.__energy_supply_conn.demand_energy(energy_supplied)
        return energy_supplied
