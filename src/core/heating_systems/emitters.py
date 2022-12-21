#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides objects to represent radiator and underfloor emitter systems.
"""

# Third-party imports
from scipy.integrate import solve_ivp

#local imports
import core.external_conditions as external_conditions

# Standard library inputs
import sys
from enum import Enum,auto
from numpy import interp

class Emitters:

    def __init__(
            self,
            thermal_mass,
            c,
            n,
            temp_diff_emit_dsgn,
            frac_convective,
            heat_source,
            zone,
            ext_cond,
            control_class,
            design_flow_temp,
            simulation_time
            ):
        """ Construct an Emitters object

        Arguments:
        thermal_mass -- thermal mass of emitters, in kWh / K
        c -- constant from characteristic equation of emitters (e.g. derived from BS EN 442 tests)
        n -- exponent from characteristic equation of emitters (e.g. derived from BS EN 442 tests)
        temp_diff_emit_dsgn -- design temperature difference across the emitters, in deg C or K
        frac_convective -- convective fraction for heating
        heat_source -- reference to an object representing the system (e.g.
                       boiler or heat pump) providing heat to the emitters
        zone -- reference to the Zone object representing the zone in which the
                emitters are located
        simulation_time -- reference to SimulationTime object

        Other variables:
        temp_emitter_prev -- temperature of the emitters at the end of the
                             previous timestep, in deg C
        """
        # TODO What if emitter system has several radiators with different specs?
        # TODO What if emitter system serves more than one zone? What would flow temp be?
        self.__thermal_mass = thermal_mass
        self.__c = c
        self.__n = n
        self.__temp_diff_emit_dsgn = temp_diff_emit_dsgn
        self.__frac_convective = frac_convective
        self.__heat_source = heat_source
        self.__zone = zone
        self.__simtime = simulation_time
        self.__external_conditions = ext_cond
        self.__outside_temp = self.__external_conditions.air_temp()
        self.__ecodesign_control_class = Ecodesign_control_class.from_num(control_class)
        self.__design_flow_temp = design_flow_temp
        
        # Set initial values
        self.__temp_emitter_prev = 20.0

    def temp_setpnt(self):
        return self.__heat_source.temp_setpnt()

    def frac_convective(self):
        return self.__frac_convective

    def temp_flow_return(self):
        """ Calculate flow and return temperature based on ecodesign control class """
        if self.__ecodesign_control_class == Ecodesign_control_class.class_II \
            or self.__ecodesign_control_class == Ecodesign_control_class.class_III \
            or self.__ecodesign_control_class == Ecodesign_control_class.class_VI \
            or self.__ecodesign_control_class == Ecodesign_control_class.class_VII \
            or self.__ecodesign_control_class == Ecodesign_control_class.class_VIII:
            # A heater flow temperature control that varies the flow temperature of 
            # water leaving the heat dependant upon prevailing outside temperature 
            # and selected weather compensation curve.

            # They feature provision for manual adjustment of the weather 
            # compensation curves and therby introduce a technical risk that optimal 
            # minimised flow temperatures are not always achieved.
            
            # TODO Ecodesign class VI has additional benefits from the use of an 
            # indoor temperature sensor to restrict boiler temperatures during 
            # low heat demand but not during high demand. 

            # weather compensation properties could be an input
            # setting max flow temp as the design flow temperature
            min_outdoor_temp = -4.0 
            max_outdoor_temp = 20.0 
            min_flow_temp = 30.0 

            outdoor_temp_limits = [min_outdoor_temp, max_outdoor_temp]
            flow_temp_limits = [min_flow_temp, self.__design_flow_temp]

            # Uses numpy interp
            flow_temp = interp(self.__outside_temp, outdoor_temp_limits, flow_temp_limits)

        elif self.__ecodesign_control_class == Ecodesign_control_class.class_I \
            or self.__ecodesign_control_class == Ecodesign_control_class.class_IV :
            flow_temp = self.__design_flow_temp

        else:
            sys.exit('Ecodesign control class ('+ str(self.__ecodesign_control_class) + ') not valid')

        return_temp = flow_temp * 6.0 / 7.0
        if flow_temp >= 70.0:
            return_temp = 60.0
        
        return flow_temp, return_temp

    def temp_emitter_req(self, power_emitter_req, temp_rm):
        """ Calculate emitter temperature that gives required power output at given room temp

        Power output from emitter (eqn from 2020 ASHRAE Handbook p644):
            power_output = c * (T_E - T_rm) ^ n
        where:
            T_E is mean emitter temperature
            T_rm is air temperature in the room/zone
            c and n are characteristic of the emitters (e.g. derived from BS EN 442 tests)
        Rearrange to solve for T_E
        """
        return (power_emitter_req / self.__c) ** (1.0 / self.__n) + temp_rm

    def __func_temp_emitter_change_rate(self, power_input):
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

    def temp_emitter(self, time_start, time_end, temp_emitter_start, temp_rm, power_input):
        """ Calculate emitter temperature after specified time with specified power input """
        # Calculate emitter temp at start of timestep
        temp_diff_start = temp_emitter_start - temp_rm

        # Get function representing change rate equation and solve iteratively
        func_temp_emitter_change_rate \
            = self.__func_temp_emitter_change_rate(power_input)
        temp_diff_emitter_rm_results \
            = solve_ivp(func_temp_emitter_change_rate, (time_start, time_end), (temp_diff_start,))

        # Calculate emitter temp at end of timestep
        temp_diff_emitter_rm_final = temp_diff_emitter_rm_results.y[0][-1]
        return temp_rm + temp_diff_emitter_rm_final

    def __energy_provided_by_heat_source(self, energy_demand, timestep, temp_rm_prev):
        # When there is some demand, calculate max. emitter temperature
        # achievable and emitter temperature required, and base calculation
        # on the lower of the two.
        # TODO The final calculation of emitter temperature below assumes
        #      constant power output from heating source over the timestep.
        #      It does not account for:
        #      - overshoot/undershoot and then stabilisation of emitter temp.
        #        This leads to emitter temp at end of timestep not exactly
        #        matching temp_emitter_target.
        #          - On warm-up, calculate max. temp achievable, then cap at target
        #            and record time this is reached, then assume target temp is
        #            maintained? Would there be an overshoot to make up for
        #            underheating during warm-up?
        #          - On cool-down to lower target temp, calculate lowest temp achieveable,
        #            with target temp as floor and record time this is reached, then
        #            assume target temp is maintained? Would there be an undershoot
        #            to make up for overheating during cool-down?
        #      - other services being served by heat source (e.g. DHW) as a
        #        higher priority. This may cause intermittent operation or
        #        delayed start which could cause the emitters to cool
        #        through part of the timestep. We could assume that all the
        #        time spent on higher priority services is at the start of
        #        the timestep and run solve_ivp for time periods 0 to
        #        higher service running time (with no heat input) and higher
        #        service running time to timestep end (with heat input). However,
        #        this may not be realistic where there are multiple space
        #        heating services which in reality would be running at the same
        #        time.

        # Calculate emitter and flow temperature required
        power_emitter_req = energy_demand / timestep
        # TODO Apply upper limit to emitter temperature (or is this dealt
        #      with in HP/boiler module?)
        temp_emitter_req = self.temp_emitter_req(power_emitter_req, temp_rm_prev)
        temp_flow_req, _ = self.temp_flow_return()

        # Calculate energy input required
        energy_req_to_warm_emitters \
            = self.__thermal_mass * (temp_emitter_req - self.__temp_emitter_prev)
        energy_req_from_heat_source = max(energy_req_to_warm_emitters + energy_demand,0.0)

        # Calculate emitter temp that can be achieved if heating on full power
        # (adjusted for time spent on higher-priority services)
        heating_sys_energy_max = self.__heat_source.energy_output_max(temp_flow_req)
        heating_sys_power_max = heating_sys_energy_max / timestep
        temp_emitter_max = self.temp_emitter(
            0.0,
            timestep,
            self.__temp_emitter_prev,
            temp_rm_prev,
            heating_sys_power_max,
            )

        # Calculate target emitter and flow temperature, accounting for the
        # max power of the heat source
        temp_emitter_target = min(temp_emitter_req, temp_emitter_max)
        temp_flow_target, temp_return_target = self.temp_flow_return()

        # Get energy output of heat source (i.e. energy input to emitters)
        # TODO Instead of passing temp_flow_req into heating system module,
        #      calculate average flow temp achieved across timestep?
        energy_provided_by_heat_source = self.__heat_source.demand_energy(
            energy_req_from_heat_source,
            temp_flow_target,
            temp_return_target,
            )
        return energy_provided_by_heat_source

    def demand_energy(self, energy_demand):
        """ Demand energy from emitters and calculate how much energy can be provided

        Arguments:
        energy_demand -- in kWh
        """
        timestep = self.__simtime.timestep()
        temp_rm_prev = self.__zone.temp_internal_air()

        if energy_demand <= 0:
            # Emitters cooling down or at steady-state with heating off
            energy_provided_by_heat_source = 0.0
        else:
            # Emitters warming up or cooling down to a target temperature
            energy_provided_by_heat_source \
                = self.__energy_provided_by_heat_source(energy_demand, timestep, temp_rm_prev)

        # Calculate emitter temperature and output achieved at end of timestep.
        # Do not allow emitter temp to fall below room temp
        power_provided_by_heat_source = energy_provided_by_heat_source / timestep
        temp_emitter = self.temp_emitter(
            0.0,
            timestep,
            self.__temp_emitter_prev,
            temp_rm_prev,
            power_provided_by_heat_source,
            )
        temp_emitter = max(temp_emitter, temp_rm_prev)
        energy_released_from_emitters \
            = energy_provided_by_heat_source \
            + self.__thermal_mass * (self.__temp_emitter_prev - temp_emitter)

        # Save emitter temperature for next timestep
        self.__temp_emitter_prev = temp_emitter

        return energy_released_from_emitters

class Ecodesign_control_class(Enum):
    # on/off room thermostat
    class_I = auto()
    # weather compensator with modulating heaters
    class_II = auto()
    # weather compensator with on/off heaters
    class_III = auto()
    # TPI room thermostat with on/off heaters
    class_IV = auto()
    # modulating room thermostat with modulating heaters
    class_V = auto()
    # weather compensator with room sensor for modulating heaters
    class_VI = auto()
    # weather compensator with room sensor for on/off heaters
    class_VII = auto()
    # multi room temperature control with modulating heaters
    class_VIII = auto()
    
    @classmethod
    def from_num(cls, numval):
        if numval == 1:
            return cls.class_I
        elif numval == 2:
            return cls.class_II
        elif numval == 3:
            return cls.class_III
        elif numval == 4:
            return cls.class_IV
        elif numval == 5:
            return cls.class_V
        elif numval == 6:
            return cls.class_VI
        elif numval == 7:
            return cls.class_VII
        elif numval == 8:
            return cls.class_VIII
        else:
            sys.exit('ecodesign control class ('+ str(numval) + ') not valid')
