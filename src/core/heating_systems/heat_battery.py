#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides object(s) to model the behaviour of heat batteries.
"""

# Third-party imports
import sys
from enum import Enum, auto
import numpy as np
#import types
#from typing import Union

# Local imports
# TODO: Decide which imports are relevant
#import core.units as units
#from core.space_heat_demand.zone import Zone
#from core.energy_supply.energy_supply import EnergySupplyConnection
from core.simulation_time import SimulationTime
#from core.controls.time_control import ToUChargeControl, SetpointTimeControl
#from core.controls.time_control import SetpointTimeControl
#from core.material_properties import WATER
from pickle import TRUE
#from numpy import interp


class ServiceType(Enum):
    WATER_REGULAR = auto()
    SPACE = auto()

class HeatBatteryService:
    """ A base class for objects representing services (e.g. water heating) provided by a heat battery.

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
        """ Construct a HeatBatteryService object

        Arguments:
        heat_battery       -- reference to the Heat Battery object providing the service
        service_name -- name of the service demanding energy from the heat battery
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
    """ An object to represent a water heating service provided by a regular heat battery.

    This object contains the parts of the heat battery calculation that are
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
        """ Construct a HeatBatteryServiceWaterRegular object

        Arguments:
        heat_battery       -- reference to the Heat Battery object providing the service
        heat_battery_data       -- regular heat battery heating properties
        service_name -- name of the service demanding energy from the heat_battery_data
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
        """ Demand energy (in kWh) from the heat_battery """
        
        return self._heat_battery._HeatBattery__demand_energy(
            self.__service_name,
            ServiceType.WATER_REGULAR,
            energy_demand,
            self.__temp_return
            )

    def energy_output_max(self):
        """ Calculate the maximum energy output of the heat_battery"""
        return self._heat_battery._HeatBattery__energy_output_max(self.__temp_hot_water)

class HeatBatteryServiceSpace(HeatBatteryService):
    """ An object to represent a space heating service provided by a heat_battery to e.g. a cylinder.

    This object contains the parts of the heat battery calculation that are
    specific to providing space heating-.
    """
    def __init__(self, heat_battery, service_name, control):
        """ Construct a HeatBatteryServiceSpace object

        Arguments:
        heat_battery       -- reference to the Heat Battery object providing the service
        service_name -- name of the service demanding energy from the heat battery
        control -- reference to a control object which must implement is_on() and setpnt() funcs
        """
        super().__init__(heat_battery, service_name)
        self.__service_name = service_name
        self.__control = control

    def temp_setpnt(self):
        return self.__control.setpnt()

    def demand_energy(self, energy_demand, temp_flow, temp_return):
        """ Demand energy (in kWh) from the heat battery """

        return self._heat_battery._HeatBattery__demand_energy(
            self.__service_name,
            ServiceType.SPACE,
            energy_demand,
            temp_return
            )

    def energy_output_max(self, temp_output):
        """ Calculate the maximum energy output of the heat battery"""
        return self._heat_battery._HeatBattery__energy_output_max(temp_output)

class HeatBattery:
    """ Class to represent Heat Batteries electrically charged """
    """ This in an initial implicit ('EDI' - experimental data interpolation) modelling approach 
        that is more heavily dependent on manufacturer's test data for each device. 
        It is PCM (phase changed material) ready for which we are developing theoretical 
        characteristic curves in addition to the existing standard curves already included in this
        file. 
        The explicit ('DEI' - differential equation integration) modelling approach used in the 
        electric storage heater model would be available as a replacement for the 'EDI' model
        implemented here depending on feedback from industry stakeholders we are seeking.  
        
        This class has been introduced as a replacement for heat sources like boilers. 
        TODO: A different type of heat batteries, primarily PCM not charged by electricity but by 
        different heat sources (heat pumps, solar thermal, etc) will be implemented in a second
        phase once additional information is provided by industry stakeholders.  
    """

    def __init__(self,
                heat_battery_dict,
                charge_control,
                energy_supply,
                energy_supply_conn,
                simulation_time,
                ext_cond 
                ):
        
        """Construct a HeatBattery object

        Arguments:
        n_units               -- number of units install in zone

        rated_charge_power    -- in kW (Charging)
        heat_storage_capacity -- in kWh
        max_rated_heat_output -- in kW (Output to hot water)
        max_rated_losses      -- in kW (Losses to internal or external)

        energy_supply         -- reference to EnergySupplyConnection object
        simulation_time       -- reference to SimulationTime object
        control               -- reference to a control object which must implement is_on() and setpnt() funcs
        
        Other variables:
        energy_supply_connections
            -- dictionary with service name strings as keys and corresponding
               EnergySupplyConnection objects as values
        """

        self.__energy_supply = energy_supply
        self.__energy_supply_conn = energy_supply_conn
        self.__simulation_time: SimulationTime = simulation_time
        self.__external_conditions = ext_cond
        self.__energy_supply_connections = {}
        #self.__control: SetpointTimeControl = control
        self.__heat_battery_location = heat_battery_dict["heat_battery_location"]

        self.__pwr_in: float = heat_battery_dict["rated_charge_power"]
        self.__heat_storage_capacity: float = heat_battery_dict["heat_storage_capacity"]
        self.__max_rated_heat_output: float = heat_battery_dict["max_rated_heat_output"]
        self.__max_rated_losses: float = heat_battery_dict["max_rated_losses"]

        self.__power_circ_pump = heat_battery_dict["electricity_circ_pump"]
        self.__power_standby = heat_battery_dict["electricity_standby"]
        self.__total_time_running_current_timestep = 0.0

        self.__n_units: int = heat_battery_dict["number_of_units"]
        self.__charge_control: ToUChargeControl = charge_control
        self.__service_results = []
        
        self.__time_unit: float = 3600
        self.__total_time_running_current_timestep = 0.0

        # labs_test for heat battery reaching 650 degC
        # Assuming it struggles to deliver heat power at 80 degC (return temperature) 
        # from 23% of the charge level
        # TODO: Possibly need for more curvers at different return temperatures that might affect
        # the lower data points in the curve.
        self.labs_tests_rated_output: list = [
            [0.0, 0],
            [0.08, 0.00],
            [0.16, 0.03],
            [0.17, 0.05],
            [0.19, 0.10],
            [0.21, 0.15],
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
        self.__charge_level: float = 0.0
        #self.__charge_capacity_in_timestep = 
        self.__flag_first_call = TRUE
        #self.__Q_out_available = self.__lab_test_rated_output(self.__charge_level) * self.__n_units

    
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
            """ Return a HeatBatteryServiceWaterRegular object and create an EnergySupplyConnection for it

            Arguments:
            service_name -- name of the service demanding energy from the heat battery
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
        """ Return a HeatBatteryServiceSpace object and create an EnergySupplyConnection for it

        Arguments:
        service_name -- name of the service demanding energy from the heat battery
        control -- reference to a control object which must implement is_on() and setpnt() funcs
        """
        self.__create_service_connection(service_name)
        return HeatBatteryServiceSpace(
            self,
            service_name,
            control,
            )


    
    def __convert_to_energy(self, power: float, timestep: float) -> float:
        """
        Converts power value supplied to the correct unit
        Arguments
        power -- Energy value in watts
        timestep -- length of the timestep

        returns -- Energy in kWH
        """
        return power * timestep * self.__n_units

    def __electric_charge(self, time: float) -> float:
        """
        Calculates power required for unit
        Arguments
        time -- current time period that we are looking at

        returns -- Power required in watts
        """
        if self.__charge_control.is_on(): 
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
        #outside_temp = self.__external_conditions.air_temp()
        self.__report_energy_supply = 0.0
            
        #self.temp_air = self.__zone.temp_internal_air()
        timestep: float = self.__simulation_time.timestep()
        current_hour: int = self.__simulation_time.current_hour()
        time_range = (current_hour)*self.__time_unit
        charge_level: float = self.__charge_level
        charge_level_qin: float = charge_level

        # Picking target charge level from control
        target_charge: float = self.__charge_control.target_charge()
        if self.__flag_first_call:
            # TODO: The following code is very similar in three different sections of the
            # Heat Battery implementation. Consider creating function with relevant arguments
            # and simplify the three instances to just one call 
            self.__Q_in_ts = self.__electric_charge(time_range)
            # Calculate max charge level possible in next timestep
            if charge_level_qin < target_charge:
                delta_charge_level = ( self.__Q_in_ts ) * timestep / self.__heat_storage_capacity
                charge_level_qin += delta_charge_level
                if charge_level_qin > target_charge:
                    charge_level_qin = target_charge

            # Estimating output rate at average of capacity in timestep
            max_output = self.__lab_test_rated_output(charge_level_qin)
            delta_charge_level = ( max_output ) * timestep / self.__heat_storage_capacity
            self.__Q_out_ts = self.__lab_test_rated_output(charge_level_qin - delta_charge_level / 2)
            self.__Q_loss_ts = self.__lab_test_losses(charge_level_qin - delta_charge_level / 2)
            self.__max_output = max_output

        # Converting energy_demand from kWh to Wh and distributing it through all units
        energy_demand: float = energy_output_required / self.__n_units

        # New code
        it_energy_demand = energy_demand
        it_power_in = self.__Q_in_ts
        Q_out = 0.0
        Q_in = 0.0
        
        it_Q_out = min( it_energy_demand / timestep, self.__Q_out_ts )
        it_Q_in = it_power_in

        delta_charge_level = ( it_Q_in - it_Q_out ) * timestep / self.__heat_storage_capacity
        charge_level += delta_charge_level
        #print(charge_level)
        if charge_level > target_charge:
            it_Q_in -= ( charge_level - target_charge ) * self.__heat_storage_capacity / timestep
            if it_Q_in < 0.0:
                it_Q_in = 0.0
                charge_level -= delta_charge_level 
                delta_charge_level = ( - it_Q_out ) * timestep / self.__heat_storage_capacity
                charge_level += delta_charge_level
            else:
                charge_level = target_charge
        Q_out += it_Q_out
        Q_in += it_Q_in
            
        if self.__flag_first_call:
            self.__flag_first_call = False
            
        energy_output_provided = self.__convert_to_energy(power = Q_out, timestep = timestep)
        
        if self.__max_output > 0:
            time_running_current_service = Q_out / self.__max_output
        else:
            time_running_current_service = 0.0
            
        self.__Q_out_ts -=  Q_out 
        self.__Q_in_ts -=  Q_in 
        self.__charge_level = charge_level
        

        self.__energy_supply_conn.demand_energy(Q_in * self.__n_units)

        self.__total_time_running_current_timestep += time_running_current_service
    
        # Save results that are needed later (in the timestep_end function)
        self.__service_results.append({
            'service_name': service_name,
            'time_running': time_running_current_service,
            'current_hb_power': self.__Q_out_ts
            })
        
        #print interim steps to output file for investigation
        #energy_loss = self.__convert_to_energy(power = self.__Q_loss_ts, timestep = timestep)
        #print (time_range, "%.6f" % Q_in, "%.6f" % charge_level, "%.6f" % energy_demand, "%.6f" % energy_output_provided, "%.6f" % energy_loss )
        
        return energy_output_provided

    def __calc_auxiliary_energy(self, timestep, time_remaining_current_timestep):
        """Calculation of heat battery auxilary energy consumption"""

        #Energy used by circulation pump
        energy_aux = self.__total_time_running_current_timestep \
            * self.__power_circ_pump
        
        #Energy used in standby mode
        energy_aux += self.__power_standby * time_remaining_current_timestep
        
        self.__energy_supply_conn.demand_energy(energy_aux)

    def timestep_end(self):
        """" Calculations to be done at the end of each timestep"""
        timestep: float = self.__simulation_time.timestep()
        time_remaining_current_timestep = timestep - self.__total_time_running_current_timestep
        
        current_hour: int = self.__simulation_time.current_hour()
        time_range = (current_hour + 1)*self.__time_unit

        
        self.__calc_auxiliary_energy(timestep, time_remaining_current_timestep)

        # Calculating heat battery losses in timestep to correct charge level
        # Currently assumed all losses are to the exterior independently of the 
        # heat battery location
        # TODO: Assign thermal losses to relevant zone if heat battery is not outdoors.
        charge_level = self.__charge_level
        delta_charge_level = ( - self.__Q_loss_ts ) * timestep / self.__heat_storage_capacity
        charge_level += delta_charge_level
        self.__charge_level = charge_level
        #energy_loss = self.__convert_to_energy(power = self.__Q_loss_ts, timestep = timestep)


        # Preparing Heat baterry for next time step
        # Variabales below need to be reset at the end of each timestep
        # Picking target charge level from control
        target_charge: float = self.__charge_control.target_charge()
        charge_level_qin = self.__charge_level
        self.__Q_in_ts = self.__electric_charge(time_range)
        # Calculate max charge level possible in next timestep
        if charge_level_qin < target_charge:
            delta_charge_level = ( self.__Q_in_ts ) * timestep / self.__heat_storage_capacity
            charge_level_qin += delta_charge_level
            if charge_level_qin > target_charge:
                charge_level_qin = target_charge

        # Estimating output rate at average of capacity in timestep
        max_output = self.__lab_test_rated_output(charge_level_qin)
        delta_charge_level = ( max_output ) * timestep / self.__heat_storage_capacity
        self.__Q_out_ts = self.__lab_test_rated_output(charge_level_qin - delta_charge_level / 2)
        self.__Q_loss_ts = self.__lab_test_losses(charge_level_qin - delta_charge_level / 2)
        
        self.__max_output = max_output

        self.__total_time_running_current_timestep = 0.0
        self.__service_results = []

    def __energy_output_max(self, temp_output):
        timestep = self.__simulation_time.timestep()
        current_hour: int = self.__simulation_time.current_hour()
        time_range = (current_hour)*self.__time_unit
        charge_level_qin: float = self.__charge_level

        # Picking target charge level from control
        target_charge: float = self.__charge_control.target_charge()
        self.__Q_in_ts = self.__electric_charge(time_range)
        # Calculate max charge level possible in next timestep
        if charge_level_qin < target_charge:
            delta_charge_level = ( self.__Q_in_ts ) * timestep / self.__heat_storage_capacity
            charge_level_qin += delta_charge_level
            if charge_level_qin > target_charge:
                charge_level_qin = target_charge

        # Estimating output rate at average of capacity in timestep
        max_output = self.__lab_test_rated_output(charge_level_qin)
        return max_output
    