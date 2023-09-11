#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides functions to implement notional building
for the Future Homes Standard.
"""

import math
import sys
import os
from core import project 
from wrappers.future_homes_standard.future_homes_standard import calc_TFA
from core.space_heat_demand.building_element import BuildingElement, HeatFlowDirection

def apply_fhs_not_preprocessing(project_dict,
                                fhs_notA_assumptions,
                                fhs_notB_assumptions,
                                fhs_FEE_notA_assumptions,
                                fhs_FEE_notB_assumptions):
    """ Apply assumptions and pre-processing steps for the Future Homes Standard Notional building """
    
    is_notA = False
    if fhs_notA_assumptions or fhs_FEE_notA_assumptions:
        is_notA = True
    edit_lighting_efficacy(project_dict)
    edit_infiltration(project_dict,is_notA)
    #TODO edit_ventilation function
    edit_opaque_ajdZTU_elements(project_dict)
    edit_transparent_element(project_dict)
    edit_ground_floors(project_dict)
    edit_thermal_bridging(project_dict)
    
    #check if a heat network is present
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
    
    #FEE calculations - Notional heated with direct electric heaters
    #if Actual dwelling is heated with heat networks - Notional heated with HIU
    #otherwise, Notional heated with a air to water heat pump
    if fhs_FEE_notA_assumptions or fhs_FEE_notB_assumptions:
        edit_not_FEE_space_heating(project_dict)
    #TODO - create functions below
    #elif is_heat_network:
    #    edit_not_heatnetwork_space_heating(project_dict)
    #else:
    #    edit_not_default_space_heating(project_dict)
    
    return project_dict

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
    
    Notional option A pressure test result at 50Pa = 4 ACH
    Notional option B pressure test result at 50Pa = 5 ACH
    All passive openings count are set to zero
    Mechanical extract fans count follows the Actual dwelling,
    with the exception that there must be at least one per wet room
    '''
    
    #pressure test results dependent on Notional option A or B
    if is_notA:
        test_result = 4
    else:
        test_result = 5
    
    project_dict['Infiltration']['test_type'] = '50Pa'
    project_dict['Infiltration']['test_result'] = test_result
    
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

def edit_transparent_element(project_dict):
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
    
    TFA = calc_TFA(project_dict)
    
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

def edit_not_FEE_space_heating(project_dict):
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
    print(project_dict['SpaceHeatSystem'])

