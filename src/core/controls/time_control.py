#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides objects to model time controls.
"""

class OnOffTimeControl:
    """ An object to model a time-only control with on/off (not modulating) operation """

    def __init__(self, schedule, simulation_time):
        """ Construct an OnOffTimeControl object

        Arguments:
        schedule        -- list of boolean values where true means "on" (one entry per timestep)
        simulation_time -- reference to SimulationTime object
        """
        self.__schedule        = schedule
        self.__simulation_time = simulation_time

    def is_on(self):
        """ Return true if control will allow system to run """
        return self.__schedule[self.__simulation_time.index()]
        # TODO Assumes schedule is one entry per timestep but in
        #      future it could be e.g. hourly figures even if timestep is
        #      sub-hourly. This would require the SimulationTime class to
        #      support such lookups.
