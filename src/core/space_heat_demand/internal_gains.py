#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides objects to represent the internal gains.
"""

class InternalGains:
    """ An object to represent internal gains """

    def __init__(self, total_internal_gains, simulation_time):
        """ Construct a InternalGains object

        Arguments:
        total_internal_gains -- list of internal gains, in W (one entry per timestep)
        simulation_time  -- reference to SimulationTime object
        """
        self.__total_internal_gains = total_internal_gains
        self.__simulation_time  = simulation_time

    def total_internal_gain(self):
        """ Return the total internal gain for the current timestep """
        return self.__total_internal_gains[self.__simulation_time.current_hour()]
