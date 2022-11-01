#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides objects to represent ventilation elements.
"""

# Standard library imports
import sys
from enum import IntEnum

# Local imports
from core.units import seconds_per_hour, litres_per_cubic_metre, W_per_kW

# Define constants
p_a = 1.204 # Air density at 20 degrees C, in kg/m^3 , BS EN ISO 52016-1:2017, Section 6.3.6
c_a = 1006.0 # Specific heat of air at constant pressure, in J/(kg K), BS EN ISO 52016-1:2017, Section 6.3.6


def air_change_rate_to_flow_rate(air_change_rate, zone_volume):
    """ Convert infiltration rate from ach to m^3/s """
    return air_change_rate * zone_volume / seconds_per_hour


class VentilationElementInfiltration:
    """ A class to represent infiltration ventilation elements """

    # Infiltration rates for openings (m3 per hour)
    # TODO Reference these
    __INF_RATE_CHIMNEY_OPEN = 80.0
    __INF_RATE_CHIMNEY_BLOCKED = 20.0
    __INF_RATE_FLUE_OPEN = 20.0
    __INF_RATE_FLUE_SOLID_FUEL_BOILER = 20.0
    __INF_RATE_FLUE_OTHER_HEATER = 35.0
    __INF_RATE_FIRE_CLOSED = 10.0
    __INF_RATE_FIRE_GAS = 40.0
    __INF_RATE_EXTRACT_FAN = 10.0
    __INF_RATE_PASSIVE_STACK_VENT = 10.0

    class ShelterType(IntEnum):
        # Values match column indices in table of divisors
        VERY_SHELTERED = 0
        SHELTERED = 1
        NORMAL = 2
        EXPOSED = 3

        @classmethod
        def from_string(cls, strval):
            if strval == "very sheltered":
                return cls.VERY_SHELTERED
            elif strval == "sheltered":
                return cls.SHELTERED
            elif strval == "normal":
                return cls.NORMAL
            elif strval == "exposed":
                return cls.EXPOSED
            else:
                sys.exit('ShelterType (' + str(strval) + ') not valid.')
                # TODO Exit just the current case instead of whole program entirely?

    class DwellingType(IntEnum):
        # Values match row indices in table of divisors
        HOUSE_1_STOREY = 0
        HOUSE_2_STOREY = 1
        FLAT_STOREY_1_TO_5 = 2
        FLAT_STOREY_6_TO_10 = 3
        FLAT_STOREY_11_PLUS = 4

        @classmethod
        def from_string(cls, strval_type, strval_storey):
            if strval_type == "house":
                if strval_storey == 1:
                    return cls.HOUSE_1_STOREY
                elif strval_storey >= 2:
                    return cls.HOUSE_2_STOREY
            elif strval_type == "flat":
                if 0 < strval_storey <= 5:
                    return cls.FLAT_STOREY_1_TO_5
                elif 5 < strval_storey <= 10:
                    return cls.FLAT_STOREY_6_TO_10
                elif strval_storey > 10:
                    return cls.FLAT_STOREY_11_PLUS
            else:
                sys.exit('DwellingType (' + str(strval_type) + ') not valid.')
                # TODO Exit just the current case instead of whole program entirely?

    # Divisors to convert air change rate at 50 Pa to infiltration
    # Values for "Normal" House 1-2 storey and Flat storeys 1-10 are from CIBSE Guide A
    # Values for "Exposed" based on CIBSE Guida A: "on severely exposed sites, a
    # 50% increase to the tabulated values should be allowed.
    # Values for "Sheltered" based on CIBSE Guide A: "on sheltered sites, the
    # infiltration rate may be reduced by 30%".
    # Values for "Very sheltered" assume a reduction of 50%.
    # Values for Flat storeys 11+ are extrapolated based on profiles of wind
    # speed vs. height, assuming storey height of 3.5 metres.
    __DIVISORS = [
        # Very sheltered | Sheltered | Normal | Exposed |
        [           39.2 ,      29.4 ,   20.6 ,    13.1 ], # House 1-storey
        [           32.5 ,      24.3 ,   17.0 ,    10.9 ], # House 2-storey
        [           33.6 ,      25.2 ,   17.3 ,    11.2 ], # Flat storeys 1-5
        [           29.4 ,      22.0 ,   15.1 ,     9.8 ], # Flat storeys 6-10
        [           28.5 ,      19.4 ,   13.4 ,     9.0 ], # Flat storeys 11+
        ]

    def __init__(self,
            storey,
            shelter,
            build_type,
            pressure_test_result_ach,
            pressure_test_type,
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
        pressure_test_result_ach -- result of pressure test, in ach
        pressure_test_type    -- measurement used for pressure test i.e. based on air change rate value at 50 Pa (50Pa) or 4 Pa (4Pa)
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
        sheltered_sides = int(sheltered_sides)

        # Calculate the infiltration rate from openings (chimneys, flues, fans, PSVs, etc.)
        # in air-changes per hour
        self.__inf_openings \
            = ( (open_chimneys    * self.__INF_RATE_CHIMNEY_OPEN) \
              + (open_flues       * self.__INF_RATE_FLUE_OPEN) \
              + (closed_fire      * self.__INF_RATE_FIRE_CLOSED) \
              + (flues_d          * self.__INF_RATE_FLUE_SOLID_FUEL_BOILER) \
              + (flues_e          * self.__INF_RATE_FLUE_OTHER_HEATER) \
              + (blocked_chimneys * self.__INF_RATE_CHIMNEY_BLOCKED) \
              + (extract_fans     * self.__INF_RATE_EXTRACT_FAN) \
              + (passive_vents    * self.__INF_RATE_PASSIVE_STACK_VENT)\
              + (gas_fires        * self.__INF_RATE_FIRE_GAS)
              ) \
            / volume

        # Choose correct divisor to apply to Q50:
        # TODO add options for bungalow and maisonette
        def init_divisor():
            dwelling_type = self.DwellingType.from_string(build_type, storey)
            shelter_type = self.ShelterType.from_string(shelter)
            return self.__DIVISORS[dwelling_type][shelter_type]

        self.__divisor = init_divisor()

        # Calculate shelter factor
        def init_shelter_factor():
            # TODO check shelter correction - option 1
            if sheltered_sides < 0 or sheltered_sides > 4:
                sys.exit( ' Number of sheltered sides not recognised.' )
                # TODO Exit just the current case instead of whole program entirely?
            # Calculate shelter factor based on formula from SAP 10.2
            # TODO Reference the origin of this formula.
            return 1.0 - (0.075 * sheltered_sides)

        self.__shelter_factor = init_shelter_factor()

        # Calculate infiltration rate
        def init_infiltration():
            if pressure_test_type == "4Pa":
                # If test results are at 4 Pa, convert to equivalent 50 Pa result
                # before applying divisor.
                # SAP 10 Technical Paper S10TP-19 "Use of low pressure pulse
                # test data in SAP" gives the relationship between air
                # permeability measured at 50 Pa and 4 Pa. The equation below is
                # based on this but has been converted to work with test results
                # expressed in ach rather than m3/m2/h.
                test_result_ach_50Pa \
                    = 5.254 * (pressure_test_result_ach**0.9241) * ((env_area / volume)**(1-0.9241))
            elif pressure_test_type == "50Pa":
                test_result_ach_50Pa = pressure_test_result_ach
            else:
                sys.exit( ' Pressure test result type not recognised.' )
                # TODO Exit just the current case instead of whole program entirely?

            return (test_result_ach_50Pa / self.__divisor) \
                 + (self.__inf_openings * self.__shelter_factor)

        self.__infiltration = init_infiltration()

    def h_ve(self, zone_volume):
        """ Calculate the heat transfer coefficient (h_ve), in W/K,
        according to ISO 52016-1:2017, Section 6.5.10.1
        
        Arguments:
        zone_volume -- volume of zone, in m3
        """

        # Apply wind speed correction factor
        wind_factor = self.__external_conditions.wind_speed() / 4.0 # 4.0 m/s represents the average wind speed
        inf_rate = self.__infiltration * wind_factor

        # Convert infiltration rate from ach to m^3/s
        q_v = inf_rate * zone_volume / seconds_per_hour

        # Calculate h_ve according to BS EN ISO 52016-1:2017 section 6.5.10 equation 61
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


class MechnicalVentilationHeatRecovery:
    """ A class to represent ventilation with heat recovery (MVHR) elements """

    def __init__(
            self,
            required_air_change_rate,
            specific_fan_power,
            efficiency_hr,
            energy_supply_conn,
            ext_con,
            simulation_time,
            ):
        """ Construct a MechnicalVentilationHeatRecovery object

        Arguments:
        required_air_change_rate -- ach (l/s)m-3 calculated according to Part F
        efficiency_hr -- heat recovery efficiency (0 to 1) allowing for in-use factor
        ext_con -- reference to ExternalConditions object
        """
        self.__air_change_rate = required_air_change_rate
        self.__sfp = specific_fan_power
        self.__efficiency = efficiency_hr
        self.__energy_supply_conn = energy_supply_conn
        self.__external_conditions = ext_con
        self.__simtime = simulation_time

    def h_ve(self, zone_volume):
        """ Calculate the heat transfer coefficient (h_ve), in W/K,
        according to ISO 52016-1:2017, Section 6.5.10.1

        Arguments:
        zone_volume -- volume of zone, in m3
        """

        q_v = air_change_rate_to_flow_rate(self.__air_change_rate, zone_volume)

        # Calculate effective flow rate of external air
        # NOTE: Technically, the MVHR system supplies air at a higher temperature
        # than the outside air. However, it is simpler to adjust the heat
        # transfer coefficient h_ve to account for the heat recovery effect
        # using an "equivalent" or "effective" flow rate of external air.
        q_v_effective = q_v * (1 - self.__efficiency)

        # Calculate h_ve according to BS EN ISO 52016-1:2017 section 6.5.10 equation 61
        h_ve = p_a * c_a * q_v_effective
        return h_ve
        # TODO b_ztu needs to be applied in the case if ventilation element
        #      is adjacent to a thermally unconditioned zone.

    def fans(self, zone_volume):
        """ Calculate gains and energy use due to fans """
        # Calculate energy use by fans (only fans on intake/supply side
        # contribute to internal gains - assume that this is half of the fan
        # power)
        q_v = air_change_rate_to_flow_rate(self.__air_change_rate, zone_volume)
        fan_power_W = self.__sfp * (q_v * litres_per_cubic_metre)
        fan_energy_use_kWh = (fan_power_W  / W_per_kW) * self.__simtime.timestep()

        self.__energy_supply_conn.demand_energy(fan_energy_use_kWh)
        return fan_energy_use_kWh / 2.0

    def temp_supply(self):
        """ Calculate the supply temperature of the air flow element
        according to ISO 52016-1:2017, Section 6.5.10.2 """
        # NOTE: Technically, the MVHR system supplies air at a higher temperature
        # than the outside air, i.e.:
        #     temp_supply = self.__efficiency * temp_int_air \
        #                 + (1 - self.__efficiency) * self.__external_conditions.air_temp()
        # However, calculating this requires the internal air temperature, which
        # has not been calculated yet. Calculating this properly would require
        # the equation above to be added to the heat balance solver. Therefore,
        # it is simpler to adjust the heat transfer coefficient h_ve to account
        # for the heat recovery effect using an "equivalent" flow rate of
        # external air.
        return self.__external_conditions.air_temp()
        
    def efficiency(self):
        return self.__efficiency

class WholeHouseExtractVentilation:
    """ A class to represent whole house extract ventilation elements """

    def __init__(
            self,
            required_air_change_rate,
            specific_fan_power,
            energy_supply_conn,
            ext_con,
            simulation_time
            ):
        """ Construct a WholeHouseExtractVentilation object

        Arguments:
        required_air_change_rate -- in ach
        specific_fan_power -- in W / (litre / second), inclusive of any in-use factors
        energy_supply_conn -- reference to EnergySupplyConnection object
        ext_con -- reference to ExternalConditions object
        """

        self.__air_change_rate = required_air_change_rate
        self.__sfp = specific_fan_power
        self.__energy_supply_conn = energy_supply_conn
        self.__external_conditions = ext_con
        self.__simtime = simulation_time

    def h_ve(self, zone_volume):
        """ Calculate the heat transfer coefficient (h_ve), in W/K,
        according to ISO 52016-1:2017, Section 6.5.10.1

        Arguments:
        zone_volume -- volume of zone, in m3
        inf_rate -- air change rate of ventilation system
        """

        q_v = air_change_rate_to_flow_rate(self.__air_change_rate, zone_volume)

        # Calculate h_ve according to BS EN ISO 52016-1:2017 section 6.5.10 equation 61
        h_ve = p_a * c_a * q_v
        return h_ve
        # TODO b_ztu needs to be applied in the case if ventilation element
        #      is adjacent to a thermally unconditioned zone.

    def fans(self, zone_volume):
        """ Calculate gains and energy use due to fans """
        # Calculate energy use by fans (does not contribute to internal gains as
        # this is extract-only ventilation)
        q_v = air_change_rate_to_flow_rate(self.__air_change_rate, zone_volume)
        fan_power_W = self.__sfp * (q_v * litres_per_cubic_metre)
        fan_energy_use_kWh = (fan_power_W  / W_per_kW) * self.__simtime.timestep()

        self.__energy_supply_conn.demand_energy(fan_energy_use_kWh)
        return 0.0

    def temp_supply(self):
        """ Calculate the supply temperature of the air flow element
        according to ISO 52016-1:2017, Section 6.5.10.2 """
        return self.__external_conditions.air_temp()
        # TODO For now, this only handles ventilation elements to the outdoor
        #      environment, not e.g. elements to adjacent zones.

