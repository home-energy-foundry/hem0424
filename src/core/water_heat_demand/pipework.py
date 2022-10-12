#!/usr/bin/env python3
""" TODO Copyright & licensing notices
This module provides object(s) to represent pipework
"""
# Standard library imports
from math import pi, log
# Local imports
import core.units as units
import core.material_properties as material_properties


class Pipework:
    """ An object to represent steady state heat transfer in a hollow cyclinder (pipe)
    with radial heat flow. Method taken from 2021 ASHRAE Handbook, Section 4.4.2 """
        
    def __init__(self, h_i, D_i, D_o, L, k_p, k_i, t_i, h_0, E):
        """Construct a Pipework object
        
        Arguments:
        h_i      -- heat transfer coefficient inside the pipe, in W / m^2 K
        D_i      -- internal diameter of the pipe, in m
        D_o      -- external diameter of the pipe, in m
        L        -- length of pipe, in m
        k_p      -- thermal conductivity of the pipe, in W / m K
        k_i      -- thermal conductivity of the insulation, in W / m K
        t_i      -- thickness of the pipe insulation, in m
        h_0      -- heat transfer coefficient at the outer surface, in W / m^2 K
        E        -- emissivity of the outer surface
        """
        self.__E = E
        self.__L = L
        self.__D_i = D_i
        
        """ Calculate the diameter of the pipe including the insulation (D_ins), in m"""
        self.__D_ins = D_o + (2.0 * t_i)
        
        """ Calculate the thermal resistance (R) values, in K/W """
        """ Calculate thermal resistance of the water in the pipe (R1) """
        self.__R1 = 1.0 / (h_i * pi * D_i * L)
        
        """ Calculate thermal resistance of the pipe (no insulation) (R2) """
        self.__R2 = log(D_o / D_i) / (2.0 * pi * k_p * L)
        
        """ Calculate thermal resistance of the insulation (R3) """
        self.__R3 = log(self.__D_ins / D_o) / (2.0 * pi * k_i * L)
        
        """ Calculate surface convective resistance (Rc) """
        self.__Rc = 1.0 / (h_0 * pi * self.__D_ins * L)
        
    def heat_loss(self, T_s, T_i, T_o):
        """" Return the heat loss (q_rc) for the current timestep
        Arguments:
        T_s    -- insulation surface temperature, in degrees C
        T_i    -- temperature of water (or air) inside the pipe, in degrees C
        T_o    -- temperature outside the pipe, in degrees C
        """
        # TODO calculate T_s (e.g. following guidance in ASHRAE, 2021) and use the value 
        #     from the previous timestep rather than having it as an input
        
        # Convert the temperature inputs from degrees C to Kelvin
        T_s_K = units.Celcius2Kelvin(T_s) 
        T_i_K = units.Celcius2Kelvin(T_i)
        T_o_K = units.Celcius2Kelvin(T_o)
        
        # Calculate the radiation heat transfer coefficient (h_r)
        h_r = self.__E * units.stefan_boltzmann_constant * (T_s_K**2.0 + T_o_K**2.0) * (T_s_K + T_o_K)
        
        # Calculate surface radiative resistance (Rr)
        Rr = 1.0 / (h_r * pi * self.__D_ins * self.__L)
        
        # Calculate total surface resistance (R4)
        R4 = (Rr * self.__Rc) / (Rr + self.__Rc)
        
        # Calculate total thermal resistance (R_tot)
        R_tot = self.__R1 + self.__R2 + self.__R3 + R4
        
        # Calculate the heat loss for the current timestep, in W
        q_rc = (T_i_K - T_o_K) / (R_tot)
        
        return q_rc
        
        
    def temperature_drop(self, T_s, T_i, T_o):
        """
        Calculates by how much the temperature of water in a full pipe will fall
        over the timestep.
        
                Arguments:
        T_s    -- insulation surface temperature, in degrees C
        T_i    -- temperature of water (or air) inside the pipe, in degrees C
        T_o    -- temperature outside the pipe, in degrees C
        """

        heat_loss_kWh = (units.seconds_per_hour * heat_loss(T_s, T_i, T_o)) / units.W_per_kW # heat loss for the one hour timestep in kWh
        
        litres = pi * (self.__D_i/2) * (self.__D_i/2) * self.__L * units.litres_per_cubic_metre

        temp_drop = max((heat_loss_kWh * units.J_per_kWh)/ (material_properties.WATER.volumetric_heat_capacity() * litres), T_i-T_o)  # Q = C m ∆t
        # temperature cannot drop below outside temperature
    
        return(temp_drop) # returns DegC
        
        
    def cool_down_loss(self, T_s, T_i, T_o):
        """
        Calculates the total heat loss from a full pipe from demand temp to ambient
        temp in kWh
         
                Arguments:
        T_s    -- insulation surface temperature, in degrees C
        T_i    -- temperature of water (or air) inside the pipe, in degrees C
        T_o    -- temperature outside the pipe, in degrees C
        """

        litres = pi * (self.__D_i/2) * (self.__D_i/2) * self.__L * units.litres_per_cubic_metre

        cool_down_loss = (material_properties.WATER.volumetric_energy_content_kWh_per_litre(T_i, T_o) * litres)
        
        return(cool_down_loss) # returns kWh


    def water_demand_to_kWh(self, litres_demand, demand_temp, cold_temp):
        """
        Calculates the kWh energy content of the hot water demand. 
         
                Arguments:
        litres_demand  -- hot water demand in litres
        demand_temp    -- temperature of hot water inside the pipe, in degrees C
        cold_temp      -- temperature outside the pipe, in degrees C
        """
        
        kWh_demand = (material_properties.WATER.volumetric_energy_content_kWh_per_litre(demand_temp, cold_temp) * litres_demand)
        
        return(kWh_demand)
