#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides objects to model time controls.
"""

# Standard library imports
import sys

class OnOffTimeControl:
    """ An object to model a time-only control with on/off (not modulating) operation """

    def __init__(self, schedule, simulation_time, start_day, time_series_step):
        """ Construct an OnOffTimeControl object

        Arguments:
        schedule         -- list of boolean values where true means "on" (one entry per hour)
        simulation_time  -- reference to SimulationTime object
        start_day        -- first day of the time series, day of the year, 0 to 365 (single value)
        time_series_step -- timestep of the time series data, in hours
        """
        self.__schedule        = schedule
        self.__simulation_time = simulation_time
        self.__start_day = start_day
        self.__time_series_step = time_series_step

    def is_on(self):
        """ Return true if control will allow system to run """
        return self.__schedule[self.__simulation_time.time_series_idx(self.__start_day, self.__time_series_step)]


class ToUChargeControl:
    """ An object to model a control that governs electrical charging of a heat storage device 
        that can respond to signals from the grid, for example when carbon intensity is low """

    def __init__(self, schedule, simulation_time, start_day, time_series_step, charge_level):
        """ Construct a ToUChargeControl object

        Arguments:
        schedule         -- list of boolean values where true means "on" (one entry per hour)
        simulation_time  -- reference to SimulationTime object
        start_day        -- first day of the time series, day of the year, 0 to 365 (single value)
        time_series_step -- timestep of the time series data, in hours
        TODO: requires creation of an enum list once options are established.
        charge_level     -- Proportion of the charge targeted for each day
        """
        self.__schedule        = schedule
        self.__simulation_time = simulation_time
        self.__start_day = start_day
        self.__time_series_step = time_series_step
        self.__charge_level = charge_level

    def is_on(self):
        """ Return true if control will allow system to run """
        return self.__schedule[self.__simulation_time.time_series_idx(self.__start_day, self.__time_series_step)]

    def target_charge(self):
        """ Return the charge level value from the list given in inputs; one value per day """
        return self.__charge_level[
            self.__simulation_time.time_series_idx_days(self.__start_day, self.__time_series_step)
        ]


class SetpointTimeControl:
    """ An object to model a control with a setpoint which varies per timestep """

    def __init__(
            self,
            schedule,
            simulation_time,
            start_day,
            time_series_step,
            setpoint_min=None,
            setpoint_max=None,
            default_to_max=None,
            ):
        """ Construct a SetpointTimeControl object

        Arguments:
        schedule         -- list of float values (one entry per hour)
        simulation_time  -- reference to SimulationTime object
        start_day        -- first day of the time series, day of the year, 0 to 365 (single value)
        time_series_step -- timestep of the time series data, in hours
        setpoint_min -- min setpoint allowed
        setpoint_max -- max setpoint allowed
        default_to_max -- if both min and max limits are set but setpoint isn't,
                          whether to default to min (False) or max (True) 
        """
        self.__schedule        = schedule
        self.__simulation_time = simulation_time
        self.__start_day = start_day
        self.__time_series_step = time_series_step
        self.__setpoint_min = setpoint_min
        self.__setpoint_max = setpoint_max
        self.__default_to_max = default_to_max

    def is_on(self):
        """ Return true if control will allow system to run """
        schedule_idx = self.__simulation_time.time_series_idx(
            self.__start_day,
            self.__time_series_step,
            )
        setpnt = self.__schedule[schedule_idx]
        # For this type of control, system is always on if min or max are set
        if setpnt is None and self.__setpoint_min is None and self.__setpoint_max is None:
            return False
        else:
            return True

    def setpnt(self):
        """ Return setpoint for the current timestep """
        schedule_idx = self.__simulation_time.time_series_idx(
            self.__start_day,
            self.__time_series_step,
            )
        setpnt = self.__schedule[schedule_idx]

        if setpnt is None:
            # If no setpoint value is in the schedule, use the min/max if set
            if self.__setpoint_max is None and self.__setpoint_min is None:
                pass # Use setpnt None
            elif self.__setpoint_max is not None and self.__setpoint_min is None:
                setpnt = self.__setpoint_max
            elif self.__setpoint_min is not None and self.__setpoint_max is None:
                setpnt = self.__setpoint_min
            else: # min and max both set
                if self.__default_to_max is None:
                    sys.exit('ERROR: Setpoint not set but min and max both set, '
                             'and which to use by default not specified')
                elif self.__default_to_max:
                    setpnt = self.__setpoint_max
                else:
                    setpnt = self.__setpoint_min
        else:
            # If there is a maximum limit, take the lower of this and the schedule value
            if self.__setpoint_max is not None:
                setpnt = min(self.__setpoint_max, setpnt)
            # If there is a minimum limit, take the higher of this and the schedule value
            if self.__setpoint_min is not None:
                setpnt = max(self.__setpoint_min, setpnt)
        return setpnt
