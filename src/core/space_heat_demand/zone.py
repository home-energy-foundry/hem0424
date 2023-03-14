#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides objects to represent the thermal zones in the building,
and to calculate the temperatures in the zone and associated building elements.
"""

# Standard library imports
import sys

# Third-party imports
import numpy as np

# Local imports
import core.units as units
from core.space_heat_demand.ventilation_element import \
    MechnicalVentilationHeatRecovery, WholeHouseExtractVentilation, \
    VentilationElementInfiltration, NaturalVentilation

# Convective fractions
# (default values from BS EN ISO 52016-1:2017, Table B.11)
f_int_c = 0.4 # Can be different for each source of internal gains
f_sol_c = 0.1

# Areal thermal capacity of air and furniture
# (default value from BS EN ISO 52016-1:2017, Table B.17)
k_m_int = 10000 # J / (m2.K)


class Zone:
    """ An object to represent a thermal zone in the building

    Temperatures of nodes in associated building elements are also calculated
    in this object by solving a matrix equation.
    """

    def __init__(
            self,
            area,
            volume,
            building_elements,
            thermal_bridging,
            vent_elements,
            vent_cool_extra = None,
            print_heat_balance = False,
            ):
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
        vent_cool_extra   -- element providing additional ventilation in response to high
                             internal temperature
        print_heat_balance-- flag to indicate whether to print the heat balance breakdown

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
        temp_prev         -- list of temperatures (nodes and internal air) from
                             previous timestep. Positions in list defined in
                             self.__element_positions and self.__zone_idx
        """
        self.__useful_area = area
        self.__volume = volume
        self.__building_elements = building_elements
        self.__vent_elements     = vent_elements
        self.__vent_cool_extra = vent_cool_extra

        # If thermal_bridging is a list of ThermalBridge objects, calculate the
        # overall heat transfer coefficient for thermal bridges, otherwise just
        # use the coefficient given
        if isinstance(thermal_bridging, list):
            self.__tb_heat_trans_coeff = 0.0
            for tb in thermal_bridging:
                self.__tb_heat_trans_coeff += tb.heat_trans_coeff()
        else:
            self.__tb_heat_trans_coeff = thermal_bridging

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

        self.__print_heat_balance = print_heat_balance

    def area(self):
        return self.__useful_area

    def volume(self):
        return self.__volume

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
            gains_solar,
            gains_heat_cool,
            f_hc_c,
            vent_extra_h_ve=0.0,
            throughput_factor=1.0,
            print_heat_balance = False,
            ):
        """ Calculate temperatures according to procedure in BS EN ISO 52016-1:2017, section 6.5.6

        Arguments:
        delta_t         -- calculation timestep, in seconds
        temp_prev       -- temperature vector X (see below) from previous timestep
        temp_ext_air    -- temperature of external air, in deg C
        gains_internal  -- total internal heat gains, in W
        gains_solar     -- directly transmitted solar gains, in W
        gains_heat_cool -- gains from heating (positive) or cooling (negative), in W
        f_hc_c          -- convective fraction for heating/cooling
        vent_extra_h_ve -- additional ventilation heat transfer coeff in response
                           to high internal temperature
        throughput_factor -- proportional increase in ventilation rate due to
                             overventilation requirement
        print_heat_balance -- flag to record whether to return the heat balance outputs

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
            i_sol_dir, i_sol_dif = eli.i_sol_dir_dif()
            f_sh_dir, f_sh_dif = eli.shading_factors_direct_diffuse()
            vector_b[idx] = (eli.k_pli[i] / delta_t) * temp_prev[idx] \
                          + (eli.h_ce() + eli.h_re()) * eli.temp_ext() \
                          + eli.a_sol * (i_sol_dif * f_sh_dif + i_sol_dir * f_sh_dir) \
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
                            + (1.0 - f_sol_c) * gains_solar \
                            + (1.0 - f_hc_c) * gains_heat_cool \
                            ) \
                          / self.__area_el_total

        # Zone heat balance:
        # - Construct row of matrix A for zone heat balance eqn
        # - Calculate RHS of zone heat balance eqn and add to vector_b

        # Coeff for temperature of thermal zone
        # TODO Throughput factor only applies to MVHR and WHEV, therefore only
        #      these systems accept throughput_factor as an argument to the h_ve
        #      function, hence the branch on the type in the loop below. This
        #      means that the MVHR and WHEV classes no longer have the same
        #      interface as other ventilation element classes, which could make
        #      future development more difficult. Ideally, we would find a
        #      cleaner way to implement this difference.
        sum_vent_elements_h_ve = vent_extra_h_ve
        for vei in self.__vent_elements:
            if type(vei) in (MechnicalVentilationHeatRecovery, WholeHouseExtractVentilation):
                sum_vent_elements_h_ve \
                    += vei.h_ve(self.__volume, throughput_factor)
            elif type(vei) in (VentilationElementInfiltration, NaturalVentilation):
                sum_vent_elements_h_ve \
                    += vei.h_ve(self.__volume)
            else:
                sys.exit( 'Applicability of throughput factor not defined for '
                        + 'ventilation element type ' + type(vei))
        matrix_a[self.__zone_idx][self.__zone_idx] \
            = (self.__c_int / delta_t) \
            + sum([ eli.area
                  * eli.h_ci(
                      temp_prev[self.__zone_idx],
                      temp_prev[self.__element_positions[eli][1]]
                      )
                  for eli in self.__building_elements
                  ]) \
            + sum_vent_elements_h_ve \
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
        # TODO Throughput factor only applies to MVHR and WHEV, therefore only
        #      these systems accept throughput_factor as an argument to the h_ve
        #      function, hence the branch on the type in the loop below. This
        #      means that the MVHR and WHEV classes no longer have the same
        #      interface as other ventilation element classes, which could make
        #      future development more difficult. Ideally, we would find a
        #      cleaner way to implement this difference.
        sum_vent_elements_h_ve_times_temp_supply = 0.0
        if vent_extra_h_ve != 0:
            sum_vent_elements_h_ve_times_temp_supply \
                += vent_extra_h_ve * self.__vent_cool_extra.temp_supply()
        for vei in self.__vent_elements:
            if type(vei) in (MechnicalVentilationHeatRecovery, WholeHouseExtractVentilation):
                sum_vent_elements_h_ve_times_temp_supply \
                    += vei.h_ve(self.__volume, throughput_factor) * vei.temp_supply()
            elif type(vei) in (VentilationElementInfiltration, NaturalVentilation):
                sum_vent_elements_h_ve_times_temp_supply \
                    += vei.h_ve(self.__volume) * vei.temp_supply()
            else:
                sys.exit( 'Applicability of throughput factor not defined for '
                        + 'ventilation element type ' + type(vei))
        vector_b[self.__zone_idx] \
            = (self.__c_int / delta_t) * temp_prev[self.__zone_idx] \
            + sum_vent_elements_h_ve_times_temp_supply \
            + self.__tb_heat_trans_coeff * temp_ext_air \
            + f_int_c * gains_internal \
            + f_sol_c * gains_solar \
            + f_hc_c * gains_heat_cool

        # Solve matrix eqn A.X = B to calculate vector_x (temperatures)
        vector_x = np.linalg.solve(matrix_a, vector_b)

        if print_heat_balance:
            heat_balance_dict = {}

            # Collect outputs, in W, for heat balance at air node
            temp_internal = vector_x[self.__zone_idx]
            hb_gains_solar = f_sol_c * gains_solar
            hb_gains_internal = f_int_c * gains_internal
            hb_gains_heat_cool = f_hc_c * gains_heat_cool
            hb_energy_to_change_temp = (self.__c_int / delta_t)*(temp_internal-temp_prev[self.__zone_idx])
            hb_loss_thermal_bridges = self.__tb_heat_trans_coeff*(temp_internal-temp_ext_air)
            hb_loss_ventilation = sum([vei.h_ve(self.__volume) * (temp_internal-vei.temp_supply()) for vei in self.__vent_elements])
            hb_loss_fabric = (hb_gains_solar+hb_gains_internal+hb_gains_heat_cool+hb_energy_to_change_temp)\
                            -(hb_loss_thermal_bridges+hb_loss_ventilation)
            heat_balance_dict['air_node'] = {
                'solar gains' : hb_gains_solar,
                'internal gains' : hb_gains_internal,
                'heating or cooling system gains' : hb_gains_heat_cool,
                'energy to change internal temperature' : hb_energy_to_change_temp,
                'heat loss through thermal bridges' : hb_loss_thermal_bridges,
                'heat loss through ventilation' : hb_loss_ventilation,
                'fabric heat loss' : hb_loss_fabric
                                }

            # Collect outputs, in W, for heat balance at external boundary
            hb_fabric_ext_boundary = 0.0
            for eli in self.__building_elements:
                # Get position in vector for the first (external) node of the building element
                idx = self.__element_positions[eli][0]
                temp_ext_surface = vector_x[idx]
                i_sol_dir, i_sol_dif = eli.i_sol_dir_dif()
                f_sh_dir, f_sh_dif = eli.shading_factors_direct_diffuse()
                hb_fabric_ext_boundary \
                    += eli.area \
                     * ( (eli.h_ce() + eli.h_re()) * (eli.temp_ext() - temp_ext_surface) \
                       + eli.a_sol * (i_sol_dif * f_sh_dif + i_sol_dir * f_sh_dir) \
                       - eli.therm_rad_to_sky \
                       )
            heat_balance_dict['external_boundary'] = {
                'solar gains': gains_solar,
                'internal gains': gains_internal,
                'heating or cooling system gains': gains_heat_cool,
                'thermal_bridges': - hb_loss_thermal_bridges,
                'ventilation': - hb_loss_ventilation,
                'fabric': hb_fabric_ext_boundary,
                }
        else:
            heat_balance_dict = None
        return vector_x, heat_balance_dict

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

    def space_heat_cool_demand(
            self,
            delta_t_h,
            temp_ext_air,
            gains_internal,
            gains_solar,
            frac_convective_heat,
            frac_convective_cool,
            temp_setpnt_heat,
            temp_setpnt_cool,
            throughput_factor=1.0,
            ):
        """ Calculate heating and cooling demand in the zone for the current timestep

        According to the procedure in BS EN ISO 52016-1:2017, section 6.5.5.2, steps 1 to 4.

        Arguments:
        delta_t_h -- calculation timestep, in hours
        temp_ext_air -- temperature of the external air for the current timestep, in deg C
        gains_internal -- internal gains for the current timestep, in W
        gains_solar -- directly transmitted solar gains, in W
        frac_convective_heat -- convective fraction for heating
        frac_convective_cool -- convective fraction for cooling
        temp_setpnt_heat -- temperature setpoint for heating, in deg C
        temp_setpnt_cool -- temperature setpoint for cooling, in deg C
        throughput_factor -- proportional increase in ventilation rate due to
                             overventilation requirement
        """
        if temp_setpnt_cool < temp_setpnt_heat:
            sys.exit('ERROR: Cooling setpoint is below heating setpoint.')

        if self.__vent_cool_extra is not None:
            temp_setpnt_cool_vent = self.__vent_cool_extra.temp_setpnt()
            if temp_setpnt_cool_vent is None:
                # Set cooling setpoint to Planck temperature to ensure no cooling demand
                temp_setpnt_cool_vent = units.Kelvin2Celcius(1.4e32)
            if temp_setpnt_cool_vent < temp_setpnt_heat:
                sys.exit('ERROR: Setpoint for additional ventilation is below heating setpoint.')

        # Calculate timestep in seconds
        delta_t = delta_t_h * units.seconds_per_hour

        # For calculation of demand, set heating/cooling gains to zero
        gains_heat_cool = 0.0

        # Calculate node and internal air temperatures with heating/cooling gains of zero
        temp_vector_no_heat_cool, _ = self.__calc_temperatures(
            delta_t,
            self.__temp_prev,
            temp_ext_air,
            gains_internal,
            gains_solar,
            gains_heat_cool,
            1.0, # Value does not matter as gains_heat_cool = 0.0
            throughput_factor = throughput_factor,
            )

        # Calculate internal operative temperature at free-floating conditions
        # i.e. with no heating/cooling
        temp_operative_free = self.__temp_operative(temp_vector_no_heat_cool)
        temp_int_air_free = temp_vector_no_heat_cool[self.__zone_idx]

        # Check setpoint for additional ventilation. If above setpoint:
        # First calculate temps with max. additional ventilation, then check
        # setpoints again. If still above cooling setpoint, do not use additional
        # ventilation - just use cooling instead. Otherwise, cooling demand is zero
        # and need to use interpolation to work out additional ventilation required
        # (just like calc for heat_cool_load_unrestricted below)
        h_ve_cool_extra = 0.0
        if self.__vent_cool_extra is not None and temp_operative_free > temp_setpnt_cool_vent:
            # Calculate node and internal air temperatures with maximum additional ventilation
            h_ve_cool_max = self.__vent_cool_extra.h_ve_max(
                self.__volume,
                temp_operative_free,
                )
            temp_vector_vent_max, _ = self.__calc_temperatures(
                delta_t,
                self.__temp_prev,
                temp_ext_air,
                gains_internal,
                gains_solar,
                gains_heat_cool,
                1.0, # Value does not matter as gains_heat_cool = 0.0
                vent_extra_h_ve = h_ve_cool_max,
                throughput_factor = throughput_factor,
                )

            # Calculate internal operative temperature with maximum ventilation
            temp_operative_vent_max = self.__temp_operative(temp_vector_vent_max)
            temp_int_air_vent_max = temp_vector_vent_max[self.__zone_idx]

            vent_cool_extra_temp_supply = self.__vent_cool_extra.temp_supply()

            # If there is cooling potential from additional ventilation
            if temp_operative_vent_max < temp_operative_free \
            and temp_int_air_free > vent_cool_extra_temp_supply:
                # Calculate ventilation required to reach cooling setpoint for ventilation
                h_ve_cool_req \
                    = h_ve_cool_max * (temp_setpnt_cool_vent - temp_operative_free) \
                    / (temp_operative_vent_max - temp_operative_free) \
                    * ( (temp_int_air_vent_max - vent_cool_extra_temp_supply)
                      / (temp_int_air_free - vent_cool_extra_temp_supply)
                      )

                # Calculate additional ventilation rate achieved
                h_ve_cool_extra = min(h_ve_cool_req, h_ve_cool_max)

                # Calculate node and internal air temperatures with heating/cooling gains of zero
                temp_vector_no_heat_cool_vent_extra, _ = self.__calc_temperatures(
                    delta_t,
                    self.__temp_prev,
                    temp_ext_air,
                    gains_internal,
                    gains_solar,
                    gains_heat_cool,
                    1.0, # Value does not matter as gains_heat_cool = 0.0
                    vent_extra_h_ve = h_ve_cool_extra,
                    throughput_factor = throughput_factor,
                    )

                # Calculate internal operative temperature at free-floating conditions
                # i.e. with no heating/cooling
                temp_operative_free_vent_extra = self.__temp_operative(temp_vector_no_heat_cool_vent_extra)

                # If temperature achieved by additional ventilation is above setpoint
                # for active cooling, assume cooling system will be used instead of
                # additional ventilation. Otherwise, use resultant operative temperature
                # in calculation of space heating/cooling demand.
                if temp_operative_free_vent_extra > temp_setpnt_cool:
                    h_ve_cool_extra = 0.0
                else:
                    temp_operative_free = temp_operative_free_vent_extra

        # Determine relevant setpoint (if neither, then return space heating/cooling demand of zero)
        # Determine maximum heating/cooling
        if temp_operative_free > temp_setpnt_cool:
            # Cooling
            # TODO Implement eqn 26 "if max power available" case rather than just "otherwise" case?
            #      Could max. power be available at this point for all heating/cooling systems?
            temp_setpnt = temp_setpnt_cool
            heat_cool_load_upper = - 10.0 * self.__useful_area
            frac_convective = frac_convective_cool
        elif temp_operative_free < temp_setpnt_heat:
            # Heating
            # TODO Implement eqn 26 "if max power available" case rather than just "otherwise" case?
            #      Could max. power be available at this point for all heating/cooling systems?
            temp_setpnt = temp_setpnt_heat
            heat_cool_load_upper = 10.0 * self.__useful_area
            frac_convective = frac_convective_heat
        else:
            return 0.0, 0.0, h_ve_cool_extra # No heating or cooling load

        # Calculate node and internal air temperatures with maximum heating/cooling
        temp_vector_upper_heat_cool, _ = self.__calc_temperatures(
            delta_t,
            self.__temp_prev,
            temp_ext_air,
            gains_internal,
            gains_solar,
            heat_cool_load_upper,
            frac_convective,
            vent_extra_h_ve = h_ve_cool_extra,
            throughput_factor = throughput_factor,
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
        return space_heat_demand, space_cool_demand, h_ve_cool_extra

    def update_temperatures(self,
            delta_t,
            temp_ext_air,
            gains_internal,
            gains_solar,
            gains_heat_cool,
            frac_convective,
            vent_extra_h_ve=0.0,
            throughput_factor=1.0,
            ):
        """ Update node and internal air temperatures for calculation of next timestep

        Arguments:
        delta_t         -- calculation timestep, in seconds
        temp_ext_air    -- temperature of external air, in deg C
        gains_internal  -- total internal heat gains, in W
        gains_solar     -- directly transmitted solar gains, in W
        gains_heat_cool -- gains from heating (positive) or cooling (negative), in W
        frac_convective -- convective fraction for heating/cooling (as appropriate)
        throughput_factor -- proportional increase in ventilation rate due to
                             overventilation requirement
        heat_balance_dict -- dictionary to record heat balance outputs
        """

        # Calculate node and internal air temperatures with calculated heating/cooling gains.
        # Save as "previous" temperatures for next timestep
        self.__temp_prev, heat_balance_dict = self.__calc_temperatures(
            delta_t,
            self.__temp_prev,
            temp_ext_air,
            gains_internal,
            gains_solar,
            gains_heat_cool,
            frac_convective,
            vent_extra_h_ve = vent_extra_h_ve,
            throughput_factor = throughput_factor,
            print_heat_balance = self.__print_heat_balance,
            )
        return heat_balance_dict

    def total_fabric_heat_loss(self):
        """ Return the total fabric heat loss from all 
        building elements in a zone, in W / K """
        total_fabric_heat_loss = 0
        for be in self.__building_elements:
            total_fabric_heat_loss += be.fabric_heat_loss()
        return total_fabric_heat_loss

    def total_heat_capacity(self):
        """ Return the total heat capacity from all building elements in a zone
        excluding ground and transparent elements, in kJ / K """
        # TODO Exclude solid door (opaque building element), or define convention
        #      that heat capacity of solid doors can be entered as zero
        total_heat_capacity = 0
        for be in self.__building_elements:
            total_heat_capacity += be.heat_capacity()
        return total_heat_capacity

    def total_thermal_bridges(self):
        """ Return the total heat transfer coefficient for all
        thermal bridges in a zone, in W / K """
        return self.__tb_heat_trans_coeff

    def total_vent_heat_loss(self):
        """ Return the ventilation heat loss from all ventilation elements, in W / K """
        total_vent_heat_loss = 0
        for ve in self.__vent_elements:
            total_vent_heat_loss += ve.h_ve_average(self.__volume)
        return total_vent_heat_loss
        