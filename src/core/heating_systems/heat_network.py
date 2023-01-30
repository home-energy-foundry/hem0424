#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides objects to model heat networks
"""

# Standard library imports
import sys

# Local imports
from core.material_properties import WATER
from core.units import hours_per_day


class HeatNetworkService:
    """ A base class for objects representing services (e.g. water heating) provided by a heat network.

    This object encapsulates the name of the service, meaning that the system
    consuming the energy does not have to specify this on every call, and
    helping to enforce that each service has a unique name.

    Derived objects provide a place to handle parts of the calculation (e.g.
    distribution flow temperature) that may differ for different services.

    Separate subclasses need to be implemented for different types of service
    (e.g. HW and space heating). These should implement the following functions:
    - demand_energy(self, energy_demand)
    """

    def __init__(self, heat_network, service_name):
        """ Construct a HeatNetworkService object

        Arguments:
        heat_network -- reference to the HeatNetwork object providing the service
        service_name -- name of the service demanding energy from the boiler
        """
        self._heat_network = heat_network
        self._service_name = service_name


class HeatNetworkServiceWaterDirect(HeatNetworkService):
    """ An object to represent a water heating service provided by a heat network.

    This object contains the parts of the heat network calculation that are
    specific to providing hot water directly to the dwelling.
    """

    def __init__(self,
                 heat_network,
                 service_name,
                 temp_hot_water,
                 cold_feed,
                 simulation_time
                ):
        """ Construct a HeatNetworkWater object

        Arguments:
        heat_network       -- reference to the HeatNetwork object providing the service
        service_name       -- name of the service demanding energy from the heat network
        temp_hot_water     -- temperature of the hot water to be provided, in deg C
        cold_feed          -- reference to ColdWaterSource object
        simulation_time    -- reference to SimulationTime object
        """
        super().__init__(heat_network, service_name)

        self.__temp_hot_water = temp_hot_water
        self.__cold_feed = cold_feed
        self.__service_name = service_name
        self.__simulation_time = simulation_time

    def demand_hot_water(self, volume_demanded):
        """ Demand energy for hot water (in kWh) from the heat network """
        return_temperature = 60
        # Calculate energy needed to meet hot water demand
        energy_content_kWh_per_litre = WATER.volumetric_energy_content_kWh_per_litre(
            self.__temp_hot_water,
            self.__cold_feed.temperature()
            )
        energy_demand = volume_demanded * energy_content_kWh_per_litre 

        return self._heat_network._HeatNetwork__demand_energy(
            self.__service_name,
            energy_demand,
            return_temperature
            )


class HeatNetworkServiceWaterStorage(HeatNetworkService):
    """ An object to represent a water heating service provided by a heat network.

    This object contains the parts of the heat network calculation that are
    specific to providing hot water to the dwelling via a hot water cylinder.
    """

    def __init__(
            self,
            heat_network,
            service_name
            ):
        """ Construct a HeatNetworkWaterStorage object

        Arguments:
        heat_network -- reference to the HeatNetwork object providing the service
        service_name -- name of the service demanding energy from the heat network
        """
        super().__init__(heat_network, service_name)

        self.__service_name = service_name

    def demand_energy(self, energy_demand):
        """ Demand energy (in kWh) from the heat network """
        # Calculate energy needed to cover losses
        return_temperature = 60
        cylinder_loss = self.cylinder_loss()
        energy_demand = energy_demand + cylinder_loss
        return self._heat_network._HeatNetwork__demand_energy(
            self.__service_name,
            energy_demand,
            return_temperature
            )


class HeatNetworkServiceSpace(HeatNetworkService):
    """ An object to represent a space heating service provided by a heat network.

    This object contains the parts of the heat network calculation that are
    specific to providing space heating-.
    """
    def __init__(self, heat_network, service_name):
        """ Construct a HeatNetworkSpace object

        Arguments:
        heat_network -- reference to the HeatNetwork object providing the service
        service_name -- name of the service demanding energy from the heat network
        """
        super().__init__(heat_network, service_name)

        self.__service_name = service_name

    def demand_energy(self, energy_demand, temp_flow, temp_return):
        """ Demand energy (in kWh) from the heat network """
        return_temperature = 60
        return self._heat_network._HeatNetwork__demand_energy(
            self.__service_name,
            energy_demand,
            return_temperature
            )

    def energy_output_max(self, temp_output):
        """ Calculate the maximum energy output of the heat network"""
        return self._heat_network._HeatNetwork__energy_output_max(temp_output)


class HeatNetwork:
    """ An object to represent a heat network """

    def __init__(self, 
                heat_network_dict,
                energy_supply,
                energy_supply_conn_name_auxiliary,
                simulation_time,
                ext_cond, 
                ):
        """ Construct a HeatNetwork object

        Arguments:
        heat_network_dict   -- dictionary of heat network characteristics, with the following elements:
                            -- TODO List elements and their definitions
        energy_supply       -- reference to EnergySupply object
        simulation_time     -- reference to SimulationTime object
        external_conditions -- reference to ExternalConditions object

        Other variables:
        energy_supply_connections -- dictionary with service name strings as keys and corresponding
                                     EnergySupplyConnection objects as values
        temp_hot_water            -- temperature of the hot water to be provided, in deg C
        cold_feed                 -- reference to ColdWaterSource object
        """

        self.__energy_supply = energy_supply
        self.__simulation_time = simulation_time
        self.__energy_supply_connections = {}
        self.__energy_supply_connection_aux \
            = self.__energy_supply.connection(energy_supply_conn_name_auxiliary)

    def __create_service_connection(self, service_name):
        """ Create an EnergySupplyConnection for the service name given """
        # Check that service_name is not already registered
        if service_name in self.__energy_supply_connections.keys():
            sys.exit("Error: Service name already used: "+service_name)
            # TODO Exit just the current case instead of whole program entirely?

        # Set up EnergySupplyConnection for this service
        self.__energy_supply_connections[service_name] = \
            self.__energy_supply.connection(service_name)

    def create_service_hot_water_direct(
            self,
            service_name,
            temp_hot_water,
            cold_feed,
            daily_loss
            ):
        """ Return a HeatNetworkSeriviceWaterDirect object and create an EnergySupplyConnection for it
        
        Arguments:
        service_name      -- name of the service demanding energy from the heat network
        temp_hot_water    -- temperature of the hot water to be provided, in deg C
        cold_feed         -- reference to ColdWaterSource object
        daily_loss        -- daily loss from the HIU, in kW
        """
        self.__create_service_connection(service_name)

        return HeatNetworkServiceWaterDirect(
            self,
            service_name,
            temp_hot_water,
            cold_feed,
            self.__simulation_time
            )

    def create_service_hot_water_storage(self, service_name):
        """ Return a HeatNetworkSeriviceWaterStorage object and create an EnergySupplyConnection for it

        Arguments:
        service_name -- name of the service demanding energy from the heat network
        """
        self.__create_service_connection(service_name)

        return HeatNetworkServiceWaterStorage(self, service_name)

    def create_service_space_heating(self, service_name):
        """ Return a HeatNetworkServiceSpace object and create an EnergySupplyConnection for it

        Arguments:
        service_name -- name of the service demanding energy from the heat network
        """
        self.__create_service_connection(service_name)

        return HeatNetworkServiceSpace(self, service_name)

    def __demand_energy(
            self,
            service_name,
            energy_output_required,
            temp_return_feed
            ):
        """ Calculate energy required by heat network to satisfy demand for the service indicated."""
        self.__energy_supply_connections[service_name].demand_energy(energy_output_required)

        return energy_output_required

    def HIU_loss(self, daily_loss):
        """ Standing heat loss from the HIU (heat interface unit) in kWh """
        # daily_loss to be sourced from the PCDB, in kW
        HIU_loss = daily_loss / hours_per_day * self.__simulation_time.timestep()

        return HIU_loss
