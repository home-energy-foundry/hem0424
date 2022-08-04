#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides object(s) to store and look up data on external conditions
(e.g. external air temperature)
"""

class ExternalConditions:
    """ An object to store and look up data on external conditions """

    def __init__(self, 
            simulation_time, 
            air_temps, 
            ground_temps, 
            diffuse_horizontal_radiation,
            direct_beam_radiation,
            solar_reflectivity_of_ground,
            latitude,
            longitude,
            timezone,
            start_day,
            end_day,
            january_first,
            daylight_savings,
            leap_day_included
            ):
        """ Construct an ExternalConditions object

        Arguments:
        simulation_time -- reference to SimulationTime object
        air_temps       -- list of external air temperatures, in deg C (one entry per timestep)
        ground_temps    -- list of external ground temperatures, in deg C (one entry per timestep)
        diffuse_horizontal_radiation    -- list of diffuse horizontal radiation values, in W/m2 (one entry per timestep)
        direct_beam_radiation           -- list of direct beam radiation values, in W/m2 (one entry per timestep)
        solar_reflectivity_of_ground    -- list of external ground temperatures, 0 to 1 (one entry per timestep)
        latitude        -- latitude of weather station, angle from south, in degrees (single value)
        longitude       -- longitude of weather station, easterly +ve westerly -ve, in degrees (single value)
        timezone        -- timezone of weather station, -12 to 12 (single value)
        start_day       -- first day of the time series, day of the year, 1 to 366 (single value)
        end_day         -- last day of the time series, day of the year, 1 to 366 (single value)
        january_first   -- day of the week for January 1st, monday to sunday, 1 to 7 (single value)
        daylight_savings    -- handling of daylight savings time, (single value)
                            e.g. applicable and taken into account, 
                            applicable but not taken into account, 
                            not applicable
        leap_day_included   -- whether climate data includes a leap day, true or false (single value)
        """
        self.__simulation_time  = simulation_time
        self.__air_temps        = air_temps
        self.__ground_temps     = ground_temps
        self.__diffuse_horizontal_radiation = diffuse_horizontal_radiation
        self.__direct_beam_radiation = direct_beam_radiation
        self.__solar_reflectivity_of_ground = solar_reflectivity_of_ground
        self.__latitude = latitude
        self.__longitude = longitude
        self.__timezone = timezone
        self.__start_day = start_day
        self.__end_day = end_day
        self.__january_first = january_first
        self.__daylight_savings = daylight_savings
        self.__leap_day_included = leap_day_included

    def air_temp(self):
        """ Return the external air temperature for the current timestep """
        return self.__air_temps[self.__simulation_time.index()]
        # TODO Assumes air temps list is one entry per timestep but in
        #      future it could be e.g. hourly figures even if timestep is
        #      sub-hourly. This would require the SimulationTime class to
        #      support such lookups.

    def ground_temp(self):
        """ Return the external ground temperature for the current timestep """
        return self.__ground_temps[self.__simulation_time.index()]
        # TODO Assumes ground temps list is one entry per timestep but in
        #      future it could be e.g. hourly figures even if timestep is
        #      sub-hourly. This would require the SimulationTime class to
        #      support such lookups.
        
    def diffuse_horizontal_radiation(self):
        """ Return the diffuse_horizontal_radiation for the current timestep """
        return self.__diffuse_horizontal_radiation[self.__simulation_time.index()]
        # TODO Assumes diffuse_horizontal_radiation list is one entry per timestep but in
        #      future it could be e.g. hourly figures even if timestep is
        #      sub-hourly. This would require the SimulationTime class to
        #      support such lookups.
        
    def direct_beam_radiation(self):
        """ Return the direct_beam_radiation for the current timestep """
        return self.__direct_beam_radiation[self.__simulation_time.index()]
        # TODO Assumes direct_beam_radiation list is one entry per timestep but in
        #      future it could be e.g. hourly figures even if timestep is
        #      sub-hourly. This would require the SimulationTime class to
        #      support such lookups.

    def solar_reflectivity_of_ground(self):
        """ Return the solar_reflectivity_of_ground for the current timestep """
        return self.__solar_reflectivity_of_ground[self.__simulation_time.index()]
        # TODO Assumes solar_reflectivity_of_ground list is one entry per timestep but in
        #      future it could be e.g. hourly figures even if timestep is
        #      sub-hourly. This would require the SimulationTime class to
        #      support such lookups.

    def latitude(self):
        """ Return the latitude """
        return self.__latitude
    
    def longitude(self):
        """ Return the longitude """
        return self.__longitude
    
    def timezone(self):
        """ Return the timezone """
        return self.__timezone
    
    def start_day(self):
        """ Return the start_day """
        return self.__start_day
        # TODO possibly this input sits better within simulation_time
        # but included here until final form decided
    
    def end_day(self):
        """ Return the end_day """
        return self.__end_day
        # TODO possibly this input sits better within simulation_time
        # but included here until final form decided
    
    def january_first(self):
        """ Return the january_first """
        return self.__january_first
        # TODO possibly this input sits better within simulation_time
        # but included here until final form decided

    def daylight_savings(self):
        """ Return the daylight_savings """
        return self.__daylight_savings
        # TODO possibly this input sits better within simulation_time
        # but included here until final form decided
        # currently unclear whether this is reffering to a choice by the user
        # or a statement of the contents of the weather data file

    def leap_day_included(self):
        """ Return the leap_day_included """
        return self.__leap_day_included
        # TODO possibly this input sits better within simulation_time
        # but included here until final form decided
        # currently unclear whether this is reffering to a choice by the user
        # or a statement of the contents of the weather data file


