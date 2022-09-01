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
from core.schedule import expand_schedule, expand_events
from core.controls.time_control import OnOffTimeControl
from core.energy_supply.energy_supply import EnergySupply
from core.heating_systems.storage_tank import ImmersionHeater, StorageTank
from core.heating_systems.instant_elec_heater import InstantElecHeater
from core.space_heat_demand.zone import Zone
from core.space_heat_demand.building_element import \
    BuildingElementOpaque, BuildingElementTransparent, BuildingElementGround
from core.space_heat_demand.thermal_bridge import \
    ThermalBridgeLinear, ThermalBridgePoint
from core.water_heat_demand.cold_water_source import ColdWaterSource
from core.water_heat_demand.shower import MixerShower, InstantElecShower
from core.space_heat_demand.internal_gains import InternalGains


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
            proj_dict['ExternalConditions']['diffuse_horizontal_radiation'],
            proj_dict['ExternalConditions']['direct_beam_radiation'],
            proj_dict['ExternalConditions']['solar_reflectivity_of_ground'],
            proj_dict['ExternalConditions']['latitude'],
            proj_dict['ExternalConditions']['longitude'],
            proj_dict['ExternalConditions']['timezone'],
            proj_dict['ExternalConditions']['start_day'],
            proj_dict['ExternalConditions']['end_day'],
            proj_dict['ExternalConditions']['january_first'],
            proj_dict['ExternalConditions']['daylight_savings'],
            proj_dict['ExternalConditions']['leap_day_included'],
            proj_dict['ExternalConditions']['direct_beam_conversion_needed']
            )

        self.__cold_water_sources = {}
        for name, data in proj_dict['ColdWaterSource'].items():
            self.__cold_water_sources[name] = ColdWaterSource(data['temperatures'], self.__simtime)

        self.__energy_supplies = {}
        for name, data in proj_dict['EnergySupply'].items():
            self.__energy_supplies[name] = EnergySupply(data['fuel'], self.__simtime)
            # TODO Consider replacing fuel type string with fuel type object

        self.__internal_gains = InternalGains(
            proj_dict['InternalGains']['total_internal_gains'],
            self.__simtime
            )

        def dict_to_ctrl(name, data):
            """ Parse dictionary of control data and return approprate control object """
            ctrl_type = data['type']
            if ctrl_type == 'OnOffTimeControl':
                sched = expand_schedule(bool, data['schedule'], "main")
                ctrl = OnOffTimeControl(sched, self.__simtime)
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

        def dict_to_event_schedules(data):
            """ Process list of events (for hot water draw-offs, appliance use etc.) """
            sim_timestep = self.__simtime.timestep()
            tot_timesteps = self.__simtime.total_steps()
            return expand_events(data, sim_timestep, tot_timesteps)

        self.__event_schedules = {}
        for sched_type, schedules in proj_dict['Events'].items():
            if sched_type not in self.__event_schedules:
                self.__event_schedules[sched_type] = {}
            for name, data in schedules.items():
                self.__event_schedules[sched_type][name] = dict_to_event_schedules(data)

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

        # If one or more space heating systems have been provided, add them to the project
        self.__space_heat_systems = {}
        # If no space heating systems have been provided, then skip. This
        # facilitates running the simulation with no heating systems at all
        if 'SpaceHeatSystem' in proj_dict:
            for name, data in proj_dict['SpaceHeatSystem'].items():
                self.__space_heat_systems[name] = dict_to_space_heat_system(name, data)

        self.__space_cool_systems = {}
        # TODO Read in space cooling systems and populate dict

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
                    data['orientation'],
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
                    data['orientation'],
                    data['g_value'],
                    data['frame_area_fraction'],
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

        self.__heat_system_name_for_zone = {}
        self.__cool_system_name_for_zone = {}

        def dict_to_zone(name, data):
            # Record which heating and cooling system this zone is heated/cooled by (if applicable)
            if 'SpaceHeatSystem' in data:
                self.__heat_system_name_for_zone[name] = data['SpaceHeatSystem']
            else:
                self.__heat_system_name_for_zone[name] = None
            if 'SpaceCoolSystem' in data:
                self.__cool_system_name_for_zone[name] = data['SpaceCoolSystem']
            else:
                self.__cool_system_name_for_zone[name] = None

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

        def hot_water_demand(t_idx):
            """ Calculate the hot water demand for the current timestep

            Arguments:
            t_idx -- timestep index/count
            """
            hw_demand = 0.0
            for name, shower in self.__showers.items():
                # Get all shower use events for the current timestep
                usage_events = self.__event_schedules['Shower'][name][t_idx]

                # If shower is used in the current timestep, get details of use
                # and calculate HW demand from shower
                if usage_events is not None:
                    for event in usage_events:
                        shower_temp = event['temperature']
                        shower_duration = event['duration']
                        hw_demand += shower.hot_water_demand(shower_temp, shower_duration)

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

            space_heat_demand_system = {} # in kWh
            for heat_system_name in self.__space_heat_systems.keys():
                space_heat_demand_system[heat_system_name] = 0.0

            space_cool_demand_system = {} # in kWh
            for cool_system_name in self.__space_cool_systems.keys():
                space_cool_demand_system[cool_system_name] = 0.0

            space_heat_demand_zone = {}
            space_cool_demand_zone = {}
            for z_name, zone in self.__zones.items():
                # Look up names of relevant heating and cooling systems for this zone
                h_name = self.__heat_system_name_for_zone[z_name]
                c_name = self.__cool_system_name_for_zone[z_name]

                # Convert W/m2 to W
                gains_internal_zone = self.__internal_gains.total_internal_gain() * zone.area()
                space_heat_demand_zone[z_name], space_cool_demand_zone[z_name] = \
                    zone.space_heat_cool_demand(delta_t_h, temp_ext_air, gains_internal_zone)

                if h_name is not None: # If the zone is heated
                    space_heat_demand_system[h_name] += space_heat_demand_zone[z_name]
                if c_name is not None: # If the zone is cooled
                    space_cool_demand_system[c_name] += space_cool_demand_zone[z_name]

            # Calculate how much heating the systems can provide
            space_heat_provided = {}
            for heat_system_name, heat_system in self.__space_heat_systems.items():
                space_heat_provided[heat_system_name] = \
                    heat_system.demand_energy(space_heat_demand_system[heat_system_name])

            # Calculate how much cooling the systems can provide
            space_cool_provided = {}
            for cool_system_name, cool_system in self.__space_cool_systems.items():
                space_cool_provided[cool_system_name] = \
                    cool_system.demand_energy(space_cool_demand_system[cool_system_name])

            # Apportion the provided heating/cooling between the zones in
            # proportion to the heating/cooling demand in each zone. Then
            # update resultant temperatures in zones.
            for z_name, zone in self.__zones.items():
                # Look up names of relevant heating and cooling systems for this zone
                h_name = self.__heat_system_name_for_zone[z_name]
                c_name = self.__cool_system_name_for_zone[z_name]

                # If zone is unheated or there was no demand on heating system,
                # set heating gains for zone to zero, else calculate
                if h_name is None or space_heat_demand_system[h_name] == 0.0:
                    gains_heat = 0.0
                else:
                    frac_heat_zone = space_heat_demand_zone[z_name] \
                                   / space_heat_demand_system[h_name]
                    gains_heat = space_heat_provided[h_name] * frac_heat_zone

                # If zone is uncooled or there was no demand on cooling system,
                # set cooling gains for zone to zero, else calculate
                if c_name is None or space_cool_demand_system[c_name] == 0.0:
                    gains_cool = 0.0
                else:
                    frac_cool_zone = space_cool_demand_zone[z_name] \
                                   / space_cool_demand_system[c_name]
                    gains_cool = space_cool_provided[c_name] * frac_cool_zone

                # Sum heating gains (+ve) and cooling gains (-ve) and convert from kWh to W
                gains_heat_cool = (gains_heat + gains_cool) * units.W_per_kW / delta_t_h

                # Convert W/m2 to W
                gains_internal_zone = self.__internal_gains.total_internal_gain() * zone.area()

                zone.update_temperatures(
                    delta_t,
                    temp_ext_air,
                    gains_internal_zone,
                    gains_heat_cool
                    )

        # Loop over each timestep
        for t_idx, t_current, delta_t_h in self.__simtime:
            hw_demand = hot_water_demand(t_idx)
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
