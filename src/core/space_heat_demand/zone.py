#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides objects to represent the thermal zones in the building,
and to calculate the temperatures in the zone and associated building elements.
"""

# Standard library imports
import numpy as np

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

    def __init__(self, area, building_elements, tb_heat_trans_coeff, vent_elements):
        """ Construct a Zone object

        Arguments:
        area              -- useful floor area of the zone, in m2
        building_elements -- list of BuildingElement objects (walls, floors, windows etc.)
        tb_heat_trans_coeff -- overall heat transfer coefficient for thermal
                               bridges in the zone, in W / K
        vent_elements     -- list of ventilation elements (infiltration, mech vent etc.)

        Other variables:
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
        """
        self.__useful_area = area
        self.__building_elements = building_elements
        self.__vent_elements     = vent_elements
        self.__tb_heat_trans_coeff = tb_heat_trans_coeff

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

    def __calc_temperatures(self,
            delta_t,
            temp_prev,
            temp_ext_air,
            gains_internal,
            gains_solar,
            gains_heat_cool
            ):
        """ Calculate temperatures according to procedure in BS EN ISO 52016-1:2017, section 6.5.6

        Arguments:
        delta_t         -- calculation timestep, in seconds
        temp_prev       -- temperature vector X (see below) from previous timestep
        temp_ext_air    -- temperature of external air, in deg C
        gains_internal  -- total internal heat gains, in W
        gains_solar     -- directly transmitted solar gains, in W
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
            idx = self.__element_positions[eli][0]
            # Coeff for temperature of this node
            matrix_a[idx][idx] = (eli.k_pli[0] / delta_t) + eli.h_ce + eli.h_re + eli.h_pli[0]
            # Coeff for temperature of next node
            matrix_a[idx][idx + 1] = - eli.h_pli[0]
            # RHS of heat balance eqn for this node
            vector_b[idx] = (eli.k_pli[0] / delta_t) * temp_prev[idx] \
                          + (eli.h_ce + eli.h_re) * eli.temp_ext() \
                          + eli.a_sol * (eli.i_sol_dif + eli.i_sol_dir * eli.f_sh_obst) \
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
            # Coeff for temperature of prev node
            matrix_a[idx][idx - 1] = - eli.h_pli[i - 1]
            # Coeff for temperature of this node
            matrix_a[idx][idx] = (eli.k_pli[i] / delta_t) + eli.h_ci \
                               + eli.h_ri * sum_area_frac + eli.h_pli[i - 1]
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
                                   - (elk.area / self.__area_el_total) * eli.h_ri
            # Coeff for temperature of thermal zone
            matrix_a[idx][self.__zone_idx] = - eli.h_ci
            # RHS of heat balance eqn for this node
            vector_b[idx] = (eli.k_pli[i] / delta_t) * temp_prev[idx] \
                          + ( (1.0 - f_int_c) * gains_internal \
                            + (1.0 - f_sol_c) * gains_solar \
                            + (1.0 - f_hc_c) * gains_heat_cool \
                            ) \
                          / self.__area_el_total

        # Zone heat balance:
        # - Construct row of matrix A for zone heat balance eqn
        # - Calculate RHS of zone heat balance eqn and add to vector_b

        # Coeff for temperature of thermal zone
        matrix_a[self.__zone_idx][self.__zone_idx] \
            = (self.__c_int / delta_t) \
            + sum([eli.area * eli.h_ci for eli in self.__building_elements]) \
            + sum([vei.h_ve for vei in self.__vent_elements]) \
            + self.__tb_heat_trans_coeff
        # Add final sum term for LHS of eqn 38 in loop below.
        # These are coeffs for temperatures of internal surface nodes of
        # all building elements in the zone
        for eli in self.__building_elements:
            col = self.__element_positions[eli][1] # Column for internal surface node temperature
            matrix_a[self.__zone_idx][col] = - eli.area * eli.h_ci
        # RHS of heat balance eqn for zone
        vector_b[self.__zone_idx] \
            = (self.__c_int / delta_t) * temp_prev[self.__zone_idx] \
            + sum([vei.h_ve * vei.temp_supply for vei in self.__vent_elements]) \
            + self.__tb_heat_trans_coeff * temp_ext_air \
            + f_int_c * gains_internal \
            + f_sol_c * gains_solar \
            + f_hc_c * gains_heat_cool

        # Solve matrix eqn M.X = B to calculate vector_x (temperatures)
        vector_x = np.linalg.solve(matrix_a, vector_b)
        return vector_x
