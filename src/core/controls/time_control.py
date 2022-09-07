#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides objects to model time controls.
"""

class OnOffTimeControl:
    """ An object to model a time-only control with on/off (not modulating) operation """

    def __init__(self, schedule, simulation_time, start_day):
        """ Construct an OnOffTimeControl object

        Arguments:
        schedule        -- list of boolean values where true means "on" (one entry per hour)
        simulation_time -- reference to SimulationTime object
        start_day       -- first day of the time series, day of the year, 0 to 365 (single value)
        """
        self.__schedule        = schedule
        self.__simulation_time = simulation_time
        self.__start_day = start_day

    def is_on(self):
        """ Return true if control will allow system to run """
        return self.__schedule[self.__simulation_time.time_series_idx(self.__start_day)]
        # TODO Assumes schedule is one entry per hour but this should be made
        #      more flexible in the future.
