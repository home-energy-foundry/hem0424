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
    BuildingElementOpaque, BuildingElementTransparent, BuildingElementGround, \
    BuildingElementAdjacentZTC
from core.space_heat_demand.ventilation_element import VentilationElementInfiltration
from core.space_heat_demand.thermal_bridge import \
    ThermalBridgeLinear, ThermalBridgePoint
from core.water_heat_demand.cold_water_source import ColdWaterSource
from core.water_heat_demand.shower import MixerShower, InstantElecShower
from core.water_heat_demand.bath import Bath
from core.water_heat_demand.other_hot_water_uses import OtherHotWater
from core.space_heat_demand.internal_gains import InternalGains
from core.water_heat_demand.pipework import Pipework

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

        # TODO Some inputs are not currently used, so set to None here rather
        #      than requiring them in input file.
        # TODO Read timezone from input file. For now, set timezone to 0 (GMT)
        # TODO Read direct_beam_conversion_needed from input file. For now,
        #      assume false (for epw files)
        self.__external_conditions = ExternalConditions(
            self.__simtime,
            proj_dict['ExternalConditions']['air_temperatures'],
            proj_dict['ExternalConditions']['wind_speeds'],
            proj_dict['ExternalConditions']['diffuse_horizontal_radiation'],
            proj_dict['ExternalConditions']['direct_beam_radiation'],
            proj_dict['ExternalConditions']['solar_reflectivity_of_ground'],
            proj_dict['ExternalConditions']['latitude'],
            proj_dict['ExternalConditions']['longitude'],
            0, #proj_dict['ExternalConditions']['timezone'],
            0, #proj_dict['ExternalConditions']['start_day'],
            365, #proj_dict['ExternalConditions']['end_day'],
            None, #proj_dict['ExternalConditions']['january_first'],
            None, #proj_dict['ExternalConditions']['daylight_savings'],
            None, #proj_dict['ExternalConditions']['leap_day_included'],
            False, #proj_dict['ExternalConditions']['direct_beam_conversion_needed']
            )

        self.__infiltration = VentilationElementInfiltration(
            proj_dict['Infiltration']['storey'],
            proj_dict['Infiltration']['shelter'],
            proj_dict['Infiltration']['build_type'],
            proj_dict['Infiltration']['test_result'],
            proj_dict['Infiltration']['test_type'],
            proj_dict['Infiltration']['env_area'],
            proj_dict['Infiltration']['volume'],
            proj_dict['Infiltration']['sheltered_sides'],
            proj_dict['Infiltration']['open_chimneys'],
            proj_dict['Infiltration']['open_flues'],
            proj_dict['Infiltration']['closed_fire'],
            proj_dict['Infiltration']['flues_d'],
            proj_dict['Infiltration']['flues_e'],
            proj_dict['Infiltration']['blocked_chimneys'],
            proj_dict['Infiltration']['extract_fans'],
            proj_dict['Infiltration']['passive_vents'],
            proj_dict['Infiltration']['gas_fires'],
            self.__external_conditions,
            )

        self.__cold_water_sources = {}
        for name, data in proj_dict['ColdWaterSource'].items():
            self.__cold_water_sources[name] \
                = ColdWaterSource(data['temperatures'], self.__simtime, data['start_day'])

        self.__energy_supplies = {}
        for name, data in proj_dict['EnergySupply'].items():
            self.__energy_supplies[name] = EnergySupply(data['fuel'], self.__simtime)
            # TODO Consider replacing fuel type string with fuel type object

        self.__internal_gains = InternalGains(
            expand_schedule(
                float,
                proj_dict['InternalGains']['schedule_total_internal_gains'],
                "main",
                ),
            self.__simtime,
            proj_dict['InternalGains']['start_day']
            )

        def dict_to_ctrl(name, data):
            """ Parse dictionary of control data and return approprate control object """
            ctrl_type = data['type']
            if ctrl_type == 'OnOffTimeControl':
                sched = expand_schedule(bool, data['schedule'], "main")
                ctrl = OnOffTimeControl(sched, self.__simtime, data['start_day'])
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
            
            
        def dict_to_baths(name, data):
            """ Parse dictionary of bath data and return approprate bath object """
            cold_water_source = self.__cold_water_sources[data['ColdWaterSource']]
            # TODO Need to handle error if ColdWaterSource name is invalid.

            bath = Bath(data['size'], cold_water_source)

            return bath

        self.__baths = {}
        for name, data in proj_dict['Bath'].items():
            self.__baths[name] = dict_to_baths(name, data)

        def dict_to_other_water_events(name, data):
            """ Parse dictionary of bath data and return approprate other event object """
            cold_water_source = self.__cold_water_sources[data['ColdWaterSource']]
            # TODO Need to handle error if ColdWaterSource name is invalid.

            other_event = OtherHotWater(data['flowrate'], cold_water_source)

            return other_event

        self.__other_water_events = {}
        for name, data in proj_dict['Other'].items():
            self.__other_water_events[name] = dict_to_other_water_events(name, data)

        def dict_to_water_distribution_system(name, data):
            # go through internal then external distribution system
            # TODO - primary system
            
            pipework = Pipework(
                data["heat_transfer_coefficient_inside"],
                data["internal_diameter"],
                data["external_diameter"],
                data["length"],
                data["pipe_thermal_conductivity"],
                data["insulation_thermal_conductivity"],
                data["insulation_thickness"],
                data["heat_transfer_coefficient_outside"],
                data["emissivity"])
                
            return(pipework)

        self.__water_heating_pipework = {}
        for name, data in proj_dict['Distribution'].items():
            self.__water_heating_pipework[name] = dict_to_water_distribution_system(name, data)
            
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
                    data['pitch'],
                    data['a_sol'],
                    data['r_c'],
                    data['k_m'],
                    data['mass_distribution_class'],
                    data['orientation'],
                    self.__external_conditions,
                    )
            elif building_element_type == 'BuildingElementTransparent':
                building_element = BuildingElementTransparent(
                    data['area'],
                    data['pitch'],
                    data['r_c'],
                    data['orientation'],
                    data['g_value'],
                    data['frame_area_fraction'],
                    self.__external_conditions,
                    )
            elif building_element_type == 'BuildingElementGround':
                building_element = BuildingElementGround(
                    data['area'],
                    data['pitch'],
                    data['u_value'],
                    data['r_f'],
                    data['k_m'],
                    data['mass_distribution_class'],
                    data['h_pi'],
                    data['h_pe'],
                    data['perimeter'],
                    data['psi_wall_floor_junc'],
                    self.__external_conditions,
                    self.__simtime,
                    )
            elif building_element_type == 'BuildingElementAdjacentZTC':
                building_element = BuildingElementAdjacentZTC(
                    data['area'],
                    data['pitch'],
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

        ''' TODO Reinstate this code when VentilationElement types other than infiltration
                 have been defined.
        def dict_to_ventilation_element(name, data):
            ventilation_element_type = data['type']
            if ventilation_element_type == '': # TODO Add ventilation element type
                # TODO Create VentilationElement object
            else:
                sys.exit( name + ': ventilation element type ('
                      + ventilation_element_type + ') not recognised.' )
                # TODO Exit just the current case instead of whole program entirely?
            return ventilation_element
        '''

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

            # Read in ventilation elements and add to list
            # All zones have infiltration, so start list with infiltration object
            vent_elements = [self.__infiltration]
            # Add any additional ventilation elements
            ''' TODO Reinstate this code when VentilationElement types other than infiltration
                     have been defined.
            # TODO Handle case of no additional VentilationElement objects for the zone
            for ventilation_element_name, ventilation_element_data in data['VentilationElement'].items():
                vent_elements.append(
                    dict_to_ventilation_element(ventilation_element_name, ventilation_element_data)
                    )
            '''

            return Zone(
                data['area'],
                data['volume'],
                building_elements,
                thermal_bridging,
                vent_elements
                )

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
            hw_duration = 0.0
            
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
                        hw_duration += event['duration'] # shower minutes duration

       
            for name, other in self.__other_water_events.items():
                # Get all other use events for the current timestep
                usage_events = self.__event_schedules['Other'][name][t_idx]

                # If other is used in the current timestep, get details of use
                # and calculate HW demand from other
                if usage_events is not None:
                    for event in usage_events:
                        other_temp = event['temperature']
                        other_duration = event['duration']
                        hw_demand += other.hot_water_demand(other_temp, other_duration)
                        hw_duration += event['duration'] # other minutes duration
                        
            for name, bath in self.__baths.items():
                # Get all bath use events for the current timestep
                usage_events = self.__event_schedules['Bath'][name][t_idx]
               
                peak_flowrate = self.__other_water_events['other'].get_flowrate()

                # If bath is used in the current timestep, get details of use
                # and calculate HW demand from bath
                if usage_events is not None:
                    for event in usage_events:
                        bath_temp = event['temperature']
                        hw_demand += bath.hot_water_demand(bath_temp)
                        hw_duration += bath.get_size() / peak_flowrate
                        # litres bath  / litres per minute flowrate = minutes

            return hw_demand, hw_duration  # litres hot water per timestep, minutes demand per timestep

            
        def calc_pipework_losses(hw_demand, t_idx, delta_t_h):
            # sum up all hw_demand and allocate pipework losses also.
            # hw_demand is volume.

            # TODO demand water temperature is 52 as elsewhere, need to set it somewhere
            demand_water_temperature = 52
            
            cold_water_source = self.__cold_water_sources[data['ColdWaterSource']]
            cold_water_temperature = self.__cold_water_source.temperature()
            
            # TODO - are the internal temperatures from the previous timestep?
            internal_air_temperature = self.__external_conditions.air_temp()
            overall_area = 0
            
            # TODO here we are treating overall indoor temperature as average of all zones
            for z_name, zone in self.__zones.items():
                internal_air_temperature += zone.temp_internal_air() * zone.__useful_area
                overall_area += zone.__useful_area
            internal_air_temperature /= overall_area # average internal temperature
            
            hot_water_time_fraction = self.hot_water_duration(t_idx) / (delta_t_h * units.minutes_per_hour)
            
            if hot_water_time_fraction>1:
                hot_water_time_fraction = 1
            
            # note - very broad approximation - if hot water is not going through the pipe it's at the cold water temperature
            #demand_water_temperature = (hot_water_time_fraction * demand_water_temperature) + ((1 - hot_water_time_fraction) * cold_water_temperature)
            
            # note - treating insulation surface temperature as the same as the temperature outside the pipe - should be similar over longer timesteps
            pipework_watts_heat_loss = self.__water_heating_pipework["internal"].heatloss(internal_air_temperature , demand_water_temperature, internal_air_temperature) + \
            self.__water_heating_pipework["external"].heatloss(self.__external_conditions.air_temp(), demand_water_temperature, self.__external_conditions.air_temp()) 
            
            # only calculate loss for times when there is hot water in the pipes - multiply by time fraction to get to kWh
            pipework_heat_loss = pipework_watts_heat_loss * hot_water_time_fraction * (delta_t_h * units.seconds_per_hour) /1000 # convert to kWh
            
            return pipework_heat_loss # heat loss in kWh for the timestep


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
            internal_air_temp = {}
            operative_temp = {}
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

                if c_name is None:
                    space_cool_demand_system[c_name] = 'n/a'

                internal_air_temp[z_name] = zone.temp_internal_air()
                operative_temp[z_name] = zone.temp_operative()

            return operative_temp, internal_air_temp, space_heat_demand_zone, space_cool_demand_zone, space_heat_demand_system, space_cool_demand_system

        timestep_array = []
        operative_temp_dict = {}
        internal_air_temp_dict = {}
        space_heat_demand_dict = {}
        space_cool_demand_dict = {}
        space_heat_demand_system_dict = {}
        space_cool_demand_system_dict = {}
        zone_list = []
        hot_water_demand_dict = {}
        hot_water_duration_dict = {}

        for z_name in self.__zones.keys():
            operative_temp_dict[z_name] = []
            internal_air_temp_dict[z_name] = []
            space_heat_demand_dict[z_name] = []
            space_cool_demand_dict[z_name] = []
            zone_list.append(z_name)

        for z_name, h_name in self.__heat_system_name_for_zone.items():
            space_heat_demand_system_dict[h_name] = []

        for z_name, c_name in self.__cool_system_name_for_zone.items():
            space_cool_demand_system_dict[c_name] = []

        hot_water_demand_dict['demand'] = []
        hot_water_duration_dict['duration'] = []

        # Loop over each timestep
        for t_idx, t_current, delta_t_h in self.__simtime:
            timestep_array.append(t_current)
            hw_demand, hw_duration = hot_water_demand(t_idx)
            self.__hot_water_sources['hw cylinder'].demand_hot_water(hw_demand)
            # TODO Remove hard-coding of hot water source name
            operative_temp, internal_air_temp, space_heat_demand_zone, space_cool_demand_zone, space_heat_demand_system, space_cool_demand_system = calc_space_heating(delta_t_h)

            for z_name, temp in operative_temp.items():
                operative_temp_dict[z_name].append(temp)

            for z_name, temp in internal_air_temp.items():
                internal_air_temp_dict[z_name].append(temp)

            for z_name, demand in space_heat_demand_zone.items():
                space_heat_demand_dict[z_name].append(demand)

            for z_name, demand in space_cool_demand_zone.items():
                space_cool_demand_dict[z_name].append(demand)

            for h_name, demand in space_heat_demand_system.items():
                space_heat_demand_system_dict[h_name].append(demand)

            for c_name, demand in space_cool_demand_system.items():
                space_cool_demand_system_dict[c_name].append(demand)
                
            hot_water_demand_dict['demand'].append(hw_demand)
            hot_water_duration_dict['duration'].append(hw_duration)

        zone_dict = {'Operative temp': operative_temp_dict, 'Internal air temp': internal_air_temp_dict, 'Space heat demand': space_heat_demand_dict, 'Space cool demand': space_cool_demand_dict}
        hc_system_dict = {'Heating system': space_heat_demand_system_dict, 'Cooling system': space_cool_demand_system_dict}
        hot_water_dict = {'Hot water demand': hot_water_demand_dict, 'Hot water duration': hot_water_duration_dict}

        # Return results from all energy supplies
        results_totals = {}
        results_end_user = {}
        for name, supply in self.__energy_supplies.items():
            results_totals[name] = supply.results_total()
            results_end_user[name] = supply.results_by_end_user()
        return timestep_array, results_totals, results_end_user, zone_dict, zone_list, hc_system_dict, hot_water_dict
