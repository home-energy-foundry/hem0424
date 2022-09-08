#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides object(s) to store and look up data on external conditions
(e.g. external air temperature)
"""

class ExternalConditions:
    """ An object to store and look up data on external conditions """

    def __init__(self, simulation_time, air_temps):
        """ Construct an ExternalConditions object

        Arguments:
        simulation_time -- reference to SimulationTime object
        air_temps       -- list of external air temperatures, in deg C (one entry per timestep)
        """
        self.__simulation_time  = simulation_time
        self.__air_temps        = air_temps

    def air_temp(self):
        """ Return the external air temperature for the current timestep """
        return self.__air_temps[self.__simulation_time.current_hour()]
        # TODO Assumes air temps list is one entry per timestep but in
        #      future it could be e.g. hourly figures even if timestep is
        #      sub-hourly. This would require the SimulationTime class to
        #      support such lookups.

    def air_temp_annual(self):
        """ Return the average air temperature for the year """
        assert len(self.__air_temps) == 8760 # Only works if data for whole year has been provided
        return sum(self.__air_temps) / len(self.__air_temps)

    def air_temp_monthly(self):
        """ Return the average air temperature for the current month """
        # Get start and end hours for current month
        idx_start, idx_end = self.__simulation_time.current_month_start_end_hour()
        # Get air temperatures for the current month
        air_temps_month = self.__air_temps[idx_start:idx_end]

        return sum(air_temps_month) / len(air_temps_month)
