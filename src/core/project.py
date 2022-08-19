#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides the high-level control flow for the core calculation, and
initialises the relevant objects in the core model.
"""

# Standard library imports
import sys

# Local imports
import core.units as units
from core.simulation_time import SimulationTime
from core.external_conditions import ExternalConditions
from core.controls.time_control import OnOffTimeControl
from core.energy_supply.energy_supply import EnergySupply
from core.heating_systems.storage_tank import ImmersionHeater, StorageTank
from core.heating_systems.instant_elec_heater import InstantElecHeater
from core.space_heat_demand.zone import Zone
from core.space_heat_demand.building_element import \
    BuildingElementOpaque, BuildingElementTransparent, BuildingElementGround, \
    BuildingElementAdjacentZTC
from core.space_heat_demand.thermal_bridge import \
    ThermalBridgeLinear, ThermalBridgePoint
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
        zones              -- dictionary of Zone objects with names as keys
        """

        self.__simtime = SimulationTime(
            proj_dict['SimulationTime']['start'],
            proj_dict['SimulationTime']['end'],
            proj_dict['SimulationTime']['step'],
            )

        self.__external_conditions = ExternalConditions(
            self.__simtime,
            proj_dict['ExternalConditions']['air_temperatures'],
            proj_dict['ExternalConditions']['ground_temperatures'],
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

        def dict_to_building_element(name, data):
            building_element_type = data['type']
            if building_element_type == 'BuildingElementOpaque':
                building_element = BuildingElementOpaque(
                    data['area'],
                    data['h_ci'],
                    data['h_ri'],
                    data['h_ce'],
                    data['h_re'],
                    data['a_sol'],
                    data['r_c'],
                    data['k_m'],
                    data['mass_distribution_class'],
                    data['pitch'],
                    self.__external_conditions,
                    )
            elif building_element_type == 'BuildingElementTransparent':
                building_element = BuildingElementTransparent(
                    data['area'],
                    data['h_ci'],
                    data['h_ri'],
                    data['h_ce'],
                    data['h_re'],
                    data['r_c'],
                    data['pitch'],
                    self.__external_conditions,
                    )
            elif building_element_type == 'BuildingElementGround':
                building_element = BuildingElementGround(
                    data['area'],
                    data['h_ci'],
                    data['h_ri'],
                    data['h_ce'],
                    data['h_re'],
                    data['r_c'],
                    data['r_gr'],
                    data['k_m'],
                    data['k_gr'],
                    data['mass_distribution_class'],
                    self.__external_conditions,
                    )
            elif building_element_type == 'BuildingElementAdjacentZTC':
                building_element = BuildingElementAdjacentZTC(
                    data['area'],
                    data['h_ci'],
                    data['h_ri'],
                    data['r_c'],
                    data['k_m'],
                    data['mass_distribution_class'],
                    self.__external_conditions,
                    )
            else:
                sys.exit( name + ': building element type ('
                        + building_element_type + ') not recognised.' )
                # TODO Exit just the current case instead of whole program entirely?
            return building_element

        def dict_to_thermal_bridging(data):
            # If data is for individual thermal bridges, initialise the relevant
            # objects and return a list of them. Otherwise, just use the overall
            # figure given.
            if isinstance(data, dict):
                thermal_bridging = []
                for tb_name, tb_data in data.items():
                    tb_type = tb_data['type']
                    if tb_type == 'ThermalBridgeLinear':
                        tb = ThermalBridgeLinear(
                                tb_data['linear_thermal_transmittance'],
                                tb_data['length']
                                )
                    elif tb_type == 'ThermalBridgePoint':
                        tb = ThermalBridgePoint(tb_data['heat_transfer_coeff'])
                    else:
                        sys.exit( tb_name + ': thermal bridge type ('
                                + tb_type + ') not recognised.' )
                        # TODO Exit just the current case instead of whole program entirely?
                    thermal_bridging.append(tb)
            else:
                thermal_bridging = data
            return thermal_bridging

        def dict_to_zone(name, data):
            # Read in building elements and add to list
            building_elements = []
            for building_element_name, building_element_data in data['BuildingElement'].items():
                building_elements.append(
                    dict_to_building_element(building_element_name, building_element_data)
                    )

            # Read in thermal bridging data
            thermal_bridging = dict_to_thermal_bridging(data['ThermalBridging'])
            # TODO Implement ventilation elements rather than using empty list (i.e. ignoring them)
            vent_elements = []

            return Zone(data['area'], building_elements, thermal_bridging, vent_elements)

        self.__zones = {}
        for name, data in proj_dict['Zone'].items():
            self.__zones[name] = dict_to_zone(name, data)

    def run(self):
        """ Run the simulation """

        def hot_water_demand():
            """ Calculate the hot water demand for the current timestep """
            hw_demand = 0.0
            for name, shower in self.__showers.items():
                hw_demand = hw_demand + shower.hot_water_demand(41.0, 6.0)
                # TODO Remove hard-coding of shower temperature and duration
            return hw_demand

        def calc_space_heating(delta_t_h):
            """ Calculate space heating demand, heating system output and temperatures

            Arguments:
            delta_t_h -- calculation timestep, in hours
            """
            temp_ext_air = self.__external_conditions.air_temp()
            # Calculate timestep in seconds
            delta_t = delta_t_h * units.seconds_per_hour

            # Calculate space heating and cooling demand for each zone and sum
            # Keep track of how much is from each zone, so that energy provided
            # can be split between them in same proportion later
            space_heat_demand_total = 0.0 # in kWh
            space_cool_demand_total = 0.0 # in kWh
            space_heat_demand_zone = {}
            space_cool_demand_zone = {}
            for name, zone in self.__zones.items():
                # TODO Calculate the gains rather than hard-coding to zero (i.e. ignoring them)
                gains_internal = 0.0
                gains_solar = 0.0

                space_heat_demand_zone[name], space_cool_demand_zone[name] = \
                    zone.space_heat_cool_demand(delta_t_h, temp_ext_air, gains_internal, gains_solar)
                space_heat_demand_total = space_heat_demand_total + space_heat_demand_zone[name]
                space_cool_demand_total = space_cool_demand_total + space_cool_demand_zone[name]

            # Calculate how much heating/cooling the systems can provide
            space_heat_provided = \
                self.__space_heat_systems['main'].demand_energy(space_heat_demand_total)
                # TODO Remove hard-coding of space heating system name and handle multiple systems
            space_cool_provided = 0.0 # TODO Handle cooling (values should be <= 0.0

            # Apportion the provided heating/cooling between the zones in
            # proportion to the heating/cooling demand in each zone. Then
            # update resultant temperatures in zones.
            for name, zone in self.__zones.items():
                if space_heat_demand_total == 0.0:
                    frac_heat_zone = 0.0
                else:
                    frac_heat_zone = space_heat_demand_zone[name] / space_heat_demand_total

                if space_cool_demand_total == 0.0:
                    frac_cool_zone = 0.0
                else:
                    frac_cool_zone = space_cool_demand_zone[name] / space_cool_demand_total

                gains_heat_cool = ( space_heat_provided * frac_heat_zone \
                                  + space_cool_provided * frac_cool_zone \
                                  ) \
                                * units.W_per_kW / delta_t_h # Convert from kWh to W

                zone.update_temperatures(
                    delta_t,
                    temp_ext_air,
                    gains_internal,
                    gains_solar,
                    gains_heat_cool
                    )

        # Loop over each timestep
        for t_idx, t_current, delta_t_h in self.__simtime:
            hw_demand = hot_water_demand()
            self.__hot_water_sources['hw cylinder'].demand_hot_water(hw_demand)
            # TODO Remove hard-coding of hot water source name

            calc_space_heating(delta_t_h)

        # Return results from all energy supplies
        results_totals = {}
        results_end_user = {}
        for name, supply in self.__energy_supplies.items():
            results_totals[name] = supply.results_total()
            results_end_user[name] = supply.results_by_end_user()
        return results_totals, results_end_user
