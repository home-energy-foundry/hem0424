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
            [0.0, 0],
            [0.16, 0.13],
            [0.17, 0.15],
            [0.19, 0.16],
            [0.21, 0.18],
            [0.23, 0.21],
            [0.25, 0.23],
            [0.28, 0.26],
            [0.31, 0.29],
            [0.34, 0.32],
            [0.38, 0.36],
            [0.42, 0.41],
            [0.47, 0.45],
            [0.52, 0.51],
            [0.58, 0.57],
            [0.64, 0.64],
            [0.72, 0.71],
            [0.8, 0.8],
            [0.89, 0.89],
            [1.0, 1.0]
        ]
        
        # Charge level x losses
        self.labs_tests_losses: list = [
            [0.0, 0],
            [0.16, 0.13],
            [0.17, 0.15],
            [0.19, 0.17],
            [0.21, 0.18],
            [0.23, 0.21],
            [0.25, 0.23],
            [0.28, 0.26],
            [0.31, 0.29],
            [0.34, 0.32],
            [0.38, 0.36],
            [0.42, 0.41],
            [0.47, 0.45],
            [0.52, 0.51],
            [0.58, 0.57],
            [0.64, 0.64],
            [0.72, 0.71],
            [0.8, 0.8],
            [0.89, 0.89],
            [1.0, 1.0]
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

    def __electric_charge(self, time: float) -> float:
        """
        Calculates power required for unit
        Arguments
        time -- current time period that we are looking at

        returns -- Power required in watts
        """
        if time <= 7 * self.__time_unit:
            return self.__pwr_in
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

    def demand_energy(self, energy_demand: float) -> float:

        # Initialising Variables
        self.__report_energy_supply = 0.0
        #self.temp_air = self.__zone.temp_internal_air()
        timestep: int = self.__simtime.timestep()
        current_hour: int = self.__simtime.current_hour()
        time_range: list = [current_hour*self.__time_unit, (current_hour + 1)*self.__time_unit]
        n_iterations: int = 10
        charge_level: float = self.__charge_level

        # Converting energy_demand from kWh to Wh and distributing it through all units
        energy_demand: float = energy_demand * units.W_per_kW / self.__n_units

        #print("%.2f" % (energy_demand * self.__n_units), end=" ")
        # DELETE after confirmation of Electric Storage Heater method

        # New code
        it_energy_demand = energy_demand / n_iterations
        it_power_in = self.__electric_charge(time_range[1]) / n_iterations
        Q_out = 0.0
        Q_loss = 0.0
        Q_in = 0.0
        for i in range(0, n_iterations):
            # TODO MC - consider the line below and whether it shuold be multiplied by timestep
            it_Q_out = min( it_energy_demand, self.__lab_test_rated_output(charge_level) / n_iterations )
            it_Q_loss = self.__lab_test_losses(charge_level) / n_iterations
            it_Q_in = it_power_in
            delta_charge_level = ( it_Q_in - it_Q_out - it_Q_loss ) / self.__heat_storage_capacity
            charge_level = charge_level + delta_charge_level
            if charge_level > 1.0:
                it_Q_in = it_Q_in - ( charge_level - 1.0 ) * self.__heat_storage_capacity 
                charge_level = 1.0
            Q_out += it_Q_out
            Q_loss += it_Q_loss
            Q_in += it_Q_in
            
        energy_output_provided = Q_out / units.W_per_kW * self.__n_units
            
        self.__charge_level = charge_level
        
        self.__energy_supply_conn.demand_energy(Q_in / units.W_per_kW * self.__n_units)
    
        return energy_output_provided

        
                
