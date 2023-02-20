#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides object(s) to model the behaviour of heat batteries.
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


class HeatBattery:
    """ Class to represent heat batteries """

    def __init__(
        self,
        rated_power_instant: float,
        flue_type: str,
        temp_dis_safe: float,
        thermal_mass: float,
        frac_convective: float,
        U_ins: float,
        mass_core: float,
        c_pcore: float,
#        temp_core_target: float,
        A_core: float,
        c_wall: float,
        n_wall: float,
        thermal_mass_wall: float,
        n_units: int,
        zone: Zone,

        rated_charge_power: float,
        heat_storage_capacity: float,
        max_rated_heat_output: float,
        max_rated_losses: float,

        energy_supply_conn: EnergySupplyConnection,
        simulation_time: SimulationTime,
        control: SetpointTimeControl
        
    ):
        """Construct an HeatBattery object

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

        rated_charge_power   -- in kW (Charging)
        heat_storage_capacity-- in kWh
        max_rated_heat_output-- in kW (Output to hot water)

        energy_supply_conn   -- reference to EnergySupplyConnection object
        simulation_time      -- reference to SimulationTime object
        control              -- reference to a control object which must implement is_on() and setpnt() funcs
        """

        self.__pwr_in: float = (rated_charge_power * units.W_per_kW)
        self.__pwr_instant: float = (rated_power_instant * units.W_per_kW)
        self.__flue_type: str = flue_type
        self.__t_dis_safe: float = temp_dis_safe
        self.__thermal_mass: float = thermal_mass
        self.__frac_convective: float = frac_convective
        self.__Uins: float = U_ins
        self.__n_units: int = n_units
        self.__zone: Zone = zone

        self.__heat_storage_capacity: float = heat_storage_capacity
        self.__max_rated_heat_output: float = max_rated_heat_output
        self.__max_rated_losses: float = max_rated_losses

        self.__energy_supply_conn: EnergySupplyConnection = energy_supply_conn
        self.__simtime: SimulationTime = simulation_time
        self.__control: SetpointTimeControl = control
        self.__mass: float = mass_core  # 180.0  # kg of core
        self.__c_pcore: float = c_pcore    # 920.0  # J/kg/K core material specific heat
        #self.__t_core_target: float = temp_core_target
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
        self.labs_tests_rated_output: list = [
            [1.0, 1.0],
            [0.9, 1.0],
            [0.8, 1.0],
            [0.7, 1.0],
            [0.6, 1.0],
            [0.5, 1.0],
            [0.4, 1.0],
            [0.3, 1.0],
            [0.2, 1.0],
            [0.1, 0.8],
            [0.05, 0.2],
            [0.01, 0.05]
        ]

        self.labs_tests_losses: list = [
            [1.0, 0.01],
            [0.9, 0.01],
            [0.8, 0.01],
            [0.7, 0.01],
            [0.6, 0.01],
            [0.5, 0.005],
            [0.4, 0.005],
            [0.3, 0.005],
            [0.2, 0.005],
            [0.1, 0.001],
            [0.05, 0.001],
            [0.01, 0.001]
        ]

        # Initial conditions
        self.t_core: float = self.__zone.temp_internal_air()
        self.t_wall: float = self.__zone.temp_internal_air()

        self.damper_fraction: float = 1.0
        self.__energy_in: float = 0.0
        
        # Set the initial charge level of the heat battery to zero.
        #self.__charge_level: float = 0.0

    def __convert_to_kwh(self, energy: float, timestep: int) -> float:
        """
        Converts energy value supplied to the correct unit
        Arguments
        energy -- Energy value in watts
        timestep -- length of the timestep

        returns -- Energy in kWH
        """
        return energy / units.W_per_kW * timestep * self.__n_units

    def __electric_charge(self, time: float, charge_level: float) -> float:
        """
        Calculates power required for unit
        Arguments
        time -- current time period that we are looking at
        charge_level -- current level of charge (proportion of 1.0)

        returns -- Power required in watts
        """
        if time <= 7 * self.__time_unit and charge_level <= 1.0:
            pwr_required: float =  self.__heat_storage_capacity * ( 1 - charge_level ) / self.__simulation_time.timestep()
            if pwr_required > self.__pwr_in:
                return self.__pwr_in
            else:
                return pwr_required
        else:
            return 0.0

    def __lab_test_rated_output(self, charge_level: float) -> float:
        # labs_test for electric storage heater
        x: list = [row[0] for row in self.labs_tests_rated_output]
        y: list = [row[1] for row in self.labs_tests_rated_output]
        return ( np.interp(charge_level, x, y) * self.__max_rated_heat_output )

    def __lab_test_losses(self, charge_level: float) -> float:
        # labs_test for electric storage heater
        x: list = [row[0] for row in self.labs_tests_losses]
        y: list = [row[1] for row in self.labs_tests_losses]
        return ( np.interp(charge_level, x, y) * self.__max_rated_losses )

    def __calulate_q_out(self, charge_level: float, energy_demand: float) -> float:
        q_out: float
        q_out = min( energy_demand, self.__lab_test_rated_output(charge_level) * self.__simulation_time.timestep() )

        return q_out

    def __return_q_out(self,
                            new_charge_level: float,
                            q_in: float,
                            q_loss: float,
                            q_out: float,
                            timestep: int,
                            time: float) -> float:
        # Setting core and wall temperatures to new values, for next iteration
        self.__charge_level = new_charge_level

        # TODO replace fan power with pump power
        # the purpose of this calculation is to calculate fan energy required by the device
        #energy_for_fan_kwh: float = 0.0
        #if self.__flue_type == "fan-assisted":
        #    self.__mass_flow_air = q_dis / (self.__c_p * (self.__t_dis_safe - self.temp_air))
        #    energy_for_fan: float = self.__mass_flow_air * self.__power_for_fan
        #    energy_for_fan_kwh = self.__convert_to_kwh(energy=energy_for_fan, timestep=timestep)

        # Convert values to correct kwh unit
        q_in_kwh: float = self.__convert_to_kwh(energy=q_in, timestep=timestep)

        # Save demand energy
        self.__energy_supply_conn.demand_energy(q_in_kwh)

        self.__report_energy_supply = self.__report_energy_supply + q_in_kwh

        # STORAGE HEATERS: print statements for testing
        #print("%.2f" % ((q_released + q_instant) * self.__n_units), end=" ")
        #print("%.2f" % self.t_core, end=" ")
        #print("%.2f" % self.t_wall, end=" ")
        #print("%.2f" % self.__report_energy_supply, end=" ")
        # DELETE after confirmation of Electric Storage Heater method

        # Multipy energy released by number of devices installed in the zone
        return self.__convert_to_kwh(energy=(q_out), timestep=timestep)

    def __heat_balance(self, charge_level: float, time: float, energy_demand: float) -> tuple:
        """
        Calculates heat balance
        """
        # Equation for electric charging
        q_in: float = self.__electric_charge(time, charge_level)
        self.__energy_in = q_in

        q_loss: float = self.__lab_test_losses(charge_level)

        # Equation for calculating q_dis
        q_out = self.__calulate_q_out(charge_level=charge_level, energy_demand=energy_demand)

        # Variation of charge level as per heat balance inside the heater
        delta_charge_level: float =  1 / self.__heat_storage_capacity * ( q_in - q_loss - q_out )
        if delta_charge_level < 0:
            if abs(delta_charge_level) > charge_level:
                delta_charge_level = -charge_level

        return delta_charge_level, q_in, q_loss, q_out

    def __func_charge_level_change_rate(self, energy_demand) -> types.FunctionType:
        """
        Lambda function for differentiation
        """
        return lambda time, charge_level: self.__heat_balance(charge_level=charge_level,
                                                                 time=time,
                                                                 energy_demand=energy_demand)[0]

    def __calculate_sol_and_q_out(self,
                                       time_range: list,
                                       charge_level: float,
                                       energy_demand: float
                                       ) -> tuple:

        # first calculate how much the system is leaking without active discharging
        sol: OdeResult = solve_ivp(fun=self.__func_charge_level_change_rate(energy_demand),
                                   t_span=time_range,
                                   y0=charge_level,
                                   method='BDF')

        new_charge_level: list = sol.y[:, -1]

        values: tuple = self.__heat_balance(charge_level=new_charge_level,
                                            time=time_range[1],
                                            energy_demand=energy_demand)
        q_in: float = values[1]
        q_loss: float = values[2]
        q_out: float = values[3]

        return new_charge_level, q_in, q_loss, q_out

    def demand_energy(self, energy_demand: float) -> float:

        # Initialising Variables
        self.__report_energy_supply = 0.0
        #self.temp_air = self.__zone.temp_internal_air()
        timestep: int = self.__simtime.timestep()
        current_hour: int = self.__simtime.current_hour()
        time_range: list = [current_hour*self.__time_unit, (current_hour + 1)*self.__time_unit]
        charge_level: float = self.__charge_level

        # Converting energy_demand from kWh to Wh and distributing it through all units
        energy_demand: float = energy_demand * units.W_per_kW / self.__n_units

        #print("%.2f" % (energy_demand * self.__n_units), end=" ")
        # DELETE after confirmation of Electric Storage Heater method

        new_charge_level, q_in, q_loss, q_out = \
            self.__calculate_sol_and_q_out(time_range=time_range,
                                                charge_level=charge_level,
                                                energy_demand=energy_demand)

        return self.__return_q_out(new_charge_level=new_charge_level,
                                        q_in=q_in,
                                        q_loss=q_loss,
                                        q_out=q_out,
                                        timestep=timestep,
                                        time=time_range[1])
