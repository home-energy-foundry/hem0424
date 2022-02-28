#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides objects to represent the source(s) of cold water.
"""

class ColdWaterSource:
    """ An object to represent a source of cold water """

    def __init__(self, cold_water_temps, simulation_time):
        """ Construct a ColdWaterSource object

        Arguments:
        cold_water_temps -- list of cold water temperatures, in deg C (one entry per timestep)
        simulation_time  -- reference to SimulationTime object
        """
        self.__cold_water_temps = cold_water_temps
        self.__simulation_time  = simulation_time

    def temperature(self):
        """ Return the cold water temperature for the current timestep """
        return self.__cold_water_temps[self.__simulation_time.index()]
        # TODO Assumes cold water temps list is one entry per timestep but in
        #      future it could be e.g. hourly figures even if timestep is
        #      sub-hourly. This would require the SimulationTime class to
        #      support such lookups.
