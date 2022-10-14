#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides object(s) to represent pipework
"""

# Standard library imports
from math import pi, log
import sys

# Local imports
import core.units as units
import core.material_properties as material_properties


class Pipework:
    """ An object to represent steady state heat transfer in a hollow cyclinder (pipe)
    with radial heat flow. Method taken from 2021 ASHRAE Handbook, Section 4.4.2 """

    def __init__(self, D_i, D_o, L, k_i, t_i, reflective, contents):
        """Construct a Pipework object
        
        Arguments:
        D_i         -- internal diameter of the pipe, in m
        D_o         -- external diameter of the pipe, in m
        L           -- length of pipe, in m
        k_i         -- thermal conductivity of the insulation, in W / m K
        t_i         -- thickness of the pipe insulation, in m
        reflective  -- whether the surface is reflective or not (boolean input)
        contents    -- whether the pipe is carrying air or water
        """
        self.__L = L
        self.__D_i = D_i

        """ Set default values for h_i, heat transfer coefficient inside the pipe, in W / m^2 K """
        if contents == 'air':
            h_i = 15.5 # CIBSE Guide C, Table 3.25, air flow rate approx 3 m/s
        elif contents == 'water':
            h_i = 1500.0 # CIBSE Guide C, Table 3.32
        else:
            sys.exit('Contents of pipe not valid.')
                # TODO Exit just the current case instead of whole program entirely?

        """ Set default values for h_0, heat transfer coefficient at the outer surface, in W / m^2 K """
        if reflective == 'true':
            h_0 = 5.7 # low emissivity reflective surface, CIBSE Guide C, Table 3.25
        elif reflective == 'false':
            h_0 = 10.0 # high emissivity non-reflective surface, CIBSE Guide C, Table 3.25
        else:
            sys.exit('Surface reflectivity input not valid.')
                # TODO Exit just the current case instead of whole program entirely?

        """ Calculate the diameter of the pipe including the insulation (D_ins), in m"""
        self.__D_ins = D_o + (2.0 * t_i)

        """ Calculate the interior linear surface resistance, in Km/W  """
        self.__R1 = 1.0 / (h_i * pi * D_i)

        """ Calculate the insulation linear thermal resistance, in Km/W  """
        self.__R2 = log(self.__D_ins / D_i) / (2.0 * pi * k_i)

        """ Calculate the exterior linear surface resistance, in Km/W  """
        self.__R3 = 1.0 / (h_0 * pi * self.__D_ins)

    def heat_loss(self, T_i, T_o):
        """" Return the heat loss (q) from the pipe for the current timestep

        Arguments:
        T_i    -- temperature of water (or air) inside the pipe, in degrees C
        T_o    -- temperature outside the pipe, in degrees C
        """
        # Calculate total thermal resistance (R_tot)
        R_tot = self.__R1 + self.__R2 + self.__R3

        # Calculate the heat loss for the current timestep, in W
        q = (T_i - T_o) / (R_tot) * self.__L

        return q

    def temperature_drop(self, T_i, T_o):
        """ Calculates by how much the temperature of water in a full pipe will fall
        over the timestep.

        Arguments:
        T_i    -- temperature of water (or air) inside the pipe, in degrees C
        T_o    -- temperature outside the pipe, in degrees C
        """
        heat_loss_kWh = (units.seconds_per_hour * self.heat_loss(T_i, T_o)) / units.W_per_kW # heat loss for the one hour timestep in kWh

        litres = pi * (self.__D_i/2) * (self.__D_i/2) * self.__L * units.litres_per_cubic_metre

        temp_drop = min((heat_loss_kWh * units.J_per_kWh)/ (material_properties.WATER.volumetric_heat_capacity() * litres), T_i-T_o)  # Q = C m ∆t
        # temperature cannot drop below outside temperature

        return(temp_drop) # returns DegC

    def cool_down_loss(self, T_i, T_o):
        """Calculates the total heat loss from a full pipe from demand temp to ambient
        temp in kWh

        Arguments:
        T_i    -- temperature of water (or air) inside the pipe, in degrees C
        T_o    -- temperature outside the pipe, in degrees C
        """
        litres = pi * (self.__D_i/2) * (self.__D_i/2) * self.__L * units.litres_per_cubic_metre

        cool_down_loss = (material_properties.WATER.volumetric_energy_content_kWh_per_litre(T_i, T_o) * litres)

        return(cool_down_loss) # returns kWh

