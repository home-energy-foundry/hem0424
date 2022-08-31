#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides objects to represent ventilation elements.
"""

# Standard library imports
import sys

# Local imports
from core.units import seconds_per_hour

class VentilationElementInfiltration:
    """ A class to represent infiltration ventilation elements """
    def __init__(self,
            storey,
            shelter,
            build_type,
            test_result,
            test_type,
            env_area,
            volume,
            sheltered_sides,
            open_chimneys,
            open_flues,
            closed_fire,
            flues_d,
            flues_e,
            blocked_chimneys,
            extract_fans,
            passive_vents,
            gas_fires,
            ext_cond
            ):
        """ Construct a VentilationElementInfiltration object """

        """Arguments:
        storey                -- for flats, storey number within building / for non-flats, total number of storeys in building
        shelter               -- exposure level of the building i.e. very sheltered, sheltered, normal, or exposed
        build_type            -- type of building e.g. house, flat, etc.
        test_result           -- result of pressure test, in ach
        test_type             -- measurement used for pressure test i.e. based on air permeability value at 50 Pa (Q50) or 4 Pa (Q4)
        env_area              -- total envelope area of the building including party walls and floors, in m^2
        volume                -- total volume of dwelling, m^3
        sheltered_sides       -- number of sides of the building which are sheltered
        open_chimneys         -- number of open chimneys
        open_flues            -- number of open flues
        closed_fire           -- number of chimneys / flues attched to closed fire
        flues_d               -- number of flues attached to soild fuel boiler
        flues_e               -- number of flues attached to other heater
        blocked_chimneys      -- number of blocked chimneys
        extract_fans          -- number of intermittent extract fans
        passive_vents         -- number of passive vents
        gas_fires             -- number of flueless gas fires
        ext_cond              -- reference to ExternalConditions object
        """

        self.__external_conditions = ext_cond
        self.__volume = volume

        # Calculate the infiltration rate from openings (chimneys, flues, fans, PSVs, etc.)
        def init_inf_openings():
            inf_openings= ((open_chimneys * 80.0) + (open_flues * 20.0) + (closed_fire * 10.0) + (flues_d * 20) \
                           + (flues_e * 35.0) + (blocked_chimneys * 20.0) + (extract_fans * 10.0) \
                           + (passive_vents * 10.0) + (gas_fires * 40.0)) / volume
            return inf_openings

        self.inf_openings = init_inf_openings()

        # Choose correct divisor to apply to Q50:
        # TODO add options for bungalow and maisonette
        def init_divisor():
            if build_type == "house":
                if storey == 1:
                    if shelter == "very sheltered":
                        divisor = 39.2
                    elif shelter == "sheltered":
                        divisor = 29.4
                    elif shelter == "normal":
                        divisor = 20.6
                    elif shelter == "exposed":
                        divisor = 13.1
                if storey >= 2:
                    if shelter == "very sheltered":
                        divisor = 32.5
                    elif shelter == "sheltered":
                        divisor = 24.3
                    elif shelter == "normal":
                        divisor = 17.0
                    elif shelter == "exposed":
                        divisor = 10.9
            elif build_type == "flat":
                if 0 < storey <= 5:
                    if shelter == "very sheltered":
                        divisor = 33.6
                    elif shelter == "sheltered":
                        divisor = 25.2
                    elif shelter == "normal":
                        divisor = 17.3
                    elif shelter == "exposed":
                        divisor = 11.2
                if 5 < storey <= 10:
                    if shelter == "very sheltered":
                        divisor = 29.4
                    elif shelter == "sheltered":
                        divisor = 22.0
                    elif shelter == "normal":
                        divisor = 15.1
                    elif shelter == "exposed":
                        divisor = 9.8
                if storey > 10:
                    if shelter == "very sheltered":
                        divisor = 28.5
                    elif shelter == "sheltered":
                        divisor = 19.4
                    elif shelter == "normal":
                        divisor = 13.4
                    elif shelter == "exposed":
                        divisor = 9.0
            else:
                sys.exit( ' Divisor for building type could not be assigned.' )
                # TODO Exit just the current case instead of whole program entirely?
            return divisor

        self.divisor = init_divisor()

        # Calculate shelter factor
        def init_shelter_factor():
            # TODO check shelter correction - option 1
            if sheltered_sides == 0:
                shelter_factor = 1.0
            elif sheltered_sides == 1:
                shelter_factor = 0.93
            elif sheltered_sides == 2:
                shelter_factor = 0.85
            elif sheltered_sides == 3:
                shelter_factor = 0.78
            elif sheltered_sides == 4:
                shelter_factor = 0.7
            else:
                sys.exit( ' Number of sheltered sides not recognised.' )
                # TODO Exit just the current case instead of whole program entirely?
            return shelter_factor

        self.shelter_factor = init_shelter_factor()

        # Calculate infiltration rate
        def init_infiltration():
            # If test results are Q4, convert to Q50 before applying divisor
            if test_type == "Q4":
                infiltration = ((5.254 * (test_result**0.9241) * ((env_area / volume)**(1-0.9241))) / self.divisor) \
                + (self.inf_openings * self.shelter_factor)
            elif test_type == "Q50":
                infiltration = (test_result / self.divisor) + (self.inf_openings * self.shelter_factor)
            else:
                sys.exit( ' Pressure test result type not recognised.' )
                # TODO Exit just the current case instead of whole program entirely?
            return infiltration

        self.infiltration = init_infiltration()

    def h_ve(self):
        """ Calculate the heat transfer coefficient (h_ve), in W/K,
        according to ISO 52016-1:2017, Section 6.5.10.1 """
        # Define constants
        p_a = 1.204 # Air density at 20 degrees C, in kg/m^3 , BS EN ISO 52016-1:2017, Section 6.3.6
        c_a = 1.006 # Specific heat of air at constant pressure, in J/(kg K), BS EN ISO 52016-1:2017, Section 6.3.6
        
        # Apply wind speed correction factor
        wind_factor = self.__external_conditions.wind_speed() / 4.0 # 4.0 m/s represents the average wind speed
        inf_rate = self.infiltration * wind_factor 
        
        # Convert infiltration rate from ach to m^3/s
        q_v = inf_rate * self.__volume / seconds_per_hour
        
        # Calculate h_ve
        h_ve = p_a * c_a * q_v
        return h_ve
        # TODO b_ztu needs to be applied in the case if ventilation element
        #      is adjacent to a thermally unconditioned zone.

    def temp_supply(self):
        """ Calculate the supply temperature of the air flow element
        according to ISO 52016-1:2017, Section 6.5.10.2 """
        return self.__external_conditions.air_temp()
        # TODO For now, this only handles ventilation elements to the outdoor
        #      environment, not e.g. elements to adjacent zones.

