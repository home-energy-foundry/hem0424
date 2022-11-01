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
from core.energy_supply.pv import PhotovoltaicSystem
from core.heating_systems.emitters import Emitters
from core.heating_systems.storage_tank import ImmersionHeater, StorageTank
from core.heating_systems.instant_elec_heater import InstantElecHeater
from core.space_heat_demand.zone import Zone
from core.space_heat_demand.building_element import \
    BuildingElementOpaque, BuildingElementTransparent, BuildingElementGround, \
    BuildingElementAdjacentZTC
from core.space_heat_demand.ventilation_element import \
    VentilationElementInfiltration, WholeHouseExtractVentilation, \
    MechnicalVentilationHeatRecovery
from core.space_heat_demand.thermal_bridge import \
    ThermalBridgeLinear, ThermalBridgePoint
from core.water_heat_demand.cold_water_source import ColdWaterSource
from core.water_heat_demand.shower import MixerShower, InstantElecShower
from core.water_heat_demand.bath import Bath
from core.water_heat_demand.other_hot_water_uses import OtherHotWater
from core.space_heat_demand.internal_gains import InternalGains, ApplianceGains
from core.pipework import Pipework
import core.water_heat_demand.misc as misc
from core.ductwork import Ductwork


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
            1, #proj_dict['ExternalConditions']['time_series_step'],
            None, #proj_dict['ExternalConditions']['january_first'],
            None, #proj_dict['ExternalConditions']['daylight_savings'],
            None, #proj_dict['ExternalConditions']['leap_day_included'],
            False, #proj_dict['ExternalConditions']['direct_beam_conversion_needed']
            proj_dict['ExternalConditions']['shading_segments'],
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
                = ColdWaterSource(data['temperatures'], self.__simtime, data['start_day'], data['time_series_step'])

        self.__energy_supplies = {}
        for name, data in proj_dict['EnergySupply'].items():
            self.__energy_supplies[name] = EnergySupply(data['fuel'], self.__simtime)
            # TODO Consider replacing fuel type string with fuel type object

        self.__internal_gains = {}
        for name, data in proj_dict['InternalGains'].items():
            self.__internal_gains[name] = InternalGains(
                                             expand_schedule(
                                                 float,
                                                 data['schedule'],
                                                 "main",
                                                 ),
                                             self.__simtime,
                                             data['start_day'],
                                             data['time_series_step']
                                             )

        def dict_to_ctrl(name, data):
            """ Parse dictionary of control data and return approprate control object """
            ctrl_type = data['type']
            if ctrl_type == 'OnOffTimeControl':
                sched = expand_schedule(bool, data['schedule'], "main")
                ctrl = OnOffTimeControl(sched, self.__simtime, data['start_day'], data['time_series_step'])
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
                    data['daily_losses'],
                    55.0, # TODO Remove hard-coding of hot water temp
                    cold_water_source,
                    self.__simtime,
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

            bath = Bath(data['size'], cold_water_source, data['flowrate'])

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
                data["internal_diameter"],
                data["external_diameter"],
                data["length"],
                data["insulation_thermal_conductivity"],
                data["insulation_thickness"],
                data["surface_reflectivity"],
                data["pipe_contents"])
                
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
                    data['base_height'],
                    data['height'],
                    data['width'],
                    self.__external_conditions,
                    )
            elif building_element_type == 'BuildingElementTransparent':
                building_element = BuildingElementTransparent(
                    data['pitch'],
                    data['r_c'],
                    data['orientation'],
                    data['g_value'],
                    data['frame_area_fraction'],
                    data['base_height'],
                    data['height'],
                    data['width'],
                    data['shading'],
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

        def dict_to_ventilation_element(name, data):
            ventilation_element_type = data['type']
            if ventilation_element_type == 'WHEV': # Whole house extract ventilation
                energy_supply = self.__energy_supplies[data['EnergySupply']]
                # TODO Need to handle error if EnergySupply name is invalid.
                energy_supply_conn = energy_supply.connection(name)

                ventilation_element = WholeHouseExtractVentilation(
                    data['req_ach'],
                    data['SFP'],
                    energy_supply_conn,
                    self.__external_conditions,
                    self.__simtime,
                    )
                    
                ductwork = None

            elif ventilation_element_type == 'MVHR':
                energy_supply = self.__energy_supplies[data['EnergySupply']]
                # TODO Need to handle error if EnergySupply name is invalid.
                energy_supply_conn = energy_supply.connection(name)

                ventilation_element = MechnicalVentilationHeatRecovery(
                    data['req_ach'],
                    data['SFP'],
                    data['efficiency'],
                    energy_supply_conn,
                    self.__external_conditions,
                    self.__simtime,
                    )
                    
                ductwork = Ductwork(
                    data['ductwork']['internal_diameter'],
                    data['ductwork']['external_diameter'],
                    data['ductwork']['length_in'],
                    data['ductwork']['length_out'],
                    data['ductwork']['insulation_thermal_conductivity'],
                    data['ductwork']['insulation_thickness'],
                    data['ductwork']['reflective'],
                    data['ductwork']['MVHR_location']
                    )
            else:
                sys.exit( name + ': ventilation element type ('
                      + ventilation_element_type + ') not recognised.' )
                # TODO Exit just the current case instead of whole program entirely?
            return ventilation_element, ductwork


        if 'Ventilation' in proj_dict:
            self.__ventilation, self.__space_heating_ductwork = \
                dict_to_ventilation_element('Ventilation system', proj_dict['Ventilation'])
        else:
            self.__ventilation, self.__space_heating_ductwork = None, None

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
            if self.__ventilation is not None:
                vent_elements.append(self.__ventilation)

            return Zone(
                data['area'],
                data['volume'],
                building_elements,
                thermal_bridging,
                vent_elements,
                data['temp_setpnt_heat'],
                data['temp_setpnt_cool'],
                )

        self.__zones = {}
        for name, data in proj_dict['Zone'].items():
            self.__zones[name] = dict_to_zone(name, data)

        total_floor_area = sum(zone.area() for zone in self.__zones.values())

        # Add internal gains from applicances to the internal gains dictionary and
        # create an energy supply connection for appliances
        for name, data in proj_dict['ApplianceGains'].items():
            energy_supply = self.__energy_supplies[data['EnergySupply']]
            # TODO Need to handle error if EnergySupply name is invalid.
            energy_supply_conn = energy_supply.connection(name)
            
            # Convert energy supplied to appliances from W to W / m2
            total_energy_supply = []
            for energy_data in expand_schedule(float, data['schedule'], "main"):
                total_energy_supply.append(energy_data / total_floor_area)

            self.__internal_gains[name] = ApplianceGains(
                                             total_energy_supply,
                                             energy_supply_conn,
                                             data['gains_fraction'],
                                             self.__simtime,
                                             data['start_day'],
                                             data['time_series_step']
                                             )

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
            # TODO For wet distribution, look up relevant heat source and set
            #      heat_source variable. The Emitter object will not work
            #      without it, so the code below should remain commented out
            #      until at least one heat source type has been defined.
            # elif space_heater_type == 'WetDistribution':
            #     zone = self.__zones[data['Zone']]
            #     space_heater = Emitters(
            #         data['thermal_mass'],
            #         data['c'],
            #         data['n'],
            #         data['temp_diff_emit_dsgn'],
            #         heat_source,
            #         zone,
            #         self.__simtime,
            #         )
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

        def dict_to_on_site_generation(name, data):
            """ Parse dictionary of on site generation data and
                return approprate on site generation object """
            on_site_generation_type = data['type']
            if on_site_generation_type == 'PhotovoltaicSystem':

                energy_supply = self.__energy_supplies[data['EnergySupply']]
                # TODO Need to handle error if EnergySupply name is invalid.
                energy_supply_conn = energy_supply.connection(name)

                pv_system = PhotovoltaicSystem(
                    data['peak_power'],
                    data['ventilation_strategy'],
                    data['pitch'],
                    data['orientation'],
                    self.__external_conditions,
                    energy_supply_conn,
                    self.__simtime,
                    )
            else:
                sys.exit(name + ': on site generation type ('
                         + on_site_generation_type + ') not recognised.')
                # TODO Exit just the current case instead of whole program entirely?
            return pv_system

        self.__on_site_generation = {}
        # If no on site generation have been provided, then skip.
        if 'OnSiteGeneration' in proj_dict:
            for name, data in proj_dict['OnSiteGeneration'].items():
                self.__on_site_generation[name] = dict_to_on_site_generation(name, data)

    def run(self):
        """ Run the simulation """

        def hot_water_demand(t_idx):
            """ Calculate the hot water demand for the current timestep

            Arguments:
            t_idx -- timestep index/count
            """
            hw_demand = 0.0
            hw_energy_demand = 0.0
            hw_duration = 0.0
            all_events = 0.0
            pw_losses = 0.0
            
            for name, shower in self.__showers.items():
                # Get all shower use events for the current timestep
                usage_events = self.__event_schedules['Shower'][name][t_idx]
                the_cold_water_temp = shower.get_cold_water_source()
                cold_water_temperature = the_cold_water_temp.temperature()

                # If shower is used in the current timestep, get details of use
                # and calculate HW demand from shower
                
                # TODO revisit structure and eliminate the branch on the type
                if usage_events is not None:
                    for event in usage_events:
                        shower_temp = event['temperature']
                        shower_duration = event['duration']
                        hw_demand_i = shower.hot_water_demand(shower_temp, shower_duration)
                        if not isinstance(shower, InstantElecShower):
                            # don't add hw demand and pipework loss from electric shower
                            hw_demand += hw_demand_i
                            hw_energy_demand += misc.water_demand_to_kWh(
                                hw_demand_i,
                                shower_temp,
                                cold_water_temperature
                                )
                            hw_duration += event['duration'] # shower minutes duration
                            all_events +=1
                            pw_losses+=calc_pipework_losses(
                                hw_demand_i,
                                t_idx,
                                delta_t_h,
                                cold_water_temperature,
                                event['duration'],
                                self.__water_heating_pipework) * (event['duration']/units.minutes_per_hour)

            for name, other in self.__other_water_events.items():
                # Get all other use events for the current timestep
                usage_events = self.__event_schedules['Other'][name][t_idx]
                the_cold_water_temp = other.get_cold_water_source()
                cold_water_temperature = the_cold_water_temp.temperature()
                
                # If other is used in the current timestep, get details of use
                # and calculate HW demand from other
                if usage_events is not None:
                    for event in usage_events:
                        other_temp = event['temperature']
                        other_duration = event['duration']
                        hw_demand += other.hot_water_demand(other_temp, other_duration)
                        hw_energy_demand += misc.water_demand_to_kWh(
                            other.hot_water_demand(other_temp, other_duration),
                            other_temp,
                            cold_water_temperature
                            )
                        hw_duration += event['duration'] # other minutes duration
                        all_events += 1
                        pw_losses += calc_pipework_losses(
                            other.hot_water_demand(other_temp, other_duration),
                            t_idx,
                            delta_t_h,
                            cold_water_temperature,
                            event['duration'],
                            self.__water_heating_pipework) * (event['duration']/units.minutes_per_hour
                            )

            for name, bath in self.__baths.items():
                # Get all bath use events for the current timestep
                usage_events = self.__event_schedules['Bath'][name][t_idx]
                the_cold_water_temp = bath.get_cold_water_source()
                cold_water_temperature = the_cold_water_temp.temperature()

                # Assume flow rate for bath event is the same as other hot water events
                peak_flowrate = bath.get_flowrate()

                # If bath is used in the current timestep, get details of use
                # and calculate HW demand from bath
                # Note that bath size is the total water used per bath, not the total capacity of the bath
                if usage_events is not None:
                    for event in usage_events:
                        bath_temp = event['temperature']
                        hw_demand += bath.hot_water_demand(bath_temp)
                        bath_duration = bath.get_size() / peak_flowrate
                        hw_energy_demand += misc.water_demand_to_kWh(
                            bath.hot_water_demand(bath_temp),
                            bath_temp,
                            cold_water_temperature
                            )
                        hw_duration += bath_duration
                        # litres bath  / litres per minute flowrate = minutes
                        all_events += 1
                        pw_losses += calc_pipework_losses(
                            bath.hot_water_demand(bath_temp),
                            t_idx,
                            delta_t_h,
                            cold_water_temperature,
                            bath_duration,
                            self.__water_heating_pipework) * (bath_duration/units.minutes_per_hour)
                        
            return hw_demand, hw_duration, all_events, pw_losses, hw_energy_demand  # litres hot water per timestep, minutes demand per timestep, number of events in timestep

        def calc_pipework_losses(hw_demand, t_idx, delta_t_h, cold_water_temperature, hw_duration, hw_pipework):
            # sum up all hw_demand and allocate pipework losses also.
            # hw_demand is volume.

            # TODO demand water temperature is 52 as elsewhere, need to set it somewhere
            demand_water_temperature = 52
            
            # Initialise internal air temperature and total area of all zones
            internal_air_temperature = 0
            overall_volume = 0
            
            # TODO here we are treating overall indoor temperature as average of all zones
            for z_name, zone in self.__zones.items():
                internal_air_temperature += zone.temp_internal_air() * zone.volume()
                overall_volume += zone.volume()
            internal_air_temperature /= overall_volume # average internal temperature
            
            hot_water_time_fraction = hw_duration / (delta_t_h * units.minutes_per_hour)
            
            if hot_water_time_fraction>1:
                hot_water_time_fraction = 1
            
            pipework_watts_heat_loss \
                = hw_pipework["internal"].heat_loss(demand_water_temperature, internal_air_temperature) \
                + hw_pipework["external"].heat_loss(demand_water_temperature, self.__external_conditions.air_temp())

            # only calculate loss for times when there is hot water in the pipes - multiply by time fraction to get to kWh
            pipework_heat_loss = pipework_watts_heat_loss * hot_water_time_fraction * (delta_t_h * units.seconds_per_hour) / units.W_per_kW # convert to kWh
            
            pipework_heat_loss += hw_pipework["internal"].cool_down_loss(
                demand_water_temperature,
                internal_air_temperature
                )
            pipework_heat_loss += hw_pipework["external"].cool_down_loss(
                demand_water_temperature,
                self.__external_conditions.air_temp()
                )
            
            return pipework_heat_loss # heat loss in kWh for the timestep

        def calc_ductwork_losses(t_idx, delta_t_h, efficiency):
            """ Calculate the losses/gains in the MVHR ductwork

            Arguments:
            t_idx -- timestep index/count
            delta_t_h -- calculation timestep, in hours
            efficiency - MVHR heat recovery efficiency
            """
            # assume 100% efficiency 
            # i.e. temp inside the supply and extract ducts is room temp and temp inside exhaust and intake is external temp
            # assume MVHR unit is running 100% of the time
    
            # Initialise internal air temperature and total area of all zones
            internal_air_temperature = 0
            overall_volume = 0
    
            # Calculate internal air temperature
            # TODO here we are treating overall indoor temperature as average of all zones
            for z_name, zone in self.__zones.items():
                internal_air_temperature += zone.temp_internal_air() * zone.volume()
                overall_volume += zone.volume()
            internal_air_temperature /= overall_volume # average internal temperature

            # Calculate heat loss from ducts when unit is inside
            # Air temp inside ducts increases, heat lost from dwelling
            ductwork = self.__space_heating_ductwork
            if ductwork == None:
                return 0

            ductwork_watts_heat_loss = 0.0

            # MVHR duct temperatures:
            # extract_duct_temp - indoor air temperature 
            # intake_duct_temp - outside air temperature
            
            temp_diff = internal_air_temperature - self.__external_conditions.air_temp()
            
            # Supply duct contains what the MVHR could recover
            supply_duct_temp = self.__external_conditions.air_temp() + (efficiency * temp_diff)
            
            # Exhaust duct contans the heat that couldn't be recovered
            exhaust_duct_temp = self.__external_conditions.air_temp() + ((1- efficiency) * temp_diff)
            
            ductwork_watts_heat_loss = \
                ductwork.total_duct_heat_loss(
                internal_air_temperature,
                supply_duct_temp,
                internal_air_temperature,
                self.__external_conditions.air_temp(),
                exhaust_duct_temp,
                efficiency)
    
            return ductwork_watts_heat_loss, overall_volume # heat loss in Watts for the timestep

        def calc_space_heating(delta_t_h):
            """ Calculate space heating demand, heating system output and temperatures

            Arguments:
            delta_t_h -- calculation timestep, in hours
            """
            temp_ext_air = self.__external_conditions.air_temp()
            # Calculate timestep in seconds
            delta_t = delta_t_h * units.seconds_per_hour

            ductwork_losses, overall_zone_volume, ductwork_losses_per_m3 = 0.0, 0.0, 0.0
            # ductwork gains/losses only for MVHR
            if isinstance(self.__ventilation, MechnicalVentilationHeatRecovery):
                ductwork_losses, overall_zone_volume = calc_ductwork_losses(0, delta_t_h, self.__ventilation.efficiency())
                ductwork_losses_per_m3 = ductwork_losses / overall_zone_volume

            # Calculate internal and solar gains for each zone
            gains_internal_zone = {}
            gains_solar_zone = {}
            for z_name, zone in self.__zones.items():
                gains_internal_zone_inner = 0.0
                for internal_gains_name, internal_gains_object in self.__internal_gains.items():
                    gains_internal_zone_inner\
                        += internal_gains_object.total_internal_gain(zone.area())
                gains_internal_zone[z_name] = gains_internal_zone_inner
                # Add gains from ventilation fans (make sure this is only called
                # once per timestep per zone)
                if self.__ventilation is not None:
                    gains_internal_zone[z_name] += self.__ventilation.fans(zone.volume())
                    gains_internal_zone[z_name] += ductwork_losses_per_m3 * zone.volume()

                gains_solar_zone[z_name] = zone.gains_solar()

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

                space_heat_demand_zone[z_name], space_cool_demand_zone[z_name] = \
                    zone.space_heat_cool_demand(
                        delta_t_h,
                        temp_ext_air,
                        gains_internal_zone[z_name],
                        gains_solar_zone[z_name],
                        )

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

                zone.update_temperatures(
                    delta_t,
                    temp_ext_air,
                    gains_internal_zone[z_name],
                    gains_solar_zone[z_name],
                    gains_heat_cool
                    )

                if h_name is None:
                    space_heat_demand_system[h_name] = 'n/a'
                if c_name is None:
                    space_cool_demand_system[c_name] = 'n/a'

                internal_air_temp[z_name] = zone.temp_internal_air()
                operative_temp[z_name] = zone.temp_operative()

            return gains_internal_zone, gains_solar_zone, \
                   operative_temp, internal_air_temp, \
                   space_heat_demand_zone, space_cool_demand_zone, \
                   space_heat_demand_system, space_cool_demand_system, \
                   ductwork_losses

        timestep_array = []
        gains_internal_dict = {}
        gains_solar_dict = {}
        operative_temp_dict = {}
        internal_air_temp_dict = {}
        space_heat_demand_dict = {}
        space_cool_demand_dict = {}
        space_heat_demand_system_dict = {}
        space_cool_demand_system_dict = {}
        zone_list = []
        hot_water_demand_dict = {}
        hot_water_energy_demand_dict = {}
        hot_water_duration_dict = {}
        hot_water_no_events_dict = {}
        hot_water_pipework_dict = {}

        for z_name in self.__zones.keys():
            gains_internal_dict[z_name] = []
            gains_solar_dict[z_name] = []
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
        hot_water_energy_demand_dict['energy_demand'] = []
        hot_water_duration_dict['duration'] = []
        hot_water_no_events_dict['no_events'] = []
        hot_water_pipework_dict['pw_losses'] = []

        # Loop over each timestep
        for t_idx, t_current, delta_t_h in self.__simtime:
            timestep_array.append(t_current)
            hw_demand, hw_duration, no_events, pw_losses, hw_energy_demand = hot_water_demand(t_idx)
            
            self.__hot_water_sources['hw cylinder'].demand_hot_water(hw_demand)
            # TODO Remove hard-coding of hot water source name
            
            gains_internal_zone, gains_solar_zone, \
                operative_temp, internal_air_temp, \
                space_heat_demand_zone, space_cool_demand_zone, \
                space_heat_demand_system, space_cool_demand_system, \
                ductwork_gains \
                = calc_space_heating(delta_t_h)

            for z_name, gains_internal in gains_internal_zone.items():
                gains_internal_dict[z_name].append(gains_internal)

            for z_name, gains_solar in gains_solar_zone.items():
                gains_solar_dict[z_name].append(gains_solar)

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
            hot_water_energy_demand_dict['energy_demand'].append(hw_energy_demand)
            hot_water_duration_dict['duration'].append(hw_duration)
            hot_water_no_events_dict['no_events'].append(no_events)
            hot_water_pipework_dict['pw_losses'].append(pw_losses)

            #loop through on-site energy generation
            for g_name, gen in self.__on_site_generation.items():
                # Get energy produced for the current timestep
                self.__on_site_generation[g_name].produce_energy()

            for _, supply in self.__energy_supplies.items():
                supply.calc_energy_import_export_betafactor()

        zone_dict = {
            'Internal gains': gains_internal_dict,
            'Solar gains': gains_solar_dict,
            'Operative temp': operative_temp_dict,
            'Internal air temp': internal_air_temp_dict,
            'Space heat demand': space_heat_demand_dict,
            'Space cool demand': space_cool_demand_dict,
            }
        hc_system_dict = {'Heating system': space_heat_demand_system_dict, 'Cooling system': space_cool_demand_system_dict}
        hot_water_dict = {'Hot water demand': hot_water_demand_dict, 'Hot water energy demand': hot_water_energy_demand_dict, 'Hot water duration': hot_water_duration_dict, 'Hot Water Events': hot_water_no_events_dict, 'Pipework losses': hot_water_pipework_dict}

        # Return results from all energy supplies
        results_totals = {}
        results_end_user = {}
        energy_import = {}
        energy_export = {}
        betafactor = {}
        for name, supply in self.__energy_supplies.items():
            results_totals[name] = supply.results_total()
            results_end_user[name] = supply.results_by_end_user()
            energy_import[name] = supply.get_energy_import()
            energy_export[name] = supply.get_energy_export()
            betafactor[name] = supply.get_beta_factor()
        return \
            timestep_array, results_totals, results_end_user, \
            energy_import, energy_export, betafactor, \
            zone_dict, zone_list, hc_system_dict, hot_water_dict, \
            ductwork_gains
