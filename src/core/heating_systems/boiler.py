#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides objects to represent boilers. The calculations are based
on the hourly method developed for calculating efficiency improvements for
different classes of boiler controls in SAP 10 Appendix D2.2 (described in the
SAP 10 technical paper S10TP-12). This in turn was based on a combination of
the DAHPSE method for heat pumps (itself based on a draft of
BS EN 15316-4-2:2017 and described in the SAP calculation method CALCM-01) and
the Energy Balance Validation (EBV) method (described in the SAP 2009 technical
paper STP09/B02).
"""

# Standard library imports
import sys
from enum import Enum, auto

#Local imports
from core.energy_supply.energy_supply import Fuel_code
from core.material_properties import WATER
import core.units as units


class Boiler_HW_test(Enum):
    M_L = auto()
    M_S = auto()
    M_only = auto()
    No_additional_tests = auto()

    @classmethod
    def from_string(cls, strval):
        if strval == 'M&L':
            return cls.M_L
        elif strval == 'M&S':
            return cls.M_S
        elif strval == 'M_only':
            return cls.M_only
        elif strval == 'No_additional_tests':
            return cls.No_additional_tests
        else:
            sys.exit('Hot water test ('+ str(strval) + ') not valid')

class BoilerService:
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

    def __init__(self, boiler, service_name):
        """ Construct a BoilerService object

        Arguments:
        boiler       -- reference to the Boiler object providing the service
        service_name -- name of the service demanding energy from the boiler
        """
        self._boiler = boiler
        self._service_name = service_name


class BoilerServiceWaterCombi(BoilerService):
    """ An object to represent a water heating service provided by a combi boiler.

    This object contains the parts of the boiler calculation that are
    specific to providing hot water.
    """

    def __init__(self, boilerservicewatercombi_dict, boiler, service_name, \
                 temp_hot_water, cold_feed, simulation_time):
        """ Construct a BoilerServiceWaterCombi object

        Arguments:
        boilerservicewatercombi_dict       -- combi boiler heating properties
        boiler       -- reference to the Boiler object providing the service
        service_name -- name of the service demanding energy from the boiler
        temp_hot_water -- temperature of the hot water to be provided, in deg C
        cold_feed -- reference to ColdWaterSource object
        """ 
        super().__init__(boiler, service_name)
        
        self.__temp_hot_water = temp_hot_water
        self.__cold_feed = cold_feed
        self.__service_name = service_name
        self.__simulation_time = simulation_time
        
        hw_tests = boilerservicewatercombi_dict["separate_DHW_tests"]
        self.__separate_DHW_tests = Boiler_HW_test.from_string(hw_tests)
        
        self.__fuel_energy_1 = boilerservicewatercombi_dict["fuel_energy_1"]
        self.__rejected_energy_1 = boilerservicewatercombi_dict["rejected_energy_1"]
        self.__storage_loss_factor_1 = boilerservicewatercombi_dict["storage_loss_factor_1"]
        self.__fuel_energy_2_test = boilerservicewatercombi_dict["fuel_energy_2"]
        self.__rejected_energy_2_test = boilerservicewatercombi_dict["rejected_energy_2"]
        self.__storage_loss_factor_2 = boilerservicewatercombi_dict["storage_loss_factor_2"]
        self.__rejected_factor_3 = boilerservicewatercombi_dict["rejected_factor_3"] 
        self.__daily_HW_usage = boilerservicewatercombi_dict["daily_HW_usage"] 
        
    def demand_hot_water(self, volume_demanded):
        """ Demand volume from boiler. Currently combi only """
        timestep = self.__simulation_time.timestep()
        return_temperature = 60 
        
        energy_content_kWh_per_litre = WATER.volumetric_energy_content_kWh_per_litre(
            self.__temp_hot_water,
            self.__cold_feed.temperature()
            )
        energy_demand = volume_demanded * energy_content_kWh_per_litre 

        combi_loss = self.boiler_combi_loss(energy_demand, timestep)
        energy_demand = energy_demand + combi_loss

        return self._boiler._Boiler__demand_energy(
            self.__service_name,
            energy_demand,
            return_temperature
            )
        
    def boiler_combi_loss(self, energy_demand, timestep):
        # daily hot water usage factor
        fu = 1.0 
        threshold_volume = 100 # litres/day
        if self.__daily_HW_usage < threshold_volume:
            fu = self.__daily_HW_usage / threshold_volume

        # Equivalent hot water litres at 60C for HW load profiles
        hw_litres_S_profile = 36.0
        hw_litres_M_profile = 100.2
        hw_litres_L_profile = 199.8

        dvf = hw_litres_M_profile - self.__daily_HW_usage
        if self.__separate_DHW_tests == Boiler_HW_test.M_S \
            and self.__daily_HW_usage < hw_litres_S_profile:
            dvf = 64.2
        elif (self.__separate_DHW_tests == Boiler_HW_test.M_L \
            and self.__daily_HW_usage < hw_litres_M_profile) \
            or (self.__separate_DHW_tests == Boiler_HW_test.M_S \
            and self.__daily_HW_usage > hw_litres_M_profile):
            dvf = 0
        elif self.__separate_DHW_tests == Boiler_HW_test.M_L \
            and self.__daily_HW_usage > hw_litres_L_profile:
            dvf = -99.6

        combi_loss = 0.0
        if (self.__separate_DHW_tests == Boiler_HW_test.M_L) \
            or (self.__separate_DHW_tests == Boiler_HW_test.M_S):
            #combi loss calculation with tapping cycle number 2 tapping test results 
            #(cycles M and S, or M and L)
            combi_loss = (energy_demand * \
                          (self.__rejected_energy_1 + dvf * self.__rejected_factor_3)) * fu \
                          + self.__storage_loss_factor_2 * (timestep / units.hours_per_day)

        elif self._boiler._Boiler__separate_DHW_tests == Boiler_HW_test.DHW_tests_M_only:
            #combi loss calculation with tapping cycle number 2 only test results
            combi_loss = (energy_demand * (self.__rejected_energy_1)) * fu \
                + self.__storage_loss_factor_2 * (timestep / units.hours_per_day)

        elif self.__separate_DHW_tests == Boiler_HW_test.No_additional_tests:
            # when no additional hot water test has been done
            default_combi_loss = 600 # annual default (kWh/day)
            combi_loss = default_combi_loss / units.days_per_year \
                        * (timestep / units.hours_per_day)

        else:
            exit('Invalid hot water test option')
        return combi_loss


class BoilerServiceSpace(BoilerService):
    """ An object to represent a space heating service provided by a boiler to e.g. a cylinder.

    This object contains the parts of the boiler calculation that are
    specific to providing space heating-.
    """
    def __init__(self, boilerservicespace_dict, boiler, service_name):
        """ Construct a BoilerServiceSpace object

        Arguments:
        boiler       -- reference to the Boiler object providing the service
        service_name -- name of the service demanding energy from the boiler
        """
        super().__init__(boiler, service_name)
        self.__service_name = service_name


    def demand_energy(self, energy_demand, temp_flow, temp_return):
        """ Demand energy (in kWh) from the boiler """

        return self._boiler._Boiler__demand_energy(
            self.__service_name,
            energy_demand,
            temp_return
            )


class Boiler:
    """ An object to represent a boiler """

    def __init__(self, boiler_dict, energy_supply, ext_cond, simulation_time):
        """ Construct a Boiler object

        Arguments:
        boiler_dict -- dictionary of boiler characteristics, with the following elements:
            TODO List elements and their definitions
        energy_supply -- reference to EnergySupply object
        simulation_time -- reference to SimulationTime object
        external_conditions -- reference to ExternalConditions object
        
        Other variables:
        energy_supply_connections
            -- dictionary with service name strings as keys and corresponding
               EnergySupplyConnection objects as values
        """
        self.__energy_supply = energy_supply
        self.__simulation_time = simulation_time
        self.__external_conditions = ext_cond
        self.__energy_supply_connections = {}

        # boiler properties
        self.__boiler_location = boiler_dict["boiler_location"]
        self.__min_modulation_load = boiler_dict["modulation_load"]
        self.__boiler_power = boiler_dict["rated_power"]
        full_load_gross = boiler_dict["efficiency_full_load"]
        part_load_gross = boiler_dict["efficiency_part_load"]
        self.__fuel_code = self.__energy_supply.fuel_type()
        
        
        # high value correction 
        net_to_gross = self.net_to_gross()
        full_load_net = full_load_gross / net_to_gross
        part_load_net = part_load_gross / net_to_gross
        corrected_full_load_net = self.high_value_correction_full_load(full_load_net)
        corrected_part_load_net = self.high_value_correction_part_load(part_load_net)
        corrected_full_load_gross = corrected_full_load_net * net_to_gross
        corrected_part_load_gross = corrected_part_load_net * net_to_gross

        #SAP model properties
        self.__room_temp = 19.5 #TODO TBC
        self.__outside_temp = self.__external_conditions.air_temp()
        #Equation 5 in EN15316-4-1
        #fgen = (c5*(Pn)^c6)/100
        #c5 = 4 c6 = -0.4 Pn = 8.8 kW
        #For simplicitiy, and due to it's small value,  a single default of 1.7% 
        #is applied within the calculation method for both regular and combination 
        #boilers.
        self.__standing_loss = round(4.0 * (8.8)** - 0.4 / 100.0, 3) 
        #30 is the nominal temperature difference between boiler and test room 
        #during standby loss test (EN15502-1 or EN15034)
        self.__standby_loss = 30.0
        #boiler standby heat loss power law index
        self.__sby_loss_idx = 1.25 
        self.__temp_boiler_loc = 19.5 
        if self.__boiler_location == "external":
            self.__temp_boiler_loc = self.__outside_temp

        #Calculate offset for EBV curves
        average_measured_eff = (corrected_part_load_gross + corrected_full_load_gross) / 2.0
        # test conducted at return temperature 30C
        temp_part_load_test = 30.0 
        # test conducted at return temperature 60C
        temp_full_load_test = 60.0 
        offset_for_theoretical_eff = 0.0
        theoretical_eff_part_load = self.effvsreturntemp(temp_part_load_test, \
                                                         offset_for_theoretical_eff)
        theoretical_eff_full_load = self.effvsreturntemp(temp_full_load_test, \
                                                         offset_for_theoretical_eff)
        average_theoretical_eff = (theoretical_eff_part_load + theoretical_eff_full_load)/ 2.0
        self.__offset = average_theoretical_eff - average_measured_eff 

    def __create_service_connection(self, service_name):
        """ Create an EnergySupplyConnection for the service name given """
        # Check that service_name is not already registered
        if service_name in self.__energy_supply_connections.keys():
            sys.exit("Error: Service name already used: "+service_name)
            # TODO Exit just the current case instead of whole program entirely?

        # Set up EnergySupplyConnection for this service
        self.__energy_supply_connections[service_name] = \
            self.__energy_supply.connection(service_name)

    def service_hot_water(self, boilerservicewatercombi_dict, service_name, temp_hot_water, temp_limit_upper, cold_feed):
        """ Return a BoilerServiceWater object and create an EnergySupplyConnection for it
        
        Arguments:
        boilerservicewatercombi_dict -- boiler hot water heating properties
        service_name -- name of the service demanding energy from the boiler
        temp_hot_water -- temperature of the hot water to be provided, in deg C
        temp_limit_upper -- upper operating limit for temperature, in deg C
        cold_feed -- reference to ColdWaterSource object
        """
        self.__create_service_connection(service_name)
        return BoilerServiceWaterCombi(self, boilerservicewatercombi_dict, service_name, temp_hot_water, temp_limit_upper, cold_feed, self.__simulation_time)


    def __cycling_adjustment(self, energy_output_required, temp_return_feed, timestep):
        prop_of_timestep_at_min_rate = min(energy_output_required \
                                       / (self.__boiler_power * self.__min_modulation_load * timestep)
                                       , 1.0)
        ton_toff = (1.0 - prop_of_timestep_at_min_rate) / prop_of_timestep_at_min_rate
        cycling_adjustment = 0.0
        if prop_of_timestep_at_min_rate < 1.0:
            cycling_adjustment = self.__standing_loss \
                                 * ton_toff \
                                 * ((temp_return_feed - self.__temp_boiler_loc) \
                                 / (self.__standby_loss) \
                                 ) \
                                 ** self.__sby_loss_idx
        
        return cycling_adjustment

    def __demand_energy(
            self,
            service_name,
            energy_output_required,
            temp_return_feed
            ):
        """ Calculate energy required by boiler to satisfy demand for the service indicated.
        #the average standing heat loss expressed as a proportional of the heat output."""
        timestep = self.__simulation_time.timestep()
        
        boiler_eff = self.effvsreturntemp(temp_return_feed, self.__offset)
                                    
        energy_output_max_power = self.__boiler_power * timestep
        energy_output_provided = min(energy_output_required, energy_output_max_power)
        
        cycling_adjustment = self.__cycling_adjustment(energy_output_required, temp_return_feed, timestep)

        location_adjustment \
            = max( (self.__standing_loss * \
                    ((temp_return_feed - self.__room_temp))**self.__sby_loss_idx \
                    - (temp_return_feed - self.__outside_temp)**self.__sby_loss_idx)\
                    , 0.0
                 )
    
        
        cyclic_location_adjustment = cycling_adjustment + location_adjustment
        
        blr_eff_final = 1.0 / (( 1.0 / boiler_eff ) + cyclic_location_adjustment)

        fuel_demand = energy_output_provided / blr_eff_final
        
        self.__energy_supply_connections[service_name].demand_energy(fuel_demand)
        
        return energy_output_provided
    
    
    def effvsreturntemp(self, return_temp, offset):
        """ Return boiler efficiency at different return temperatures """
        mains_gas_dewpoint = 52.2
        #TODO: add remaining fuels 
        if self.__fuel_code == Fuel_code.MAINS_GAS:
            if return_temp < mains_gas_dewpoint:
                theoretical_eff = -0.00007 * (return_temp)**2 + 0.0017 * return_temp + 0.979 
            else:
                theoretical_eff = -0.0006 * return_temp + 0.9129
            
            blr_theoretical_eff = theoretical_eff - offset
        else:
            exit('Fuel code does not exist')
        
        return blr_theoretical_eff

    def high_value_correction_part_load(self, net_efficiency_part_load):
        """ Return a Boiler efficiency corrected for high values """
        if self.__fuel_code == Fuel_code.MAINS_GAS:
            corrected_net_efficiency_part_load = min(net_efficiency_part_load \
                                                     - 0.213 * (net_efficiency_part_load - 0.966), 1.08)
        else:
            exit('Unknown fuel code '+str(self.__fuel_code))
        return corrected_net_efficiency_part_load

    def high_value_correction_full_load(self, net_efficiency_full_load):
        if self.__fuel_code == Fuel_code.MAINS_GAS:
            corrected_net_efficiency_full_load = min(net_efficiency_full_load \
                                                     - 0.673 * (net_efficiency_full_load - 0.955), 0.98)
        else:
            exit('Unknown fuel code '+str(self.__fuel_code))
        return corrected_net_efficiency_full_load

    def net_to_gross(self):
        """ Returns net to gross factor """
        if self.__fuel_code == Fuel_code.MAINS_GAS:
            net_to_gross = 0.901
        else:
            exit('Unknown fuel code '+str(self.__fuel_code))
        return net_to_gross
                

