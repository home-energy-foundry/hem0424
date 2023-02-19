#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides object(s) to model the behaviour of electric storage heaters.
"""

# Third-party imports
from scipy.integrate import solve_ivp
import numpy as np
from scipy.integrate._ivp.ivp import OdeResult
import types
from typing import Union

# Local imports
import core.units as units
from core.space_heat_demand.zone import Zone
from core.energy_supply.energy_supply import EnergySupplyConnection
from core.simulation_time import SimulationTime
from core.controls.time_control import SetpointTimeControl


class ElecStorageHeater:
    """ Class to represent electric storage heaters """

    def __init__(
        self,
        rated_power: float,
        rated_power_instant: float,
        flue_type: str,
        temp_dis_safe: float,
        thermal_mass: float,
        frac_convective: float,
        U_ins: float,
        mass_core: float,
        c_pcore: float,
        temp_core_target: float,
        A_core: float,
        c_wall: float,
        n_wall: float,
        thermal_mass_wall: float,
        n_units: int,
        zone: Zone,
        energy_supply_conn: EnergySupplyConnection,
        simulation_time: SimulationTime,
        control: SetpointTimeControl
    ):
        """Construct an ElecStorageHeater object

        Arguments:
        rated_power          -- in kW (Charging)
        rated_power_instant  -- in kW (Instant backup)
        flue_type            -- type of Electric Storage Heater:
                             -- fan-assisted
                             -- damper
        temp_dis_safe        -- safe temperature to discharge hot air from device (60 degC)
        thermal_mass         -- thermal mass of emitters, in kWh / K
        frac_convective      -- convective fraction for heating (TODO: Check if necessary)
        U_ins                -- U-value insulation between core and case [W/m^2/K]
        mass_core            -- kg mass core material [kg]
        c_pcore              -- thermal capacity of core material [J/kg/K]
        temp_core_target     -- target temperature for the core material on charging mode
                             -- this might include weather compensation with future more 
                             -- advances controls
        A_core               -- Transfer area between the core and air [m2]
        c_wall               -- constant from characteristic equation of emitters (e.g. derived from BS EN 442 tests)
        n_wall               -- exponent from characteristic equation of emitters (e.g. derived from BS EN 442 tests)
        thermal_mass_wall    -- thermal mass of the case
        n_units              -- number of units install in zone
        zone                 -- zone where the unit(s) is/are installed
        energy_supply_conn   -- reference to EnergySupplyConnection object
        simulation_time      -- reference to SimulationTime object
        control              -- reference to a control object which must implement is_on() and setpnt() funcs
        """

        self.__pwr_in: float = (rated_power * units.W_per_kW)
        self.__pwr_instant: float = (rated_power_instant * units.W_per_kW)
        self.__flue_type: str = flue_type
        self.__t_dis_safe: float = temp_dis_safe
        self.__thermal_mass: float = thermal_mass
        self.__frac_convective: float = frac_convective
        self.__Uins: float = U_ins
        self.__n_units: int = n_units
        self.__zone: Zone = zone
        self.__energy_supply_conn: EnergySupplyConnection = energy_supply_conn
        self.__simtime: SimulationTime = simulation_time
        self.__control: SetpointTimeControl = control
        self.__mass: float = mass_core  # 180.0  # kg of core
        self.__c_pcore: float = c_pcore    # 920.0  # J/kg/K core material specific heat
        self.__t_core_target: float = temp_core_target
        self.__A: float = A_core  # 4.0  # m^2 transfer area between core and case or wall
        self.__c: float = c_wall
        self.__n: float = n_wall
        self.__thermal_mass_wall  = thermal_mass_wall

        # Power for driving fan
        # TODO: Parameter will be provided by business, once this happens we can add it to the input json data
        self.__power_for_fan: float = 0.0

        # Initialising other variables
        # Parameters
        self.__time_unit: float = 3600
        self.__c_p: float = 1.0054  # J/kg/K air specific heat

        self.__report_energy_supply: float = 0.0

        """
        The value of R (resistance of air gap) depends on several factors such as the thickness of the air gap, the
        temperature difference across the gap, and the air flow characteristics.
        Here are some typical values for R per inch of air gap thickness:
        Still air: 0.17 m²·K/W
        Air movement (average): 0.07 m²·K/W
        Air movement (high): 0.04 m²·K/W
        Note: These values are for a temperature difference of 24°F (14°C) and a pressure difference of 1 inch of water
        column. The values will change with changes in temperature and pressure differences.
        """

        # 0.17  # Thermal resistance of the air layer between the insulation and the wall of the device.
        # Assuming no change of resistance with temp diff. (Rough aprox)
        self.__Rair_off: float = 0.17
        self.__Rair_on: float = 0.07  # Same as above when the damper is on

        self.temp_air: float = self.__zone.temp_internal_air()  # °C Room temperature
        # case/wall c and n parameters as emitter.

        # kg/s this is the nominal or max rate of air mass passing through the heater with damper open and
        # ideal fan assisted mode
        self.__mass_flow_air: float = 0.0

        # This parameter specicify the opening ratio for the damper of the storage heater. It's set to 1.0 by
        # default but there might be control strategies using this to configure diferent levels of release
        self.damper_fraction: float = 1.0
        # labs_test for electric storage heater reaching 300 degC
        # This represents the temperature difference between the core and the room on the first column
        # and the fraction of air flow relating to the nominal as defined above on the second column
        self.labs_tests_400: list = [
            [324.91, 3.77],
            [286.52, 3.58],
            [254.93, 3.4],
            [228.63, 3.25],
            [206.41, 3.13],
            [187.41, 3.02],
            [171.03, 2.92],
            [156.79, 2.83],
            [144.29, 2.75],
            [133.25, 2.68],
            [123.42, 2.62],
            [114.57, 2.6],
            [106.36, 1.6],
            [98.73, 1.6],
            [91.65, 1.6],
            [85.07, 1.6]
        ]

        self.labs_tests_400_fan: list = [
            [270.15, 5.03],
            [202.2, 5.03],
            [151.33, 5.03],
            [113.24, 5.03],
            [84.73, 5.03],
            [63.39, 5.03],
            [47.1491642, 5.03],
            [35.47, 5.03],
            [26.53, 5.03],
            [19.84, 5.03],
            [14.84, 5.03],
            [11.1, 5.03],
            [8.31, 5.03],
            [6.22, 5.03],
            [4.66, 5.02],
            [3.49, 5.03],
            [2.62, 5.02]
        ]
        self.labs_tests_400_mod: list = [
            [670.15, 6.03],
            [570.15, 6.03],
            [470.15, 6.03],
            [270.15, 6.03],
            [202.2, 4.03],
            [151.33, 4.03],
            [113.24, 4.03],
            [84.73, 4.03],
            [63.39, 4.03],
            [47.42, 4.03],
            [35.47, 4.03],
            [26.53, 4.03],
            [19.84, 4.03],
            [14.84, 4.03],
            [11.1, 4.03],
            [8.31, 4.03],
            [6.22, 4.03],
            [4.66, 4.02],
            [3.49, 4.03],
            [2.62, 4.02]
        ]

        # This represents the temperature difference between the core and the room on the first column
        # and the fraction of air flow relating to the nominal as defined above on the second column
        self.labs_tests: list
        if self.__flue_type == "fan-assisted":
            self.labs_tests = self.labs_tests_400_fan
        else:
            self.labs_tests = self.labs_tests_400

        # Initial conditions
        self.t_core: float = self.__zone.temp_internal_air()
        self.t_wall: float = self.__zone.temp_internal_air()

        self.damper_fraction: float = 1.0
        self.__energy_in: float = 0.0

    def temp_setpnt(self):
        return self.__control.setpnt()

    def frac_convective(self):
        return self.__frac_convective

    def __convert_to_kwh(self, energy: float, timestep: int) -> float:
        """
        Converts energy value supplied to the correct unit
        Arguments
        energy -- Energy value in watts
        timestep -- length of the timestep

        returns -- Energy in kWH
        """
        return energy / units.W_per_kW * timestep * self.__n_units

    def __electric_charge(self, time: float, t_core: float) -> float:
        """
        Calculates power required for unit
        Arguments
        time -- current time period that we are looking at
        t_core -- current temperature of the core

        returns -- Power required in watts
        """
        if time <= 7 * self.__time_unit and t_core <= self.__t_core_target:
            pwr_required: float = (self.__t_core_target - t_core) * self.__mass * self.__c_pcore
            if pwr_required > self.__pwr_in:
                return self.__pwr_in
            else:
                return pwr_required
        else:
            return 0.0

    def __lab_test_ha(self, t_core_rm_diff: float) -> float:
        # labs_test for electric storage heater
        x: list = [row[0] for row in self.labs_tests]
        y: list = [row[1] for row in self.labs_tests]
        return np.interp(t_core_rm_diff, x, y)

    def __calulate_q_dis(self, time: float, t_core: float, q_out_wall: float, q_dis_modo: str) -> float:
        q_dis: float
        if q_dis_modo == "max":
            q_dis = self.__lab_test_ha(t_core - self.temp_air) * (t_core - self.temp_air)

        elif q_dis_modo == 0:
            q_dis = q_dis_modo

        else:
            # Equation for heat transfer to room from wall/case of heater
            q_dis = q_dis_modo - q_out_wall

        return q_dis

    def __return_q_released(self,
                            new_temp_core_and_wall: list,
                            q_released: float,
                            q_dis: float,
                            timestep: int,
                            time: float,
                            q_instant: float = 0.0) -> float:
        # Setting core and wall temperatures to new values, for next iteration
        self.t_core = new_temp_core_and_wall[0]
        self.t_wall = new_temp_core_and_wall[1]

        # the purpose of this calculation is to calculate fan energy required by the device
        energy_for_fan_kwh: float = 0.0
        if self.__flue_type == "fan-assisted":
            self.__mass_flow_air = q_dis / (self.__c_p * (self.__t_dis_safe - self.temp_air))
            energy_for_fan: float = self.__mass_flow_air * self.__power_for_fan
            energy_for_fan_kwh = self.__convert_to_kwh(energy=energy_for_fan, timestep=timestep)

        # might need to redo this calc, but with new t_core calc
        q_in: float = self.__electric_charge(time, self.t_core)

        # Convert values to correct kwh unit
        q_in_kwh: float = self.__convert_to_kwh(energy=q_in, timestep=timestep)
        q_instant_kwh: float = self.__convert_to_kwh(energy=q_instant, timestep=timestep)

        # Save demand energy
        self.__energy_supply_conn.demand_energy(q_in_kwh + energy_for_fan_kwh + q_instant_kwh)

        self.__report_energy_supply = self.__report_energy_supply + q_in_kwh + energy_for_fan_kwh + q_instant_kwh

        # STORAGE HEATERS: print statements for testing
        #print("%.2f" % ((q_released + q_instant) * self.__n_units), end=" ")
        #print("%.2f" % self.t_core, end=" ")
        #print("%.2f" % self.t_wall, end=" ")
        #print("%.2f" % self.__report_energy_supply, end=" ")
        # DELETE after confirmation of Electric Storage Heater method

        # Multipy energy released by number of devices installed in the zone
        return self.__convert_to_kwh(energy=(q_released + q_instant), timestep=timestep)

    def __heat_balance(self, temp_core_and_wall: list, time: float, q_dis_modo=0) -> tuple:
        """
        Calculates heat balance
        """
        t_core: float = temp_core_and_wall[0]
        t_wall: float = temp_core_and_wall[1]
        # Equation for electric charging
        q_in: float = self.__electric_charge(time, t_core)
        self.__energy_in = q_in

        q_dis: float

        q_out_wall: float = self.__c * (t_wall - self.temp_air) ** self.__n

        # Equation for calculating q_dis
        q_dis = self.__calulate_q_dis(time=time, t_core=t_core, q_out_wall=q_out_wall, q_dis_modo=q_dis_modo)

        # Calculation of the U value between core and wall/case as
        # U value for the insulation and resistance of the air layer between the insulation and the wall/case
        if q_dis > 0:
            insulation: float = 1 / (1 / self.__Uins + self.__Rair_on)
        else:
            insulation: float = 1 / (1 / self.__Uins + self.__Rair_off)

        # Equation for the heat transfer between the core and the wall/case of the heater
        q_out_ins: float = insulation * self.__A * (t_core - t_wall)


        # Variation of Core temperature as per heat balance inside the heater
        dT_core: float = (1 / (self.__mass * self.__c_pcore)) * (q_in - q_out_ins - q_dis)

        # Variation of Wall/case temperature as per heat balance in surface of the heater
        dT_wall: float = (1 / self.__thermal_mass_wall) * (q_out_ins - q_out_wall)

        q_released: float = q_dis + q_out_wall

        return [dT_core, dT_wall], q_released, q_dis

    def __func_core_temperature_change_rate(self, q_dis_modo: Union[str, float]) -> types.FunctionType:
        """
        Lambda function for differentiation
        """
        return lambda time, t_core_and_wall: self.__heat_balance(temp_core_and_wall=t_core_and_wall,
                                                                 time=time,
                                                                 q_dis_modo=q_dis_modo)[0]

    def __calculate_sol_and_q_released(self,
                                       time_range: list,
                                       temp_core_and_wall: list,
                                       q_dis_modo: Union[str, float]) -> tuple:

        # first calculate how much the system is leaking without active discharging
        sol: OdeResult = solve_ivp(fun=self.__func_core_temperature_change_rate(q_dis_modo=q_dis_modo),
                                   t_span=time_range,
                                   y0=temp_core_and_wall,
                                   method='BDF')

        new_temp_core_and_wall: list = sol.y[:, -1]

        values: tuple = self.__heat_balance(temp_core_and_wall=new_temp_core_and_wall,
                                            time=time_range[1],
                                            q_dis_modo=q_dis_modo)
        q_released: float = values[1]
        q_dis: float = values[2]

        return new_temp_core_and_wall, q_released, q_dis

    def demand_energy(self, energy_demand: float) -> float:

        # Initialising Variables
        self.__report_energy_supply = 0.0
        self.temp_air = self.__zone.temp_internal_air()
        timestep: int = self.__simtime.timestep()
        current_hour: int = self.__simtime.current_hour()
        time_range: list = [current_hour*self.__time_unit, (current_hour + 1)*self.__time_unit]
        temp_core_and_wall: list = [self.t_core, self.t_wall]

        # Converting energy_demand from kWh to Wh and distributing it through all units
        energy_demand: float = energy_demand * units.W_per_kW / self.__n_units

        #print("%.2f" % (energy_demand * self.__n_units), end=" ")
        # DELETE after confirmation of Electric Storage Heater method
        

        #################################################
        # Step 1                                        #
        #################################################
        # first calculate how much the system is leaking without active discharging
        new_temp_core_and_wall: list
        q_released: float
        q_dis: float
        new_temp_core_and_wall, q_released, q_dis = \
            self.__calculate_sol_and_q_released(time_range=time_range,
                                                temp_core_and_wall=temp_core_and_wall,
                                                q_dis_modo=0)

        # if Q_released is more than what the zone wants, that's it
        if q_released >= energy_demand:
            # More energy than needed to be released. End of calculations.
            return self.__return_q_released(new_temp_core_and_wall=new_temp_core_and_wall,
                                            q_released=q_released,
                                            q_dis=q_dis,
                                            timestep=timestep,
                                            time=time_range[1])

        #################################################
        # Step 2                                        #
        #################################################
        # Zone needs more than leaked, let's calculate with max discharging capability
        new_temp_core_and_wall, q_released, q_dis = \
            self.__calculate_sol_and_q_released(time_range=time_range,
                                                temp_core_and_wall=temp_core_and_wall,
                                                q_dis_modo="max")

        # If Q_released is not sufficient for zone demand, that's it
        # unless there is instnat backup that can top up the energy provided
        if q_released < energy_demand:
            if self.__pwr_instant > 0:
                energy_supplied_instant = min(energy_demand - q_released, self.__pwr_instant * timestep)
            else:
                energy_supplied_instant = 0.0

            # The system can only discharge the maximum amount, zone doesn't get everything it needs
            return self.__return_q_released(new_temp_core_and_wall=new_temp_core_and_wall,
                                            q_released=q_released,
                                            q_dis=q_dis,
                                            timestep=timestep,
                                            time=time_range[1],
                                            q_instant=energy_supplied_instant)

        #################################################
        # Step 3                                        #
        #################################################
        # Zone actually needs an amount of energy that can be released by the system:
        # Let's call the heat balance forcing that amount (assuming perfect damper or
        # fan assisted control of the unit)
        q_dis = energy_demand
        new_temp_core_and_wall, q_released, q_dis = \
            self.__calculate_sol_and_q_released(time_range=time_range,
                                                temp_core_and_wall=temp_core_and_wall,
                                                q_dis_modo=q_dis)

        return self.__return_q_released(new_temp_core_and_wall=new_temp_core_and_wall,
                                        q_released=q_released,
                                        q_dis=q_dis,
                                        timestep=timestep,
                                        time=time_range[1])
