#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides object(s) to store and look up data on external conditions
(e.g. external air temperature)
"""

class ExternalConditions:
    """ An object to store and look up data on external conditions """

    def __init__(self, simulation_time, air_temps, ground_temps, wind_speeds):
        """ Construct an ExternalConditions object

        Arguments:
        simulation_time -- reference to SimulationTime object
        air_temps       -- list of external air temperatures, in deg C (one entry per timestep)
        ground_temps    -- list of external ground temperatures, in deg C (one entry per timestep)
        """
        self.__simulation_time  = simulation_time
        self.__air_temps        = air_temps
        self.__ground_temps     = ground_temps
        self.__wind_speeds      = wind_speeds

    def air_temp(self):
        """ Return the external air temperature for the current timestep """
        return self.__air_temps[self.__simulation_time.current_hour()]
        # TODO Assumes air temps list is one entry per timestep but in
        #      future it could be e.g. hourly figures even if timestep is
        #      sub-hourly. This would require the SimulationTime class to
        #      support such lookups.

    def ground_temp(self):
        """ Return the external ground temperature for the current timestep """
        return self.__ground_temps[self.__simulation_time.current_hour()]
        # TODO Assumes ground temps list is one entry per timestep but in
        #      future it could be e.g. hourly figures even if timestep is
        #      sub-hourly. This would require the SimulationTime class to
        #      support such lookups.

    def wind_speed(self):
        """ Return the wind speed for the current timestep """
        return self.__wind_speeds[self.__simulation_time.current_hour()]
        # TODO Assumes ground temps list is one entry per timestep but in
        #      future it could be e.g. hourly figures even if timestep is
        #      sub-hourly. This would require the SimulationTime class to
        #      support such lookups.
