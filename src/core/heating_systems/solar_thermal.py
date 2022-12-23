#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains objects that represent solar thermal systems.
Method 3 in BS EN 15316-4-3:2017.
"""

# Standard library imports

# Local imports
from core.material_properties import WATER
import core.units as units
# TODO MJFC: Any other imports required?


class SolarThermalSystem:
    """ An object to represent a solar thermal system """

    #BS EN 15316-4-3:2017 Appendix B default input data
    #Model Information
    #Air temperature in a heated space in the building
    #Default taken from Table B20 of standard
    __air_temp_heated_room = 20

    """ Initially hard code inputs and add them to the input file later """
    #Table 18
    # Water specific heat (J/kg.K) - Cw
    __water_specific_heat = 4186
    #Collector loop location ("HS", "NHS", "OUT")
    __SOL_LOC = "NHS"
    

    def __init__(self, 
                 sol_loc,
                 area_module,
                 modules,
                 peak_collector_efficiency,
                 incidence_angle_modifier,
                 first_order_hlc,
                 second_order_hlc,
                 collector_mass_flow_rate,
                 power_pump,
                 power_pump_control,
                 tilt,
                 orientation,
                 solar_loop_piping_hlc,
                 ext_cond, 
                 simulation_time,
                 contents=WATER,
                 ):
        """ Construct a SolarThermalSystem object

        Arguments:
        sol_loc          -- Peak power in kW; represents the electrical power of a photovoltaic
                            system with a given area and a for a solar irradiance of 1 kW/m2
                            on this surface (at 25 degrees)
                            TODO - Could add other options at a later stage.
                            Standard has alternative method when peak power is not available
                            (input type of PV module and Area instead when peak power unknown)
        ventilation_strategy   -- ventilation strategy of the PV system.
                                  This will be used to determine the system performance factor
                                   based on a lookup table
        pitch            -- is the tilt angle (inclination) of the PV panel from horizontal,
                            measured upwards facing, 0 to 90, in degrees.
                            0=horizontal surface, 90=vertical surface.
                            Needed to calculate solar irradiation at the panel surface.
        orientation      -- is the orientation angle of the inclined surface, expressed as the
                            geographical azimuth angle of the horizontal projection of the inclined
                            surface normal, -180 to 180, in degrees;
                            Assumed N 180 or -180, E 90, S 0, W -90
                            TODO - PV standard refers to angle as between 0 to 360?
                            Needed to calculate solar irradiation at the panel surface.
        ext_cond         -- reference to ExternalConditions object
        energy_supply_conn    -- reference to EnergySupplyConnection object
        simulation_time  -- reference to SimulationTime object
        overshading      -- TODO could add at a later date. Feed into solar module
        """
        self.__sol_loc = sol_loc
        self.__area_module = area_module
        self.__modules = modules
        self.__area = area_module * modules
        self.__peak_collector_efficiency = peak_collector_efficiency
        self.__incidence_angle_modifier = incidence_angle_modifier
        self.__first_order_hlc = first_order_hlc
        self.__second_order_hlc = second_order_hlc
        self.__collector_mass_flow_rate = collector_mass_flow_rate
        self.__power_pump = power_pump
        self.__power_pump_control = power_pump_control
        self.__tilt = tilt
        self.__orientation = orientation
        self.__solar_loop_piping_hlc = solar_loop_piping_hlc
        self.__external_conditions = ext_cond
        self.__simulation_time = simulation_time
        
        #water specific heat in kWh/kg.K
        self.__Cp = contents.specific_heat_capacity_kWh()

    def collector_reference_area(self):
        """ Calculate total collector reference area from collector module reference area and
            number of modules
            eq 50 of STANDARD """

        #collector reference area in m2
        self.__area = self.__area_module * self.__modules

