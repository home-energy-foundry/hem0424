#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides functions to implement notional building
for the Future Homes Standard.
"""

import math
import sys
import os
from copy import deepcopy
from core.project import Project
from core.space_heat_demand.building_element import BuildingElement, HeatFlowDirection
import core.units as units
from wrappers.future_homes_standard.future_homes_standard import calc_TFA, livingroom_setpoint_fhs, restofdwelling_setpoint_fhs


def apply_fhs_not_preprocessing(project_dict,
                                fhs_notA_assumptions,
                                fhs_notB_assumptions,
                                fhs_FEE_notA_assumptions,
                                fhs_FEE_notB_assumptions):
    """ Apply assumptions and pre-processing steps for the Future Homes Standard Notional building """
    
    is_notA = fhs_notA_assumptions or fhs_FEE_notA_assumptions
    is_FEE  = fhs_FEE_notA_assumptions or fhs_FEE_notB_assumptions

    # Determine cold water source
    for cold_water_type in project_dict['ColdWaterSource'].keys():
        cold_water_source = cold_water_type

    # Determine the TFA
    TFA = calc_TFA(project_dict)

    edit_lighting_efficacy(project_dict)
    edit_infiltration(project_dict,is_notA)
    edit_opaque_ajdZTU_elements(project_dict)
    edit_transparent_element(project_dict, TFA)
    edit_ground_floors(project_dict)
    edit_thermal_bridging(project_dict)

    # Set initial temperature set point for all zones
    initialise_temperature_setpoints(project_dict)

    # Create a Project instance
    project = Project(deepcopy(project_dict), False, False)

    # Calculate heat transfer coefficients and heat loss parameters
    heat_trans_coeff, heat_loss_param, HTC_dict, HLP_dict  = project.calc_HTC_HLP()

    # Calculate design capacity
    design_capacity_dict, design_capacity_overall = calc_design_capacity(project_dict, HTC_dict)

    # Edit space heating system
    edit_space_heating_system(
        project_dict,
        is_FEE,
        cold_water_source,
        design_capacity_dict,
        design_capacity_overall,
        TFA,
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
    edit_air_conditioning(project_dict)

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
        if "efficacy" not in project_dict["Zone"][zone]["Lighting"].keys():
            sys.exit("missing lighting efficacy in zone "+ zone)
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
    if wet_rooms_count == 0:
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
    there is a max area of windows of 25% of TFA
    
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
    
    total_window_area = 0
    total_rooflight_area = 0
    average_roof_light_u_value = 0
    for zone in project_dict['Zone'].values():
        for building_element_name, building_element in zone['BuildingElement'].items():
            if building_element['type'] == 'BuildingElementTransparent': 
                if not 'is_roof_light' in building_element.keys():
                    sys.exit('Missing input /"is_roof_light/" in transparent element: {building_element_name}')
                if building_element['is_roof_light'] == False:
                    #if it is not a roof light, it is a glazed door or window
                    total_window_area += building_element['height'] * building_element['width']
                    building_element['u_value'] = 1.2
                    building_element.pop('r_c', None)
                elif building_element['is_roof_light'] == True:
                    #rooflight
                    rooflight_area = building_element['height'] * building_element['width']
                    total_rooflight_area += rooflight_area
                    average_roof_light_u_value += building_element['u_value'] * rooflight_area
                    building_element['u_value'] = 1.7
                    building_element.pop('r_c', None)
    
    if total_rooflight_area != 0:
        #avoid divided by 0 if there are no rooflights
        average_roof_light_u_value /= total_rooflight_area
        max_rooflight_area_red_factor = total_rooflight_area / TFA * ((average_roof_light_u_value - 1.2)/1.2)
        max_rooflight_area = TFA*0.25*max_rooflight_area_red_factor
        if total_rooflight_area > max_rooflight_area:
            correct_transparent_area(project_dict, total_rooflight_area, max_rooflight_area, is_rooflight = True)
    
    max_window_area = 0.25 * TFA
    if total_window_area > max_window_area:
        correct_transparent_area(project_dict, total_window_area, max_window_area, is_rooflight = False)

def correct_transparent_area(project_dict, total_area, max_area, is_rooflight = False):
    '''
    Applies correction to transparent elements area and their supporting opaque elements 
    
    TODO - the correction is applied to curtain walls too, awaiting confirmation that this is correct
    '''
    #window_reduction_factor is applied to both height and width (hence sqrt)
    #to preserve similar geometry as in the actual dwelling
    if is_rooflight == False:
        area_reduction_factor = math.sqrt(max_area / total_area)
        for zone in project_dict['Zone'].values():
            for building_element_name, building_element in \
            zone['BuildingElement'].items():
                if building_element['type'] == 'BuildingElementTransparent':
                    old_area = building_element['height'] * building_element['width']
                    building_element['height'] = area_reduction_factor * building_element['height']
                    building_element['width'] = area_reduction_factor * building_element['width']
                    new_area = building_element['height'] * building_element['width']
                    
                    #add the window area difference to the external wall it belongs to
                    #TODO confirm how to deal with curtain walls
                    area_diff = old_area - new_area
                    if 'opaque_support' not in building_element.keys():
                        sys.exit(f'missing element opaque_support in transparent element {building_element_name}')
                    wall_name = building_element['opaque_support']
                    if wall_name in zone['BuildingElement'].keys():
                        zone['BuildingElement'][wall_name]['area'] += area_diff
                    elif wall_name != 'curtain wall':
                        sys.exit(f'Unrecognised opaque_support: \"{wall_name}\". ' +\
                                 'Options are: an existing opaque element name or \"curtain wall\"')

def edit_ground_floors(project_dict):
    '''
    Apply notional building ground specifications
    u-value = 0.13 W/m2.K
    ground thermal resistance, r_f = 6.12 m2.K/W
    linear thermal transmittance, psi_wall_floor_junc = 0.16 W/m.K
    
    TODO - waiting from DELUHC/DESNZ for clarification if basement floors and basement walls are treated the same
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
                        sys.exit(f'Invalid linear thermal bridge \"junction_type\": {junction_type}. \
                        Option must be one available in SAP10.2 Table R2')
                    thermal_bridge['linear_thermal_transmittance'] = table_R2[junction_type]

def edit_FEE_space_heating(project_dict):
    '''
    Apply space heating system to notional building for FEE caluclation
    
    TODO - the specifications spreadsheet mentions a control class 2,
    but it's not applicable for non-wet ditribution systems.
    the spreadsheet also specifies a set back temp, which is odd with direct electric 
    Awaiting clarifications from DELUHC/DESNZ
    '''
    
    for space_heating_name, space_heating in project_dict['SpaceHeatSystem'].items():
        project_dict['SpaceHeatSystem'].pop(space_heating_name)
        project_dict['SpaceHeatSystem'][space_heating_name] = {
            "type": "InstantElecHeater",
            "rated_power": 10000.0,
            "frac_convective": 0.95,
            "temp_setback": 18.0,
            "EnergySupply": "mains elec"
            }

def edit_add_heatnetwork_space_heating(project_dict, cold_water_source):
    '''
    Apply heat network settings to notional building calculation in project_dict.
    '''

    # TODO: Specify the details for HeatSourceWet
    project_dict['HeatSourceWet'] = {
        "HeatNetwork": {
            "type": "HIU",
            "EnergySupply": "heat network",
            "power_max": 45,
            "HIU_daily_loss": 0.8
        }
    }

    project_dict['HotWaterSource'] = {
        "hw cylinder": {
            "type": "HIU",
            "ColdWaterSource": cold_water_source,
            "HeatSourceWet": "HeatNetwork",
            "Control": "hw timer"
            }
        }

    heat_network_fuel_data = {
        "heat network": {
            "fuel": "custom",
            "factor":{
                "Emissions Factor kgCO2e/kWh": 0.041,
                "Emissions Factor kgCO2e/kWh including out-of-scope emissions": 0.041,
                "Primary Energy Factor kWh/kWh delivered": 0.850
                }
            }
        }
    project_dict['EnergySupply'].update(heat_network_fuel_data)

def edit_heatnetwork_space_heating_distribution_system(project_dict):
    '''
    Apply heat network distribution system details to notional building calculation
    
    '''

    for zone_name, zone in project_dict['Zone'].items():
        #TODO currently repeats the same radiator characteristics for both zones
        space_heating_name = zone['SpaceHeatSystem']
        heat_network_distribution_details = {
                "HeatSource": {
                    "name": "HeatNetwork"
                },
                "ecodesign_controller": {
                    "ecodesign_control_class": 2,
                    "max_flow_temp": 45,
                    "max_outdoor_temp": 0,
                    "min_flow_temp": 25,
                    "min_outdoor_temp": 20
                },
                "temp_setback": 18,
                "type": "WetDistribution"
            }
        project_dict['SpaceHeatSystem'][space_heating_name].update(heat_network_distribution_details)

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
        "hp": {
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
            "design_flow_temp": design_flow_temp,
            "Zone": zone_name,
            "temp_setback" : 18
            }

        project_dict['SpaceHeatSystem'][zone_name + '_SpaceHeatSystem_Notional'] = space_distribution_system

def edit_bath_shower_other(project_dict, cold_water_source):
    # Define Bath, Shower, and Other DHW outlet
    project_dict['Bath'] = {
        "medium": {
            "ColdWaterSource": cold_water_source,
            "flowrate": 12,
            "size": 170
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
    # add WWHRS if more than 1 storey, notional A and not FEE
    if project_dict['Infiltration']['storey'] > 1 and is_notA and not is_FEE:
        # TODO storey input now changed
        shower_dict = project_dict['Shower']['mixer']
        shower_dict["WWHRS"] = "Notional_Inst_WWHRS"
     
        project_dict['WWHRS'] = {
            "Notional_Inst_WWHRS": {
                "ColdWaterSource": cold_water_source,
                "efficiencies": [50, 50, 50, 50, 50],
                "flow_rates": [5, 7, 8, 11, 13],
                "type": "WWHRS_InstantaneousSystemB",
                "utilisation_factor": 0.98
            }
        }

def calculate_daily_losses(cylinder_vol, thickness):
    
    factory_insulated_coeff = 0.005
    thickness_coeff = 0.55
    
    #calculate cylinder factor insulated factor
    cylinder_factory_insulated = factory_insulated_coeff + thickness_coeff / (thickness + 4.0)

    # calculate volume factor
    vol_factor = (120 / cylinder_vol) ** (1 / 3)
    
    # Temperature factor
    temp_factor = 0.6 * 0.9

    # Calculate daily losses
    daily_losses = cylinder_factory_insulated * vol_factor * temp_factor
    
    return daily_losses

def edit_storagetank(project_dict, cold_water_source, TFA):
    # look up cylinder volume
    thickness = 120  # mm

    # TODO Calculate cylinder volume
    cylinder_vol = 215

    # Calculate daily losses and update daily losses in project_dict
    daily_losses = calculate_daily_losses(cylinder_vol, thickness)

    #modify primary pipework chracteristics
    primary_pipework_dict = edit_primary_pipework(project_dict, TFA)
    
    # check if cylinder in project_dict
    project_dict['HotWaterSource']['hw cylinder'] = {}
    project_dict['HotWaterSource']['hw cylinder'] = {
            "ColdWaterSource": cold_water_source,
            "HeatSource": {
                "hp": {
                    "ColdWaterSource": cold_water_source,
                    "Control": "hw timer",
                    "EnergySupply": "mains elec",
                    "heater_position": 0.1,
                    "name": "hp",
                    "temp_flow_limit_upper": 55,
                    "thermostat_position": 0.1,
                    "type": "HeatSourceWet"
                }
            },
            "daily_losses": daily_losses,
            "min_temp": 52.0,
            "primary_pipework": {
                "external_diameter": 0.024,
            },
            "setpoint_temp": 60.0,
            "type": "StorageTank",
            "volume": cylinder_vol,
            "primary_pipework":primary_pipework_dict
        }

def edit_primary_pipework(project_dict, TFA):
    
    # Define minimum values
    internal_diameter_mm_min = 0.022
    external_diameter_mm_min = 0.024
    length_min =  0.05 * (TFA / 2)
    insulation_thickness_mm_min = 0.025

    # Update primary pipework object when primary pipework not present
    if 'primary_pipework' not in project_dict['HotWaterSource']['hw cylinder']:
        project_dict['HotWaterSource']['hw cylinder']['primary_pipework'] = {}
        # primary pipework dictionary
        primary_pipework_dict = {
                "internal_diameter_mm": internal_diameter_mm_min,
                "external_diameter_mm": external_diameter_mm_min,
                "length": length_min,
                "insulation_thermal_conductivity": 0.035,
                "insulation_thickness_mm": insulation_thickness_mm_min,
                "surface_reflectivity": False,
                "pipe_contents": "water"
            }

    # Update primary pipework object using actual values
    if 'primary_pipework' in project_dict['HotWaterSource']['hw cylinder']:
        primary_pipework_dict = project_dict['HotWaterSource']['hw cylinder']['primary_pipework']
        length = primary_pipework_dict['length']
        internal_diameter_mm = max(primary_pipework_dict['internal_diameter_mm'], internal_diameter_mm_min)
        external_diameter_mm = max(primary_pipework_dict['external_diameter_mm'], external_diameter_mm_min)
        # update insulation thickness based on internal diameter
        if internal_diameter_mm > 0.025:
            insulation_thickness_mm = 0.032

        # primary pipework dictionary
        primary_pipework_dict = {
                "internal_diameter_mm": internal_diameter_mm,
                "external_diameter_mm": external_diameter_mm,
                "length": length,
                "insulation_thermal_conductivity": 0.035,
                "insulation_thickness_mm": insulation_thickness_mm,
                "surface_reflectivity": False,
                "pipe_contents": "water"
            }
    return primary_pipework_dict

def edit_hot_water_distribution_inner(project_dict, TFA):
    # hot water dictionary
    hot_water_distribution_inner_dict = project_dict['Distribution']['internal']

    # Update length
    length = hot_water_distribution_inner_dict['length']
    length =  min(length, 0.2 * TFA)

    internal_diameter_mm = hot_water_distribution_inner_dict['internal_diameter_mm']
    internal_diameter_mm_min = 0.015
    internal_diameter_mm = max(internal_diameter_mm, internal_diameter_mm_min)
    # update internal diameter if not present
    if 'internal_diameter_mm' not in hot_water_distribution_inner_dict:
        internal_diameter_mm = internal_diameter_mm_min

    external_diameter_mm = hot_water_distribution_inner_dict['external_diameter_mm']
    external_diameter_mm_min = 0.017
    external_diameter_mm = max(external_diameter_mm, external_diameter_mm_min)
    # update external diameter if not present
    if 'external_diameter_mm' not in hot_water_distribution_inner_dict:
        external_diameter_mm = external_diameter_mm_min

    # update insulation thickness based on internal diameter
    insulation_thickness_mm = 0.020
    if internal_diameter_mm > 0.025:
         insulation_thickness_mm = 0.024

    hot_water_distribution_inner_dict = {
        "external_diameter_mm": external_diameter_mm,
        "insulation_thermal_conductivity": 0.035,
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
    if 'diverter' in project_dict['EnergySupply']['mains elec'].keys():
        del project_dict['EnergySupply']['mains elec']['diverter']

def remove_electric_battery_if_present(project_dict):
    if 'ElectricBattery' in project_dict['EnergySupply']['mains elec'].keys():
        del project_dict['EnergySupply']['mains elec']['ElectricBattery']

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

    # Calculate air change rate (l/s)/m3
    minimum_ach = max(min_ventilation_rate_a, min_ventilation_rate_b) / total_volume

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
            "EnergySupply": "mains elec"
            }
    else:
        # Natural ventilation
        project_dict['Ventilation'] = {
            'type': 'NatVent',
            'req_ach': req_ach,
            "EnergySupply": "mains elec"
            }

def edit_space_heating_system(project_dict,
                              is_FEE,
                              cold_water_source,
                              design_capacity_dict,
                              design_capacity_overall,
                              TFA,
                              ):
    
    #check if a heat network is present
    is_heat_network = check_heatnetwork_present(project_dict)

    #FEE calculations - Notional heated with direct electric heaters
    #if Actual dwelling is heated with heat networks - Notional heated with HIU
    #otherwise, Notional heated with a air to water heat pump
    if is_FEE:
        edit_FEE_space_heating(project_dict)
    elif is_heat_network:
        edit_add_heatnetwork_space_heating(project_dict, cold_water_source)
        edit_heatnetwork_space_heating_distribution_system(project_dict)
        edit_storagetank(project_dict, cold_water_source, TFA)
    else:
        edit_add_default_space_heating_system(project_dict, design_capacity_overall)
        edit_default_space_heating_distribution_system(project_dict, design_capacity_dict)
        edit_storagetank(project_dict, cold_water_source, TFA)

def edit_air_conditioning(project_dict):
    if project_dict['PartO_air_conditioning_needed']:
        for space_cooling_name in project_dict['SpaceCoolSystem'].keys():
            project_dict['SpaceCoolSystem'][space_cooling_name]['efficiency'] = 5.1
            project_dict['SpaceCoolSystem'][space_cooling_name]['efficiency'] = 0.95

def calc_design_capacity(project_dict, HTC_dict):
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
        sys.exit("Setpoint error - invalid zone name ")

    return set_point

def initialise_temperature_setpoints(project_dict):
    ''' Intitilise temperature setpoints for all zones.
    The initial set point is needed to call the Project class. 
    Set as 18C for now. The FHS wrapper will overwrite temp_setpnt_init '''
    for zone_name, zone in project_dict['Zone'].items():
        zone['temp_setpnt_init'] = 18
