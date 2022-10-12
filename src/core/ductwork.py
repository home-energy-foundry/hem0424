#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides object(s) to represent ductwork
"""

# Standard library imports
import sys
from math import pi, log

class Ductwork:
    """ An object to represent ductwork for mechanical ventilation with heat recovery 
    (MVHR), assuming steady state heat transfer in a hollow cyclinder (duct)
    with radial heat flow. """

    def __init__(self, D_i, D_o, L, k_i, t_i, reflective, duct_type, MVHR_location):
        """Construct a ductwork object
        Arguments:
        D_i              -- internal diameter of the duct, in m
        D_o              -- external diameter of the duct, in m
        L                -- length of duct, in m
        k_i              -- thermal conductivity of the insulation, in W / m K
        t_i              -- thickness of the duct insulation, in m
        reflective       -- whether the outer surface of the duct is reflective (true) or not (false) (boolean input)
        duct_type        -- type of duct (extract, supply, exhaust, or intake)
        MVHR_location    -- location of the MVHR unit (inside or outside the thermal envelope) 
        """
        self.__L = L
        self.__duct_type = duct_type
        self.__MVHR_location = MVHR_location 

        """ Set default value for h_i, heat transfer coefficient inside the duct, in W / m^2 K """
        h_i = 15.5 # CIBSE Guide C, Table 3.25, air flow rate approx 3 m/s

        """ Set default values for h_0, heat transfer coefficient at the outer surface, in W / m^2 K """
        if reflective == 'true':
            h_0 = 5.7
            # low emissivity reflective surface, CIBSE Guide C, Table 3.25
        elif reflective == 'false':
            h_0 = 10.0
            # high emissivity non-reflective surface, CIBSE Guide C, Table 3.25
        else:
            sys.exit('Surface reflectivity input not valid.')
                # TODO Exit just the current case instead of whole program entirely?

        """ Calculate the diameter of the duct including the insulation (D_ins), in m"""
        self.__D_ins = D_o + (2.0 * t_i)

        """ Calculate the interior linear surface resistance, in Km/W  """
        self.__R1 = 1.0 / (h_i * pi * D_i)

        """ Calculate the insulation linear thermal resistance, in Km/W  """
        self.__R2 = log(self.__D_ins / D_i) / (2.0 * pi * k_i)

        """ Calculate the exterior linear surface resistance, in Km/W  """
        self.__R3 = 1.0 / (h_0 * pi * self.__D_ins)

    def heat_loss(self, T_i, T_o):
        """" Return the heat loss (q) for air inside the duct for the current timestep
        Arguments:
        T_i    -- temperature of air inside the duct, in degrees C
        T_o    -- temperature outside the duct, in degrees C
        """
        # Calculate total thermal resistance (R_tot)
        R_tot = self.__R1 + self.__R2 + self.__R3

        # Calculate the heat loss, depending on location of MVHR unit and duct type, in W
        # TODO add losses to space heating for when the MVHR unit is inside the dwelling
        # TODO calculate change in air temperature inside the extract and intake ducts
        if self.__MVHR_location == 'outside':
            if self.__duct_type == 'supply' or self.__duct_type == 'extract':
                q = (T_i - T_o) / (R_tot) * self.__L
                # Air inside the pipe loses heat, external environment gains heat
            elif self.__duct_type == 'exhaust' or self.__duct_type == 'intake':
                q = 0.0
            else:
                sys.exit('Duct type not valid.')
                # TODO Exit just the current case instead of whole program entirely?
        elif self.__MVHR_location == 'inside':
            if self.__duct_type == 'exhaust' or self.__duct_type == 'intake':
                q = (T_i - T_o) / (R_tot) * self.__L
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

