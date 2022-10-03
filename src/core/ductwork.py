#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides object(s) to represent ductwork
"""

# Standard library imports
import sys
from math import pi, log

# Local imports
import core.units as units

class Ductwork:
    """ An object to represent ductwork for mechanical ventilation with heat recovery 
    (MVHR), assuming steady state heat transfer in a hollow cyclinder (duct)
    with radial heat flow. Method taken from 2021 ASHRAE Handbook, Section 4.4.2 """

    def __init__(self, D_i, D_o, L, k_d, k_i, t_i, h_0, h_i, E, duct_type, MVHR_location):
        """Construct a ductwork object

        Arguments:
        D_i              -- internal diameter of the duct, in m
        D_o              -- external diameter of the duct, in m
        L                -- length of duct, in m
        k_d              -- thermal conductivity of the duct, in W / m K
        k_i              -- thermal conductivity of the insulation, in W / m K
        t_i              -- thickness of the duct insulation, in m
        h_0              -- heat transfer coefficient at the outer surface, in W / m^2 K
        h_i              -- heat transfer coefficient inside the duct, in W / m^2 K
        E                -- emissivity of the outer surface
        duct_type        -- type of duct (extract, supply, exhaust, or intake)
        MVHR_location    -- location of the MVHR unit (inside or outside the thermal envelope) 
        """
        # TODO calculate h_i and h_0 instead of having as inputs

        self.__E = E
        self.__L = L
        self.__D_i = D_i
        self.__D_o = D_o
        self.__h_0 = h_0
        self.__duct_type = duct_type
        self.__MVHR_location = MVHR_location 

        """ Calculate the diameter of the pipe including the insulation (D_ins), in m"""
        self.__D_ins = D_o + 2.0 * t_i

        """ Calculate the thermal resistance (R) values, in K/W """
        """ Calculate thermal resistance of the air in the duct (R1) """
        self.__R1 = 1.0 / (h_i * pi * D_i * L)

        """ Calculate thermal resistance of the duct (R2) """
        self.__R2 = log(D_o / D_i) / (2.0 * pi * k_d * L)

        """ Calculate thermal resistance of the insulation (R3) """
        self.__R3 = log(self.__D_ins / D_o) / (2.0 * pi * k_i * L)

    def heat_loss(self, T_d, T_i, T_o):
        """" Return the heat loss (q) for air inside the duct for the current timestep

        Arguments:
        T_d    -- insulation surface temperature, in degrees C
        T_i    -- temperature of air inside the duct, in degrees C 
        T_o    -- temperature of air outside the duct, in degrees C """

        # Convert the temperature inputs from degrees C to Kelvin
        T_d_K = units.Celcius2Kelvin(T_d) 
        T_i_K = units.Celcius2Kelvin(T_i)
        T_o_K = units.Celcius2Kelvin(T_o)

        # Calculate the radiation heat transfer coefficient (h_r) for R4
        h_r_4 = self.__E * units.stefan_boltzmann_constant * (T_d_K**2.0 + T_o_K**2.0) * (T_d_K + T_o_K)
        
        # Calculate surface radiative resistance (Rr) for R4
        Rr_4 = 1.0 / (h_r_4 * pi * self.__D_ins * self.__L)
        
        # Calculate surface convective resistance (Rc) for R4
        Rc_4 = 1.0 / (self.__h_0 * pi * self.__D_ins * self.__L)
        
        # Calculate thermal resistance of the air outside the duct (R4)
        R4 = (Rr_4 * Rc_4) / (Rr_4 + Rc_4)

        # Calculate the total thermal resistance (R_tot)
        R_tot = self.__R1 + self.__R2 + self.__R3 + R4
        
        # Calculate the heat loss, depending on location of MVHR unit and duct type, in W
        # TODO add losses to space heating for when the MVHR unit is inside the dwelling
        # TODO calculate change in air temperature inside the extract and intake ducts
        if self.__MVHR_location == 'outside':
            if self.__duct_type == 'supply' or self.__duct_type == 'extract':
                q = (T_i_K - T_o_K) / (R_tot)
                # Air inside the pipe loses heat, external environment gains heat
            elif self.__duct_type == 'exhaust' or self.__duct_type == 'intake':
                q = 0.0
            else:
                sys.exit('Duct type not valid.')
                # TODO Exit just the current case instead of whole program entirely?
        elif self.__MVHR_location == 'inside':
            if self.__duct_type == 'exhaust' or self.__duct_type == 'intake':
                q = (T_i_K - T_o_K) / (R_tot)
                # This will be a negative heat loss i.e. air inside the duct gains heat, dwelling loses heat
            elif self.__duct_type == 'supply' or self.__duct_type == 'extract':
                q = 0.0
            else:
                sys.exit('Duct type not valid.')
                # TODO Exit just the current case instead of whole program entirely?
        else:
            sys.exit('MVHR location not valid.')
            # TODO Exit just the current case instead of whole program entirely?
        return q

