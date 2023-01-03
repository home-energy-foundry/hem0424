#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides functions to implement pre- and post-processing
steps for the Future Homes Standard.
"""

import math
import sys
import os
import json
import csv
from core import project, schedule
from core.units import Kelvin2Celcius

this_directory = os.path.dirname(os.path.relpath(__file__))
FHSEMISFACTORS =  os.path.join(this_directory, "FHS_emisPEfactors_04-11-2022.csv")

def apply_fhs_preprocessing(project_dict):
    """ Apply assumptions and pre-processing steps for the Future Homes Standard """
    
    project_dict['SimulationTime']["start"] = 0
    project_dict['SimulationTime']["end"] = 8760
    
    project_dict['InternalGains'].pop("total_internal_gains", None)
    
    
    TFA = calc_TFA(project_dict)
    N_occupants = calc_N_occupants(TFA)
    
    #construct schedules
    schedule_occupancy_weekday, schedule_occupancy_weekend = create_occupancy(N_occupants)
    create_metabolic_gains(
        project_dict,
        TFA, 
        schedule_occupancy_weekday, 
        schedule_occupancy_weekend)
    
    create_heating_pattern(project_dict)
    create_evaporative_losses(project_dict, TFA, N_occupants)
    create_lighting_gains(project_dict, TFA, N_occupants)
    create_cooking_gains(project_dict,TFA, N_occupants)
    create_appliance_gains(project_dict, TFA, N_occupants)
    create_hot_water_use_pattern(project_dict, TFA, N_occupants)
    create_cooling(project_dict)
    create_cold_water_feed_temps(project_dict)
    
    
    return project_dict

def apply_fhs_postprocessing(project_dict, results_totals, energy_import, energy_export, timestep_array, file_path):
    """ Post-process core simulation outputs as required for Future Homes Standard """
    
    emissionfactors = {}
    results = {}
    
    unprocessed_result_dict = {'total': results_totals,
                               'import': energy_import,
                               'export': energy_export}
    
    #replace parts of the headers from the emission factors csv when creating output file
    header_replacements = [
        (" Factor", ""),
        ("/kWh", ""),
        ("delivered", "")
    ]
    
    '''
    first read in factors from csv. not all rows have a code yet
    so only read in rows with a fuel code
    '''
    with open(FHSEMISFACTORS,'r') as emissionfactorscsv:
        emissionfactorsreader = csv.DictReader(emissionfactorscsv, delimiter=',')
        for row in emissionfactorsreader:
            if row["Fuel Code"]!= "":
                this_fuel_code = row["Fuel Code"]
                emissionfactors[this_fuel_code] = row
                #getting rid of keys that aren't factors to be applied to results for ease of looping
                emissionfactors[this_fuel_code].pop("Fuel Code")
                emissionfactors[this_fuel_code].pop("Fuel")
    '''
    loop over all energy supplies in the project dict.
    find all factors for relevant fuel and apply them
    '''
    project_dict["EnergySupply"]['_unmet_demand'] = {"fuel": "unmet_demand"}
    for Energysupply in project_dict["EnergySupply"]:
        this_fuel_code = project_dict["EnergySupply"][Energysupply]["fuel"]
        #only apply factors to import/export if there is any export
        if sum(energy_export[Energysupply]) != 0:
            for factor in emissionfactors[this_fuel_code]:
                
                factor_header_part = str(factor)
                for replacement in header_replacements:
                    factor_header_part = factor_header_part.replace(*replacement)
                    
                this_header = (str(Energysupply) + 
                               ' total ' +
                               factor_header_part
                )
                results[this_header] = [
                    x * float(emissionfactors[this_fuel_code][factor])
                    for x in results_totals[Energysupply]
                ]
                
                this_fuel_code_export = this_fuel_code + "_export"
                this_header = (str(Energysupply) + 
                               ' import ' +
                               factor_header_part
                )
                results[this_header] = [
                    x * float(emissionfactors[this_fuel_code_export][factor])
                    for x in energy_import[Energysupply]
                ]
                this_header = (str(Energysupply) + 
                               ' export ' +
                               factor_header_part
                )
                results[this_header] = [
                    x * float(emissionfactors[this_fuel_code_export][factor])
                    for x in energy_export[Energysupply]
                ]
        else:
            for factor in emissionfactors[this_fuel_code]:
                
                factor_header_part = str(factor)
                for replacement in header_replacements:
                    factor_header_part = factor_header_part.replace(*replacement)
                    
                this_header = (str(Energysupply) + 
                               ' total ' +
                               factor_header_part
                )
                results[this_header] = [
                    x * float(emissionfactors[this_fuel_code][factor])
                    for x in results_totals[Energysupply]
                ]

    with open(file_path + '_postproc.csv', 'w') as postproc_file:
        writer = csv.writer(postproc_file)
        #write header row
        writer.writerow(results.keys())
        #results dict is arranged by column, we want to write rows so transpose via zip
        results_transposed = list(zip(*results.values()))
        
        for t_idx, timestep in enumerate(timestep_array):
            row = results_transposed[t_idx]
            writer.writerow(row)

def calc_TFA(project_dict):
     
    TFA = 0.0
    
    for zones in project_dict["Zone"].keys():
        TFA += project_dict["Zone"][zones]["area"]
        
    return TFA

def calc_N_occupants(TFA):
    #in number of occupants + m^2
    N = 0.0
    
    if TFA > 13.9:
        N = 1 + 1.76 * (1 - math.exp(-0.000349 * (TFA -13.9)**2)) + 0.0013 * (TFA -13.9)
    elif TFA <= 13.9:
        N = 1.0
        
    return N

def create_occupancy(N_occupants):
    #in number of occupants
    occupancy_weekday_fhs = [
        1, 1, 1, 1, 1, 1, 0.5, 0.5, 0.5, 0.1, 0.1, 0.1, 0.1,
        0.2, 0.2, 0.2, 0.5, 0.5, 0.5, 0.8, 0.8, 1, 1, 1,
    ]
    occupancy_weekend_fhs = [
        1, 1, 1, 1, 1, 1, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8,
        0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 1, 1, 1
    ]
    
    schedule_occupancy_weekday = [
        x * N_occupants for x in occupancy_weekday_fhs
    ]
    schedule_occupancy_weekend = [
        x * N_occupants for x in occupancy_weekend_fhs
    ]
    
    return schedule_occupancy_weekday, schedule_occupancy_weekend

def create_metabolic_gains(project_dict, 
                           TFA, 
                           schedule_occupancy_weekday, 
                           schedule_occupancy_weekend):
    #Watts/occupant
    metabolic_gains_fhs = [
        41.0, 41.0, 41.0, 41.0, 41.0, 41.0, 
        41.0, 89.0, 89.0, 89.0, 89.0, 89.0,
        89.0, 89.0, 89.0, 89.0, 89.0, 89.0, 
        89.0, 89.0, 58.0, 58.0, 58.0, 58.0
    ]
    #note divide by TFA. units are Wm^-2
    schedule_metabolic_gains_weekday = [
        occupancy * gains / TFA for occupancy, gains
        in zip(schedule_occupancy_weekday, metabolic_gains_fhs)
    ]
    schedule_metabolic_gains_weekend = [
        occupancy * gains / TFA for occupancy, gains
        in zip(schedule_occupancy_weekend, metabolic_gains_fhs)
    ]
    
    project_dict['InternalGains']['metabolic gains'] = {
        "start_day": 0,
        "time_series_step": 1,
        "schedule": {
            #watts m^-2
            "main": [{"repeat": 53, "value": "week"}],
            "week": [{"repeat": 5, "value": "weekday"},
                     {"repeat": 2, "value": "weekend"}],
            "weekday": schedule_metabolic_gains_weekday,
            "weekend": schedule_metabolic_gains_weekend

        }
    }

    return schedule_metabolic_gains_weekday, schedule_metabolic_gains_weekend

def create_heating_pattern(project_dict):
    '''
    space heating
    '''
    
    livingroom_setpoint_fhs = 21.0
    restofdwelling_setpoint_fhs = 18.0

    # Set heating setpoint to absolute zero to ensure no heating demand
    heating_off_setpoint = Kelvin2Celcius(0.0)

    #07:30-09:30 and then 16:30-22:00
    heating_fhs_weekday = (
        [False for x in range(14)] +
        [True for x in range(5)] +
        [False for x in range(14)] +
        [True for x in range(11)] +
        [False for x in range(4)])
    
    #07:30-09:30 and then 18:30-22:00
    heating_nonlivingarea_fhs_weekday = (
        [False for x in range(14)] +
        [True for x in range(5)] +
        [False for x in range(18)] +
        [True for x in range(7)] +
        [False for x in range(4)])

    #08:30 - 22:00
    heating_fhs_weekend = (
        [False for x in range(17)] +
        [True for x in range(28)] +
        [False for x in range(3)])

    '''
    if there is not separate time control of the non-living rooms
    (i.e. control type 3 in SAP 10 terminology),
    the heating times are necessarily the same as the living room,
    so the evening heating period would also start at 16:30 on weekdays.
    '''
    
    
    for zone in project_dict['Zone']:
        if "SpaceHeatControl" in project_dict["Zone"][zone].keys():
            if project_dict['Zone'][zone]["SpaceHeatControl"] == "livingroom":
                project_dict['Control']['HeatingPattern_LivingRoom'] = {
                    "type": "SetpointTimeControl",
                    "start_day" : 0,
                    "time_series_step":0.5,
                    "schedule": {
                        "main": [{"repeat": 53, "value": "week"}],
                        "week": [{"repeat": 5, "value": "weekday"},
                                 {"repeat": 2, "value": "weekend"}],
                        "weekday": [livingroom_setpoint_fhs if x
                                    else heating_off_setpoint
                                    for x in heating_fhs_weekday],
                        "weekend": [livingroom_setpoint_fhs if x
                                    else heating_off_setpoint
                                    for x in heating_fhs_weekend],
                    }
                }
                if "SpaceHeatSystem" in project_dict["Zone"][zone].keys():
                    spaceheatsystem = project_dict["Zone"][zone]["SpaceHeatSystem"]
                    project_dict["SpaceHeatSystem"][spaceheatsystem]["Control"] = "HeatingPattern_LivingRoom"
                    
            elif project_dict['Zone'][zone]["SpaceHeatControl"] == "restofdwelling":
                project_dict['Control']['HeatingPattern_RestOfDwelling'] =  {
                    "type": "SetpointTimeControl",
                    "start_day" : 0,
                    "time_series_step":0.5,
                    "schedule":{
                        "main": [{"repeat": 53, "value": "week"}],
                        "week": [{"repeat": 5, "value": "weekday"},
                                 {"repeat": 2, "value": "weekend"}],
                        "weekday": [restofdwelling_setpoint_fhs if x
                                    else heating_off_setpoint
                                    for x in heating_nonlivingarea_fhs_weekday],
                        "weekend": [restofdwelling_setpoint_fhs if x
                                    else heating_off_setpoint
                                    for x in heating_fhs_weekend],
                    }
                }
                if "SpaceHeatSystem" in project_dict["Zone"][zone].keys():
                    spaceheatsystem = project_dict["Zone"][zone]["SpaceHeatSystem"]
                    project_dict["SpaceHeatSystem"][spaceheatsystem]["Control"] = "HeatingPattern_RestOfDwelling"
    '''
    water heating pattern - same as space heating
    '''

    for hwsource in project_dict['HotWaterSource']:
        # Instantaneous water heating systems must be available 24 hours a day
        if project_dict['HotWaterSource'][hwsource]["type"] == "StorageTank":
            for heatsource in project_dict['HotWaterSource'][hwsource]["HeatSource"]:
                hwcontrolname = project_dict['HotWaterSource'][hwsource]["HeatSource"][heatsource]["Control"]
                project_dict["Control"][hwcontrolname] = {
                    "type": "OnOffTimeControl",
                    "start_day" : 0,
                    "time_series_step":0.5,
                    "schedule":{
                        "main": [{"repeat": 53, "value": "week"}],
                        "week": [{"repeat": 5, "value": "weekday"},
                                 {"repeat": 2, "value": "weekend"}],
                        "weekday": heating_nonlivingarea_fhs_weekday,
                        "weekend": heating_fhs_weekend
                    }
                }
    


def create_evaporative_losses(project_dict,TFA, N_occupants):
    evaporative_losses_fhs = -40 * N_occupants / TFA
    
    project_dict['InternalGains']['EvaporativeLosses'] = {
        "start_day": 0,
        "time_series_step": 1,
        "schedule": {
            #in Wm^-2
            "main": [{"value": evaporative_losses_fhs, "repeat": 8760 }]
        }
    } #repeats for length of simulation which in FHS should be whole year.

def create_lighting_gains(project_dict, TFA, N_occupants):
    '''
    Calculate the annual energy requirement in kWh using the procedure described in SAP 10.2 up to and including step 9.
    Divide this by 365 to get the average daily energy use.
    Multiply the daily energy consumption figure by the following profiles to
    create a daily profile for each month of the year (to be applied to all days in that month).
    '''

    '''
    here we calculate an overall lighting efficacy as
    the average of zone lighting efficacies weighted by zone
    floor area.
    '''
    lighting_efficacy = 0
    for zone in project_dict["Zone"]:
        if "Lighting"  not in project_dict["Zone"][zone].keys():
            sys.exit("missing lighting in zone "+ zone)
        if "efficacy" not in project_dict["Zone"][zone]["Lighting"].keys():
            sys.exit("missing lighting efficacy in zone "+ zone)
        lighting_efficacy += project_dict["Zone"][zone]["Lighting"]["efficacy"] * project_dict["Zone"][zone]["area"] / TFA
        
    if lighting_efficacy == 0:
        sys.exit('invalid/missing lighting efficacy for all zones')
        
    
    # TODO Consider defining large tables like this in a separate file rather than inline
    avg_monthly_halfhr_profiles = [
        [0.029235831, 0.02170637, 0.016683155, 0.013732757, 0.011874713, 0.010023118, 0.008837131, 0.007993816,
         0.007544302, 0.007057335, 0.007305208, 0.007595198, 0.009170401, 0.013592425, 0.024221707, 0.034538234,
         0.035759809, 0.02561524, 0.019538678, 0.017856399, 0.016146846, 0.014341097, 0.013408345, 0.013240894,
         0.013252628, 0.013314013, 0.013417126, 0.01429735, 0.014254224, 0.014902582, 0.017289786, 0.023494947,
         0.035462982, 0.050550653, 0.065124006, 0.072629223, 0.073631053, 0.074451912, 0.074003097, 0.073190397,
         0.071169797, 0.069983033, 0.06890179, 0.066130187, 0.062654436, 0.056634675, 0.047539646, 0.037801233],
        [0.026270349, 0.01864863, 0.014605535, 0.01133541, 0.009557625, 0.008620514, 0.007385915, 0.00674999,
         0.006144089, 0.005812534, 0.005834644, 0.006389013, 0.007680219, 0.013106226, 0.021999709, 0.027144574,
         0.02507541, 0.0179487, 0.014855879, 0.012930469, 0.011690622, 0.010230198, 0.00994897, 0.009668602,
         0.00969183, 0.010174279, 0.011264866, 0.011500069, 0.011588248, 0.011285427, 0.012248949, 0.014420402,
         0.01932017, 0.027098032, 0.044955369, 0.062118024, 0.072183735, 0.075100799, 0.075170654, 0.072433133,
         0.070588417, 0.069756433, 0.068356831, 0.06656098, 0.06324827, 0.055573729, 0.045490296, 0.035742204],
        [0.02538112, 0.018177936, 0.012838313, 0.00961673, 0.007914015, 0.006844738, 0.00611386, 0.005458354,
         0.00508359, 0.004864933, 0.004817922, 0.005375289, 0.006804643, 0.009702514, 0.013148583, 0.013569968,
         0.01293754, 0.009183378, 0.007893734, 0.00666975, 0.006673791, 0.006235776, 0.006096299, 0.006250229,
         0.006018285, 0.00670324, 0.006705105, 0.006701531, 0.006893458, 0.006440525, 0.006447363, 0.007359989,
         0.009510975, 0.011406472, 0.017428875, 0.026635564, 0.042951415, 0.057993474, 0.066065305, 0.067668248,
         0.067593187, 0.067506237, 0.065543759, 0.063020652, 0.06004127, 0.052838397, 0.043077683, 0.033689246],
        [0.029044978, 0.020558675, 0.014440871, 0.010798435, 0.008612364, 0.007330799, 0.006848797, 0.006406058,
         0.00602619, 0.005718987, 0.005804901, 0.006746423, 0.007160898, 0.008643678, 0.010489867, 0.011675722,
         0.011633729, 0.008939881, 0.007346857, 0.007177037, 0.007113926, 0.007536109, 0.007443049, 0.006922747,
         0.00685514, 0.006721853, 0.006695838, 0.005746367, 0.005945173, 0.005250153, 0.005665752, 0.006481695,
         0.006585193, 0.00751989, 0.009038481, 0.009984259, 0.011695555, 0.014495872, 0.018177089, 0.027110627,
         0.042244993, 0.056861545, 0.064008071, 0.062680016, 0.060886258, 0.055751568, 0.048310205, 0.038721632],
        [0.023835444, 0.016876637, 0.012178456, 0.009349274, 0.007659691, 0.006332517, 0.005611274, 0.005650048,
         0.005502101, 0.005168442, 0.005128425, 0.005395259, 0.004998272, 0.005229362, 0.006775116, 0.007912694,
         0.008514274, 0.006961449, 0.00630672, 0.00620858, 0.005797218, 0.005397357, 0.006006318, 0.005593869,
         0.005241095, 0.005212189, 0.00515531, 0.004906504, 0.004757624, 0.004722969, 0.004975738, 0.005211879,
         0.005684004, 0.006331507, 0.007031149, 0.008034144, 0.008731998, 0.010738922, 0.013170262, 0.016638631,
         0.021708313, 0.0303703, 0.043713685, 0.051876584, 0.054591464, 0.05074126, 0.043109775, 0.033925231],
        [0.023960632, 0.016910619, 0.012253193, 0.009539031, 0.007685214, 0.006311553, 0.00556675, 0.005140391,
         0.004604673, 0.004352551, 0.004156956, 0.004098101, 0.00388452, 0.00433039, 0.005658606, 0.006828804,
         0.007253075, 0.005872749, 0.004923197, 0.004521087, 0.004454765, 0.004304616, 0.004466648, 0.004178716,
         0.004186183, 0.003934784, 0.004014114, 0.003773073, 0.003469885, 0.003708517, 0.003801095, 0.004367245,
         0.004558263, 0.005596378, 0.005862632, 0.006068665, 0.006445161, 0.007402661, 0.007880006, 0.009723385,
         0.012243076, 0.016280074, 0.023909324, 0.03586776, 0.046595858, 0.047521241, 0.041417407, 0.03322265],
        [0.024387138, 0.017950032, 0.01339296, 0.010486231, 0.008634325, 0.00752814, 0.006562675, 0.006180296,
         0.00566116, 0.005092682, 0.004741384, 0.004680853, 0.00479228, 0.004921812, 0.005950605, 0.007010479,
         0.007057257, 0.005651136, 0.004813649, 0.00454666, 0.004121156, 0.003793481, 0.004122788, 0.004107635,
         0.004363668, 0.004310674, 0.004122943, 0.004014391, 0.004009496, 0.003805058, 0.004133355, 0.004188447,
         0.005268291, 0.005964825, 0.005774607, 0.006292344, 0.006813734, 0.007634982, 0.008723529, 0.009855823,
         0.012318322, 0.017097237, 0.026780014, 0.037823534, 0.046797578, 0.045940354, 0.039472789, 0.033058217],
        [0.023920296, 0.01690733, 0.012917415, 0.010191735, 0.008787867, 0.007681138, 0.006600128, 0.006043227,
         0.005963814, 0.005885256, 0.006164212, 0.005876554, 0.005432168, 0.00580157, 0.00641092, 0.007280576,
         0.00811752, 0.007006283, 0.006505718, 0.005917892, 0.005420978, 0.005527121, 0.005317478, 0.004793601,
         0.004577663, 0.004958332, 0.005159584, 0.004925386, 0.005192686, 0.0054453, 0.005400465, 0.005331386,
         0.005994507, 0.006370203, 0.006800758, 0.007947816, 0.009005592, 0.010608225, 0.012905449, 0.015976909,
         0.024610768, 0.036414926, 0.04680022, 0.050678553, 0.051188831, 0.046725936, 0.03998602, 0.032496965],
        [0.022221313, 0.016428778, 0.01266253, 0.010569518, 0.008926713, 0.007929788, 0.007134802, 0.006773883,
         0.006485147, 0.006766094, 0.007202971, 0.007480145, 0.008460127, 0.011414527, 0.014342431, 0.01448993,
         0.012040415, 0.008520428, 0.0077578, 0.006421555, 0.005889369, 0.005915144, 0.006229011, 0.005425193,
         0.005094464, 0.005674584, 0.005898523, 0.006504338, 0.005893063, 0.005967896, 0.0061056, 0.006017598,
         0.007500459, 0.008041236, 0.0099079, 0.012297435, 0.01592606, 0.021574549, 0.032780393, 0.04502082,
         0.054970312, 0.05930568, 0.060189471, 0.057269758, 0.05486585, 0.047401041, 0.038520417, 0.029925316],
        [0.023567522, 0.016304584, 0.012443113, 0.009961033, 0.008395854, 0.007242191, 0.006314956, 0.005722235,
         0.005385313, 0.005197814, 0.005444756, 0.0064894, 0.008409762, 0.015347201, 0.025458901, 0.028619409,
         0.023359044, 0.014869014, 0.011900433, 0.010931316, 0.010085903, 0.009253621, 0.008044246, 0.007866149,
         0.007665985, 0.007218414, 0.00797338, 0.008005782, 0.007407311, 0.008118996, 0.008648934, 0.010378068,
         0.013347814, 0.018541666, 0.026917161, 0.035860046, 0.049702909, 0.063560224, 0.069741764, 0.070609245,
         0.069689625, 0.069439031, 0.068785313, 0.065634051, 0.062207874, 0.053986076, 0.043508937, 0.033498873],
        [0.025283869, 0.018061868, 0.013832406, 0.01099122, 0.009057752, 0.007415348, 0.006415533, 0.006118688,
         0.005617255, 0.005084989, 0.005552217, 0.006364787, 0.00792208, 0.014440148, 0.02451, 0.02993728,
         0.024790064, 0.016859553, 0.013140437, 0.012181571, 0.010857371, 0.010621789, 0.010389982, 0.010087677,
         0.00981219, 0.0097001, 0.01014589, 0.01052881, 0.01044948, 0.011167223, 0.013610154, 0.02047533,
         0.035335895, 0.05409712, 0.067805633, 0.074003571, 0.077948793, 0.078981046, 0.077543712, 0.074620225,
         0.072631194, 0.070886175, 0.06972224, 0.068354439, 0.063806373, 0.055709895, 0.045866391, 0.035248054],
        [0.030992394, 0.022532047, 0.016965296, 0.013268634, 0.010662773, 0.008986943, 0.007580978, 0.006707669,
         0.00646337, 0.006180296, 0.006229094, 0.006626391, 0.00780049, 0.013149437, 0.022621172, 0.033064744,
         0.035953213, 0.029010413, 0.023490829, 0.020477646, 0.018671663, 0.017186751, 0.016526661, 0.015415424,
         0.014552683, 0.014347935, 0.014115058, 0.013739051, 0.014944386, 0.017543021, 0.021605977, 0.032100988,
         0.049851633, 0.063453382, 0.072579104, 0.076921792, 0.079601317, 0.079548711, 0.078653413, 0.076225647,
         0.073936893, 0.073585752, 0.071911165, 0.069220452, 0.065925982, 0.059952377, 0.0510938, 0.041481111]]
    
    lumens = 11.2 * 59.73 * (TFA * N_occupants) ** 0.4714
    
    kWhperyear = 1/3 * lumens/21 + 2/3 * lumens/lighting_efficacy
    kWhperday = kWhperyear / 365
    #lighting_energy_kWh=[]
    lighting_gains_W = []
        
    for monthly_profile in avg_monthly_halfhr_profiles:
        #lighting_energy_kWh+=[frac * kWhperday for frac in monthly_profile]
        '''
        To obtain the lighting gains,
        the above should be converted to Watts by multiplying the individual half-hourly figure by (2 x 1000).
        Since some lighting energy will be used in external light
        (e.g. outdoor security lights or lights in unheated spaces like garages and sheds)
        a factor of 0.85 is also applied to get the internal gains from lighting.
        '''
        lighting_gains_W.append([(frac * kWhperday) * 2 * 1000 for frac in monthly_profile])
    
    project_dict['ApplianceGains']['lighting'] = {
        "type": "lighting",
        "start_day": 0,
        "time_series_step" : 0.5,
        "gains_fraction": 0.85,
        "EnergySupply": "mains elec",
        "schedule": {
            "main": [{"value": "jan", "repeat": 31},
                    {"value": "feb", "repeat": 28},
                    {"value": "mar", "repeat": 31},
                    {"value": "apr", "repeat": 30},
                    {"value": "may", "repeat": 31},
                    {"value": "jun", "repeat": 30},
                    {"value": "jul", "repeat": 31},
                    {"value": "aug", "repeat": 31},
                    {"value": "sep", "repeat": 30},
                    {"value": "oct", "repeat": 31},
                    {"value": "nov", "repeat": 30},
                    {"value": "dec", "repeat": 31}
                     ],
            "jan":lighting_gains_W[0],
            "feb":lighting_gains_W[1],
            "mar":lighting_gains_W[2],
            "apr":lighting_gains_W[3],
            "may":lighting_gains_W[4],
            "jun":lighting_gains_W[5],
            "jul":lighting_gains_W[6],
            "aug":lighting_gains_W[7],
            "sep":lighting_gains_W[8],
            "oct":lighting_gains_W[9],
            "nov":lighting_gains_W[10],
            "dec":lighting_gains_W[11]
        }
    }


def create_cooking_gains(project_dict,TFA, N_occupants):
    
    cooking_profile_fhs = [
        0.001192419, 0.000825857, 0.000737298, 0.000569196,
        0.000574409, 0.000573778, 0.000578369, 0.000574619, 0.000678235,
        0.000540799, 0.000718043, 0.002631192, 0.002439288, 0.003263445,
        0.003600656, 0.005743044, 0.011250675, 0.015107564, 0.014475307,
        0.016807917, 0.018698336, 0.018887283, 0.021856976, 0.047785397,
        0.08045051, 0.099929701, 0.042473353, 0.02361216, 0.015650513,
        0.014345379, 0.015951211, 0.01692045, 0.037738026, 0.066195428,
        0.062153502, 0.073415686, 0.077486476, 0.069093846, 0.046706527,
        0.024924648, 0.014783978, 0.009192004, 0.005617715, 0.0049381,
        0.003529689, 0.002365773, 0.001275927, 0.001139293
    ]
    
    EC1elec = 0
    EC1gas = 0
    EC2elec = 0
    EC2gas = 0
    '''
    check for gas and/or electric cooking. Remove any existing objects
    so that we can add our own (just one for gas and one for elec)
    '''
    cookingenergysupplies=[]
    for item in list(project_dict["ApplianceGains"]):
        if project_dict["ApplianceGains"][item]["type"]=="cooking":
            cookingenergysupplies.append(project_dict["ApplianceGains"][item]["EnergySupply"])
            project_dict["ApplianceGains"].pop(item)
        
    if "mains elec" in cookingenergysupplies and "mains gas" in cookingenergysupplies:
        EC1elec = 138
        EC2elec = 28
        EC1gas = 241
        EC2gas = 48
    elif "mains gas" in cookingenergysupplies:
        EC1elec = 0
        EC2elec = 0
        EC1gas = 481
        EC2gas = 96
    elif "mains elec" in cookingenergysupplies:
        EC1elec = 275
        EC2elec = 55
        EC1gas = 0
        EC2gas = 0
        #TODO - if there is cooking with energy supply other than
        #mains gas or electric, it could be accounted for here -
        #but presently it will be ignored.
        
    annual_cooking_elec_kWh = EC1elec + EC2elec * N_occupants
    annual_cooking_gas_kWh = EC1gas + EC2gas * N_occupants
    
    #energy consumption, W_m2, gains factor not applied
    cooking_elec_profile_W = [(1000 * 2) * annual_cooking_elec_kWh / 365
                              * halfhr for halfhr in cooking_profile_fhs]
    cooking_gas_profile_W = [(1000 * 2) * annual_cooking_gas_kWh / 365
                             * halfhr for halfhr in cooking_profile_fhs]

    
    #add back gas and electric cooking gains if they are present 
    if "mains gas" in cookingenergysupplies:
        project_dict['ApplianceGains']['Gascooking'] = {
            "type":"cooking",
            "EnergySupply": "mains gas",
            "start_day" : 0,
            "time_series_step": 0.5,
            "gains_fraction": 0.75, 
            "schedule": {
                "main": [{"repeat": 365, "value": "day"}],
                "day": cooking_gas_profile_W
            }
        }
    if "mains elec" in cookingenergysupplies:
        project_dict['ApplianceGains']['Eleccooking'] = {
            "type":"cooking",
            "EnergySupply": "mains elec",
            "start_day" : 0,
            "time_series_step": 0.5,
            "gains_fraction": 0.9,
            "schedule": {
                "main": [{"repeat": 365, "value": "day"}],
                "day": cooking_elec_profile_W
            }
        }

def create_appliance_gains(project_dict,TFA,N_occupants):
    
    avg_monthly_hr_profiles = [
        [0.025995114, 0.023395603, 0.022095847, 0.020796091, 0.019496336, 0.022095847, 0.02729487, 0.040292427, 0.048090962, 0.049390717, 0.050690473, 0.049390717, 0.053289984, 0.049390717, 0.050690473, 0.053289984, 0.074086076, 0.087083633, 0.08188461, 0.070186809, 0.064987786, 0.057189252, 0.046791206, 0.033793649],
        [0.025995114, 0.023395603, 0.022095847, 0.020796091, 0.019496336, 0.022095847, 0.02729487, 0.032493893, 0.046791206, 0.051990229, 0.049390717, 0.046791206, 0.048090962, 0.046791206, 0.04549145, 0.049390717, 0.062388274, 0.074086076, 0.080584854, 0.067587297, 0.059788763, 0.050690473, 0.044191694, 0.032493893],
        [0.024695359, 0.020796091, 0.020796091, 0.019496336, 0.020796091, 0.022095847, 0.029894381, 0.041592183, 0.04549145, 0.048090962, 0.04549145, 0.04549145, 0.049390717, 0.048090962, 0.048090962, 0.049390717, 0.057189252, 0.070186809, 0.07278632, 0.067587297, 0.061088519, 0.051990229, 0.041592183, 0.029894381],
        [0.022095847, 0.022095847, 0.022095847, 0.022095847, 0.023395603, 0.029894381, 0.038992672, 0.046791206, 0.046791206, 0.044191694, 0.046791206, 0.048090962, 0.044191694, 0.042891939, 0.044191694, 0.051990229, 0.062388274, 0.061088519, 0.058489007, 0.057189252, 0.050690473, 0.041592183, 0.033793649, 0.024695359],
        [0.024695359, 0.022095847, 0.020796091, 0.020796091, 0.023395603, 0.031194137, 0.038992672, 0.044191694, 0.048090962, 0.046791206, 0.044191694, 0.04549145, 0.041592183, 0.037692916, 0.038992672, 0.049390717, 0.05458974, 0.058489007, 0.051990229, 0.055889496, 0.050690473, 0.041592183, 0.031194137, 0.024695359],
        [0.022095847, 0.020796091, 0.020796091, 0.019496336, 0.020796091, 0.024695359, 0.032493893, 0.042891939, 0.044191694, 0.041592183, 0.040292427, 0.042891939, 0.040292427, 0.038992672, 0.040292427, 0.044191694, 0.053289984, 0.057189252, 0.048090962, 0.048090962, 0.04549145, 0.041592183, 0.031194137, 0.024695359],
        [0.022095847, 0.020796091, 0.020796091, 0.019496336, 0.020796091, 0.024695359, 0.032493893, 0.041592183, 0.042891939, 0.042891939, 0.041592183, 0.041592183, 0.040292427, 0.037692916, 0.037692916, 0.044191694, 0.051990229, 0.05458974, 0.046791206, 0.046791206, 0.04549145, 0.042891939, 0.031194137, 0.024695359],
        [0.022095847, 0.020796091, 0.020796091, 0.019496336, 0.020796091, 0.024695359, 0.032493893, 0.044191694, 0.044191694, 0.044191694, 0.044191694, 0.044191694, 0.042891939, 0.040292427, 0.041592183, 0.044191694, 0.051990229, 0.055889496, 0.050690473, 0.051990229, 0.049390717, 0.042891939, 0.031194137, 0.024695359],
        [0.022095847, 0.020796091, 0.020796091, 0.019496336, 0.023395603, 0.029894381, 0.040292427, 0.041592183, 0.044191694, 0.044191694, 0.04549145, 0.044191694, 0.042891939, 0.042891939, 0.042891939, 0.051990229, 0.059788763, 0.064987786, 0.061088519, 0.058489007, 0.051990229, 0.038992672, 0.031194137, 0.023395603],
        [0.022095847, 0.020796091, 0.019496336, 0.022095847, 0.023395603, 0.029894381, 0.040292427, 0.046791206, 0.049390717, 0.04549145, 0.046791206, 0.049390717, 0.04549145, 0.044191694, 0.04549145, 0.053289984, 0.067587297, 0.07278632, 0.066287542, 0.059788763, 0.053289984, 0.042891939, 0.031194137, 0.023395603],
        [0.024695359, 0.022095847, 0.020796091, 0.020796091, 0.020796091, 0.024695359, 0.029894381, 0.042891939, 0.048090962, 0.049390717, 0.04549145, 0.04549145, 0.046791206, 0.046791206, 0.044191694, 0.051990229, 0.064987786, 0.08188461, 0.076685587, 0.067587297, 0.061088519, 0.05458974, 0.04549145, 0.032493893],
        [0.025995114, 0.023395603, 0.022095847, 0.020796091, 0.019496336, 0.022095847, 0.02729487, 0.032493893, 0.048090962, 0.053289984, 0.051990229, 0.05458974, 0.057189252, 0.051990229, 0.055889496, 0.058489007, 0.075385832, 0.083184366, 0.08188461, 0.068887053, 0.062388274, 0.055889496, 0.046791206, 0.033793649]]
    
    EA_annual_kWh = 207.8 * (TFA * N_occupants) ** 0.4714
    
    appliance_gains_W = []
    for monthly_profile in avg_monthly_hr_profiles:
        appliance_gains_W.append([1000 * EA_annual_kWh * frac / 365
                                  for frac in monthly_profile])
        
    project_dict['ApplianceGains']['appliances'] = {
        "type": "appliances",
        "EnergySupply": "mains elec",
        "start_day": 0,
        "time_series_step": 1,
        "gains_fraction": 1,
        "schedule": {
            #watts
            "main": [{"value": "jan", "repeat": 31},
                    {"value": "feb", "repeat": 28},
                    {"value": "mar", "repeat": 31},
                    {"value": "apr", "repeat": 30},
                    {"value": "may", "repeat": 31},
                    {"value": "jun", "repeat": 30},
                    {"value": "jul", "repeat": 31},
                    {"value": "aug", "repeat": 31},
                    {"value": "sep", "repeat": 30},
                    {"value": "oct", "repeat": 31},
                    {"value": "nov", "repeat": 30},
                    {"value": "dec", "repeat": 31}
                     ],
            "jan": appliance_gains_W[0],
            "feb": appliance_gains_W[1],
            "mar": appliance_gains_W[2],
            "apr": appliance_gains_W[3],
            "may": appliance_gains_W[4],
            "jun": appliance_gains_W[5],
            "jul": appliance_gains_W[6],
            "aug": appliance_gains_W[7],
            "sep": appliance_gains_W[8],
            "oct": appliance_gains_W[9],
            "nov": appliance_gains_W[10],
            "dec": appliance_gains_W[11]
        }
    }

class FHS_HW_events:
    '''
    class to hold HW events to be added based on showers, baths, other facilities present in dwelling
    '''
    def __init__(self, 
                 project_dict,
                 FHW,
                 HW_events_valuesdict,
                 behavioural_hw_factorm,
                 other_hw_factorm,
                 partGbonus):
        self.showers = []
        self.baths = []
        self.other= []
        self.which_shower = -1
        self.which_bath = -1
        self.which_other = -1
        #event and monthidx are only things that should change between events, rest are globals so dont need to be captured
        #we need unused "event" in shower and bath syntax so that its the same for all 3
        self.showerdurationfunc = lambda event, monthidx: \
            6 * FHW  * behavioural_hw_factorm[monthidx]
        self.bathdurationfunc = lambda event, monthidx: \
            6 * FHW  * behavioural_hw_factorm[monthidx] * partGbonus
        self.otherdurationfunc = lambda event, monthidx: \
            6 * (HW_events_valuesdict[event] / 1.4) * FHW  * other_hw_factorm[monthidx]
        '''
        set up events dict
        check if showers/baths are present
        if multiple showers/baths are present, we need to cycle through them
        if either is missing replace with the one that is present,
        if neither is present, "other" events with same consumption as a bath should be used
        '''
        project_dict["Events"].clear()
        project_dict["Events"]["Shower"] = {}
        project_dict["Events"]["Bath"] = {}
        project_dict["Events"]["Other"] = {}
        
        for shower in project_dict["Shower"]:
            project_dict["Events"]["Shower"][shower] = []
            self.showers.append(("Shower",shower,self.showerdurationfunc))
            
        for bath in project_dict["Bath"]:
            project_dict["Events"]["Bath"][bath] = []
            self.baths.append(("Bath",bath,self.bathdurationfunc))
            
        for other in project_dict["Other"]:
            project_dict["Events"]["Other"][other] = []
            self.other.append(("Other",other,self.otherdurationfunc))
        
        #if theres no other events we need to add them
        if self.other == []:
            project_dict["Events"]["Other"] = {"other":[]}
            self.other.append(("Other","other",self.otherdurationfunc))
        #if no shower present, baths should be taken and vice versa. If neither is present then bath sized drawoff
        if not self.showers and self.baths:
            self.showers = self.baths
        elif not self.baths and self.showers:
            self.baths = self.showers
        elif not self.showers and not self.baths:
            self.baths.append(("Other","other",self.bathdurationfunc))
            self.showers.append(("Other","other",self.bathdurationfunc))
    '''
    the below getters return the name of the end user for the drawoff, 
    and the function to calculate the duration of the drawoff.
    If there is no shower then baths are taken when showers would have been, as specified above, so
    this will return the duration function *for a bath*, ie with the possibility
    for part G bonus. 
    '''
    def get_shower(self):
        self.which_shower = (self.which_shower + 1) % len(self.showers)
        return self.showers[self.which_shower]
    def get_bath(self):
        self.which_bath = (self.which_bath + 1) % len(self.baths)
        return self.baths[self.which_bath]
    def get_other(self):
        self.which_other = (self.which_other + 1) % len(self.other)
        return self.other[self.which_other]

def create_hot_water_use_pattern(project_dict, TFA, N_occupants):

    HW_events_dict = {
        #time in decimal fractions of an hour
        'Time': [7, 7.083333333, 7.5, 8.016666667, 8.25, 8.5, 8.75, 9, 9.5, 10.5, 11.5, 11.75, 12.75, 14.5, 15.5, 16.5, 18, 18.25, 18.5, 19, 20.5, 21.25, 21.5],
        'Weekday': ['Small', 'Shower', 'Small', 'Small', 'Small', 'Small', 'Small', 'Small', 'Small', 'Floor cleaning', 'Small', 'Small', 'Sdishwash', 'Small', 'Small', 'Small', 'Small', 'Household cleaning', 'Household cleaning', 'Small', 'Ldishwash', 'Small', 'Shower'],
        'Saturday': ['Small', 'Shower', 'Shower', 'Small', 'Small', 'Small', 'Small', 'Small', 'Small', 'Floor cleaning', 'Small', 'Small', 'Sdishwash', 'Small', 'Small', 'Small', 'Small', 'Household cleaning', 'Household cleaning', 'Small', 'Ldishwash', 'Small', 'Small'],
        'Sunday': ['Small', 'Shower', 'Small', 'Small', 'Small', 'Small', 'Small', 'Small', 'Small', 'Floor cleaning', 'Small', 'Small', 'Sdishwash', 'Small', 'Small', 'Small', 'Small', 'Household cleaning', 'Household cleaning', 'Small', 'Ldishwash', 'Small', 'Bath']
        }

    HW_events_valuesdict = {
        #event energy consumption in kWh
        "Small":0.105,
        "Shower":1.4,
        "Floor cleaning":0.105,
        "Sdishwash":0.315,
        "Ldishwash":0.735,
        "Household cleaning":0.105,
        "Bath":1.4,
        "None":0.0 #not in supplied spec, added for convenience with deleting events.
        }
    #utility for applying the sap10.2 monly factors (below)
    month_hour_starts = [744, 1416, 2160, 2880, 3624, 4344, 5088, 5832, 6552, 7296, 8016, 8760]
    #from sap10.2 J5
    behavioural_hw_factorm = [1.035, 1.021, 1.007, 0.993, 0.979, 0.965, 0.965, 0.979, 0.993, 1.007, 1.021, 1.035]
    #from sap10.2 j2
    other_hw_factorm = [1.10, 1.06, 1.02, 0.98, 0.94, 0.90, 0.90, 0.94, 0.98, 1.02, 1.06, 1.10, 1.00]
    
    Weekday_values = [HW_events_valuesdict[x] for x in HW_events_dict['Weekday']]
    Saturday_values = [HW_events_valuesdict[x] for x in HW_events_dict['Saturday']]
    Sunday_values = [HW_events_valuesdict[x] for x in HW_events_dict['Sunday']]
    
    annual_HW_events = []
    annual_HW_events_values = []
    startmod = 1 #this changes which day of the week we start on. 0 is sunday.

    for i in range(365):
        if (i+startmod) % 6 == 0:
            annual_HW_events.extend(HW_events_dict['Saturday'])
            annual_HW_events_values.extend(Saturday_values)
        elif(i+startmod) % 7 == 0:
            annual_HW_events.extend(HW_events_dict['Sunday'])
            annual_HW_events_values.extend(Sunday_values)
        else:
            annual_HW_events.extend(HW_events_dict['Weekday'])
            annual_HW_events_values.extend(Weekday_values)

    vol_daily_average = (25 * N_occupants) + 36

    # Add daily average hot water use to hot water only heat pump (HWOHP) object, if present
    # TODO This is probably only valid if HWOHP is the only heat source for the
    #      storage tank. Make this more robust/flexible in future.
    for hw_source_obj in project_dict['HotWaterSource'].values():
        if hw_source_obj['type'] == 'StorageTank':
            for heat_source_obj in hw_source_obj['HeatSource'].values():
                if heat_source_obj['type'] == 'HeatPump_HWOnly':
                    heat_source_obj['vol_hw_daily_average'] = vol_daily_average

    SAP2012QHW = 365 * 4.18 * (37/3600) * vol_daily_average
    refQHW = 365 * sum(Weekday_values)

    '''
    this will determine what proportion of events in the list to eliminate, if less than 1
    '''
    ratio = SAP2012QHW / refQHW

    if ratio < 1.0:
        '''
        for each event type in the valuesdict, we want to eliminate every
        kth event where k = ROUND(1/1-ratio,0)
        '''
        k=round(1.0/(1-ratio),0)
        counters={event_type:0 for event_type in HW_events_valuesdict.keys()}
        
        for i,event in enumerate(annual_HW_events):
            NEC = (math.floor(counters[event]/k) + math.floor(k/2)) % k
            if counters[event] % k == NEC:
                annual_HW_events_values[i] =  0.0
                annual_HW_events[i] = 'None'
            counters[event] += 1
            
        '''
        correction factor
        '''
        QHWEN_eliminations = sum(annual_HW_events_values)
        FHW = SAP2012QHW / QHWEN_eliminations

        HW_events_valuesdict = {key : FHW * HW_events_valuesdict[key] for key in HW_events_valuesdict.keys()}
    else:
        FHW = 1.0
        
    '''
    if part G has been complied with, apply 5% reduction to duration of all events except showers
    '''
    partGbonus = 1.0
    if "PartGcompliance" in project_dict:
        if project_dict["PartGcompliance"] == True:
            partGbonus = 0.95
    else:
        sys.exit("Part G compliance missing from input file")
    
    FHS_HW_event = FHS_HW_events(project_dict,
                     FHW,
                     HW_events_valuesdict,
                     behavioural_hw_factorm,
                     other_hw_factorm,
                     partGbonus
                     )
    '''
    now create lists of events
    Shower events should be  evenly spread across all showers in dwelling
    and so on for baths etc.
    
    energy adjustment factor FHW is applied to duration of event.
    Durations of non shower events are obtained by finding ratio
    of energy consumption vs showers, which have to be 6 mins long.
    (so we are assuming temperature is always 41C and duration is
    directly proportional to energy)
    '''
    for i, event in enumerate(annual_HW_events):
        if event != "None":
            if event == "Shower":
                #starttime from daily dict plus 24hrs for each dayn elapsed
                eventstart = 24 * math.floor(i / 23) + HW_events_dict["Time"][i % 23]
                #now get monthly behavioural factor and apply it, along with FHW
                monthidx  = next(idx for idx, value in enumerate(month_hour_starts) if value > eventstart)
                eventtype, name, durationfunc = FHS_HW_event.get_shower()
                duration = durationfunc(event,monthidx)
                project_dict["Events"][eventtype][name].append(
                    {"start": eventstart,
                    "duration": duration, 
                    "temperature": 41.0}
                )
            elif event =="Bath":
                #starttime from daily dict plus 24hrs for each dayn elapsed
                eventstart = 24 * math.floor(i / 23) + HW_events_dict["Time"][i % 23]
                #now get monthly behavioural factor and apply it, along with FHW and partGbonus
                monthidx  = next(idx for idx, value in enumerate(month_hour_starts) if value > eventstart)
                eventtype, name, durationfunc = FHS_HW_event.get_bath()
                duration = durationfunc(event,monthidx)
                project_dict["Events"][eventtype][name].append(
                    {"start": eventstart,
                     "duration": duration,
                     "temperature": 41.0}
                )
            else:
                #starttime from daily dict plus 24hrs for each dayn elapsed
                eventstart = 24 * math.floor(i / 23) + HW_events_dict["Time"][i % 23]
                #now get monthly behavioural factor and apply it, along with FHW
                monthidx  = next(idx for idx, value in enumerate(month_hour_starts) if value > eventstart)
                eventtype, name, durationfunc = FHS_HW_event.get_other()
                duration = durationfunc(event,monthidx)
                project_dict["Events"][eventtype][name].append(
                    {"start": eventstart,
                     "duration": duration,
                     "temperature": 41.0}
                )
        


def create_cooling(project_dict):
    cooling_setpoint = 24.0
    # Set cooling setpoint to Planck temperature to ensure no cooling demand
    cooling_off_setpoint = Kelvin2Celcius(1.4e32)

    # TODO The livingroom subschedules below have the same time pattern as the
    #      livingroom heating schedules. Consolidate these definitions to avoid
    #      repetition.

    #07:30-09:30 and then 16:30-22:00
    cooling_subschedule_livingroom_weekday = (
        [cooling_off_setpoint for x in range(14)] +
        [cooling_setpoint for x in range(5)] +
        [cooling_off_setpoint for x in range(14)] +
        [cooling_setpoint for x in range(11)] +
        [cooling_off_setpoint for x in range(4)])

    #08:30 - 22:00
    cooling_subschedule_livingroom_weekend = (
        [cooling_off_setpoint for x in range(17)] +
        [cooling_setpoint for x in range(28)] +
        [cooling_off_setpoint for x in range(3)])

    cooling_subschedule_restofdwelling = (
        #22:00-07:00 - ie nighttime only
        [cooling_setpoint for x in range(14)] +
        [cooling_off_setpoint for x in range(30)] +
        [cooling_setpoint for x in range(4)]
    )
    
    for zone in project_dict['Zone']:
        if "SpaceHeatControl" in project_dict['Zone'][zone]:
            if project_dict['Zone'][zone]["SpaceHeatControl"] == "livingroom" and "SpaceCoolSystem" in project_dict['Zone'][zone]:
                project_dict['Control']['Cooling_LivingRoom'] = {
                    "type": "SetpointTimeControl",
                    "start_day" : 0,
                    "time_series_step":0.5,
                    "schedule": {
                        "main": [{"repeat": 53, "value": "week"}],
                        "week": [{"repeat": 5, "value": "weekday"},
                                 {"repeat": 2, "value": "weekend"}],
                        "weekday": cooling_subschedule_livingroom_weekday,
                        "weekend": cooling_subschedule_livingroom_weekend,
                    }
                }
                spacecoolsystem = project_dict["Zone"][zone]["SpaceCoolSystem"]
                project_dict["SpaceCoolSystem"][spacecoolsystem]["Control"] = "Cooling_LivingRoom"

            elif project_dict['Zone'][zone]["SpaceHeatControl"] == "restofdwelling" and "SpaceCoolSystem" in project_dict['Zone'][zone]:
                project_dict['Control']['Cooling_RestOfDwelling'] = {
                    "type": "SetpointTimeControl",
                    "start_day" : 0,
                    "time_series_step":0.5,
                    "schedule": {
                        "main": [{"repeat": 365, "value": "day"}],
                        "day": cooling_subschedule_restofdwelling
                    }
                }
                spacecoolsystem = project_dict["Zone"][zone]["SpaceCoolSystem"]
                project_dict["SpaceCoolSystem"][spacecoolsystem]["Control"] = "Cooling_RestOfDwelling"


def create_cold_water_feed_temps(project_dict):
    
    #24 hour average feed temperature (degreees Celsius) per month m. SAP 10.2 Table J1
    T24m_header_tank = [11.1, 11.3, 12.3, 14.5, 16.2, 18.8, 21.3, 19.3, 18.7, 16.2, 13.2, 11.2]
    T24m_mains = [8, 8.2, 9.3, 12.7, 14.6, 16.7, 18.4, 17.6, 16.6, 14.3, 11.1, 8.5]
    T24m=[]
    feedtype=""
    #typical fall in feed temp from midnight to 6am
    delta = 1.5
    
    if "header tank" in project_dict["ColdWaterSource"]:
        T24m = T24m_header_tank
        feedtype="header tank"
    else:
        T24m = T24m_mains
        feedtype="mains water"
    
    cold_feed_schedulem=[]
    
    for T in T24m:
        #typical cold feed temp between 3pm and midnight
        Teveningm = T + (delta * 15 /48)
        
        #variation throughout the day
        cold_feed_schedulem += [[
        Teveningm - delta * t/6 for t in range(0,6)]+
        [Teveningm - (15-t) * delta /9 for t in range(6,15)]+
        [Teveningm for t in range(15,24)]]
        
    outputfeedtemp=[]
    for i in range(31):
        outputfeedtemp.extend(cold_feed_schedulem[0])
    for i in range(28):
        outputfeedtemp.extend(cold_feed_schedulem[1])
    for i in range(31):
        outputfeedtemp.extend(cold_feed_schedulem[2])
    for i in range(30):
        outputfeedtemp.extend(cold_feed_schedulem[3])
    for i in range(31):
        outputfeedtemp.extend(cold_feed_schedulem[4])
    for i in range(30):
        outputfeedtemp.extend(cold_feed_schedulem[5])
    for i in range(31):
        outputfeedtemp.extend(cold_feed_schedulem[6])
    for i in range(31):
        outputfeedtemp.extend(cold_feed_schedulem[7])
    for i in range(30):
        outputfeedtemp.extend(cold_feed_schedulem[8])
    for i in range(31):
        outputfeedtemp.extend(cold_feed_schedulem[9])
    for i in range(30):
        outputfeedtemp.extend(cold_feed_schedulem[10])
    for i in range(31):
        outputfeedtemp.extend(cold_feed_schedulem[11])
    
    project_dict['ColdWaterSource'][feedtype] = {
        "start_day": 0,
        "time_series_step": 1,
        "temperatures": outputfeedtemp
    }
