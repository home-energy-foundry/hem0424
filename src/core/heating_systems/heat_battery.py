#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides object(s) to model the behaviour of heat batteries.
"""

# Third-party imports
import sys
from enum import Enum, auto
import numpy as np
import types
from typing import Union

# Local imports
import core.units as units
from core.space_heat_demand.zone import Zone
from core.energy_supply.energy_supply import EnergySupplyConnection
from core.simulation_time import SimulationTime
from core.controls.time_control import SetpointTimeControl
from core.material_properties import WATER
#from numpy import interp


class ServiceType(Enum):
    WATER_REGULAR = auto()
    SPACE = auto()

class HeatBatteryService:
    """ A base class for objects representing services (e.g. water heating) provided by a boiler.

    This object encapsulates the name of the service, meaning that the system
    consuming the energy does not have to specify this on every call, and
    helping to enforce that each service has a unique name.

    Derived objects provide a place to handle parts of the calculation (e.g.
    distribution flow temperature) that may differ for different services.

    Separate subclasses need to be implemented for different types of service
    (e.g. HW and space heating). These should implement the following functions:
    - demand_energy(self, energy_demand)
    """

    def __init__(self, heat_battery, service_name, control=None):
        """ Construct a BoilerService object

        Arguments:
        boiler       -- reference to the Boiler object providing the service
        service_name -- name of the service demanding energy from the boiler
        """
        self._heat_battery = heat_battery
        self._service_name = service_name
        self.__control = control

    def is_on(self):
        if self.__control is not None:
            service_on = self.__control.is_on()
        else:
            service_on = True
        return service_on

class HeatBatteryServiceWaterRegular(HeatBatteryService):
    """ An object to represent a water heating service provided by a regular boiler.

    This object contains the parts of the boiler calculation that are
    specific to providing hot water.
    """

    def __init__(self,
                 heat_battery,
                 heat_battery_data,
                 service_name,
                 temp_hot_water,
                 cold_feed,
                 temp_return,
                 simulation_time
                ):
        """ Construct a BoilerServiceWaterRegular object

        Arguments:
        boiler       -- reference to the Boiler object providing the service
        boiler_data       -- regular boiler heating properties
        service_name -- name of the service demanding energy from the boiler_data
        temp_hot_water -- temperature of the hot water to be provided, in deg C
        cold_feed -- reference to ColdWaterSource object
        simulation_time -- reference to SimulationTime object
        """
        super().__init__(heat_battery, service_name)
        
        self.__temp_hot_water = temp_hot_water
        self.__cold_feed = cold_feed
        self.__service_name = service_name
        self.__simulation_time = simulation_time
        self.__temp_return = temp_return


    def demand_energy(self, energy_demand):
        """ Demand energy (in kWh) from the boiler """
        
        return self._heat_battery._HeatBattery__demand_energy(
            self.__service_name,
            ServiceType.WATER_REGULAR,
            energy_demand,
            self.__temp_return
            )

    def energy_output_max(self):
        """ Calculate the maximum energy output of the boiler"""
        return self._heat_battery._HeatBattery__energy_output_max(self.__temp_hot_water)

class HeatBatteryServiceSpace(HeatBatteryService):
    """ An object to represent a space heating service provided by a boiler to e.g. a cylinder.

    This object contains the parts of the boiler calculation that are
    specific to providing space heating-.
    """
    def __init__(self, heat_battery, service_name, control):
        """ Construct a BoilerServiceSpace object

        Arguments:
        boiler       -- reference to the Boiler object providing the service
        service_name -- name of the service demanding energy from the boiler
        control -- reference to a control object which must implement is_on() and setpnt() funcs
        """
        super().__init__(heat_battery, service_name)
        self.__service_name = service_name
        self.__control = control

    def temp_setpnt(self):
        return self.__control.setpnt()

    def demand_energy(self, energy_demand, temp_flow, temp_return):
        """ Demand energy (in kWh) from the boiler """

        return self._heat_battery._HeatBattery__demand_energy(
            self.__service_name,
            ServiceType.SPACE,
            energy_demand,
            temp_return
            )

    def energy_output_max(self, temp_output):
        """ Calculate the maximum energy output of the boiler"""
        return self._heat_battery._HeatBattery__energy_output_max(temp_output)

class HeatBattery:
    """ Class to represent heat batteries """

    def __init__(self,
                heat_battery_dict,
                energy_supply,
                energy_supply_conn_name_auxiliary,
                #energy_supply_conn,
                simulation_time,
                ext_cond 
                ):
        
        """        
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
        """        
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

        self.__energy_supply = energy_supply
        #self.__energy_supply_conn: EnergySupplyConnection = energy_supply_conn
        self.__energy_supply_connection_aux \
            = self.__energy_supply.connection(energy_supply_conn_name_auxiliary)
        self.__simulation_time: SimulationTime = simulation_time
        self.__external_conditions = ext_cond
        self.__energy_supply_connections = {}
        #self.__control: SetpointTimeControl = control
        self.__heat_battery_location = heat_battery_dict["heat_battery_location"]

        self.__pwr_in: float = (heat_battery_dict["rated_charge_power"] * units.W_per_kW)
        self.__heat_storage_capacity: float = heat_battery_dict["heat_storage_capacity"]
        self.__max_rated_heat_output: float = heat_battery_dict["max_rated_heat_output"]
        self.__max_rated_losses: float = heat_battery_dict["max_rated_losses"]
        self.__power_circ_pump = heat_battery_dict["electricity_circ_pump"]
        self.__power_standby = heat_battery_dict["electricity_standby"]
        self.__n_units: int = heat_battery_dict["number_of_units"]
        self.__service_results = []
        
        self.__time_unit: float = 3600
        self.__total_time_running_current_timestep = 0.0

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


        
        # Set the initial charge level of the heat battery to zero.
        self.__charge_level: float = 1.0
        #self.__charge_capacity_in_timestep = 
        self.__energy_available_in_timestep = self.__lab_test_rated_output(self.__charge_level) * self.__n_units

    
    def __create_service_connection(self, service_name):
        #Create an EnergySupplyConnection for the service name given 
        # Check that service_name is not already registered
        if service_name in self.__energy_supply_connections.keys():
            sys.exit("Error: Service name already used: "+service_name)
            # TODO Exit just the current case instead of whole program entirely?

        # Set up EnergySupplyConnection for this service
        self.__energy_supply_connections[service_name] = \
            self.__energy_supply.connection(service_name)
    

    def create_service_hot_water_regular(
            self,
            heat_battery_data,
            service_name,
            temp_hot_water,
            cold_feed,
            temp_return
            ):
            """ Return a BoilerServiceWaterRegular object and create an EnergySupplyConnection for it

            Arguments:
            service_name -- name of the service demanding energy from the boiler
            temp_hot_water -- temperature of the hot water to be provided, in deg C
            temp_limit_upper -- upper operating limit for temperature, in deg C
            cold_feed -- reference to ColdWaterSource object
            control -- reference to a control object which must implement is_on() func
            """
            
            self.__create_service_connection(service_name)
            return HeatBatteryServiceWaterRegular(
                self,
                heat_battery_data,
                service_name,
                temp_hot_water,
                cold_feed,
                temp_return,
                self.__simulation_time
                )

    def create_service_space_heating(
            self,
            service_name,
            control,
            ):
        """ Return a BoilerServiceSpace object and create an EnergySupplyConnection for it

        Arguments:
        service_name -- name of the service demanding energy from the boiler
        control -- reference to a control object which must implement is_on() and setpnt() funcs
        """
        self.__create_service_connection(service_name)
        return HeatBatteryServiceSpace(
            self,
            service_name,
            control,
            )


    
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

    def __demand_energy(
            self,
            service_name,
            service_type,
            energy_output_required,
            temp_return_feed
            ):

        # Initialising Variables
        outside_temp = self.__external_conditions.air_temp()
        self.__report_energy_supply = 0.0
        #self.temp_air = self.__zone.temp_internal_air()
        timestep: int = self.__simulation_time.timestep()
        current_hour: int = self.__simulation_time.current_hour()
        time_range: list = [current_hour*self.__time_unit, (current_hour + 1)*self.__time_unit]
        charge_level: float = self.__charge_level

        # Converting energy_demand from kWh to Wh and distributing it through all units
        energy_demand: float = energy_output_required * units.W_per_kW / self.__n_units

        #print("%.2f" % (energy_demand * self.__n_units), end=" ")
        # DELETE after confirmation of Electric Storage Heater method

        # New code
        n_iterations: int = 10
        it_energy_demand = energy_demand / n_iterations
        it_power_in = self.__electric_charge(time_range[1]) / n_iterations
        Q_out = 0.0
        Q_loss = 0.0
        Q_in = 0.0
        for i in range(0, n_iterations):
            # TODO MC - consider the line below and whether it shuold be multiplied by timestep
            it_Q_out = min( it_energy_demand / timestep, self.__lab_test_rated_output(charge_level) / n_iterations )
            it_Q_loss = self.__lab_test_losses(charge_level) / n_iterations
            it_Q_in = it_power_in
            delta_charge_level = ( it_Q_in - it_Q_out - it_Q_loss ) * timestep / self.__heat_storage_capacity
            charge_level = charge_level + delta_charge_level
            if charge_level > 1.0:
                it_Q_in = it_Q_in - ( charge_level - 1.0 ) * self.__heat_storage_capacity / timestep  
                charge_level = 1.0
            Q_out += it_Q_out
#            if Q_out * self.__n_units > self.__energy_available_in_timestep:
#                Q_out = self.__energy_available_in_timestep
            Q_loss += it_Q_loss
            Q_in += it_Q_in
            
        energy_output_provided = Q_out * timestep / units.W_per_kW * self.__n_units
#        self.__energy_available_in_timestep -= Q_out * self.__n_units    
        self.__charge_level = charge_level
        
        self.__energy_supply_connections[service_name].demand_energy(energy_output_provided)

        #self.__energy_supply_conn.demand_energy(Q_in / units.W_per_kW * self.__n_units)
    
        # Calculate running time of Boiler
        time_running_current_service = \
            timestep - self.__total_time_running_current_timestep
        self.__total_time_running_current_timestep += time_running_current_service
        
        # Save results that are needed later (in the timestep_end function)
        self.__service_results.append({
            'service_name': service_name,
            'time_running': time_running_current_service,
            })
        print ("output: ", energy_output_provided * 1000, "  Time: ", time_range[1], "  Q_in: ", Q_in, energy_demand)
        return energy_output_provided

    def __calc_auxiliary_energy(self, timestep, time_remaining_current_timestep):
        """Calculation of boiler electrical consumption"""

        #Energy used by circulation pump
        energy_aux = self.__total_time_running_current_timestep \
            * self.__power_circ_pump
        
        #Energy used in standby mode
        energy_aux += self.__power_standby * time_remaining_current_timestep
        
        self.__energy_supply_connection_aux.demand_energy(energy_aux)

    def timestep_end(self):
        """" Calculations to be done at the end of each timestep"""
        timestep = self.__simulation_time.timestep()
        time_remaining_current_timestep = timestep - self.__total_time_running_current_timestep

        self.__calc_auxiliary_energy(timestep, time_remaining_current_timestep)

        #Variabales below need to be reset at the end of each timestep
        self.__total_time_running_current_timestep = 0.0
        self.__service_results = []

    def __energy_output_max(self, temp_output):
        self.__lab_test_rated_output(self.__charge_level)
        
        timestep = self.__simulation_time.timestep()
        time_available = timestep #- self.__total_time_running_current_timestep
        return self.__boiler_power * time_available

        
                
