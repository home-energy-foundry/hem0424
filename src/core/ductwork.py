#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides object(s) to represent pipework
"""

# Standard library imports
from math import pi, log

# Local imports
import core.units as units

class ductwork:
    """ An object to represent ductwork for mechanical ventilation with heat recovery 
    (MVHR), assuming steady state heat transfer in a hollow cyclinder (duct)
    with radial heat flow. Method taken from 2021 ASHRAE Handbook, Section 4.4.2 """
        
    def __init__(self, D_i, D_o, L, k_d, k_i, t_i, E, duct_type, MVHR_location):
        """Construct a ductwork object
        
        Arguments:
        h_i              -- heat transfer coefficient inside the duct, in W / m^2 K
        D_i              -- internal diameter of the duct, in m
        D_o              -- external diameter of the duct, in m
        L                -- length of duct, in m
        k_d              -- thermal conductivity of the duct, in W / m K
        k_i              -- thermal conductivity of the insulation, in W / m K
        t_i              -- thickness of the pipe insulation, in m
        h_0              -- heat transfer coefficient at the outer surface, in W / m^2 K
        E                -- emissivity of the outer surface
        duct_type         -- type of duct (extract, supply, exhaust, or intake)
        MVHR_location      -- location of the MVHR unit (inside the dwelling or outside) 
        """
        self.__E = E
        self.__L = L
        self.__D_i = D_i
        self.__duct_type = duct_type
        self.__MVHR_location = MVHR_location 

        """ Calculate the diameter of the pipe including the insulation (D_ins), in m"""
        self.__D_ins = D_o + (2.0 * t_i)

        """ Calculate the thermal resistance (R) values, in K/W """
        """ Calculate thermal resistance of the pipe (R2) """
        self.__R2 = log(D_o / D_i) / (2.0 * pi * k_d * L)

        """ Calculate thermal resistance of the insulation (R3) """
        self.__R3 = log(self.__D_ins / D_o) / (2.0 * pi * k_i * L)

    def heat_loss(self, T_d, T_i, T_o, h_0, h_i):
        """" Return the heat loss (q_rc) for the current timestep

        Arguments:
        T_d    -- duct wall surface temperature, in degrees C
        T_i    -- temperature of air inside the duct, in degrees C 
        T_o    -- temperature outside the pipe, in degrees C
        h_0    -- heat transfer coefficient at the outer surface, in W / m^2 K
        h_i       -- heat transfer coefficient inside the duct, in W / m^2 K """
        
        # Convert the temperature inputs from degrees C to Kelvin
        T_d_K = units.Celcius2Kelvin(T_d) 
        T_i_K = units.Celcius2Kelvin(T_i)
        T_o_K = units.Celcius2Kelvin(T_o)
        
        """ Calculate R1 and R4 using the same equations, taking into account heat transfer by 
        convection and radiation """
        # TODO h_c may need to be calculated e.g. PHPP rather than an input - takes into account air flow rate? (for h_i and h_0)
        # h_c = 10.45 - v + (10 * (v ** 0.5)), where v is the relative speed between object surface and air, in m/s
        # or follow PHPP e.g.:
        wms = (4.0 * air_flow) / ((w ** 2) * pi * 3600)
        Re = (wms * w) * 0.0000138
        N = 0.023 * (Re **0.8) * (0.71 ** 0.4)
        h_c = N * 24.915 * 0.001 / w
        # w is the width of air duct, would this vary depending on h_i and h_0 e.g. include insultion thickness for h_0
        
        # Calculate the radiation heat transfer coefficient (h_r) for R1 and R4
        h_r_1 = self.__E * units.stefan_boltzmann_constant * (T_d_K**2.0 + T_i_K**2.0) * (T_d_K + T_i_K)
        h_r_4 = self.__E * units.stefan_boltzmann_constant * (T_s_K**2.0 + T_o_K**2.0) * (T_s_K + T_o_K)
        
        # Calculate surface radiative resistance (Rr) for R1 and R4
        Rr_1 = 1.0 / (h_r_1 * pi * self.__D_i * self.__L)
        Rr_4 = 1.0 / (h_r_4 * pi * self.__D_ins * self.__L)
        
        # Calculate surface convective resistance (Rc) for R1 and R4
        Rc_1 = 1.0 / (h_i * pi * self.__D_i * self.__L)
        Rc_4 = 1.0 / (h_0 * pi * self.__D_ins * self.__L)
        
        # Calculate thermal resistance of the air in the duct (R1) and the air outside the duct (R4)
        R1 = (Rr_1 * Rc_1) / (Rr_1 + Rc_1)
        R4 = (Rr_4 * Rc_4) / (Rr_4 + Rc_4)

        # Calculate the total thermal resistance (R_tot)
        R_tot = R1 + self.__R2 + self.__R3 + R4
        
        # Calculate the heat loss, depending on location of MVHR unit and duct function, in W
        # TODO if unit is inside need to add losses to space heating, add to internal gains
        # TODO calculate change in air temp inside the extract and intake ducts
        if MVHR_location == 'outside':
            if self.__duct_type == 'supply' or self.__duct_type == 'extract':
                q = (T_i_K - T_o_K) / (R_tot)
                T_i_K = 
            elif self.__duct_type == 'exhaust' or self.__duct_type == 'intake':
                q = 0.0
            else:
                sys.exit('Duct type not valid.')
               # TODO Exit just the current case instead of whole program entirely?
        elif MVHR_location == 'inside':
            if self.__duct_type == 'exhaust' or self.__duct_type == 'intake':
                q = (T_i_K - T_o_K) / (R_tot)
                # This will be a negative heat loss i.e. heat gain into duct
            elif self.__duct_type == 'supply' or self.__duct_type == 'extract':
                q = 0.0
            else:
                sys.exit('Duct type not valid.')
               # TODO Exit just the current case instead of whole program entirely?
        else:
            sys.exit('MVHR location not valid.')
            # TODO Exit just the current case instead of whole program entirely?
        return q

