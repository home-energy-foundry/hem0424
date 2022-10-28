#!/usr/bin/env python3
import scipy.interpolate

"""TODO Copyright & licensing notices

This module provides objects to model waste water heat recovery systems of different types.
"""

class WWHRS_InstantaneousSystemB:
    """ A class to represent instantaneous waste water heat recovery systems with arrangement B
    
    For System B WWHRS, output of the heat exchanger is fed to the shower only
    """
    
    def __init__(self, flow_rates, efficiencies, cold_water_source):
        self.__cold_water_source = cold_water_source
        self.__flow_rates = flow_rates
        self.__efficiencies = efficiencies


    def temperature(self, temp_target, flowrate_waste_water=None, flowrate_cold_water=None):
        # TODO The cold water flow rate depends on the temperature returned from
        #      this function, which may create a circularity in the calculation.
        #      May need to integrate System B into shower module and/or combine
        #      equations.
        
        # Get cold feed temperature
        temp_cold = self.__cold_water_source.temperature()
        
        # TODO If flowrates have been provided for waste and cold water:
        #    - Calc heat recovered from waste water. Need to do this per shower
        #      individually? Need WWHRS_Connection object?
        wwhrs_efficiency = self.get_efficiency_from_flowrate(flowrate_waste_water)
        
        print(wwhrs_efficiency)
        print(temp_cold)
        print (temp_target)
        
        #    - Calc temp of pre-heated water based on heat recovered and flow rates
        temp_cold = temp_cold + ((wwhrs_efficiency/100) * (temp_target - temp_cold))
        
        # TODO we need to account for any lag in the heatup on heat recovery
        
        # Return temp of cold water (pre-heated if relevant)
        return(temp_cold)


    def get_efficiency_from_flowrate(self, flowrate):

        y_interp = scipy.interpolate.interp1d(self.__flow_rates, self.__efficiencies)
        
        return(y_interp(flowrate))
        
        

class WWHRS_InstantaneousSystemC:
    """ A class to represent instantaneous waste water heat recovery systems with arrangement C
    
    For System C WWHRS, output of the heat exchanger is fed to the hot water system only
    """
    
    def __init__(self, eff_vs_flowrate, cold_water_source):
        self.__efficiency = eff_vs_flowrate # TODO Handle efficiency vs flow rate lookup
        self.__cold_water_source = cold_water_source
        
    # TODO Cold water flowrate to the shower is irrelevant for SystemC
    #      - the cold water flowing to the boiler is the hot water flowing
    #      to the shower. Need to differentiate between calls from shower
    #      object and calls from hot water system object as only the latter
    #      should see the elevated cold water temp due to heat recovery.
    #      Note that waste water flowrate can be provided by shower object
    #      and hot water flowrate could be provided by hot water system
    #      object. Could handle this by having two types of WWHRS_Connection
    #      object or just two different functions to call in this object.
    
    def drain_water(self, flowrate_waste_water):
        # TODO Save waste water flowrate for later calculation
        pass

    def temperature(self, flowrate_cold_water):
        # Note the cold water flowrate to the boiler is the hot water flowrate to the shower.
        
        # Get cold feed temperature
        temp_cold = self.__cold_water_source.temperature()
        
        # TODO If flowrates have been provided for waste and hot water:
        #    - Calc heat recovered from waste water. Need to do this per shower
        #      individually? Need WWHRS_Connection object?
        #    - Calc temp of pre-heated water based on heat recovered and flow rates
        #    - Save temp of pre-heated water
        
        # TODO Return temp of cold water (not pre-heated if this is being
        #      called by shower object)
        pass


class WWHRS_InstantaneousSystemA:
    """ A class to represent instantaneous waste water heat recovery systems with arrangement A
    
    For System A WWHRS, output of the heat exchanger is fed to both the shower
    and the hot water system
    """
    
    def __init__(self, eff_vs_flowrate, cold_water_source):
        self.__efficiency = eff_vs_flowrate # TODO Handle efficiency vs flow rate lookup
        self.__cold_water_source = cold_water_source
    
    def drain_water(self, flowrate_waste_water, flowrate):
        # TODO May need cold water flow rates to both shower and hot water
        #      system (which would be the cold and hot flow rates to the shower)
        #      and waste water flow rate (sum of the cold and hot flow rates)
        #      for calculation
        temp_cold = self.__cold_water_source.temperature()
        # TODO Calc heat recovered and save. Need to do this per shower individually?
        #      Need to differentiate between shower and hot water system querying temp - WWHRS_Connection object?
        #      Perhaps merge this with temperature() function, giving that
        #      function optional arguments that only showers will use? This
        #      would need same optional inputs added to ColdWaterSource temperature() func

    def temperature(self):
        pass # TODO Return cold feed temp with recovered heat
