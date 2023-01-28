#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides object(s) to model the behaviour of electric storage heaters.
"""

# Third-party imports
from scipy.integrate import solve_ivp
from pickle import FALSE

class ElecStorageHeater:
    """ Class to represent electric storage heaters """

    def __init__(
            self,
            rated_power,
            thermal_mass,
            frac_convective,
            zone,
            energy_supply_conn,
            simulation_time,
            control,
            ):
        """ Construct an ElecStorageHeater object

        Arguments:
        rated_power        -- in kW
        thermal_mass       -- thermal mass of emitters, in kWh / K
        frac_convective    -- convective fraction for heating
        energy_supply_conn -- reference to EnergySupplyConnection object
        simulation_time    -- reference to SimulationTime object
        control -- reference to a control object which must implement is_on() and setpnt() funcs
        """
        self.__pwr                = rated_power
        self.__thermal_mass       = thermal_mass
        self.__frac_convective    = frac_convective
        self.__zone = zone
        self.__energy_supply_conn = energy_supply_conn
        self.__simtime            = simulation_time
        self.__control            = control
        
        #Initialising other variables
        self.__temp_core_target   = 600#
        self.__temp_core_prev  = 20.0
        self.__c = 0.08
        self.__n = 1.2

    def temp_setpnt(self):
        return self.__control.setpnt()

    def frac_convective(self):
        return self.__frac_convective   
    
    def __func_temp_core_change_rate(self, power_input):
        """ Differential eqn for change rate of emitter temperature, to be solved iteratively

        Derivation:

        Heat balance equation for radiators:
            (T_E(t) - T_E(t-1)) * K_E / timestep = power_input - power_output
        where:
            T_E is mean emitter temperature
            K_E is thermal mass of emitters

        Power output from emitter (eqn from 2020 ASHRAE Handbook p644):
            power_output = c * (T_E(t) - T_rm) ^ n
        where:
            T_rm is air temperature in the room/zone
            c and n are characteristic of the emitters (e.g. derived from BS EN 442 tests)

        Substituting power output eqn into heat balance eqn gives:
            (T_E(t) - T_E(t-1)) * K_E / timestep = power_input - c * (T_E(t) - T_rm) ^ n

        Rearranging gives:
            (T_E(t) - T_E(t-1)) / timestep = (power_input - c * (T_E(t) - T_rm) ^ n) / K_E
        which gives the differential equation as timestep goes to zero:
            d(T_E)/dt = (power_input - c * (T_E - T_rm) ^ n) / K_E

        If T_rm is assumed to be constant over the time period, then the rate of
        change of T_E is the same as the rate of change of deltaT, where:
            deltaT = T_E - T_rm

        Therefore, the differential eqn can be expressed in terms of deltaT:
            d(deltaT)/dt = (power_input - c * deltaT(t) ^ n) / K_E

        This can be solved for deltaT over a specified time period using the
        solve_ivp function from scipy.
        """
        # Apply min value of zero to temp_diff because the power law does not
        # work for negative temperature difference
        return lambda t, temp_diff: (
            (power_input - self.__c * max(0, temp_diff[0]) ** self.__n) / self.__thermal_mass,
        )

    def temp_core(self, time_start, time_end, temp_core_start, temp_rm, power_input):
        """ Calculate emitter temperature after specified time with specified power input """
        # Calculate emitter temp at start of timestep
        temp_diff_start = temp_core_start - temp_rm

        # Get function representing change rate equation and solve iteratively
        func_temp_core_change_rate \
            = self.__func_temp_core_change_rate(power_input)
        temp_diff_core_rm_results \
            = solve_ivp(func_temp_core_change_rate, (time_start, time_end), (temp_diff_start,))

        # Calculate core temp at end of timestep
        temp_diff_core_rm_final = temp_diff_core_rm_results.y[0][-1]
        return temp_rm + temp_diff_core_rm_final
    
    def __energy_to_target_temp(self, temp_core_prev):
        # Calculate the amount energy needed to bring the core to the target temperature
        return(self.__thermal_mass * (self.__temp_core_target - temp_core_prev))

    def __energy_provided_by_charging(self, timestep, temp_core_prev):
        
        flag_charging = False
        current_hour = self.__simtime.current_hour()
        if current_hour < 7:
            flag_charging = True
        
        if flag_charging:    
            if temp_core_prev >= self.__temp_core_target:
                energy_charging = 0.0
            else:
                energy_charging \
                = min(self.__energy_to_target_temp(temp_core_prev), 
                      self.__pwr * self.__simtime.timestep()
                     )
        else:
            energy_charging = 0.0
            
        return energy_charging

    def demand_energy(self, energy_demand):
        """ Demand energy (in kWh) from the heater """

        """ PREVIOUS CODE FROM INSTANT ELEC HEATER
        # Account for time control where present. If no control present, assume
        # system is always active (except for basic thermostatic control, which
        # is implicit in demand calculation).
        # TODO Account for manual (or smart) control where heater may be left
        #      on for longer than it would be under a simple thermostatic
        #      control?
        if self.__control is None or self.__control.is_on():
            # Energy that heater is able to supply is limited by power rating
            # STORAGE HEATERS: 0.7 used as an initial value for passive heating through leakage.
            energy_supplied = min(energy_demand + 0.7, self.__pwr * self.__simulation_time.timestep())
            
            print("%.2f" % energy_supplied, end=" ") 
            print("\t", end=" ")
        else:
            energy_supplied = 0.0

        self.__energy_supply_conn.demand_energy(energy_supplied)
        return energy_supplied """
    
        timestep = self.__simtime.timestep()
        temp_rm_prev = self.__zone.temp_internal_air()
        
        # Calculating energy input from charging process
        energy_provided_by_charging \
                = self.__energy_provided_by_charging(timestep, self.__temp_core_prev)

        # Calculate core temperature and output achieved at end of timestep.
        # Do not allow core temp to fall below room temp
        power_provided_by_charging = energy_provided_by_charging / timestep
        
        current_hour = self.__simtime.current_hour()

        if current_hour > 8 and current_hour < 20:
            # Energy that heater is able to supply is limited by power rating
            # STORAGE HEATERS: 0.7 used as an initial value for passive heating through leakage.
            temp_core = self.temp_core(
                0.0,
                timestep,
                self.__temp_core_prev,
                temp_rm_prev,
                power_provided_by_charging,
                )
            temp_core = max(temp_core, temp_rm_prev)
            energy_released_from_core \
                = energy_provided_by_charging \
                + self.__thermal_mass * (self.__temp_core_prev - temp_core)
            
            energy_supplied = min(energy_demand, energy_released_from_core)
                        
        else:
            # Energy that heater is able to supply is limited by power rating
            # STORAGE HEATERS: 0.7 used as an initial value for passive heating through leakage.
            temp_core = self.temp_core(
                0.0,
                timestep,
                self.__temp_core_prev,
                self.__temp_core_prev-10,
                power_provided_by_charging,
                )
            temp_core = max(temp_core, temp_rm_prev)
            energy_released_from_core \
                = self.__thermal_mass * (self.__temp_core_prev - temp_core)
            
            energy_supplied = energy_released_from_core
        
        # Save emitter temperature for next timestep
        self.__temp_core_prev = temp_core

        print("%.2f" % energy_released_from_core, end=" ") 
        print("\t", end=" ")

        print("%.2f" % temp_core, end=" ") 
        print("\t", end=" ")

        return energy_released_from_core

