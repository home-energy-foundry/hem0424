#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides objects to model heat storage vessels e.g. hot water
cylinder with immersion heater.
Energy calculation (storage modelled with multiple volumes) - Method A from BS EN 15316-5:2017
"""

# Standard library imports
from copy import deepcopy

# Local imports
from core.material_properties import WATER
from core.pipework import Pipework
import core.units as units


class StorageTank:
    """ An object to represent a hot water storage tank/cylinder

    Models the case where hot water is drawn off and replaced by fresh cold
    water which is then heated in the tank by a heat source. Assumes the water
    is stratified by temperature.

    Implements function demand_hot_water(volume_demanded) which all hot water
    source objects must implement.
    """
    #BS EN 15316-5:2017 Appendix B default input data
    #Model Information
    #number of volumes the storage is modelled with
    #see App.C (C.1.2 selection of the number of volumes to model the storage unit)
    #for more details if this wants to be changed.
    __NB_VOL = 4
    #Product Description Data
    #factors for energy recovery Table B.3
    #part of the auxiliary energy transmitted to the medium
    __f_rvd_aux = 0.25
    #part of the thermal losses transmitted to the room
    __f_sto_m = 0.75
    #standby losses adaptation
    __f_sto_bac_acc = 1
    #Design Data
    #***Operative conditions Table B.4
    #TODO - determine difference and purpose between temperature required for DHW and set point
    #temperature required for DHW - degress
    #__temp_out_W_min = 55 default in table B.4
    #hot water was found to be leaving the cylinder at 52oC
    #in the 2008 EST field trial that SAP10 and earlier are based on.
    #Assume this is refering to the same thing until investigated further.
    #TODO possibly link and vary per demand event in future
    __temp_out_W_min = 52
    #ambient temperature - degress
    #TODO - link to zone temp at timestep possibly and location of tank (in or out of heated space)
    __temp_amb = 16
    #thermostat set temperature - degrees
    #TODO - possible move to init  as input, maybe per layer and/or timestep
    #__temp_set_on = 65  default in table B.4
    #use 55oC as more consistent with average delivery temperature of 52
    __temp_set_on = 55
    # Primary pipework gains for the timestep
    __primary_gains = 0

    def __init__(self, volume, losses, temp_hot, cold_feed, simulation_time,  primary_pipework=None, contents=WATER):
        """ Construct a StorageTank object

        Arguments:
        volume               -- total volume of the tank, in litres
        losses               -- measured standby losses due to cylinder insulation
                                at standardised conditions, in kWh/24h
        temp_hot             -- temperature of the hot water, in deg C
        cold_feed            -- reference to ColdWaterSource object
        simulation_time      -- reference to SimulationTime object
        contents             -- reference to MaterialProperties object

        Other variables:
        heat_sources         -- list (initialised to empty) of heat sources
        """
        self.__Q_std_ls_ref = losses
        self.__temp_hot     = temp_hot
        self.__cold_feed    = cold_feed
        self.__contents     = contents
        self.__simulation_time = simulation_time
        self.__heat_sources = []

        #total volume in litres
        self.__V_total = volume
        #list of volume of layers in litres
        self.__Vol_n = [self.__V_total / self.__NB_VOL] * self.__NB_VOL
        #water specific heat in kWh/kg.K
        self.__Cp = contents.specific_heat_capacity_kWh()
        #volumic mass in kg/litre
        self.__rho = contents.density()
        #6.4.3.2 STEP 0 Initialization
        """for initial conditions all temperatures in the thermal storage unit(s)
         are equal to the set point temperature in degrees.
         We are expecting to run a "warm-up" period for the main calculation so this doesn't matter.
         """
        self.__temp_n = [self.__temp_set_on] * self.__NB_VOL
        
        if primary_pipework is not None:
            self.__primary_pipework = Pipework(
                    primary_pipework["internal_diameter"],
                    primary_pipework["external_diameter"],
                    primary_pipework["length"],
                    primary_pipework["insulation_thermal_conductivity"],
                    primary_pipework["insulation_thickness"],
                    primary_pipework["surface_reflectivity"],
                    primary_pipework["pipe_contents"])

    def add_heat_source(self, heat_source, proportion_of_tank_heated):
        """ Add a reference to heat source object and specify position in tank.

        Heat source object must implement the demand_energy(energy_demand) function.
        """
        # TODO Add proportion to list. Account for thermostat position for each
        #      heat source individually?
        self.__heat_sources.append(heat_source)

    def stand_by_losses_coefficient(self):
        """Appendix B B.2.8 Stand-by losses are usually determined in terms of energy losses during
        a 24h period. Formula (B.2) allows the calculation of _sto_stbl_ls_tot based on a reference
        value of the daily thermal energy losses.

        H_sto_ls is the stand-by losses, in kW/K

        TODO there are alternative methods listed in App B (B.2.8) which are not included here."""
        #BS EN 12897:2016 appendix B B.2.2
        #temperature of the water in the storage for the standardized conditions - degrees
        #these are reference (ref) temperatures from the standard test conditions for cylinder loss.
        temp_set_ref = 65
        temp_amb_ref = 20
    
        H_sto_ls = (1000 * self.__Q_std_ls_ref) / (24 * (temp_set_ref - temp_amb_ref))

        return H_sto_ls

    def energy_stored(self):
        """Calculate the energy stored for each layer in the storage volume - kWh

        The energy stored is calculated, for information, accordingly to the limit value of
        temperature for domestic hot water."""
        Q_out_W_n = [0] * self.__NB_VOL
        for i, temp_i in enumerate(self.__temp_n):
            #TODO not sure if __temp_out_W_min is right temperature to be using. 
            #use cold temp instead.
            """if temp_i > self.__temp_out_W_min:
                Q_out_W_n[i] = self.__rho * self.__Cp * self.__Vol_n[i] \
                               * (self.__temp_n[i] - self.__temp_out_W_min)"""
            if temp_i > self.__temp_out_W_min:
                Q_out_W_n[i] = self.__rho * self.__Cp * self.__Vol_n[i] \
                               * (self.__temp_n[i] - self.__cold_feed.temperature())
            else:
                Q_out_W_n[i] = 0

        return Q_out_W_n

    def energy_required(self, volume_demanded):
        """Convert the volume (in litres) demanded into an energy required in kWh
        """
        #TODO energy delivered to the distribution system for heating and domestic hot water is
        #obtained in accordance to EN 15316-3. Check here for details for converting from volume.
        #TODO check what temperatures should be used to determine delta T in this equation.
        #it should match temperature range used in the enrgy withdrawn function I think.
        Q_out_W_dis_req = self.__rho * self.__Cp * volume_demanded \
                            * (self.__temp_out_W_min - self.__cold_feed.temperature())

        return Q_out_W_dis_req

    def energy_withdrawn(self, Q_out_W_dis_req, Q_out_W_n):
        """the calculation of the volume to be withdrawn is made accordingly with the energy to be
        delivered to the distribution system with a threshold value for the minimum available
        temperature according to the scenarios for domestic hot water.

        In this model only domestic hot water is considered for now.

        The volume of water withdrawn is based on contribution of the homogenous volumes of the
        storage unit, from the volume connected to the water output to the volume connected
        to the water input."""
        #initialise list of volume(s) to be withdrawn in litres
        Vol_use_W_n = [0] * self.__NB_VOL
        #initialise list of energy used for DHW in kWh
        Q_use_W_n = [0] * self.__NB_VOL
        #initialise tracker for energy required remainder / unmet energy
        Q_out_W_dis_req_rem = Q_out_W_dis_req

        """TODO A few checks to make
        1. Check condition used to compare to cold feed temperature in two places below
        #seems odd to check against cold water temp for all layers.
        if self.__temp_n[i] >= self.__cold_feed.temperature():
        2. Also not sure if temperature self.__temp_out_W_min is right temperature to use in deltaT.
           Using cold temp instead as per spreadsheet"""

        #IMPORTANT to iterate in reversed order -from top of tank where draw off happens
        for i, vol_i in reversed(list(enumerate(self.__Vol_n))):
            #special condition for first layer considered (the top layer)
            if i == self.__NB_VOL-1:
                #threshold minimum temperature
                if self.__temp_n[i] >= self.__cold_feed.temperature():
                    #total energy to be delivered can be met by top layer
                    if Q_out_W_dis_req <= Q_out_W_n[i]:
                        Vol_use_W_n[i] \
                            = Q_out_W_dis_req \
                            / ( self.__rho * self.__Cp \
                              * (self.__temp_n[i] - self.__cold_feed.temperature()) \
                              )
                        Q_use_W_n[i] = Q_out_W_dis_req
                        Q_out_W_dis_req_rem = 0
                        #no need to carry on as energy required has been met
                        break
                    else:
                    #top layer cannot meet all energy required
                    #so all of top layer volume will be withdrawn
                        Vol_use_W_n[i] = vol_i
                        Q_use_W_n[i] = Q_out_W_n[i]
                        #update remaining energy still required from lower layers
                        Q_out_W_dis_req_rem -= Q_out_W_n[i]
                else:
                    #temperature not met by top layer so no volume will be withdrawn
                    break
            #now iterate over lower layers in turn
            #threshold minimum temperature
            elif self.__temp_n[i] >= self.__cold_feed.temperature():
                #this layer can meet and/or exceed remainder energy required for distribution
                if Q_out_W_dis_req_rem <= Q_out_W_n[i]:
                    Vol_use_W_n[i] \
                        = Q_out_W_dis_req_rem \
                        / ( self.__rho * self.__Cp \
                          * (self.__temp_n[i] - self.__cold_feed.temperature()) \
                          )
                    Q_use_W_n[i] = Q_out_W_dis_req_rem
                    Q_out_W_dis_req_rem = 0
                    #no need to carry on as energy required has been met
                    break
                elif Q_out_W_n[i] > 0:
                #this layer cannot meet remainder energy required
                #so all of this layer volume will be withdrawn
                    Vol_use_W_n[i] = vol_i
                    Q_use_W_n[i] = Q_out_W_n[i]
                    #update remaining energy still required from lower layers
                    Q_out_W_dis_req_rem -= Q_out_W_n[i]
            else:
                pass

        return Q_use_W_n, Q_out_W_dis_req_rem, Vol_use_W_n

    def volume_withdrawn_replaced(self, Vol_use_W_n):
        """Principles: the volume withdrawn is replaced with the identical quantity of water
        provided to the input of the storage heater (bottom). The water of the upper volume is
        melted with the quantity of withdrawn water at the temperature of the lower level. """
        #initialise list of temperature of layers AFTER volume withdrawn in degrees
        temp_s3_n = deepcopy(self.__temp_n)
        #initialise volume in each layer remaining after draw-off
        V_sto_rem_n = [x - y for x, y in zip(self.__Vol_n, Vol_use_W_n)]

        #Temperature change only applicable if there is any volume withdrawn
        if sum(Vol_use_W_n) > 0:
            #determine how much water is displaced
            #IMPORTANT to iterate in reverse order -from top of tank
            for i, vol_i in reversed(list(enumerate(self.__Vol_n))):
                vol_to_replace = self.__Vol_n[i]
                #set list of flags for which layers need mixing for this layer
                vol_mix_n = [0] * self.__NB_VOL
                #loop through layers i and below
                for j, vol_j in reversed(list(enumerate(V_sto_rem_n[:i+1]))):
                    if V_sto_rem_n[j] == 0:
                        pass
                    #layer can replace all of volume withdrawn
                    elif V_sto_rem_n[j] >= vol_to_replace:
                        vol_mix_n[j] = vol_to_replace
                        V_sto_rem_n[j] -= vol_to_replace
                        vol_to_replace = 0
                        break
                    #layer can replace some of volume withdrawn
                    elif V_sto_rem_n[j] < vol_to_replace:
                        vol_mix_n[j] = V_sto_rem_n[j]
                        V_sto_rem_n[j] = 0
                        vol_to_replace -= vol_mix_n[j]
                #any volume remainder after looping through all layers will be at cold water temp

                #calculate new temperature of layer
                #note 6.4.3.5 equation 9 has an error as adding temps to volumes.
                temp_s3_n[i] \
                    = ( (self.__cold_feed.temperature() * vol_to_replace) \
                        + (sum(self.__temp_n[k] * vol_mix_n[k] for k in range(len(vol_mix_n)))) \
                      ) \
                      / self.__Vol_n[i]

        return temp_s3_n

    def potential_energy_input(self):
        """Energy input for the storage from the generation system
        (expressed per energy carrier X)
        Heat Source = energy carrier"""
        #initialise list of potential energy input for each layer
        Q_x_in_n = [0] * self.__NB_VOL

        #TODO - allow position of heat source to be defined in any layer (assume bottom tank atm)
        #TODO - this should be calculated in accordance to EN 15316-1. check this is used.
        for heat_source in self.__heat_sources:
            energy_potential = heat_source.energy_output_max()
            Q_x_in_n[0] += energy_potential

        return Q_x_in_n

    def energy_input(self, temp_s3_n, Q_x_in_n):
        """The input of energy(s) is (are) allocated to the specific location(s)
        of the input of energy.
        Note: for energy withdrawn froma heat exchanger, the energy is accounted negatively.

        For step 6, the addition of the temperature of volume 'i' and theoretical variation of
        temperature calculated according to formula (10) can exceed the set temperature defined
        by the control system of the storage unit."""
        #initialise list of theoretical variation of temperature of layers in degrees
        delta_temp_n = [0] * self.__NB_VOL
        #initialise list of theoretical temperature of layers after input in degrees
        temp_s6_n = [0] * self.__NB_VOL
        #output energy delivered by the storage in kWh - timestep dependent
        Q_sto_h_out_n = [0] * self.__NB_VOL

        for i, vol_i in list(enumerate(self.__Vol_n)):
            delta_temp_n[i] = (Q_x_in_n[i] + Q_sto_h_out_n[i]) \
                              / (self.__rho * self.__Cp * self.__Vol_n[i])
            temp_s6_n[i] = temp_s3_n[i] + delta_temp_n[i]

        Q_s6 = self.__rho * self.__Cp * sum(self.__Vol_n[i] \
                * temp_s6_n[i] for i in range(len(self.__Vol_n)))

        return Q_s6, temp_s6_n

    def rearrange_temperatures(self, temp_s6_n):
        """When the temperature of the volume i is higher than the one of the upper volume,
        then the 2 volumes are melted. This iterative process is maintained until the temperature
        of the volume i is lower or equal to the temperature of the volume i+1."""
        #set list of flags for which layers need mixing
        mix_layer_n = [0] * self.__NB_VOL
        temp_s7_n = deepcopy(temp_s6_n)
        #for loop :-1 is important here!
        #loop through layers from bottom to top, without including top layer.
        #this is because the top layer has no upper layer to compare too
        for i, vol_i in list(enumerate(self.__Vol_n[:-1])):
            if temp_s7_n[i] > temp_s7_n[i+1]:
                #set layers to mix
                mix_layer_n[i] = 1
                mix_layer_n[i+1] = 1
                #mix temeratures of all applicable layers
                #note error in formula 12 in standard as adding temperature to volume
                #this is what I think they intended from the description
                temp_mix = sum( self.__Vol_n[k] * temp_s7_n[k] * mix_layer_n[k] \
                                for k in range(len(self.__Vol_n)) \
                              ) \
                            / ( sum(self.__Vol_n[l] * mix_layer_n[l] \
                                    for l in range(len(self.__Vol_n)) \
                                   ) \
                              )
                #set same temperature for all applicable layers
                for j, temp_j in list(enumerate(temp_s7_n[:i+2])):
                    if mix_layer_n[j] == 1:
                        temp_s7_n[j] = temp_mix
            else:
                #reset mixing as lower levels now stabalised
                mix_layer_n = [0] * self.__NB_VOL

        Q_h_sto_end = self.__rho * self.__Cp \
                     * sum(self.__Vol_n[i] * temp_s7_n[i]
                           for i in range(len(self.__Vol_n)))

        return Q_h_sto_end, temp_s7_n

    def thermal_losses(self, temp_s7_n, Q_x_in_n, Q_h_sto_s7):
        """Thermal losses are calculated with respect to the impact of the temperature set point"""
        #standby losses coefficient - kW/K
        H_sto_ls = self.stand_by_losses_coefficient()

        #standby losses correction factor - dimensionless
        #do not think these are applicable so used: f_sto_dis_ls = 1, f_sto_bac_acc = 1

        #initialise list of thermal losses in kWh
        Q_ls_n = [0] * self.__NB_VOL
        #initialise list of final temperature of layers after thermal losses in degrees
        temp_s8_n = [0] * self.__NB_VOL

        #thermal losses
        for i, vol_i in list(enumerate(self.__Vol_n)):
            Q_ls_n[i] = (H_sto_ls * self.__rho * self.__Cp) \
                        * (self.__Vol_n[i] / self.__V_total) \
                        * (min(temp_s7_n[i], self.__temp_set_on) - self.__temp_amb)

        #total thermal losses kWh
        Q_ls = sum(Q_ls_n)

        #the final value of the temperature is reduced due to the effect of the thermal losses.
        #check temperature compared to set point
        #the temperature for each volume are limited to the set point for any volume controlled
        for i, vol_i in list(enumerate(self.__Vol_n)):
            if temp_s7_n[i] > self.__temp_set_on:
                #Case 2 - Temperature exceeding the set point
                temp_s8_n[i] = self.__temp_set_on
            else:
                #Case 1 - Temperature below the set point
                #TODO - spreadsheet accounts for total thermal losses not just layer
                """temp_s8_n[i] \
                    = temp_s7_n[i] - (Q_ls / (self.__rho * self.__Cp * self.__V_total))"""

                #the final value of the temperature
                #is reduced due to the effect of the thermal losses
                #Formula (14) in the standard appears to have error as addition not multiply
                #and P instead of rho
                temp_s8_n[i] \
                    = temp_s7_n[i] - (Q_ls_n[i] / (self.__rho * self.__Cp * self.__Vol_n[i]))

        #excess energy / energy surplus
        """excess energy is calculated as the difference from the energy stored, Qsto,step7, and
           energy stored once the set temperature is obtained, Qsto,step8, with addition of the
           thermal losses."""
        #TODO depends on the position of the thermostat
        #TODO - assumption currently that the thermostat is in the bottom layer of the tank
        if temp_s7_n[0] > self.__temp_set_on:
            energy_surplus = Q_h_sto_s7 - Q_ls \
                             - ( self.__rho * self.__Cp * self.__V_total * self.__temp_set_on)
        else:
            energy_surplus = 0

        #the thermal energy provided to the system (from heat sources) shall be limited
        #adjustment of the energy delivered to the storage according with the set temperature
        #potential input from generation
        Q_x_in_adj = sum(Q_x_in_n)
        #TODO - find in standard - availability of back-up - where is this from?
        #also refered to as electrical power on
        STO_BU_ON = 1
        Q_in_H_W = min((Q_x_in_adj - energy_surplus), Q_x_in_adj * STO_BU_ON)

        return Q_in_H_W, Q_ls, temp_s8_n

    def testoutput(self, volume_demanded, Q_out_W_n, Q_out_W_dis_req, Q_use_W_n,
                   Q_out_W_dis_req_rem, Vol_use_W_n, temp_s3_n, Q_x_in_n,
                   Q_s6, temp_s6_n, temp_s7_n, Q_in_H_W, Q_ls,
                   temp_s8_n
                   ):
        """ print output to a file for analysis """
        #write headers first
        with open("test_storage_tank.csv", "a") as o:
            if self.__simulation_time.current_hour() == 0:
                o.write("\n")
                o.write("time,volume total,specific heat,density,cold water,\
                initial temperatures,,,,energy stored,,,,volume demanded,\
                energy required for volume demanded,energy withdrawn,,,,unmet energy required,\
                volume withdrawn,,,,temperatures after volume withdrawn,,,,\
                potential energy input,,,,theoretical energy stored after energy input,\
                theoretical temperatures after energy input,,,,temperatures after volume mixing,,,,\
                energy input (adjusted),thermal losses,temperatures after thermal losses"
                )
                o.write("\n")
                o.write("h,litres,kWh/kgK,kg/l,\
                        oC,oC,,,,kWh,,,,litres,\
                        kWh,kWh,,,,kWh,\
                        litres,,,,oC,,,,\
                        kWh,,,,kWh,\
                        oC,,,,oC,,,,\
                        kWh,kWh,oC"
                        )
            o.write("\n")
            o.write(str(self.__simulation_time.hour_of_day()))
            o.write(",")
            o.write(str(self.__V_total))
            o.write(",")
            o.write(str(self.__Cp))
            o.write(",")
            o.write(str(self.__rho))
            o.write(",")
            o.write(str(self.__cold_feed.temperature()))
            o.write(",")
            o.write(str(self.__temp_n))
            o.write(",")
            o.write(str(Q_out_W_n))
            o.write(",")
            o.write(str(volume_demanded))
            o.write(",")
            o.write(str(Q_out_W_dis_req))
            o.write(",")
            o.write(str(Q_use_W_n))
            o.write(",")
            o.write(str(Q_out_W_dis_req_rem))
            o.write(",")
            o.write(str(Vol_use_W_n))
            o.write(",")
            o.write(str(temp_s3_n))
            o.write(",")
            o.write(str(Q_x_in_n))
            o.write(",")
            o.write(str(Q_s6))
            o.write(",")
            o.write(str(temp_s6_n))
            o.write(",")
            o.write(str(temp_s7_n))
            o.write(",")
            o.write(str(Q_in_H_W))
            o.write(",")
            o.write(str(Q_ls))
            o.write(",")
            o.write(str(temp_s8_n))
            o.write(",")

    def demand_hot_water(self, volume_demanded):
        """ Draw off hot water from the tank
        Energy calculation as per BS EN 15316-5:2017 Method A sections 6.4.3, 6.4.6, 6.4.7

        Arguments:
        volume_demanded -- volume of hot water required, in litres
        """
        #6.4.3.3 STEP 1 Calculate energy stored
        #energy stored for domestic hot water - kWh
        Q_out_W_n = self.energy_stored()
        #TODO energy stored for heating - kWh

        #6.4.3.4 STEP 2 Volume (and energy) to be withdrawn from the storage (for DHW)
        #energy required for domestic hot water in kWh
        # TODO Should demand be in terms of volume or energy? Or option for both?
        #      In terms of volume is simpler because cold water temperature
        #      (and therefore baseline energy) is variable.
        #      But method expects an energy value as input.
        Q_out_W_dis_req = self.energy_required(volume_demanded)
        #energy withdrawn, unmet energy required, volume withdrawn
        Q_use_W_n, Q_out_W_dis_req_rem, Vol_use_W_n \
            = self.energy_withdrawn(Q_out_W_dis_req, Q_out_W_n)
        #TODO decide if there should be an exit statement/ reported elsewhere
        #    if tank cannot provide enough hot water?
        #    if Q_out_W_dis_req_rem > 0:
        #    sys.exit('condition for delivering the required quantity of hot water is not obtained.')

        #6.4.3.5 STEP 3 Temperature of the storage after volume withdrawn (for DHW)
        temp_s3_n = self.volume_withdrawn_replaced(Vol_use_W_n)

        #TODO 6.4.3.6 STEP 4 Volume to be withdrawn from the storage (for Heating)
        #TODO - 6.4.3.7 STEP 5 Temperature of the storage after volume withdrawn (for Heating)

        #6.4.3.8 STEP 6 Energy input into the storage
        #input energy delivered to the storage in kWh - timestep dependent
        Q_x_in_n = self.potential_energy_input()

        Q_s6, temp_s6_n = self.energy_input(temp_s3_n, Q_x_in_n)

        #6.4.3.9 STEP 7 Re-arrange the temperatures in the storage after energy input
        Q_h_sto_s7, temp_s7_n = self.rearrange_temperatures(temp_s6_n)

        #STEP 8 Thermal losses and final temperature
        Q_in_H_W, Q_ls, temp_s8_n \
            = self.thermal_losses(temp_s7_n, Q_x_in_n, Q_h_sto_s7)

        #TODO 6.4.3.11 Heat exchanger

        #Additional calculations
        #6.4.6 Calculation of the auxiliary energy
        #accounted for elsewhere so not included here
        W_sto_aux = 0

        #6.4.7 Recoverable, recovered thermal losses
        #recovered auxiliary energy to the heating medium - kWh
        Q_sto_h_aux_rvd = W_sto_aux * self.__f_rvd_aux
        #recoverable auxiliary energy transmitted to the heated space - kWh
        Q_sto_h_rbl_aux = W_sto_aux * self.__f_sto_m * (1 - self.__f_rvd_aux)
        #recoverable heat losses (storage) - kWh
        Q_sto_h_rbl_env = Q_ls * self.__f_sto_m
        #total recoverable heat losses  for heating - kWh
        self.__Q_sto_h_ls_rbl = Q_sto_h_rbl_env + Q_sto_h_rbl_aux

        #demand adjusted energy from heat source (before was just using potential without taking it)
        input_energy_adj = deepcopy(Q_in_H_W)
        for heat_source in self.__heat_sources:
            input_energy_adj = input_energy_adj - self.get_demand_energy(heat_source, input_energy_adj)

        #set temperatures calculated to be initial temperatures of volumes for the next timestep
        self.__temp_n = deepcopy(temp_s8_n)

        #TODOrecoverable heat losses for heating should impact heating

        #print interim steps to output file for investigation
        """self.testoutput(
            volume_demanded, Q_out_W_n, Q_out_W_dis_req, Q_use_W_n, Q_out_W_dis_req_rem,
            Vol_use_W_n, temp_s3_n, Q_x_in_n, Q_s6, temp_s6_n,
            temp_s7_n, Q_in_H_W, Q_ls, temp_s8_n,
            )"""
        return Q_out_W_dis_req_rem

    def internal_gains(self):
        """ Return the DHW recoverable heat losses as internal gain for the current timestep in W"""
        primary_gains_timestep = self.__primary_gains
        self.__primary_gains = 0
        return self.__Q_sto_h_ls_rbl * units.W_per_kW / self.__simulation_time.timestep() \
        + primary_gains_timestep

            
    def get_demand_energy(self, heat_source, input_energy_adj):
        # function that also calculates pipework loss before sending on the demand energy 
        # if immersion heater, no pipework losses
        if isinstance(heat_source, ImmersionHeater):
            return(heat_source.demand_energy(input_energy_adj))
        else:
            demand_energy = heat_source.demand_energy(input_energy_adj)
            # primary losses for the timestep calculated from  temperature difference
            primary_pipework_losses = self.__primary_pipework.heat_loss(self.__temp_hot, self.__temp_amb)
            self.__primary_gains = primary_pipework_losses
            demand_energy+=primary_pipework_losses
            # TODO - how are these gains reflected in the calculations? allocation by zone?
            return(demand_energy)



class ImmersionHeater:
    """ An object to represent an immersion heater """

    def __init__(self, rated_power, energy_supply_conn, simulation_time, control=None):
        """ Construct an ImmersionHeater object

        Arguments:
        rated_power        -- in kW
        energy_supply_conn -- reference to EnergySupplyConnection object
        simulation_time    -- reference to SimulationTime object
        control            -- reference to a control object which must implement is_on() func
        """
        self.__pwr                = rated_power
        self.__energy_supply_conn = energy_supply_conn
        self.__simulation_time    = simulation_time
        self.__control            = control

    def demand_energy(self, energy_demand):
        """ Demand energy (in kWh) from the heater """

        # Account for time control where present. If no control present, assume
        # system is always active (except for basic thermostatic control, which
        # is implicit in demand calculation).
        if self.__control is None or self.__control.is_on():
            # Energy that heater is able to supply is limited by power rating
            energy_supplied = min(energy_demand, self.__pwr * self.__simulation_time.timestep())
        else:
            energy_supplied = 0.0

        self.__energy_supply_conn.demand_energy(energy_supplied)
        return energy_supplied

    def energy_output_max(self):
        """ Calculate the maximum energy output (in kWh) from the heater """

        # Account for time control where present. If no control present, assume
        # system is always active (except for basic thermostatic control, which
        # is implicit in demand calculation).
        if self.__control is None or self.__control.is_on():
            # Energy that heater is able to supply is limited by power rating
            power_max = self.__pwr * self.__simulation_time.timestep()
        else:
            power_max = 0.0

        return power_max
