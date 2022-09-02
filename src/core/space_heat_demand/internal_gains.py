#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides objects to represent the internal gains.
"""

class InternalGains:
    """ An object to represent internal gains """

    def __init__(self, total_internal_gains, simulation_time, start_day):
        """ Construct a InternalGains object

        Arguments:
        total_internal_gains -- list of internal gains, in W/m2 (one entry per timestep)
        simulation_time  -- reference to SimulationTime object
        start_day        -- first day of the time series, day of the year, 0 to 365 (single value)
        """
        self.__total_internal_gains = total_internal_gains
        self.__simulation_time  = simulation_time
        self.__start_day = start_day

    def total_internal_gain(self):
        """ Return the total internal gain for the current timestep """
        return self.__total_internal_gains[self.__simulation_time.time_series_idx(self.__start_day)]
