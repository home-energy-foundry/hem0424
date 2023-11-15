#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides functions to implement notional building
for the Future Homes Standard.
"""

import math
import sys
import os
import numpy as np
from copy import deepcopy
from core.project import Project
from core.space_heat_demand.building_element import BuildingElement, HeatFlowDirection
import core.units as units
from wrappers.future_homes_standard.future_homes_standard import calc_TFA, livingroom_setpoint_fhs, restofdwelling_setpoint_fhs, energysupplyname_electricity

# Default names
notional_HIU = 'notionalHIU'
notional_HP = 'notional_HP'
hw_timer = "hw timer"
hw_timer_eco7 = "hw timer eco7"
heating_pattern = "HeatingPattern_Null"

def apply_fhs_not_preprocessing(project_dict,
                                fhs_notA_assumptions,
                                fhs_notB_assumptions,
                                fhs_FEE_notA_assumptions,
                                fhs_FEE_notB_assumptions):
    """ Apply assumptions and pre-processing steps for the Future Homes Standard Notional building """

    is_notA = fhs_notA_assumptions or fhs_FEE_notA_assumptions
    is_FEE  = fhs_FEE_notA_assumptions or fhs_FEE_notB_assumptions

    # Check if a heat network is present
    is_heat_network = check_heatnetwork_present(project_dict)

    # Determine cold water source
    cold_water_type = list(project_dict['ColdWaterSource'].keys())
    if len(cold_water_type) == 1:
        cold_water_source = cold_water_type[0]
    else:
        sys.exit('Error: There should be exactly one cold water type')

    # Determine the TFA
    TFA = calc_TFA(project_dict)

    edit_lighting_efficacy(project_dict)
    edit_infiltration(project_dict,is_notA)
    edit_opaque_ajdZTU_elements(project_dict)
    edit_transparent_element(project_dict, TFA)
    edit_glazing_for_glazing_limit(project_dict, TFA)
    edit_ground_floors(project_dict)
    edit_thermal_bridging(project_dict)

    # Modify control object
    control_objects(project_dict)

    # Edit space heating system
    edit_space_heating_system(
        project_dict,
        cold_water_source,
        TFA,
        is_heat_network,
        is_FEE,
        )

    # modify bath, shower and other dhw characteristics
    edit_bath_shower_other(project_dict, cold_water_source)

    # add WWHRS if needed
    add_wwhrs(project_dict, cold_water_source, is_notA, is_FEE)
    
    #modify hot water distribution
    edit_hot_water_distribution_inner(project_dict, TFA)
    remove_hot_water_distribution_external(project_dict)
    
    #remove pv diverter or electric battery if present
    remove_pv_diverter_if_present(project_dict)
    remove_electric_battery_if_present(project_dict)

    # modify ventilation
    minimum_ach = minimum_air_change_rate(project_dict, TFA) 
    edit_ventilation(project_dict, is_notA, minimum_ach)

    # Modify air conditioning
    edit_spacecoolsystem(project_dict)

    # Add Solar PV 
    add_solar_PV(project_dict, is_notA, is_FEE, TFA)

    return project_dict

def check_heatnetwork_present(project_dict):
    is_heat_network = False
    if "HeatSourceWet" in project_dict.keys():
        for heat_source_dict in project_dict["HeatSourceWet"].values():
            if heat_source_dict['type'] == 'HIU':
                is_heat_network = True
                break
            elif 'source_type' in heat_source_dict.keys():
                if heat_source_dict['source_type'] == 'HeatNetwork':
                    is_heat_network = True
                    break
    return is_heat_network

def edit_lighting_efficacy(project_dict):
    '''
    Apply notional lighting efficacy
    
    efficacy = 120 lm/W
    '''
    lighting_efficacy = 120
    for zone in project_dict["Zone"]:
        if "Lighting"  not in project_dict["Zone"][zone].keys():
            sys.exit("missing lighting in zone "+ zone)
        project_dict["Zone"][zone]["Lighting"]["efficacy"] = lighting_efficacy

def edit_infiltration(project_dict,is_notA):
    '''
    Apply Notional infiltration specifications
    
    Notional option A pressure test result at 50Pa = 4 m3/h.m2
    Notional option B pressure test result at 50Pa = 5 m3/h.m2
    All passive openings count are set to zero
    Mechanical extract fans count follows the Actual dwelling,
    with the exception that there must be at least one per wet room
    '''
    
    #pressure test results dependent on Notional option A or B
    if is_notA:
        test_result = 4
    else:
        test_result = 5
    
    #c onvert from air permeability to ach
    test_result_ach \
        = test_result \
        * project_dict['Infiltration']['env_area'] \
        / project_dict['Infiltration']['volume']
    
    project_dict['Infiltration']['test_type'] = '50Pa'
    project_dict['Infiltration']['test_result'] = test_result_ach
    
    #all openings set to 0
    openings = ['open_chimneys','open_flues','closed_fire','flues_d',
                'flues_e','blocked_chimneys','passive_vents','gas_fires']
    for opening in openings:
        project_dict['Infiltration'][opening] = 0
    
    #extract_fans follow the same as the actual dwelling
    #but there must be a minimum of one extract fan
    #per wet room, as per ADF guidance
    if "NumberOfWetRooms" not in project_dict.keys():
        sys.exit("missing NumberOfWetRooms - required for FHS notional building")
    else:
        wet_rooms_count = project_dict["NumberOfWetRooms"]
    if wet_rooms_count <= 1:
        sys.exit('invalid/missing NumberOfWetRooms')
    if project_dict['Infiltration']['extract_fans'] < wet_rooms_count:
        project_dict['Infiltration']['extract_fans'] = wet_rooms_count

def edit_opaque_ajdZTU_elements(project_dict):
    """ Apply notional u-value (W/m2K) to: 
            external elements: walls (0.18), doors (1.0), roofs (0.11), exposed floors (0.13)
            elements adjacent to unheated space: walls (0.18), ceilings (0.11), floors (0.13)
        
        to differenciate external doors from walls, user input: is_external_door
    """
    for zone in project_dict['Zone'].values():
        for building_element in zone['BuildingElement'].values():
            if building_element['type'] in \
            ('BuildingElementOpaque', 'BuildingElementAdjacentZTU_Simple'):
                if BuildingElement.pitch_class(building_element['pitch']) == \
                    HeatFlowDirection.DOWNWARDS:
                    #exposed floor or floor adjacent to unheated space
                    building_element['u_value'] = 0.13
                elif BuildingElement.pitch_class(building_element['pitch']) == \
                    HeatFlowDirection.UPWARDS:
                    #roof or ceiling adjacent to unheated space
                    building_element['u_value'] = 0.11
                elif BuildingElement.pitch_class(building_element['pitch']) == \
                    HeatFlowDirection.HORIZONTAL:
                    #external walls and walls adjacent to unheated space
                    building_element['u_value'] = 0.18
                    #exception if external door
                    if building_element['type'] == 'BuildingElementOpaque':
                        if 'is_external_door' not in building_element.keys():
                            sys.exit('Missing is_external_door - needed distinguish between external walls and doors')
                        if building_element['is_external_door'] == True:
                            building_element['u_value'] = 1.0
                else:
                    sys.exit('missing or unrecognised pitch in opaque element')
                #remove the r_c input if it was there, as engine would prioritise r_c over u_value
                building_element.pop('r_c', None)

def edit_transparent_element(project_dict, TFA):
    '''
    Apply notional u-value to windows & glazed doors and rooflights
    
    for windows and glazed doors
    u-value is 1.2

    for rooflights
    u-value is 1.7
    the max rooflight area is exactly defined as:
    Max area of glazing if rooflight, as a % of TFA = 25% of TFA - % reduction
    where % reduction = area of actual rooflight as a % of TFA * ((actual u-value of rooflight - 1.2)/1.2)
    
    interpret the instruction for max rooflight area as:
    max_area_reduction_factor = total_rooflight_area / TFA * ((average_uvalue - 1.2)/1.2)
    where
        total_rooflight_area = total area of all rooflights combined
        average_uvalue = area weighted average actual rooflight u-value
    
    max_rooflight_area = maximum allowed total area of all rooflights combined
    max_rooflight_area = TFA*0.25*max_area_reduction_factor
    
    TODO - awaiting confirmation from DLUHC/DESNZ that interpretation is correct
    '''
    total_rooflight_area = 0
    sum_uval_times_area = 0
    for zone in project_dict['Zone'].values():
        for building_element_name, building_element in zone['BuildingElement'].items():
            if building_element['type'] == 'BuildingElementTransparent':
                if BuildingElement.pitch_class(building_element['pitch']) == \
                     HeatFlowDirection.UPWARDS:
                    #rooflight
                    rooflight_area = building_element['height'] * building_element['width']
                    total_rooflight_area += rooflight_area
                    sum_uval_times_area += building_element['u_value'] * rooflight_area
                    building_element['u_value'] = 1.7
                    building_element.pop('r_c', None)

                else:
                    #if it is not a roof light, it is a glazed door or window
                    building_element['u_value'] = 1.2
                    building_element.pop('r_c', None)


def split_glazing_and_walls(project_dict):
    """Split windows/rooflights and walls/roofs into dictionaries."""
    windows_rooflight = {}
    walls_roofs = {}
    for zone in project_dict['Zone'].values():
        for building_element_name, building_element in zone['BuildingElement'].items():
            if building_element['type'] == 'BuildingElementTransparent':
                windows_rooflight[building_element_name] = building_element
            elif building_element['type'] == 'BuildingElementOpaque':
                walls_roofs[building_element_name] = building_element
            elif building_element['type'] == 'BuildingElementGround'\
            or building_element['type'] == 'BuildingElementAdjacentZTC'\
            or building_element['type'] == 'BuildingElementAdjacentZTU_Simple':
                pass
            else:
                sys.exit('Error: unknown building element type')
    
    return windows_rooflight, walls_roofs

def calculate_area_diff_and_adjust_glazing_area(linear_reduction_factor, window_rooflight):
    """Calculate difference between old  and new glazing area and adjust the glazing areas"""
    old_area = window_rooflight['height'] * window_rooflight['width']
    window_rooflight['height'] *= linear_reduction_factor
    window_rooflight['width'] *= linear_reduction_factor
    new_area = window_rooflight['height'] * window_rooflight['width']
    area_diff = old_area - new_area
    return area_diff

def find_walls_roofs_with_same_orientation_and_pitch(walls_roofs, window_rooflight):
    """ Find all walls/roofs with same orientation and pitch as this window/rooflight."""
    orientation = window_rooflight['orientation360']
    pitch = window_rooflight['pitch']

    same_orientation = [
        wall_roof for wall_roof in walls_roofs.values()
        if wall_roof['orientation360'] == orientation
        and wall_roof['pitch'] == pitch
        ]

    if not same_orientation:
        raise ValueError(" There are no walls/roofs with the same orientation"
                         " and pitch as this window/rooflight. ")

    return same_orientation

def calc_max_glazing_area_fraction(project_dict, TFA):
    """ Calculate max glazing area fraction for notional building, adjusted for rooflights """
    total_rooflight_area = 0.0
    sum_uval_times_area = 0.0
    for zone in project_dict['Zone'].values():
        for building_element in zone['BuildingElement'].values():
            if building_element['type'] == 'BuildingElementTransparent' \
            and BuildingElement.pitch_class(building_element['pitch']) \
            == HeatFlowDirection.UPWARDS:
                rooflight_area = building_element['height'] * building_element['width']
                total_rooflight_area += rooflight_area
                sum_uval_times_area += rooflight_area * building_element['u_value']

    if total_rooflight_area == 0.0:
        rooflight_correction_factor = 0.0
    else:
        average_rooflight_uval = sum_uval_times_area / total_rooflight_area
        rooflight_proportion = total_rooflight_area / TFA
        rooflight_correction_factor = max(
            0.0,
            rooflight_proportion * (average_rooflight_uval - 1.2) / 1.2,
            )
    return 0.25 - rooflight_correction_factor

def edit_glazing_for_glazing_limit(project_dict, TFA):
    """" Resize window/rooflight and wall/roofs to meet glazing limits"""
    total_glazing_area = sum(
        building_element['height'] * building_element['width']
        for zone in project_dict['Zone'].values()
        for building_element in zone['BuildingElement'].values()
        if building_element['type'] == 'BuildingElementTransparent'
        )
    max_glazing_area_fraction = calc_max_glazing_area_fraction(project_dict, TFA)
    max_glazing_area = max_glazing_area_fraction * TFA
    windows_rooflight, walls_roofs = split_glazing_and_walls(project_dict)

    if total_glazing_area > max_glazing_area:
        linear_reduction_factor = math.sqrt(max_glazing_area / total_glazing_area)
        for window_rooflight in windows_rooflight.values():
            area_diff = calculate_area_diff_and_adjust_glazing_area(linear_reduction_factor, window_rooflight)
            same_orientation = find_walls_roofs_with_same_orientation_and_pitch(
                walls_roofs, 
                window_rooflight,
                )
            wall_roof_area_total = sum(wall_roof['area'] for wall_roof in same_orientation)

            for wall_roof in same_orientation:
                wall_roof_prop =  wall_roof['area'] / wall_roof_area_total
                wall_roof['area'] += area_diff * wall_roof_prop

def edit_ground_floors(project_dict):
    '''
    Apply notional building ground specifications
    u-value = 0.13 W/m2.K
    thermal resistance of the floor construction,excluding the ground, r_f = 6.12 m2.K/W
    linear thermal transmittance, psi_wall_floor_junc = 0.16 W/m.K
    
    TODO - waiting from DLUHC/DESNZ for clarification if basement floors and basement walls are treated the same
    '''
    for zone in project_dict['Zone'].values():
        for building_element_name, building_element in zone['BuildingElement'].items():
            if building_element['type'] == 'BuildingElementGround':
                building_element['u_value'] = 0.13
                building_element['r_f'] = 6.12
                building_element['psi_wall_floor_junc'] = 0.16

def edit_thermal_bridging(project_dict):
    '''
    The notional building must follow the same thermal bridges as specified in
    SAP10.2 Table R2
    
    TODO - how to deal with ThermalBridging when lengths are not specified?
    '''
    table_R2 = {
        'E1' : 0.05,
        'E2' : 0.05,
        'E3' : 0.05,
        'E4' : 0.05,
        'E5' : 0.16,
        'E19' : 0.07,
        'E20' : 0.32,
        'E21' : 0.32,
        'E22' : 0.07,
        'E6' : 0,
        'E7' : 0.07,
        'E8' : 0,
        'E9' : 0.02,
        'E23' : 0.02,
        'E10' : 0.06,
        'E24' : 0.24,
        'E11' : 0.04,
        'E12' : 0.06,
        'E13' : 0.08,
        'E14' : 0.08,
        'E15' : 0.56,
        'E16' : 0.09,
        'E17' : -0.09,
        'E18' : 0.06,
        'E25' : 0.06,
        'P1' : 0.08,
        'P6' : 0.07,
        'P2' : 0,
        'P3' : 0,
        'P7' : 0.16,
        'P8' : 0.24,
        'P4' : 0.12,
        'P5' : 0.08 ,
        'R1' : 0.08,
        'R2' : 0.06,
        'R3' : 0.08,
        'R4' : 0.08,
        'R5' : 0.04,
        'R6' : 0.06,
        'R7' : 0.04,
        'R8' : 0.06,
        'R9' : 0.04,
        'R10' : 0.08,
        'R11' : 0.08
        }
    for zone in project_dict['Zone'].values():
        if type(zone['ThermalBridging']) is dict:
            for thermal_bridge in zone['ThermalBridging'].values():
                if thermal_bridge['type'] == 'ThermalBridgePoint':
                    thermal_bridge['heat_transfer_coeff'] = 0.0
                elif thermal_bridge['type'] == 'ThermalBridgeLinear':
                    junction_type = thermal_bridge['junction_type']
                    if not junction_type in table_R2.keys():
                        sys.exit('Invalid linear thermal bridge \"junction_type\": {junction_type}. \
                        Option must be one available in SAP10.2 Table R2')
                    thermal_bridge['linear_thermal_transmittance'] = table_R2[junction_type]


def edit_add_heatnetwork_heating(project_dict, cold_water_source):
    '''
    Apply heat network settings to notional building calculation in project_dict.
    '''
    heat_network_name = "_notional_heat_network"

    project_dict['HeatSourceWet'] = {
        notional_HIU: {
            "type": "HIU",
            "EnergySupply": heat_network_name,
            "power_max": 45,
            "HIU_daily_loss": 0.8,
            "building_level_distribution_losses": 62,
        }
    }

    project_dict['HotWaterSource'] = {
        "hw cylinder": {
            "type": "HIU",
            "ColdWaterSource": cold_water_source,
            "HeatSourceWet": notional_HIU,
            "Control": hw_timer
            }
        }

    heat_network_fuel_data = {
        heat_network_name: {
            "fuel": "custom",
            "factor":{
                "Emissions Factor kgCO2e/kWh": 0.033,
                "Emissions Factor kgCO2e/kWh including out-of-scope emissions": 0.033,
                "Primary Energy Factor kWh/kWh delivered": 0.75
                }
            }
        }
    project_dict['EnergySupply'].update(heat_network_fuel_data)

def edit_add_default_space_heating_system(project_dict, design_capacity_overall):
    '''
    Apply default space heating system to notional building calculation
    
    '''
    factors_35 = {'A':1.00, 'B':0.62, 'C':0.55, 'D':0.47, 'F':1.05}
    factors_55 = {'A':0.99, 'B':0.60, 'C':0.49, 'D':0.51, 'F':1.03}

    capacity_results_dict_35 = {}
    for record, factor in factors_35.items():
        result = round(design_capacity_overall * factor, 3)
        capacity_results_dict_35[record] = result
    
    capacity_results_dict_55 = {}
    for record, factor in factors_55.items():
        result = round(design_capacity_overall * factor, 3)
        capacity_results_dict_55[record] = result

    project_dict['HeatSourceWet'] = {}
    space_heating_system = {
        notional_HP: {
            "EnergySupply": "mains elec",
            "backup_ctrl_type": "TopUp",
            "min_modulation_rate_35": 0.4,
            "min_modulation_rate_55": 0.4,
            "min_temp_diff_flow_return_for_hp_to_operate": 0,
            "modulating_control": True,
            "power_crankcase_heater": 0.01,
            "power_heating_circ_pump": capacity_results_dict_55['F'] * 0.003,
            "power_max_backup": 3,
            "power_off": 0,
            "power_source_circ_pump": 0,
            "power_standby": 0.01,
            "sink_type": "Water",
            "source_type": "OutsideAir",
            "temp_lower_operating_limit": -10,
            "temp_return_feed_max": 60,
            "test_data": [
                {
                    "capacity": capacity_results_dict_35['A'],
                    "cop": 2.788,
                    "degradation_coeff": 0.9,
                    "design_flow_temp": 35,
                    "temp_outlet": 34,
                    "temp_source": -7,
                    "temp_test": -7,
                    "test_letter": "A"
                },
                {
                    "capacity": capacity_results_dict_35['B'],
                    "cop": 4.292,
                    "degradation_coeff": 0.9,
                    "design_flow_temp": 35,
                    "temp_outlet": 30,
                    "temp_source": 2,
                    "temp_test": 2,
                    "test_letter": "B"
                },
                {
                    "capacity": capacity_results_dict_35['C'],
                    "cop": 5.906,
                    "degradation_coeff": 0.9,
                    "design_flow_temp": 35,
                    "temp_outlet": 27,
                    "temp_source": 7,
                    "temp_test": 7,
                    "test_letter": "C"
                },
                {
                    "capacity": capacity_results_dict_35['D'],
                    "cop": 8.016,
                    "degradation_coeff": 0.9,
                    "design_flow_temp": 35,
                    "temp_outlet": 24,
                    "temp_source": 12,
                    "temp_test": 12,
                    "test_letter": "D"
                },
                {
                    "capacity": capacity_results_dict_35['F'],
                    "cop": 2.492,
                    "degradation_coeff": 0.9,
                    "design_flow_temp": 35,
                    "temp_outlet": 35,
                    "temp_source": -10,
                    "temp_test": -10,
                    "test_letter": "F"
                },
                {
                    "capacity": capacity_results_dict_55['A'],
                    "cop": 2.034,
                    "degradation_coeff": 0.9,
                    "design_flow_temp": 55,
                    "temp_outlet": 52,
                    "temp_source": -7,
                    "temp_test": -7,
                    "test_letter": "A"
                },
                {
                    "capacity": capacity_results_dict_55['B'],
                    "cop": 3.118,
                    "degradation_coeff": 0.9,
                    "design_flow_temp": 55,
                    "temp_outlet": 42,
                    "temp_source": 3,
                    "temp_test": 2,
                    "test_letter": "B"
                },
                {
                    "capacity": capacity_results_dict_55['C'],
                    "cop": 4.406,
                    "degradation_coeff": 0.9,
                    "design_flow_temp": 55,
                    "temp_outlet": 36,
                    "temp_source": 7,
                    "temp_test": 7,
                    "test_letter": "C"
                },
                {
                    "capacity": capacity_results_dict_55['D'],
                    "cop": 6.298,
                    "degradation_coeff": 0.9,
                    "design_flow_temp": 55,
                    "temp_outlet": 30,
                    "temp_source": 12,
                    "temp_test": 12,
                    "test_letter": "D"
                },
                {
                    "capacity": capacity_results_dict_55['F'],
                    "cop": 1.868,
                    "degradation_coeff": 0.9,
                    "design_flow_temp": 55,
                    "temp_outlet": 55,
                    "temp_source": -10,
                    "temp_test": -10,
                    "test_letter": "F"
                }
            ],
            "time_constant_onoff_operation": 140,
            "time_delay_backup": 1,
            "type": "HeatPump",
            "var_flow_temp_ctrl_during_test": True
        }
    }
    project_dict['HeatSourceWet'] = space_heating_system


def edit_default_space_heating_distribution_system(project_dict, design_capacity_dict):
    '''Apply distribution system details to notional building calculation '''

    design_flow_temp = 45 
    c_per_rad = 0.01
    n = 1.34
    thermal_mass_per_rad = 51.8 / units.J_per_kWh

    # Initialise space heating system in project dict
    project_dict['SpaceHeatSystem'] = {}

    for zone_name, zone in project_dict['Zone'].items():
        project_dict['Zone'][zone_name]['SpaceHeatSystem'] = zone_name + '_SpaceHeatSystem_Notional'
        heatsourcewet_name = list(project_dict['HeatSourceWet'].keys())
        
        # Calculate number of radiators
        emitter_cap = design_capacity_dict[zone_name]
        power_output_per_rad = c_per_rad * (design_flow_temp - set_point_per_zone(zone)) ** n
        number_of_rads = math.ceil(emitter_cap / power_output_per_rad)

        # Calculate c and thermal mass
        c = number_of_rads * c_per_rad
        thermal_mass = number_of_rads * thermal_mass_per_rad

        # Create radiator dict for zone
        space_distribution_system = {
            "type": "WetDistribution",
            "advanced_start": 1,
            "thermal_mass": thermal_mass,
            "c": c,
            "n": n,
            "temp_diff_emit_dsgn": 5,
            "frac_convective": 0.7,
            "HeatSource": {
                "name": heatsourcewet_name[0],
                "temp_flow_limit_upper": 65.0
            },
            "ecodesign_controller": {
                    "ecodesign_control_class": 2,
                    "max_outdoor_temp": 20,
                    "min_flow_temp": 25,
                    "min_outdoor_temp": 0
                    },
            "Control": heating_pattern,
            "design_flow_temp": design_flow_temp,
            "Zone": zone_name,
            "temp_setback" : 18
            }

        project_dict['SpaceHeatSystem'][zone_name + '_SpaceHeatSystem_Notional'] = space_distribution_system

def edit_heatnetwork_space_heating_distribution_system(project_dict):
    '''Edit distribution system details to notional building heat network '''

    for distribution_name, distribution in project_dict['SpaceHeatSystem'].items():
        project_dict['SpaceHeatSystem'][distribution_name]['advanced_start'] = 0
        project_dict['SpaceHeatSystem'][distribution_name]["HeatSource"] = {"name": notional_HIU}

def edit_bath_shower_other(project_dict, cold_water_source):
    # Define Bath, Shower, and Other DHW outlet
    project_dict['Bath'] = {
        "medium": {
            "ColdWaterSource": cold_water_source,
            "flowrate": 12,
            "size": 73
        }
    }

    project_dict['Shower'] = {
        "mixer": {
            "ColdWaterSource": cold_water_source,
            "flowrate": 8,
            "type": "MixerShower"
        }
    }

    project_dict['Other'] = {
        "other": {
            "ColdWaterSource": cold_water_source,
            "flowrate": 6
        }
    }

def add_wwhrs(project_dict, cold_water_source, is_notA, is_FEE):
    # add WWHRS if more than 1 storeys in building, notional A and not FEE
    if project_dict['Infiltration']['storeys_in_building'] > 1 and is_notA and not is_FEE:
        shower_dict = project_dict['Shower']['mixer']
        shower_dict["WWHRS"] = "Notional_Inst_WWHRS"
     
        project_dict['WWHRS'] = {
            "Notional_Inst_WWHRS": {
                "ColdWaterSource": cold_water_source,
                "efficiencies": [50, 50],
                "flow_rates": [0, 100],
                "type": "WWHRS_InstantaneousSystemB",
                "utilisation_factor": 0.98
            }
        }

def calculate_daily_losses(cylinder_vol):

    cylinder_loss_constant = 0.005
    factory_insulated_thickness_coeff = 0.55
    thickness = 120  # mm

    #calculate cylinder factor insulated factor
    cylinder_heat_loss_factor = cylinder_loss_constant + factory_insulated_thickness_coeff / (thickness + 4.0)

    # calculate volume factor
    vol_factor = (120 / cylinder_vol) ** (1 / 3)
    
    # Temperature factor
    temp_factor = 0.6 * 0.9

    # Calculate daily losses
    daily_losses = cylinder_heat_loss_factor * vol_factor * temp_factor * cylinder_vol
    
    return daily_losses

def edit_storagetank(project_dict, cold_water_source, TFA):
    #TODO get actual daily hot water demand
    daily_HWD = [2, 4, 6, 8]
    
    # Use sizing logic when  storage tank volume not present
    if 'volume' not in project_dict['HotWaterSource']['hw cylinder']:
        cylinder_vol = calculate_cylinder_volume(daily_HWD)
    else:
        cylinder_vol = project_dict['HotWaterSource']['hw cylinder']['volume']

    # Calculate daily losses
    daily_losses = calculate_daily_losses(cylinder_vol)

    # Modify primary pipework chracteristics
    primary_pipework_dict = edit_primary_pipework(project_dict, TFA)

    # Modify cylinder characteristics
    project_dict['HotWaterSource']['hw cylinder'] = {}
    project_dict['HotWaterSource']['hw cylinder'] = {
            "ColdWaterSource": cold_water_source,
            "HeatSource": {
                notional_HP: {
                    "ColdWaterSource": cold_water_source,
                    "Control": hw_timer,
                    "Control_hold_at_setpnt": hw_timer_eco7, 
                    "EnergySupply": energysupplyname_electricity,
                    "heater_position": 0.1,
                    "name": notional_HP,
                    "temp_flow_limit_upper": 60,
                    "thermostat_position": 0.1,
                    "type": "HeatSourceWet"
                }
            },
            "daily_losses": daily_losses,
            "type": "StorageTank",
            "volume": cylinder_vol,
            "primary_pipework":primary_pipework_dict
        }

def edit_primary_pipework(project_dict, TFA):
    
    # Define minimum values
    internal_diameter_mm_min = 20
    external_diameter_mm_min = 22
    insulation_thickness_mm_min = 25
    surface_reflectivity = False
    pipe_contents = "water"
    insulation_thermal_conductivity = 0.035
    
    # calculate maximum length
    if project_dict['Infiltration']['build_type'] == 'flat': 
        length_max =  0.05 * TFA
    elif project_dict['Infiltration']['build_type'] == 'house':
        length_max =  0.05 * project_dict['GroundFloorArea']
    else:
        sys.exit('Unrecognised building type')

    # Update primary pipework object when primary pipework not present
    if 'primary_pipework' not in project_dict['HotWaterSource']['hw cylinder']:
        project_dict['HotWaterSource']['hw cylinder']['primary_pipework'] = {}
        # primary pipework dictionary
        primary_pipework_dict = {
                "internal_diameter_mm": internal_diameter_mm_min,
                "external_diameter_mm": external_diameter_mm_min,
                "length": length_max,
                "insulation_thermal_conductivity": insulation_thermal_conductivity,
                "insulation_thickness_mm": insulation_thickness_mm_min,
                "surface_reflectivity": surface_reflectivity,
                "pipe_contents": pipe_contents
            }

    # Update primary pipework object when primary pipework present
    else:
        primary_pipework_dict = project_dict['HotWaterSource']['hw cylinder']['primary_pipework']
        length = primary_pipework_dict['length']
        internal_diameter_mm = max(primary_pipework_dict['internal_diameter_mm'], internal_diameter_mm_min)
        external_diameter_mm = max(primary_pipework_dict['external_diameter_mm'], external_diameter_mm_min)
        # update insulation thickness based on internal diameter
        if internal_diameter_mm > 25:
            insulation_thickness_mm_min = 35

        # primary pipework should not be greater than maximum length
        length = min(length, length_max)

        # primary pipework dictionary
        primary_pipework_dict = {
                "internal_diameter_mm": internal_diameter_mm,
                "external_diameter_mm": external_diameter_mm,
                "length": length,
                "insulation_thermal_conductivity": insulation_thermal_conductivity,
                "insulation_thickness_mm": insulation_thickness_mm_min,
                "surface_reflectivity": surface_reflectivity,
                "pipe_contents": pipe_contents
            }
    return primary_pipework_dict

def edit_hot_water_distribution_inner(project_dict, TFA):
    # hot water dictionary
    hot_water_distribution_inner_dict = project_dict['Distribution']['internal']

    # Defaults
    internal_diameter_mm_min = 13
    external_diameter_mm_min = 15
    insulation_thickness_mm = 20

    # Update length
    length = hot_water_distribution_inner_dict['length']
    length =  min(length, 0.2 * TFA)

    # Update internal diameter to minimum if not present and should not be lower than the minimum
    if 'internal_diameter_mm' not in hot_water_distribution_inner_dict:
        internal_diameter_mm = internal_diameter_mm_min
    else:
        internal_diameter_mm = hot_water_distribution_inner_dict['internal_diameter_mm']

    internal_diameter_mm = max(internal_diameter_mm, internal_diameter_mm_min)

    # Update external diameter to minimum if not present and should not be lower than the minimum
    if 'external_diameter_mm' not in hot_water_distribution_inner_dict:
        external_diameter_mm = external_diameter_mm_min
    else:
        external_diameter_mm = hot_water_distribution_inner_dict['external_diameter_mm']

    external_diameter_mm = max(external_diameter_mm, external_diameter_mm_min)

    # update insulation thickness based on internal diameter
    if internal_diameter_mm > 25:
         insulation_thickness_mm = 24

    hot_water_distribution_inner_dict = {
        "external_diameter_mm": external_diameter_mm,
        "insulation_thermal_conductivity": 35,
        "insulation_thickness_mm": insulation_thickness_mm,
        "internal_diameter_mm": internal_diameter_mm,
        "length": length,
        "pipe_contents": "water",
        "surface_reflectivity": False
        }

def remove_hot_water_distribution_external(project_dict):
    # setting the length to 0 to effectively remove external pipework
    project_dict['Distribution']['external']['length'] = 0.0

def remove_pv_diverter_if_present(project_dict):
    for energy_supply_name, energy_supply in project_dict['EnergySupply'].items():
        if 'diverter' in energy_supply:
            del project_dict['EnergySupply'][energy_supply_name]['diverter']

def remove_electric_battery_if_present(project_dict):
    for energy_supply_name, energy_supply in project_dict['EnergySupply'].items():
        if 'ElectricBattery' in energy_supply:
            del project_dict['EnergySupply'][energy_supply_name]['ElectricBattery']

def minimum_air_change_rate(project_dict, TFA):
    """ Calculate effective air change rate accoring to according to Part F 1.24 a """
    
    # Retrieve the number of bedrooms and total volume
    bedroom_number = project_dict['NumberOfBedrooms']
    total_volume = project_dict['Infiltration']['volume']

    # minimum ventilation rates method B
    min_ventilation_rates_b = [19, 25, 31, 37, 43]
    
    #Calculate minimum whole dwelling ventilation rate l/s method A
    min_ventilation_rate_a = TFA * 0.3

    #Calculate minimum whole dwelling ventilation rate l/s method B
    if bedroom_number <= 5:
        min_ventilation_rate_b = min_ventilation_rates_b[bedroom_number -1]
    elif bedroom_number > 6:
        min_ventilation_rate_b = min_ventilation_rates_b[-1] + (bedroom_number - 5) * 6

    # Calculate air change rate ACH
    minimum_ach = ( max(min_ventilation_rate_a, min_ventilation_rate_b) / total_volume ) \
                    * units.seconds_per_hour / units.litres_per_cubic_metre

    return minimum_ach

def edit_ventilation(project_dict, isnotA, minimum_ach):
    # Retrieve ventilation dictionary
    ventilation = project_dict['Ventilation']

    # Calculate the required air changes per hour
    req_ach = max(ventilation['req_ach'], minimum_ach)

    if  isnotA:
        # Continous decentralised mechanical extract ventilation
        project_dict['Ventilation'] = {
            'type': 'WHEV',
            'req_ach': req_ach,
            'SFP': 0.15,
            "EnergySupply": energysupplyname_electricity
            }
    else:
        # Natural ventilation
        project_dict['Ventilation'] = {
            'type': 'NatVent',
            'req_ach': req_ach,
            }

def edit_space_heating_system(project_dict,
                              cold_water_source,
                              TFA,
                              is_heat_network,
                              is_FEE,
                              ):

    if not is_FEE:
        # If Actual dwelling is heated with heat networks - Notional heated with HIU.
        # Otherwise, notional heated with an air to water heat pump
        if is_heat_network:
            edit_add_heatnetwork_heating(project_dict, cold_water_source)
            edit_heatnetwork_space_heating_distribution_system(project_dict)
        else:
            design_capacity_dict, design_capacity_overall = calc_design_capacity(project_dict)
            edit_add_default_space_heating_system(project_dict, design_capacity_overall)
            edit_default_space_heating_distribution_system(project_dict, design_capacity_dict)
            edit_storagetank(project_dict, cold_water_source, TFA)
    else:
        # FEE calculation which doesn't need the space heating system at this stage.
        pass

def edit_spacecoolsystem(project_dict):
    if project_dict['PartO_active_cooling_required']:
        for space_cooling_name in project_dict['SpaceCoolSystem'].keys():
            project_dict['SpaceCoolSystem'][space_cooling_name]['efficiency'] = 5.1
            project_dict['SpaceCoolSystem'][space_cooling_name]['frac_convective'] = 0.95

def calc_design_capacity(project_dict):
    '''Calculate design capacity for each zone and overall design capacity.'''
    # Make a copy and remove space heating system to initiliase project
    project_dict_copy = deepcopy(project_dict)
    project_dict_copy['SpaceHeatSystem'] = {}

    # Set initial temperature set point for all zones
    initialise_temperature_setpoints(project_dict_copy)

    # Create a Project instance
    project = Project(project_dict_copy, False, False, False)

    # Calculate heat transfer coefficients and heat loss parameters
    heat_trans_coeff, heat_loss_param, HTC_dict, HLP_dict = project.calc_HTC_HLP()

    # Calculate design capacity
    min_air_temp = min(project_dict['ExternalConditions']['air_temperatures'])
    design_capacity_dict = {}
    for zone_name, zone in project_dict['Zone'].items():
        set_point = set_point_per_zone(zone)
        temperature_difference = set_point - min_air_temp
        design_heat_loss = HTC_dict[zone_name] * temperature_difference
        design_capacity = 2 * design_heat_loss
        design_capacity_dict[zone_name] = design_capacity / units.W_per_kW

    design_capacity_overall = sum(design_capacity_dict.values())

    return design_capacity_dict, design_capacity_overall

def set_point_per_zone(zone):
    if zone['SpaceHeatControl'] == 'livingroom':
        set_point = livingroom_setpoint_fhs
    elif zone['SpaceHeatControl'] == 'restofdwelling':
        set_point = restofdwelling_setpoint_fhs
    else:
        sys.exit("Setpoint error - SpaceHeatControl name is not applicable")

    return set_point

def initialise_temperature_setpoints(project_dict):
    ''' Intitilise temperature setpoints for all zones.
    The initial set point is needed to call the Project class. 
    Set as 18C for now. The FHS wrapper will overwrite temp_setpnt_init '''
    for zone_name, zone in project_dict['Zone'].items():
        zone['temp_setpnt_init'] = 18

def add_solar_PV(project_dict, is_notA, is_FEE, TFA):

    number_of_storeys = project_dict['Infiltration']['storeys_in_building']

    # PV is included in the notional if the building contains 15 stories or 
    # less that contain dwellings.
    if number_of_storeys <= 15 and is_notA and not is_FEE: 
        GFA = project_dict['GroundFloorArea']
        if project_dict['Infiltration']['build_type'] == 'house':
            peak_kW = GFA * 0.4 / 4.5
            base_heights = [
                building_element['base_height']
                for zone in project_dict['Zone'].values()
                for building_element_name, building_element in zone['BuildingElement'].items()
                if 'base_height' in building_element
            ]
            base_height_pv = max(base_heights)
        elif project_dict['Infiltration']['build_type'] == 'flat':
            peak_kW = TFA * 0.4 / (4.5 * number_of_storeys)
            zone_volumes = [zone['volume'] for zone in project_dict['Zone'].values()]
            zone_total_volume= sum(zone_volumes)
            zone_areas = [zone['area'] for zone in project_dict['Zone'].values()]
            zone_total_area = sum(zone_areas)
            base_height_pv = (zone_total_volume / zone_total_area + 0.3) * number_of_storeys

        else:
            sys.exit('Unrecognised building type')

        # PV array area
        PV_area = 4.5 * peak_kW
        # PV width and height based on 2:1 aspect ratio
        PV_width = (PV_area / 2)**0.5
        PV_height = 2 * PV_width

        project_dict['OnSiteGeneration'] = {
            "PV1": {
                "EnergySupply": energysupplyname_electricity,
                "orientation360": 180,
                "peak_power": peak_kW,
                "pitch": 45,
                "type": "PhotovoltaicSystem",
                "ventilation_strategy": "moderately_ventilated",
                "base_height": base_height_pv,
                "height":PV_height,
                "width":PV_width,
                }
            }

def control_objects(project_dict):

    project_dict["Control"] = {
        hw_timer: {
            "type": "OnOffTimeControl",
            "start_day": 0,
            "time_series_step": 0.5,
            "schedule": {
                "main": [
                    {
                        "value": "day",
                        "repeat": 365
                    }
                ],
                "day": [
                    {
                        "value": True,
                        "repeat": 48
                    }
                ]
            }
        },
        hw_timer_eco7: {
            "type": "OnOffCostMinimisingTimeControl",
            "start_day": 0,
            "time_series_step": 0.5,
            "time_on_daily": 7,
            "schedule": {
                "main": [
                    {
                        "value": "day",
                        "repeat": 365
                    }
                ],
                "day": [
                    {
                        "value": 0.1436,
                        "repeat": 14
                    },
                    {
                        "value": 0.252,
                        "repeat": 34
                    }
                ]
            }
        },
        "Window_Opening": {
            "type": "SetpointTimeControl",
            "start_day": 0,
            "time_series_step": 0.5,
            "schedule": {
                "main": [
                    {
                        "value": "day",
                        "repeat": 365
                    }
                ],
                "day": [
                    {
                        "value": None,
                        "repeat": 14
                    },
                    {
                        "value": 22.0,
                        "repeat": 34
                    }
                ]
            }
        }
    }

def calculate_cylinder_volume(daily_HWD):

    # Data from the table
    percentiles_kWh   = [3.7, 4.4, 5.2, 5.9, 6.7, 7.4, 8.1, 8.9, 9.6, 10.3, 11.1]
    vessel_sizes_litres = [165, 190, 215, 240, 265, 290, 315, 340, 365, 390, 415]

    # Calculate the 75th percentile of daily hot water demand 
    percentile_75_kWh = np.percentile(daily_HWD, 75)

    # Use numpy's linear interpolation to find the appropriate vessel size
    interpolated_size_litres = np.interp(percentile_75_kWh, percentiles_kWh, vessel_sizes_litres)
    interpolated_size_litres = round(interpolated_size_litres)

    # If the size of the hot water storage vessel is unavailable, the next 
    # largest size available should be selected
    if interpolated_size_litres not in vessel_sizes_litres:
        for size in vessel_sizes_litres:
            if size > interpolated_size_litres:
                next_largest_size = size
                break
        interpolated_size_litres = next_largest_size

    return interpolated_size_litres

