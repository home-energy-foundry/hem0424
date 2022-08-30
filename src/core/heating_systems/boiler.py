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

#Local imports
from core.energy_supply.energy_supply import Fuel_code


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
        self.__boiler = boiler
        self.__service_name = service_name


class BoilerServiceWater(BoilerService):
    """ An object to represent a water heating service provided by a boiler to e.g. a cylinder.

    This object contains the parts of the boiler calculation that are
    specific to providing hot water.

    TODO Handle combi boilers as well - would need to implement demand_hot_water function
    """

    def __init__(self, boiler, service_name, temp_hot_water, temp_limit_upper, cold_feed):
        """ Construct a BoilerServiceWater object
        
        Arguments:
        boiler       -- reference to the Boiler object providing the service
        service_name -- name of the service demanding energy from the boiler
        temp_hot_water -- temperature of the hot water to be provided, in deg C
        temp_limit_upper -- upper operating limit for temperature, in deg C
        cold_feed -- reference to ColdWaterSource object
        """
        super().__init__(boiler, service_name)

        self.__temp_hot_water = temp_hot_water
        self.__temp_limit_upper = temp_limit_upper
        self.__cold_feed = cold_feed

    def demand_energy(self, energy_demand):
        """ Demand energy (in kWh) from the boiler """
        temp_cold_water = self.__cold_feed.temperature()

        return self.__boiler._Boiler__demand_energy(
            self.__service_name,
            energy_demand,
            self.__temp_hot_water,
            temp_cold_water,
            self.__temp_limit_upper,
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
        self.__modulation_load = boiler_dict["modulation_load"]
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

    def service_hot_water(self, service_name, temp_hot_water, temp_limit_upper, cold_feed):
        """ Return a BoilerServiceWater object and create an EnergySupplyConnection for it
        
        Arguments:
        service_name -- name of the service demanding energy from the boiler
        temp_hot_water -- temperature of the hot water to be provided, in deg C
        temp_limit_upper -- upper operating limit for temperature, in deg C
        cold_feed -- reference to ColdWaterSource object
        """
        self.__create_service_connection(service_name)
        return BoilerServiceWater(self, service_name, temp_hot_water, temp_limit_upper, cold_feed)

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
        #Proportion of time interval at minimum rate
        uncapped_modulation_proportion = energy_output_required / \
                                    (self.__boiler_power * self.__modulation_load * timestep)
        energy_output_provided = uncapped_modulation_proportion
        modulation_proportion = min(uncapped_modulation_proportion, 1.0)
        ton_toff = (1.0- modulation_proportion)/ modulation_proportion
        
        cycling_adjustment = 0.0
        if modulation_proportion > 0.0:
            cycling_adjustment \
                = ( self.__standing_loss * ton_toff \
                  * (temp_return_feed - self.__temp_boiler_loc) \
                  / (self.__standby_loss) \
                  ) \
                  **self.__sby_loss_idx

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
                

