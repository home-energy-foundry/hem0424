#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains object(s) to track and control information on the
simulation timestep.
"""

# Standard library imports
import math

class SimulationTime:
    """ An iterator object to track properties relating to the simulation timestep

    This object is a "single source of truth" for information on timesteps, and it controls
    incrementing the timestep. It can be queried by other objects that have references to it.
    """
    # TODO Re-write this class in terms of datetime and timedelta objects
    # TODO Add options to return timestep (timedelta) in particular units
    #      (e.g. seconds, minutes or hours)
    # TODO Account for GMT/BST switchover

    def __init__(self, starttime, endtime, step):
        """ Construct a SimulationTime object

        Arguments:
        starttime -- The start time of the simulation, in hours from an arbitrary zero point
        endtime   -- The end time of the simulation, in hours from the same
                     arbitrary zero point as starttime
        step      -- The time increment for each step of the calculation, in hours

        Other variables:
        current   -- The current simulation time, in hours from the same
                     arbitrary zero point as starttime
        total     -- Number of timesteps in simulation
        idx       -- Number of timesteps already run (i.e. zero-based ordinal
                     enumeration of current timestep)
        first     -- True if there have been no iterations yet, False otherwise
        """

        self.__step    = step
        self.__end     = endtime
        self.__current = starttime

        self.__total   = math.ceil((endtime - starttime) / step)
        self.__idx     = 0

        self.__first   = True

    def __iter__(self):
        """ Return a reference to this object when an iterator is required """
        return self

    def __next__(self):
        """ Increment simulation timestep """
        if self.__first:
            # If we are on the first iteration, don't increment counters, but
            # set flag to False for next iteration
            self.__first = False
        else:
            # Increment counters
            self.__idx     = self.__idx     + 1
            self.__current = self.__current + self.__step

        if self.__current >= self.__end:
            # If we have reached the end of the simulation, stop iteration
            raise StopIteration

        return self.__idx, self.__current, self.timestep()

    def current(self):
        """ Return current simulation time """
        return self.__current

    def index(self):
        """ Return ordinal enumeration of current timestep """
        return self.__idx

    def current_hour(self):
        """ Return current hour """
        return int(math.floor(self.__current))

    def hour_of_day(self):
        """ Return hour of day (00:00-01:00 is hour zero) """
        # TODO Assumes that self.__current == 0 is midnight - make this more flexible
        time_of_day = self.__current % 24
        return int(math.floor(time_of_day))

    def total_steps(self):
        """ Return the total number of timesteps in simulation """
        return self.__total

    def timestep(self):
        """ Return the length of the current timestep, in hours """
        return self.__step
