#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides functions to implement pre- and post-processing
steps for the Future Homes Standard.
"""

import math
#from src.core.simulation_time import SimulationTime
#import src.core.units


def apply_fhs_preprocessing(project_dict):
    """ Apply assumptions and pre-processing steps for the Future Homes Standard """
    # TODO Populate project_dict with input profiles etc. before returning modified version
    
    '''
    simtime will be one whole year
    0-8760
    '''
    
    TFA = calc_TFA(project_dict)
    N_occupants = calc_N_occupants(TFA)
    
    #construct schedules
    schedule_occupancy_weekday , schedule_occupancy_weekend = create_occupancy(project_dict, N_occupants)
    create_metabolic_gains(project_dict, TFA, schedule_occupancy_weekday, schedule_occupancy_weekend)
    create_heating_pattern(project_dict)
    create_evaporative_losses(project_dict, N_occupants)
    create_lighting_gains(project_dict, TFA, N_occupants)
    create_cooking_gains(project_dict, N_occupants)
    create_appliance_gains(project_dict, TFA, N_occupants)
    create_hot_water_gains(project_dict, TFA, N_occupants)
    create_cooling(project_dict)
    
    return project_dict

def apply_fhs_postprocessing():
    """ Post-process core simulation outputs as required for Future Homes Standard """
    pass # TODO Implement required post-processing

def calc_TFA(project_dict):
    
    TFA=0.0
    
    for zones in project_dict["Zone"].keys():
        TFA+= project_dict["Zone"][zones]["area"]
    
    return TFA

def calc_N_occupants(TFA):
    
    N = 0.0
    
    if TFA>13.9:
        N = 1+ 1.76 *(1-math.exp(-0.000349 * (TFA -13.9)**2)) + 0.0013 * (TFA -13.9)
    elif TFA<=13.9:
        N=1.0
    
    return N

def create_occupancy(project_dict, N_occupants):
    occupancy_weekday_fhs = [
        1,1,1,1,1,1,0.5,0.5,0.5,0.1,0.1,0.1,0.1,
        0.2,0.2,0.2,0.5,0.5,0.5,0.8,0.8,1,1,1,
        ]
    
    occupancy_weekend_fhs= [
        1,1,1,1,1,1,0.8,0.8,0.8,0.8,0.8,0.8,0.8,
        0.8,0.8,0.8,0.8,0.8,0.8,0.8,0.8,1,1,1
        ]
    
    schedule_occupancy_weekday = [x * N_occupants for x in occupancy_weekday_fhs]#split these out into own func, linting
    schedule_occupancy_weekend = [x * N_occupants for x in occupancy_weekend_fhs]
    
    project_dict['Occupancy'] = {
        "start_day" : 0,
        "timestep":1,
        "schedule_occupancy":{
            "N_weekday": schedule_occupancy_weekday,
            "N_weekend": schedule_occupancy_weekend
        }
    }
    return schedule_occupancy_weekday, schedule_occupancy_weekend

def create_metabolic_gains(project_dict, TFA, schedule_occupancy_weekday, schedule_occupancy_weekend):
    metabolic_gains_fhs = [
        41.0,41.0,41.0,41.0,41.0,41.0,41.0,89.0,89.0,89.0,89.0,89.0,
        89.0,89.0,89.0,89.0,89.0,89.0,89.0,89.0,58.0,58.0,58.0,58.0
        ]
    
    schedule_metabolic_gains_weekday = [occupancy * gains / TFA for occupancy, gains in zip(schedule_occupancy_weekday, metabolic_gains_fhs)]
    schedule_metabolic_gains_weekend = [occupancy * gains / TFA for occupancy, gains in zip(schedule_occupancy_weekend, metabolic_gains_fhs)]
    
    project_dict['InternalGains']['MetabolicGains'] = {
        "start_day" : 0,
        "timestep":1,
        "schedule_metabolic_gains":{
            "Watts_m^-2_weekday": schedule_metabolic_gains_weekday, #need this per square meter!
            "Watts_m^-2_weekend": schedule_metabolic_gains_weekend
        }
    }
    
    return schedule_metabolic_gains_weekday, schedule_metabolic_gains_weekend

def create_heating_pattern(project_dict):
    livingroom_setpoint_fhs = 21.0
    restofdwelling_setpoint_fhs= 18.0
    
    heating_fhs_weekday = (
        #07:30-09:30 and then 16:30-22:00
        [False for x in range(14)] + 
        [True for x in range(5)] + 
        [False for x in range(14)] + 
        [True for x in range(11)] + 
        [False for x in range(4)])
    
    '''
    TODO - if there is not separate time control of the non-living rooms 
    (i.e. control type 3 in SAP 10 terminology), 
    the heating times are necessarily the same as the living room, 
    so the evening heating period would also start at 16:30 on weekdays. 
    '''
    heating_nonlivingarea_fhs_weekday = (
        #07:30-09:30 and then 16:30-22:00
        [False for x in range(14)] + 
        [True for x in range(5)] + 
        [False for x in range(18)] + 
        [True for x in range(7)] + 
        [False for x in range(4)])
        
    heating_fhs_weekend = (
        #08:30 - 22:00
        [False for x in range(17)] + 
        [True for x in range(28)] + 
        [False for x in range(3)])
    
    project_dict['HeatingPattern'] = {
        "start_day" : 0,
        "timestep":0.5,
        "setpoints":{"livingroom":livingroom_setpoint_fhs,
                     "restofdwelling":restofdwelling_setpoint_fhs},
        "schedule_heating":{
            "onoff_livingroom_weekday": heating_fhs_weekday,
            "onoff_livingroom_weekend": heating_fhs_weekend,
            "onoff_restofdwelling_weekday": heating_nonlivingarea_fhs_weekday,
            "onoff_restofdwelling_weekend": heating_fhs_weekend
        }
    }
    
def create_evaporative_losses(project_dict, N_occupants):
    evaporative_losses_fhs = 40 * N_occupants
    
    project_dict['InternalGains']['EvaporativeLosses'] = {
        "start_day" : 0,
        "timestep":1,
        "schedule_evaporative_losses":{
            "main":[{"value": evaporative_losses_fhs, "repeat": 8760 }]
        }
    } #repeats for length of simulation which in FHS should be whole year.
    
def create_lighting_gains(project_dict,TFA,N_occupants):
    '''
    presently there is no lighting in the project dict 
    to get an efficacy from - this is just a placeholder value
    TODO: get lighting efficacy from project dict
    '''
    
    '''
    Calculate the annual energy requirement in kWh using the procedure described in SAP 10.2 up to and including step 9. 
    Divide this by 365 to get the average daily energy use. 
    Multiply the daily energy consumption figure by the following profiles to 
    create a daily profile for each month of the year (to be applied to all days in that month).
    '''
    
    lighting_efficacy = 56
    
    '''seems quite silly having these inline...'''
    avg_monthly_halfhr_profiles =[
        [0.029235831,0.02170637,0.016683155,0.013732757,0.011874713,0.010023118,0.008837131,0.007993816,
         0.007544302,0.007057335,0.007305208,0.007595198,0.009170401,0.013592425,0.024221707,0.034538234,
         0.035759809,0.02561524,0.019538678,0.017856399,0.016146846,0.014341097,0.013408345,0.013240894,
         0.013252628,0.013314013,0.013417126,0.01429735,0.014254224,0.014902582,0.017289786,0.023494947,
         0.035462982,0.050550653,0.065124006,0.072629223,0.073631053,0.074451912,0.074003097,0.073190397,
         0.071169797,0.069983033,0.06890179,0.066130187,0.062654436,0.056634675,0.047539646,0.037801233],
        [0.026270349,0.01864863,0.014605535,0.01133541,0.009557625,0.008620514,0.007385915,0.00674999,
         0.006144089,0.005812534,0.005834644,0.006389013,0.007680219,0.013106226,0.021999709,0.027144574,
         0.02507541,0.0179487,0.014855879,0.012930469,0.011690622,0.010230198,0.00994897,0.009668602,
         0.00969183,0.010174279,0.011264866,0.011500069,0.011588248,0.011285427,0.012248949,0.014420402,
         0.01932017,0.027098032,0.044955369,0.062118024,0.072183735,0.075100799,0.075170654,0.072433133,
         0.070588417,0.069756433,0.068356831,0.06656098,0.06324827,0.055573729,0.045490296,0.035742204],
        [0.02538112,0.018177936,0.012838313,0.00961673,0.007914015,0.006844738,0.00611386,0.005458354,
         0.00508359,0.004864933,0.004817922,0.005375289,0.006804643,0.009702514,0.013148583,0.013569968,
         0.01293754,0.009183378,0.007893734,0.00666975,0.006673791,0.006235776,0.006096299,0.006250229,
         0.006018285,0.00670324,0.006705105,0.006701531,0.006893458,0.006440525,0.006447363,0.007359989,
         0.009510975,0.011406472,0.017428875,0.026635564,0.042951415,0.057993474,0.066065305,0.067668248,
         0.067593187,0.067506237,0.065543759,0.063020652,0.06004127,0.052838397,0.043077683,0.033689246],
        [0.029044978,0.020558675,0.014440871,0.010798435,0.008612364,0.007330799,0.006848797,0.006406058,
         0.00602619,0.005718987,0.005804901,0.006746423,0.007160898,0.008643678,0.010489867,0.011675722,
         0.011633729,0.008939881,0.007346857,0.007177037,0.007113926,0.007536109,0.007443049,0.006922747,
         0.00685514,0.006721853,0.006695838,0.005746367,0.005945173,0.005250153,0.005665752,0.006481695,
         0.006585193,0.00751989,0.009038481,0.009984259,0.011695555,0.014495872,0.018177089,0.027110627,
         0.042244993,0.056861545,0.064008071,0.062680016,0.060886258,0.055751568,0.048310205,0.038721632],
        [0.023835444,0.016876637,0.012178456,0.009349274,0.007659691,0.006332517,0.005611274,0.005650048,
         0.005502101,0.005168442,0.005128425,0.005395259,0.004998272,0.005229362,0.006775116,0.007912694,
         0.008514274,0.006961449,0.00630672,0.00620858,0.005797218,0.005397357,0.006006318,0.005593869,
         0.005241095,0.005212189,0.00515531,0.004906504,0.004757624,0.004722969,0.004975738,0.005211879,
         0.005684004,0.006331507,0.007031149,0.008034144,0.008731998,0.010738922,0.013170262,0.016638631,
         0.021708313,0.0303703,0.043713685,0.051876584,0.054591464,0.05074126,0.043109775,0.033925231],
        [0.023960632,0.016910619,0.012253193,0.009539031,0.007685214,0.006311553,0.00556675,0.005140391,
         0.004604673,0.004352551,0.004156956,0.004098101,0.00388452,0.00433039,0.005658606,0.006828804,
         0.007253075,0.005872749,0.004923197,0.004521087,0.004454765,0.004304616,0.004466648,0.004178716,
         0.004186183,0.003934784,0.004014114,0.003773073,0.003469885,0.003708517,0.003801095,0.004367245,
         0.004558263,0.005596378,0.005862632,0.006068665,0.006445161,0.007402661,0.007880006,0.009723385,
         0.012243076,0.016280074,0.023909324,0.03586776,0.046595858,0.047521241,0.041417407,0.03322265],
        [0.024387138,0.017950032,0.01339296,0.010486231,0.008634325,0.00752814,0.006562675,0.006180296,
         0.00566116,0.005092682,0.004741384,0.004680853,0.00479228,0.004921812,0.005950605,0.007010479,
         0.007057257,0.005651136,0.004813649,0.00454666,0.004121156,0.003793481,0.004122788,0.004107635,
         0.004363668,0.004310674,0.004122943,0.004014391,0.004009496,0.003805058,0.004133355,0.004188447,
         0.005268291,0.005964825,0.005774607,0.006292344,0.006813734,0.007634982,0.008723529,0.009855823,
         0.012318322,0.017097237,0.026780014,0.037823534,0.046797578,0.045940354,0.039472789,0.033058217],
        [0.023920296,0.01690733,0.012917415,0.010191735,0.008787867,0.007681138,0.006600128,0.006043227,
         0.005963814,0.005885256,0.006164212,0.005876554,0.005432168,0.00580157,0.00641092,0.007280576,
         0.00811752,0.007006283,0.006505718,0.005917892,0.005420978,0.005527121,0.005317478,0.004793601,
         0.004577663,0.004958332,0.005159584,0.004925386,0.005192686,0.0054453,0.005400465,0.005331386,
         0.005994507,0.006370203,0.006800758,0.007947816,0.009005592,0.010608225,0.012905449,0.015976909,
         0.024610768,0.036414926,0.04680022,0.050678553,0.051188831,0.046725936,0.03998602,0.032496965],
        [0.022221313,0.016428778,0.01266253,0.010569518,0.008926713,0.007929788,0.007134802,0.006773883,
         0.006485147,0.006766094,0.007202971,0.007480145,0.008460127,0.011414527,0.014342431,0.01448993,
         0.012040415,0.008520428,0.0077578,0.006421555,0.005889369,0.005915144,0.006229011,0.005425193,
         0.005094464,0.005674584,0.005898523,0.006504338,0.005893063,0.005967896,0.0061056,0.006017598,
         0.007500459,0.008041236,0.0099079,0.012297435,0.01592606,0.021574549,0.032780393,0.04502082,
         0.054970312,0.05930568,0.060189471,0.057269758,0.05486585,0.047401041,0.038520417,0.029925316],
        [0.023567522,0.016304584,0.012443113,0.009961033,0.008395854,0.007242191,0.006314956,0.005722235,
         0.005385313,0.005197814,0.005444756,0.0064894,0.008409762,0.015347201,0.025458901,0.028619409,
         0.023359044,0.014869014,0.011900433,0.010931316,0.010085903,0.009253621,0.008044246,0.007866149,
         0.007665985,0.007218414,0.00797338,0.008005782,0.007407311,0.008118996,0.008648934,0.010378068,
         0.013347814,0.018541666,0.026917161,0.035860046,0.049702909,0.063560224,0.069741764,0.070609245,
         0.069689625,0.069439031,0.068785313,0.065634051,0.062207874,0.053986076,0.043508937,0.033498873],
        [0.025283869,0.018061868,0.013832406,0.01099122,0.009057752,0.007415348,0.006415533,0.006118688,
         0.005617255,0.005084989,0.005552217,0.006364787,0.00792208,0.014440148,0.02451,0.02993728,
         0.024790064,0.016859553,0.013140437,0.012181571,0.010857371,0.010621789,0.010389982,0.010087677,
         0.00981219,0.0097001,0.01014589,0.01052881,0.01044948,0.011167223,0.013610154,0.02047533,
         0.035335895,0.05409712,0.067805633,0.074003571,0.077948793,0.078981046,0.077543712,0.074620225,
         0.072631194,0.070886175,0.06972224,0.068354439,0.063806373,0.055709895,0.045866391,0.035248054],
        [0.030992394,0.022532047,0.016965296,0.013268634,0.010662773,0.008986943,0.007580978,0.006707669,
         0.00646337,0.006180296,0.006229094,0.006626391,0.00780049,0.013149437,0.022621172,0.033064744,
         0.035953213,0.029010413,0.023490829,0.020477646,0.018671663,0.017186751,0.016526661,0.015415424,
         0.014552683,0.014347935,0.014115058,0.013739051,0.014944386,0.017543021,0.021605977,0.032100988,
         0.049851633,0.063453382,0.072579104,0.076921792,0.079601317,0.079548711,0.078653413,0.076225647,
         0.073936893,0.073585752,0.071911165,0.069220452,0.065925982,0.059952377,0.0510938,0.041481111]]
    
    lumens = 11.2*59.73*(TFA*N_occupants)**0.4714
    
    kWhperyear = 1/3*lumens/21+2/3*lumens/lighting_efficacy
    kWhperday = kWhperyear / 365
    #lighting_energy_kWh=[]
    lighting_gains_W=[]
    
    for monthly_profile in avg_monthly_halfhr_profiles:
        #lighting_energy_kWh+=[frac * kWhperday for frac in monthly_profile]
        '''
        To obtain the lighting gains, 
        the above should be converted to Watts by multiplying the individual half-hourly figure by (2 x 1000). 
        Since some lighting energy will be used in external light 
        (e.g. outdoor security lights or lights in unheated spaces like garages and sheds) 
        a factor of 0.85 is also applied to get the internal gains from lighting. 
        '''
        lighting_gains_W.append([0.85 *(frac*kWhperday) * 2 * 1000 for frac in monthly_profile])
    
    project_dict['InternalGains']['LightingGains'] = {
        "start_day" : 0,
        "timestep":0.5,
        "schedule_lighting_gains":{
            "Watts_lighting_monthly": lighting_gains_W
        }
    }
    
def create_cooking_gains(project_dict,N_occupants):
    
    '''
    no cooking type in project dict yet, using dummy
    '''
    cooking_type = 'gasonly'
    
    cooking_profile_fhs = [
        0.001192419,0.000825857,0.000737298,0.000569196,
        0.000574409,0.000573778,0.000578369,0.000574619,0.000678235,
        0.000540799,0.000718043,0.002631192,0.002439288,0.003263445,
        0.003600656,0.005743044,0.011250675,0.015107564,0.014475307,
        0.016807917,0.018698336,0.018887283,0.021856976,0.047785397,
        0.08045051,0.099929701,0.042473353,0.02361216,0.015650513,
        0.014345379,0.015951211,0.01692045,0.037738026,0.066195428,
        0.062153502,0.073415686,0.077486476,0.069093846,0.046706527,
        0.024924648,0.014783978,0.009192004,0.005617715,0.0049381,
        0.003529689,0.002365773,0.001275927,0.001139293]
    
    if cooking_type == 'eleconly':
        EC1elec = 275
        EC1gas = 55
        EC2elec = 0
        EC2gas = 0
    elif cooking_type == 'gasonly':
        EC1elec = 0
        EC1gas = 0
        EC2elec = 481
        EC2gas = 96
    elif cooking_type == 'gaselecmix':
        EC1elec = 138
        EC1gas = 28
        EC2elec = 241
        EC2gas = 48
        
    annual_cooking_elec_kWh = EC1elec + EC2elec * N_occupants
    annual_cooking_gas_kWh = EC1gas + EC2gas * N_occupants
    
    cooking_elec_profile_W = [(1000/2) * 0.9 * annual_cooking_elec_kWh / 365 * halfhr for halfhr in cooking_profile_fhs]
    cooking_gas_profile_W = [ (1000/2) * 0.75 * annual_cooking_gas_kWh / 365 * halfhr for halfhr in cooking_profile_fhs]
    
    project_dict['InternalGains']['CookingGains'] = {
        "start_day" : 0,
        "timestep":0.5,
        "schedule_cooking_gains":{
            "Watts_Gas": cooking_elec_profile_W, #need this per square meter!
            "Watts_Elec": cooking_gas_profile_W
        }
    }
    
def create_appliance_gains(project_dict,TFA,N_occupants):
    
    avg_monthly_hr_profiles = [
    [0.025995114,0.023395603,0.022095847,0.020796091,0.019496336,0.022095847,0.02729487,0.040292427,0.048090962,0.049390717,0.050690473,0.049390717,0.053289984,0.049390717,0.050690473,0.053289984,0.074086076,0.087083633,0.08188461,0.070186809,0.064987786,0.057189252,0.046791206,0.033793649],
    [0.025995114,0.023395603,0.022095847,0.020796091,0.019496336,0.022095847,0.02729487,0.032493893,0.046791206,0.051990229,0.049390717,0.046791206,0.048090962,0.046791206,0.04549145,0.049390717,0.062388274,0.074086076,0.080584854,0.067587297,0.059788763,0.050690473,0.044191694,0.032493893],
    [0.024695359,0.020796091,0.020796091,0.019496336,0.020796091,0.022095847,0.029894381,0.041592183,0.04549145,0.048090962,0.04549145,0.04549145,0.049390717,0.048090962,0.048090962,0.049390717,0.057189252,0.070186809,0.07278632,0.067587297,0.061088519,0.051990229,0.041592183,0.029894381],
    [0.022095847,0.022095847,0.022095847,0.022095847,0.023395603,0.029894381,0.038992672,0.046791206,0.046791206,0.044191694,0.046791206,0.048090962,0.044191694,0.042891939,0.044191694,0.051990229,0.062388274,0.061088519,0.058489007,0.057189252,0.050690473,0.041592183,0.033793649,0.024695359],
    [0.024695359,0.022095847,0.020796091,0.020796091,0.023395603,0.031194137,0.038992672,0.044191694,0.048090962,0.046791206,0.044191694,0.04549145,0.041592183,0.037692916,0.038992672,0.049390717,0.05458974,0.058489007,0.051990229,0.055889496,0.050690473,0.041592183,0.031194137,0.024695359],
    [0.022095847,0.020796091,0.020796091,0.019496336,0.020796091,0.024695359,0.032493893,0.042891939,0.044191694,0.041592183,0.040292427,0.042891939,0.040292427,0.038992672,0.040292427,0.044191694,0.053289984,0.057189252,0.048090962,0.048090962,0.04549145,0.041592183,0.031194137,0.024695359],
    [0.022095847,0.020796091,0.020796091,0.019496336,0.020796091,0.024695359,0.032493893,0.041592183,0.042891939,0.042891939,0.041592183,0.041592183,0.040292427,0.037692916,0.037692916,0.044191694,0.051990229,0.05458974,0.046791206,0.046791206,0.04549145,0.042891939,0.031194137,0.024695359],
    [0.022095847,0.020796091,0.020796091,0.019496336,0.020796091,0.024695359,0.032493893,0.044191694,0.044191694,0.044191694,0.044191694,0.044191694,0.042891939,0.040292427,0.041592183,0.044191694,0.051990229,0.055889496,0.050690473,0.051990229,0.049390717,0.042891939,0.031194137,0.024695359],
    [0.022095847,0.020796091,0.020796091,0.019496336,0.023395603,0.029894381,0.040292427,0.041592183,0.044191694,0.044191694,0.04549145,0.044191694,0.042891939,0.042891939,0.042891939,0.051990229,0.059788763,0.064987786,0.061088519,0.058489007,0.051990229,0.038992672,0.031194137,0.023395603],
    [0.022095847,0.020796091,0.019496336,0.022095847,0.023395603,0.029894381,0.040292427,0.046791206,0.049390717,0.04549145,0.046791206,0.049390717,0.04549145,0.044191694,0.04549145,0.053289984,0.067587297,0.07278632,0.066287542,0.059788763,0.053289984,0.042891939,0.031194137,0.023395603],
    [0.024695359,0.022095847,0.020796091,0.020796091,0.020796091,0.024695359,0.029894381,0.042891939,0.048090962,0.049390717,0.04549145,0.04549145,0.046791206,0.046791206,0.044191694,0.051990229,0.064987786,0.08188461,0.076685587,0.067587297,0.061088519,0.05458974,0.04549145,0.032493893],
    [0.025995114,0.023395603,0.022095847,0.020796091,0.019496336,0.022095847,0.02729487,0.032493893,0.048090962,0.053289984,0.051990229,0.05458974,0.057189252,0.051990229,0.055889496,0.058489007,0.075385832,0.083184366,0.08188461,0.068887053,0.062388274,0.055889496,0.046791206,0.033793649]]
    
    EA_annual_kWh=207.8*(TFA*N_occupants)**0.4714
    
    appliance_gains_W=[]
    for monthly_profile in avg_monthly_hr_profiles:
        appliance_gains_W.append([1000* EA_annual_kWh * frac / 365 for frac in monthly_profile])
        
    project_dict['InternalGains']['ApplianceGains'] = {
        "start_day" : 0,
        "timestep":1,
        "schedule_appliance_gains":{
            "Watts_appliances_monthly": appliance_gains_W
        }
    }
    
def create_hot_water_gains(project_dict,TFA,N_occupants):
    
    HW_events_dict = {'Time':[7,7.083333333,7.5,8.016666667,8.25,8.5,8.75,9,9.5,10.5,11.5,11.75,12.75,14.5,15.5,16.5,18,18.25,18.5,19,20.5,21.25,21.5],
    'Weekday':['Small','Shower','Small','Small','Small','Small','Small','Small','Small','Floor cleaning','Small','Small','Sdishwash','Small','Small','Small','Small','Household cleaning','Household cleaning','Small','Ldishwash','Small','Shower'],
    'Saturday':['Small','Shower','Shower','Small','Small','Small','Small','Small','Small','Floor cleaning','Small','Small','Sdishwash','Small','Small','Small','Small','Household cleaning','Household cleaning','Small','Ldishwash','Small','Small'],
    'Sunday':['Small','Shower','Small','Small','Small','Small','Small','Small','Small','Floor cleaning','Small','Small','Sdishwash','Small','Small','Small','Small','Household cleaning','Household cleaning','Small','Ldishwash','Small','Bath']}
    
    HW_events_valuesdict = {
        "Small":0.105,
        "Shower":1.4,
        "Floor cleaning":0.105,
        "Sdishwash":0.315,
        "Ldishwash":0.735,
        "Household cleaning":0.105,
        "Bath":1.4,
        "None":0.0 #not in JHs sheet but convenient for eliminations
        }
    
    Weekday_values = [HW_events_valuesdict[x] for x in HW_events_dict['Weekday']]
    Saturday_values = [HW_events_valuesdict[x] for x in HW_events_dict['Saturday']]
    Sunday_values = [HW_events_valuesdict[x] for x in HW_events_dict['Sunday']]
    
    annual_HW_events = []
    annual_HW_events_values = []
    startmod = 0 #this changes what day of the week we start on. 0 is sunday.
    
    for i in range(365):
        if (i+startmod) % 6 ==0:
            annual_HW_events.extend(HW_events_dict['Saturday'])
            annual_HW_events_values.extend(Saturday_values)
        elif(i+startmod) % 7 ==0: 
            annual_HW_events.extend(HW_events_dict['Sunday'])
            annual_HW_events_values.extend(Sunday_values)
        else:
            annual_HW_events.extend(HW_events_dict['Weekday'])
            annual_HW_events_values.extend(Weekday_values)
            
    #QHWEN_original=sum(annual_HW_events_values)
    
    #ref_occupancy = 4.002
    
    SAP2012QHW = 365 * 4.18 * (37/3600) *((25 * N_occupants) + 36)
    refQHW = 365 * sum(Weekday_values)
    
    '''
    this will determine what proportion of events in the list to eliminate, if less than 1
    '''
    ratio = SAP2012QHW / refQHW
    
    if ratio < 1.0:
        '''
        for each event type in the valuesdict, we want to eliminate every 
        kth event where k = ROUND(1/1-ratio,0)
        in one doc JH supplied it was 1/ratio not sure which it should be
        
        this isnt the way JH suggested implementing ,but, unless misunderstood, its doing what is needed
        '''
        k=round(1.0/(1-ratio),0)
        counters={event_type:0 for event_type in HW_events_valuesdict.keys()}
        
        for i,event in enumerate(annual_HW_events):
            counters[event]+=1
            if counters[event] % k == 0:
                annual_HW_events_values[i] =  0.0
                annual_HW_events[i] = 'None'
        
        '''
        correction factor
        '''
        QHWEN_eliminations = sum(annual_HW_events_values)
        FHW = SAP2012QHW / QHWEN_eliminations
    
        HW_events_valuesdict = {key : FHW * HW_events_valuesdict[key] for key in HW_events_valuesdict.keys()}
    
    project_dict['InternalGains']['HWGains'] = {"kWh_per_HW_event":HW_events_valuesdict}
    
    
def create_cooling(project_dict):
    '''
    TODO - only do this if there is a cooling system
    '''
    cooling_setpoint = 24.0
    cooling_schedule_livingroom = project_dict['HeatingPattern']['schedule_heating']['onoff_livingroom_weekday']
    cooling_schedule_restofdwelling = (
        #22:00-07:00 - taking this to mean nighttime only?
        [True for x in range(14)] + 
        [False for x in range(30)] + 
        [True for x in range(4)])
    
    project_dict['CoolingPattern'] = {
        "start_day" : 0,
        "timestep":0.5,
        "setpoints":{"livingroom":cooling_setpoint,
                     "restofdwelling":cooling_setpoint},
        "schedule_heating":{
            "onoff_livingroom_weekday": cooling_schedule_livingroom,
            "onoff_livingroom_weekend": cooling_schedule_livingroom,
            "onoff_restofdwelling_weekday": cooling_schedule_restofdwelling,
            "onoff_restofdwelling_weekend": cooling_schedule_restofdwelling
        }
    }
    
    