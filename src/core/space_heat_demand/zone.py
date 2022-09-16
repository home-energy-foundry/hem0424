#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides objects to represent the thermal zones in the building,
and to calculate the temperatures in the zone and associated building elements.
"""

# Third-party imports
import numpy as np

# Local imports
import core.units as units

# Convective fractions
# (default values from BS EN ISO 52016-1:2017, Table B.11)
f_int_c = 0.4 # Can be different for each source of internal gains
f_sol_c = 0.1
f_hc_c  = 0.4 # Listed as separate f_h_c and f_c_c values in standard, but same value for both

# Areal thermal capacity of air and furniture
# (default value from BS EN ISO 52016-1:2017, Table B.17)
k_m_int = 10000 # J / (m2.K)


class Zone:
    """ An object to represent a thermal zone in the building

    Temperatures of nodes in associated building elements are also calculated
    in this object by solving a matrix equation.
    """

    def __init__(self, area, volume, building_elements, thermal_bridging, vent_elements):
        """ Construct a Zone object

        Arguments:
        area              -- useful floor area of the zone, in m2
        volume            -- total volume of the zone, m3
        building_elements -- list of BuildingElement objects (walls, floors, windows etc.)
        thermal_bridging  -- Either:
                             - overall heat transfer coefficient for thermal
                               bridges in the zone, in W / K
                             - list of ThermalBridge objects for this zone
        vent_elements     -- list of ventilation elements (infiltration, mech vent etc.)

        Other variables:
        temp_setpnt_heat  -- temperature setpoint for heating, in deg C
        temp_setpnt_cool  -- temperature setpoint for cooling, in deg C
        area_el_total     -- total area of all building elements associated
                             with this zone, in m2
        c_int             -- internal thermal capacity of the zone, in J / K
        element_positions -- dictionary where key is building element and
                             values are 2-element tuples storing matrix row and
                             column numbers (both same) where the first element
                             of the tuple gives the position of the heat
                             balance eqn (row) and node temperature (column)
                             for the external surface and the second element
                             gives the position for the internal surface.
                             Positions in between will be for the heat balance
                             and temperature of the inside nodes of the
                             building element
        zone_idx          -- matrix row and column number (both same)
                             corresponding to heat balance eqn for zone (row)
                             and temperature of internal air (column)
        no_of_temps       -- number of unknown temperatures (each node in each
                             building element + 1 for internal air) to be
                             solved for
        temp_prev         -- list of temperatures (nodes and internal air) from
                             previous timestep. Positions in list defined in
                             self.__element_positions and self.__zone_idx
        """
        self.__useful_area = area
        self.__volume = volume
        self.__building_elements = building_elements
        self.__vent_elements     = vent_elements

        # If thermal_bridging is a list of ThermalBridge objects, calculate the
        # overall heat transfer coefficient for thermal bridges, otherwise just
        # use the coefficient given
        if isinstance(thermal_bridging, list):
            self.__tb_heat_trans_coeff = 0.0
            for tb in thermal_bridging:
                self.__tb_heat_trans_coeff += tb.heat_trans_coeff()
        else:
            self.__tb_heat_trans_coeff = thermal_bridging

        # TODO Make the temperature setpoints inputs for each timestep
        self.__temp_setpnt_heat = 21.0
        self.__temp_setpnt_cool = 25.0

        self.__area_el_total = sum([eli.area for eli in self.__building_elements])
        self.__c_int = k_m_int * area

        # Calculate:
        # - size of required matrix/vectors (total number of nodes across all
        #   building elements + 1 for internal air)
        # - positions of heat balance eqns and temperatures in matrix for each node
        self.__element_positions = {}
        n = 0
        for eli in self.__building_elements:
            start_idx = n
            n = n + eli.no_of_nodes()
            end_idx = n - 1
            self.__element_positions[eli] = (start_idx, end_idx)
        self.__zone_idx = n
        self.__no_of_temps = n + 1

        # Set starting point for temperatures (self.__temp_prev)
        # TODO Currently hard-coded to 10.0 deg C - make this configurable?
        self.__temp_prev = [10.0] * self.__no_of_temps

    def area(self):
        return self.__useful_area

    def gains_solar(self):
        """sum solar gains for all elements in the zone
        only transparent elements will have solar gains > 0 """

        solar_gains = 0
        for eli in self.__building_elements:
            solar_gains += eli.solar_gains()

        return solar_gains

    def __calc_temperatures(self,
            delta_t,
            temp_prev,
            temp_ext_air,
            gains_internal,
            gains_heat_cool
            ):
        """ Calculate temperatures according to procedure in BS EN ISO 52016-1:2017, section 6.5.6

        Arguments:
        delta_t         -- calculation timestep, in seconds
        temp_prev       -- temperature vector X (see below) from previous timestep
        temp_ext_air    -- temperature of external air, in deg C
        gains_internal  -- total internal heat gains, in W
        gains_heat_cool -- gains from heating (positive) or cooling (negative), in W

        Temperatures are calculated by solving (for X) a matrix equation A.X = B, where:
        A is a matrix of known coefficients
        X is a vector of unknown temperatures
        B is a vector of known quantities

        Each row in vector X is a temperature variable - one for each node in each
        building element plus the internal air temperature in the zone.

        Each row of matrix A contains the coefficients from the heat balance equations
        for each of the nodes in each building element, plus one row for the heat
        balance equation of the zone.

        Each column of matrix A contains the coefficients for a particular temperature
        variable (in same order that they appear in vector X). Where the particular
        temperature does not appear in the equation this coefficient will be zero.

        Note that for this implementation, the columns and rows will be in corresponding
        order, so the heat balance equation for node i will be in row i and the
        coefficients in each row for the temperature at node i will be in column i.

        Each row of vector B contains the other quantities (i.e. those that are not
        coefficients of the temperature variables) from the heat balance equations
        for each of the nodes in each building element, plus one row for the heat
        balance equation of the zone, in the same order that the rows appear in matrix
        A.
        """

        # Init matrix with zeroes
        # Number of rows in matrix = number of columns
        # = total number of nodes + 1 for overall zone heat balance (and internal air temp)
        matrix_a = np.zeros((self.__no_of_temps, self.__no_of_temps))

        # Init vector_b with zeroes (length = number of nodes + 1 for overall zone heat balance)
        vector_b = np.zeros(self.__no_of_temps)

        # One term in eqn 39 is sum from k = 1 to n of (A_elk / A_tot). Given
        # that A_tot is defined as the sum of A_elk from k = 1 to n, this term
        # will always evaluate to 1.
        # TODO Check this is correct. It seems a bit pointless if it is but we
        #      should probably retain it as an explicit term anyway to match
        #      the standard.
        sum_area_frac = 1.0

        # Node heat balances - loop through building elements and their nodes:
        # - Construct row of matrix_a for each node energy balance eqn
        # - Calculate RHS of node energy balance eqn and add to vector_b
        for eli in self.__building_elements:
            # External surface node (eqn 41)
            # Get position (row == column) in matrix previously calculated for the first (external) node
            idx = self.__element_positions[eli][0]
            # Position of first (external) node within element is zero
            i = 0
            # Coeff for temperature of this node
            matrix_a[idx][idx] = (eli.k_pli[i] / delta_t) + eli.h_ce() + eli.h_re() + eli.h_pli[i]
            # Coeff for temperature of next node
            matrix_a[idx][idx + 1] = - eli.h_pli[i]
            # RHS of heat balance eqn for this node
            vector_b[idx] = (eli.k_pli[i] / delta_t) * temp_prev[idx] \
                          + (eli.h_ce() + eli.h_re()) * eli.temp_ext() \
                          + eli.a_sol * (eli.i_sol_dif() + eli.i_sol_dir() * eli.f_sh_obst) \
                          - eli.therm_rad_to_sky

            # Inside node(s), if any (eqn 40)
            for i in range(1, eli.no_of_inside_nodes() + 1):
                idx = idx + 1
                # Coeff for temperature of prev node
                matrix_a[idx][idx - 1] = - eli.h_pli[i - 1]
                # Coeff for temperature of this node
                matrix_a[idx][idx] = (eli.k_pli[i] / delta_t) + eli.h_pli[i] + eli.h_pli[i - 1]
                # Coeff for temperature of next node
                matrix_a[idx][idx + 1] = - eli.h_pli[i]
                # RHS of heat balance eqn for this node
                vector_b[idx] = (eli.k_pli[i] / delta_t) * temp_prev[idx]

            # Internal surface node (eqn 39)
            idx = idx + 1
            assert idx == self.__element_positions[eli][1]
            i = i + 1
            assert i == eli.no_of_nodes() - 1
            # Get internal convective surface heat transfer coefficient, which
            # depends on direction of heat flow, which depends in temperature of
            # zone and internal surface
            h_ci = eli.h_ci(temp_prev[self.__zone_idx], temp_prev[idx])
            # Coeff for temperature of prev node
            matrix_a[idx][idx - 1] = - eli.h_pli[i - 1]
            # Coeff for temperature of this node
            matrix_a[idx][idx] = (eli.k_pli[i] / delta_t) + h_ci \
                               + eli.h_ri() * sum_area_frac + eli.h_pli[i - 1]
            # Add final sum term for LHS of eqn 39 in loop below.
            # These are coeffs for temperatures of internal surface nodes of
            # all building elements in the zone
            for elk in self.__building_elements:
                col = self.__element_positions[elk][1]
                # The line below must be an adjustment to the existing value
                # to handle the case where col = idx (i.e. where we have
                # already partially set the value of the matrix element above
                # (before this loop) and do not want to overwrite it)
                matrix_a[idx][col] = matrix_a[idx][col] \
                                   - (elk.area / self.__area_el_total) * eli.h_ri()
            # Coeff for temperature of thermal zone
            matrix_a[idx][self.__zone_idx] = - h_ci
            # RHS of heat balance eqn for this node
            vector_b[idx] = (eli.k_pli[i] / delta_t) * temp_prev[idx] \
                          + ( (1.0 - f_int_c) * gains_internal \
                            + (1.0 - f_sol_c) * self.gains_solar() \
                            + (1.0 - f_hc_c) * gains_heat_cool \
                            ) \
                          / self.__area_el_total

        # Zone heat balance:
        # - Construct row of matrix A for zone heat balance eqn
        # - Calculate RHS of zone heat balance eqn and add to vector_b

        # Coeff for temperature of thermal zone
        matrix_a[self.__zone_idx][self.__zone_idx] \
            = (self.__c_int / delta_t) \
            + sum([ eli.area
                  * eli.h_ci(
                      temp_prev[self.__zone_idx],
                      temp_prev[self.__element_positions[eli][1]]
                      )
                  for eli in self.__building_elements
                  ]) \
            + sum([vei.h_ve(self.__volume) for vei in self.__vent_elements]) \
            + self.__tb_heat_trans_coeff
        # Add final sum term for LHS of eqn 38 in loop below.
        # These are coeffs for temperatures of internal surface nodes of
        # all building elements in the zone
        for eli in self.__building_elements:
            col = self.__element_positions[eli][1] # Column for internal surface node temperature
            matrix_a[self.__zone_idx][col] \
                = - eli.area \
                * eli.h_ci(temp_prev[self.__zone_idx], temp_prev[self.__element_positions[eli][1]])
        # RHS of heat balance eqn for zone
        vector_b[self.__zone_idx] \
            = (self.__c_int / delta_t) * temp_prev[self.__zone_idx] \
            + sum([vei.h_ve(self.__volume) * vei.temp_supply() for vei in self.__vent_elements]) \
            + self.__tb_heat_trans_coeff * temp_ext_air \
            + f_int_c * gains_internal \
            + f_sol_c * self.gains_solar() \
            + f_hc_c * gains_heat_cool

        # Solve matrix eqn A.X = B to calculate vector_x (temperatures)
        vector_x = np.linalg.solve(matrix_a, vector_b)
        return vector_x

    def __temp_operative(self, temp_vector):
        """ Calculate the operative temperature, in deg C

        According to the procedure in BS EN ISO 52016-1:2017, section 6.5.5.3.

        Arguments:
        temp_vector -- vector (list) of temperatures calculated from the heat balance equations
        """
        temp_int_air = temp_vector[self.__zone_idx]

        # Mean radiant temperature is weighted average of internal surface temperatures
        temp_mean_radiant = sum([eli.area * temp_vector[self.__element_positions[eli][1]] \
                                 for eli in self.__building_elements]) \
                          / self.__area_el_total

        return (temp_int_air + temp_mean_radiant) / 2.0

    def temp_operative(self):
        """ Return operative temperature, in deg C """
        return self.__temp_operative(self.__temp_prev)

    def temp_internal_air(self):
        """ Return internal air temperature, in deg C """
        return self.__temp_prev[self.__zone_idx]

    def space_heat_cool_demand(self, delta_t_h, temp_ext_air, gains_internal):
        """ Calculate heating and cooling demand in the zone for the current timestep

        According to the procedure in BS EN ISO 52016-1:2017, section 6.5.5.2, steps 1 to 4.

        Arguments:
        delta_t_h -- calculation timestep, in hours
        temp_ext_air -- temperature of the external air for the current timestep, in deg C
        gains_internal -- internal gains for the current timestep, in W
        """
        # Calculate timestep in seconds
        delta_t = delta_t_h * units.seconds_per_hour

        # For calculation of demand, set heating/cooling gains to zero
        gains_heat_cool = 0.0

        # Calculate node and internal air temperatures with heating/cooling gains of zero
        temp_vector_no_heat_cool = self.__calc_temperatures(
            delta_t,
            self.__temp_prev,
            temp_ext_air,
            gains_internal,
            gains_heat_cool,
            )

        # Calculate internal operative temperature at free-floating conditions
        # i.e. with no heating/cooling
        temp_operative_free = self.__temp_operative(temp_vector_no_heat_cool)

        # Determine relevant setpoint (if neither, then return space heating/cooling demand of zero)
        # Determine maximum heating/cooling
        if temp_operative_free > self.__temp_setpnt_cool:
            # Cooling
            # TODO Implement eqn 26 "if max power available" case rather than just "otherwise" case?
            #      Could max. power be available at this point for all heating/cooling systems?
            temp_setpnt = self.__temp_setpnt_cool
            heat_cool_load_upper = - 10.0 * self.__useful_area
        elif temp_operative_free < self.__temp_setpnt_heat:
            # Heating
            # TODO Implement eqn 26 "if max power available" case rather than just "otherwise" case?
            #      Could max. power be available at this point for all heating/cooling systems?
            temp_setpnt = self.__temp_setpnt_heat
            heat_cool_load_upper = 10.0 * self.__useful_area
        else:
            return 0.0, 0.0 # No heating or cooling load

        # Calculate node and internal air temperatures with maximum heating/cooling
        temp_vector_upper_heat_cool = self.__calc_temperatures(
            delta_t,
            self.__temp_prev,
            temp_ext_air,
            gains_internal,
            heat_cool_load_upper,
            )

        # Calculate internal operative temperature with maximum heating/cooling
        temp_operative_upper = self.__temp_operative(temp_vector_upper_heat_cool)

        # Calculate heating (positive) or cooling (negative) required to reach setpoint
        heat_cool_load_unrestricted = heat_cool_load_upper * (temp_setpnt - temp_operative_free) \
                                    / (temp_operative_upper - temp_operative_free)

        # Convert from W to kWh
        heat_cool_demand = heat_cool_load_unrestricted / units.W_per_kW * delta_t_h

        space_heat_demand = 0.0 # in kWh
        space_cool_demand = 0.0 # in kWh
        if heat_cool_demand < 0.0:
            space_cool_demand = heat_cool_demand
        elif heat_cool_demand > 0.0:
            space_heat_demand = heat_cool_demand
        else:
            pass
        return space_heat_demand, space_cool_demand

    def update_temperatures(self,
            delta_t,
            temp_ext_air,
            gains_internal,
            gains_heat_cool,
            ):
        """ Update node and internal air temperatures for calculation of next timestep

        Arguments:
        delta_t         -- calculation timestep, in seconds
        temp_ext_air    -- temperature of external air, in deg C
        gains_internal  -- total internal heat gains, in W
        gains_heat_cool -- gains from heating (positive) or cooling (negative), in W
        """

        # Calculate node and internal air temperatures with calculated heating/cooling gains.
        # Save as "previous" temperatures for next timestep
        self.__temp_prev = self.__calc_temperatures(
            delta_t,
            self.__temp_prev,
            temp_ext_air,
            gains_internal,
            gains_heat_cool,
            )
