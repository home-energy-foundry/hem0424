#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides the high-level control flow for the core calculation, and
initialises the relevant objects in the core model.
"""

# Standard library imports
import sys

# Local imports
from core.simulation_time import SimulationTime
from core.external_conditions import ExternalConditions
from core.controls.time_control import OnOffTimeControl
from core.energy_supply.energy_supply import EnergySupply
from core.heating_systems.storage_tank import ImmersionHeater, StorageTank
from core.heating_systems.instant_elec_heater import InstantElecHeater
from core.water_heat_demand.cold_water_source import ColdWaterSource
from core.water_heat_demand.shower import MixerShower, InstantElecShower


class Project:
    """ An object to represent the overall model to be simulated """

    def __init__(self, proj_dict):
        """ Construct a Project object and the various components of the simulation

        Arguments:
        proj_dict -- dictionary of project data, containing nested dictionaries
                     and lists of input data for system components, external
                     conditions, occupancy etc.

        Other (self.__) variables:
        simtime            -- SimulationTime object for this Project
        external_conditions -- ExternalConditions object for this Project
        cold_water_sources -- dictionary of ColdWaterSource objects with names as keys
        energy_supplies    -- dictionary of EnergySupply objects with names as keys
        controls           -- dictionary of control objects (of varying types) with names as keys
        hot_water_sources  -- dictionary of hot water source objects (of varying types)
                              with names as keys
        showers            -- dictionary of shower objects (of varying types) with names as keys
        space_heat_systems -- dictionary of space heating system objects (of varying
                              types) with names as keys
        """

        self.__simtime = SimulationTime(
            proj_dict['SimulationTime']['start'],
            proj_dict['SimulationTime']['end'],
            proj_dict['SimulationTime']['step'],
            )

        self.__external_conditions = ExternalConditions(
            self.__simtime,
            proj_dict['ExternalConditions']['air_temperatures'],
            )

        self.__cold_water_sources = {}
        for name, data in proj_dict['ColdWaterSource'].items():
            self.__cold_water_sources[name] = ColdWaterSource(data['temperatures'], self.__simtime)

        self.__energy_supplies = {}
        for name, data in proj_dict['EnergySupply'].items():
            self.__energy_supplies[name] = EnergySupply(data['fuel'], self.__simtime)
            # TODO Consider replacing fuel type string with fuel type object

        def dict_to_ctrl(name, data):
            """ Parse dictionary of control data and return approprate control object """
            ctrl_type = data['type']
            if ctrl_type == 'OnOffTimeControl':
                ctrl = OnOffTimeControl(data['schedule'], self.__simtime)
            else:
                sys.exit(name + ': control type (' + ctrl_type + ') not recognised.')
                # TODO Exit just the current case instead of whole program entirely?
            return ctrl

        self.__controls = {}
        for name, data in proj_dict['Control'].items():
            self.__controls[name] = dict_to_ctrl(name, data)

        def dict_to_heat_source(name, data):
            """ Parse dictionary of heat source data and return approprate heat source object """
            heat_source_type = data['type']
            if heat_source_type == 'ImmersionHeater':
                if 'Control' in data.keys():
                    ctrl = self.__controls[data['Control']]
                    # TODO Need to handle error if Control name is invalid.
                else:
                    ctrl = None

                energy_supply = self.__energy_supplies[data['EnergySupply']]
                # TODO Need to handle error if EnergySupply name is invalid.
                energy_supply_conn = energy_supply.connection(name)

                heat_source = ImmersionHeater(
                    data['power'],
                    energy_supply_conn,
                    self.__simtime,
                    ctrl,
                    )
            else:
                sys.exit(name + ': heat source type (' + heat_source_type + ') not recognised.')
                # TODO Exit just the current case instead of whole program entirely?
            return heat_source

        def dict_to_hot_water_source(name, data):
            """ Parse dictionary of HW source data and return approprate HW source object """
            hw_source_type = data['type']
            if hw_source_type == 'StorageTank':
                cold_water_source = self.__cold_water_sources[data['ColdWaterSource']]
                # TODO Need to handle error if ColdWaterSource name is invalid.

                hw_source = StorageTank(
                    data['volume'],
                    1.0,  # TODO Remove hard-coding of initial hot fraction
                    55.0, # TODO Remove hard-coding of hot water temp
                    cold_water_source,
                    )

                for heat_source_name, heat_source_data in data['HeatSource'].items():
                    heat_source = dict_to_heat_source(heat_source_name, heat_source_data)
                    hw_source.add_heat_source(heat_source, 1.0)
            else:
                sys.exit(name + ': hot water source type (' + hw_source_type + ') not recognised.')
                # TODO Exit just the current case instead of whole program entirely?
            return hw_source

        self.__hot_water_sources = {}
        for name, data in proj_dict['HotWaterSource'].items():
            self.__hot_water_sources[name] = dict_to_hot_water_source(name, data)

        def dict_to_shower(name, data):
            """ Parse dictionary of shower data and return approprate shower object """
            cold_water_source = self.__cold_water_sources[data['ColdWaterSource']]
            # TODO Need to handle error if ColdWaterSource name is invalid.

            shower_type = data['type']
            if shower_type == 'MixerShower':
                shower = MixerShower(data['flowrate'], cold_water_source)
            elif shower_type == 'InstantElecShower':
                energy_supply = self.__energy_supplies[data['EnergySupply']]
                # TODO Need to handle error if EnergySupply name is invalid.
                energy_supply_conn = energy_supply.connection(name)

                shower = InstantElecShower(
                    data['rated_power'],
                    cold_water_source,
                    energy_supply_conn,
                    )
            else:
                sys.exit(name + ': shower type (' + shower_type + ') not recognised.')
                # TODO Exit just the current case instead of whole program entirely?
            return shower

        self.__showers = {}
        for name, data in proj_dict['Shower'].items():
            self.__showers[name] = dict_to_shower(name, data)

        def dict_to_space_heat_system(name, data):
            space_heater_type = data['type']
            if space_heater_type == 'InstantElecHeater':
                if 'Control' in data.keys():
                    ctrl = self.__controls[data['Control']]
                    # TODO Need to handle error if Control name is invalid.
                else:
                    ctrl = None

                energy_supply = self.__energy_supplies[data['EnergySupply']]
                # TODO Need to handle error if EnergySupply name is invalid.
                energy_supply_conn = energy_supply.connection(name)

                space_heater = InstantElecHeater(
                    data['rated_power'],
                    energy_supply_conn,
                    self.__simtime,
                    ctrl,
                    )
            else:
                sys.exit(name + ': space heating system type (' \
                       + space_heater_type + ') not recognised.')
                # TODO Exit just the current case instead of whole program entirely?
            return space_heater

        self.__space_heat_systems = {}
        for name, data in proj_dict['SpaceHeatSystem'].items():
            self.__space_heat_systems[name] = dict_to_space_heat_system(name, data)


    def run(self):
        """ Run the simulation """

        def hot_water_demand():
            """ Calculate the hot water demand for the current timestep """
            hw_demand = 0.0
            for name, shower in self.__showers.items():
                hw_demand = hw_demand + shower.hot_water_demand(41.0, 6.0)
                # TODO Remove hard-coding of shower temperature and duration
            return hw_demand

        # Loop over each timestep
        for t_idx, t_current, delta_t_h in self.__simtime:
            hw_demand = hot_water_demand()
            self.__hot_water_sources['hw cylinder'].demand_hot_water(hw_demand)
            # TODO Remove hard-coding of hot water source name

        # Return results from all energy supplies
        results_totals = {}
        results_end_user = {}
        for name, supply in self.__energy_supplies.items():
            results_totals[name] = supply.results_total()
            results_end_user[name] = supply.results_by_end_user()
        return results_totals, results_end_user
