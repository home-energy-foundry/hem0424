#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides objects to represent building elements such as walls,
floors and windows. Each of these building elements has 2 or more nodes and is
associated with a thermal zone.

Note that the temperatures at each node for each timestep of the calculation
are calculated and stored in the zone module, not here. This is based on the
method described in BS EN ISO 52016-1:2017, section 6.5.6.
"""

# Standard library imports
import sys
from math import cos, pi

# Difference between external air temperature and sky temperature
# (default value for intermediate climatic region from BS EN ISO 52016-1:2017, Table B.19)
temp_diff_sky = 11.0 # Kelvin

def sky_view_factor(pitch):
    """ Calculate longwave sky view factor from pitch in degrees """
    # TODO account for shading
    # TODO check longwave is correct
    pitch_rads = pitch*pi/180
    return 0.5 * (1 + cos(pitch_rads))
    

class BuildingElement:
    """ A base class with common functionality for building elements

    Classes for particular types of building element should inherit from this
    one and add/override functionality as required. It is not intended for
    objects of this class to be used directly.

    Subclasses should calculate/implement (at least) the following:
    self.h_pli      -- list (len = number of nodes - 1) of thermal conductances,
                       in W / (m2.K) . Element 0 will be conductance between nodes
                       0 and 1. Calculate according to BS EN ISO 52016-1:2017,
                       section 6.5.7
    self.k_pli      -- list of areal heat capacities for each node, in J / (m2.K)
                       Calculate according to BS EN ISO 52016-1:2017, section 6.5.7
    self.temp_ext() -- function to return the temperature of the external
                       environment, in deg C
    """

    def __init__(self, area, pitch, a_sol, f_sky):
        """ Initialisation common to all building element types

        Arguments (names based on those in BS EN ISO 52016-1:2017):
        area  -- area (in m2) of this building element
        pitch -- pitch, in degrees, where 0 means facing down, and 90 means vertical
        a_sol -- solar absorption coefficient at the external surface (dimensionless)
        f_sky -- view factor to the sky (see BS EN ISO 52016-1:2017, section 6.5.13.3)

        Other variables:
        i_sol_dif -- diffuse part (excluding circumsolar) of the solar irradiance
                     on the element, in W / m2
        i_sol_dir -- direct part (excluding circumsolar) of the solar irradiance
                     on the element, in W / m2
        f_sh_obst -- shading reduction_factor for external obstacles for the element
        therm_rad_to_sky -- thermal radiation to the sky, in W / m2, calculated
                            according to BS EN ISO 52016-1:2017, section 6.5.13.3

        TODO i_sol_dif, i_sol_dir, f_sh_obst should be calculated (taking into
             account tilt and orientation of the element). Set to zero (i.e.
             ignore solar radiation on external surfaces) for now, until these
             calculations have been implemented
        """
        self.area  = area
        self.__pitch = pitch
        self.a_sol = a_sol
        self.i_sol_dif = 0.0
        self.i_sol_dir = 0.0
        self.f_sh_obst = 0.0

        self.therm_rad_to_sky = f_sky * self.h_re() * temp_diff_sky

    def h_ci(self, temp_int_air, temp_int_surface):
        """ Return internal convective heat transfer coefficient, in W / (m2.K) """
        # Values from BS EN ISO 13789:2017, Table 8

        # From BR 443: The values under "horizontal" apply to heat flow
        # directions +/- 30 degrees from horizontal plane.
        if self.__pitch >= 60 and self.__pitch <= 120:
            # Horizontal heat flow
            return 2.5
        else:
            inwards_heat_flow = (temp_int_air < temp_int_surface)
            upwards_heat_flow \
                = ( (self.__pitch < 90 and inwards_heat_flow)     # Floor
                 or (self.__pitch > 90 and not inwards_heat_flow) # Ceiling
                  )
            if upwards_heat_flow:
                # Upwards heat flow
                return 5.0
            else:
                # Downwards heat flow
                return 0.7

    def h_ri(self):
        """ Return internal radiative heat transfer coefficient, in W / (m2.K) """
        # Value from BS EN ISO 13789:2017, Table 8
        return 5.13

    def h_ce(self):
        """ Return external convective heat transfer coefficient, in W / (m2.K) """
        # Value from BS EN ISO 13789:2017, Table 8
        return 20.0

    def h_re(self):
        """ Return external radiative heat transfer coefficient, in W / (m2.K) """
        # Value from BS EN ISO 13789:2017, Table 8
        return 4.14

    def no_of_nodes(self):
        """ Return number of nodes including external and internal layers """
        return len(self.k_pli)

    def no_of_inside_nodes(self):
        """ Return number of nodes excluding external and internal layers """
        return self.no_of_nodes() - 2


class BuildingElementOpaque(BuildingElement):
    """ A class to represent opaque building elements (walls, roofs, etc.) """

    def __init__(self,
            area,
            pitch,
            a_sol,
            r_c,
            k_m,
            mass_distribution_class,
            ext_cond,
            ):
        """ Construct a BuildingElementOpaque object

        Arguments (names based on those in BS EN ISO 52016-1:2017):
        area     -- area (in m2) of this building element
        pitch    -- pitch, in degrees, where 0 means facing down, and 90 means vertical
        a_sol    -- solar absorption coefficient at the external surface (dimensionless)
        r_c      -- thermal resistance, in m2.K / W
        k_m      -- areal heat capacity, in J / (m2.K)
        ext_cond -- reference to ExternalConditions object
        mass_distribution_class
                 -- distribution of mass in building element, one of:
                    - 'I':  mass concentrated on internal side
                    - 'E':  mass concentrated on external side
                    - 'IE': mass divided over internal and external side
                    - 'D':  mass equally distributed
                    - 'M':  mass concentrated inside

        Other variables:
        f_sky -- view factor to the sky (see BS EN ISO 52016-1:2017, section 6.5.13.3)
        """
        self.__external_conditions = ext_cond

        # This is the f_sky value for an unshaded surface
        f_sky = sky_view_factor(pitch)

        # Initialise the base BuildingElement class
        super().__init__(area, pitch, a_sol, f_sky)

        # Calculate node conductances (h_pli) and node heat capacities (k_pli)
        # according to BS EN ISO 52016-1:2017, section 6.5.7.2

        def init_h_pli():
            h_outer = 6.0 / r_c
            h_inner = 3.0 / r_c
            return [h_outer, h_inner, h_inner, h_outer]

        self.h_pli = init_h_pli()

        def init_k_pli():
            if   mass_distribution_class == 'I':
                return [0.0, 0.0, 0.0, 0.0, k_m]
            elif mass_distribution_class == 'E':
                return [k_m, 0.0, 0.0, 0.0, 0.0]
            elif mass_distribution_class == 'IE':
                k_ie = k_m / 2.0
                return [k_ie, 0.0, 0.0, 0.0, k_ie]
            elif mass_distribution_class == 'D':
                k_inner = k_m / 4.0
                k_outer = k_m / 8.0
                return [k_outer, k_inner, k_inner, k_inner, k_outer]
            elif mass_distribution_class == 'M':
                return [0.0, 0.0, k_m, 0.0, 0.0]
            else:
                sys.exit("Mass distribution class ("+str(mass_distribution_class)+") not valid")
                # TODO Exit just the current case instead of whole program entirely?

        self.k_pli = init_k_pli()

    def temp_ext(self):
        """ Return the temperature of the air on the other side of the building element """
        return self.__external_conditions.air_temp()
        # TODO For now, this only handles building elements to the outdoor
        #      environment, not e.g. elements to adjacent zones.


class BuildingElementAdjacentZTC(BuildingElement):
    """ A class to represent building elements adjacent to a thermally conditioned zone (ZTC) """

    def __init__(self,
            area,
            pitch,
            r_c,
            k_m,
            mass_distribution_class,
            ext_cond,
            ):
        """ Construct a BuildingElementAdjacentZTC object

        Arguments (names based on those in BS EN ISO 52016-1:2017):
        area     -- area (in m2) of this building element
        pitch    -- pitch, in degrees, where 0 means facing down, and 90 means vertical
        r_c      -- thermal resistance, in m2.K / W
        k_m      -- areal heat capacity, in J / (m2.K)
        ext_cond -- reference to ExternalConditions object
        mass_distribution_class
                 -- distribution of mass in building element, one of:
                    - 'I':  mass concentrated on internal side
                    - 'E':  mass concentrated on external side
                    - 'IE': mass divided over internal and external side
                    - 'D':  mass equally distributed
                    - 'M':  mass concentrated inside

        Other variables:
        f_sky -- view factor to the sky (see BS EN ISO 52016-1:2017, section 6.5.13.3)
        h_ce     -- external convective heat transfer coefficient, in W / (m2.K)
        h_re     -- external radiative heat transfer coefficient, in W / (m2.K)
        a_sol    -- solar absorption coefficient at the external surface (dimensionless)
        """
        self.__external_conditions = ext_cond

        # Element is adjacent to another building / thermally conditioned zone therefore
        # according to BS EN ISO 52016-1:2017, section 6.5.6.3.6:
        # View factor to the sky is zero 
        f_sky = 0
        # Solar absorption coefficient at the external surface is zero
        a_sol = 0
        # External heat transfer coefficients are zero
        h_ce = 0
        h_re = 0

        # Initialise the base BuildingElement class
        super().__init__(area, pitch, a_sol, f_sky)

        # Calculate node conductances (h_pli) and node heat capacities (k_pli)
        # according to BS EN ISO 52016-1:2017, section 6.5.7.2

        def init_h_pli():
            h_outer = 6.0 / r_c
            h_inner = 3.0 / r_c
            return [h_outer, h_inner, h_inner, h_outer]

        self.h_pli = init_h_pli()

        def init_k_pli():
            if   mass_distribution_class == 'I':
                return [0.0, 0.0, 0.0, 0.0, k_m]
            elif mass_distribution_class == 'E':
                return [k_m, 0.0, 0.0, 0.0, 0.0]
            elif mass_distribution_class == 'IE':
                k_ie = k_m / 2.0
                return [k_ie, 0.0, 0.0, 0.0, k_ie]
            elif mass_distribution_class == 'D':
                k_inner = k_m / 4.0
                k_outer = k_m / 8.0
                return [k_outer, k_inner, k_inner, k_inner, k_outer]
            elif mass_distribution_class == 'M':
                return [0.0, 0.0, k_m, 0.0, 0.0]
            else:
                sys.exit("Mass distribution class ("+str(mass_distribution_class)+") not valid")
                # TODO Exit just the current case instead of whole program entirely?

        self.k_pli = init_k_pli()

    def h_ce(self):
        """ Return external convective heat transfer coefficient, in W / (m2.K) """
        # Element is adjacent to another building / thermally conditioned zone
        # therefore according to BS EN ISO 52016-1:2017, section 6.5.6.3.6,
        # external heat transfer coefficients are zero
        return 0.0

    def h_re(self):
        """ Return external radiative heat transfer coefficient, in W / (m2.K) """
        # Element is adjacent to another building / thermally conditioned zone
        # therefore according to BS EN ISO 52016-1:2017, section 6.5.6.3.6,
        # external heat transfer coefficients are zero
        return 0.0

    def temp_ext(self):
        """ Return the temperature of the air on the other side of the building element """
        return self.__external_conditions.air_temp()
        # Air on other side of building element is in ZTC
        # Assume adiabtiatic boundary conditions (BS EN ISO 52016-1:2017, section 6.5.6.3.6)
        # Therefore no heat transfer from external facing node


class BuildingElementGround(BuildingElement):
    """ A class to represent ground building elements """

    def __init__(self,
            area,
            pitch,
            u_value,
            r_f,
            k_m,
            mass_distribution_class,
            ext_cond,
            ):
        """ Construct a BuildingElementGround object
    
        Arguments (names based on those in BS EN ISO 52016-1:2017):
        area     -- area (in m2) of this building element
        pitch    -- pitch, in degrees, where 0 means facing down, and 90 means vertical
        u_value  -- steady-state thermal transmittance of floor, including the
                    effect of the ground, in W / (m2.K)
        r_f      -- total thermal resistance of all layers in the floor construction, in (m2.K) / W
        k_m      -- areal heat capacity of the ground floor element, in J / (m2.K)
        ext_cond -- reference to ExternalConditions object
        mass_distribution_class
                 -- distribution of mass in building element, one of:
                    - 'I':  mass concentrated on internal side
                    - 'E':  mass concentrated on external side
                    - 'IE': mass divided over internal and external side
                    - 'D':  mass equally distributed
                    - 'M':  mass concentrated inside

        Other variables:
        h_ce     -- external convective heat transfer coefficient, in W / (m2.K)
        h_re     -- external radiative heat transfer coefficient, in W / (m2.K)
        r_c      -- thermal resistance of the ground floor element including the
                    effect of the ground, in m2.K / W
        r_gr     -- thermal resistance of the fixed ground layer, in m2.K / W
        k_gr     -- areal heat capacity of the fixed ground layer, in J / (m2.K)
        """
        self.__u_value = u_value
        self.__external_conditions = ext_cond

        # Solar absorption coefficient at the external surface of the ground element is zero
        # according to BS EN ISO 52016-1:2017, section 6.5.7.3
        a_sol = 0.0
        
        # View factor to the sky is zero because element is in contact with the ground
        f_sky = 0.0

        # Thermal properties of ground from BS EN ISO 13370:2017 Table 7
        # Use values for clay or silt (same as BR 443 and SAP 10)
        thermal_conductivity = 1.5
        heat_capacity_per_vol = 300000

        # Calculate thermal resistance and heat capacity of fixed ground layer
        # using BS EN ISO 13370:2017
        thickness_ground_layer = 0.5 # Specified in BS EN ISO 52016-1:2017 section 6.5.8.2
        r_gr = thickness_ground_layer / thermal_conductivity
        k_gr = thickness_ground_layer * heat_capacity_per_vol

        # Calculate thermal resistance of virtual layer using BS EN ISO 13370:2017 Equation (F1)
        r_si = 0.17 # ISO 6946 - internal surface resistance
        r_vi = (1.0 / u_value) - r_si - r_f - r_gr

        # Set external surface heat transfer coeffs as per BS EN ISO 52016-1:2017 eqn 49
        # Must be set before initialisation of base class, as these are referenced there
        self.__h_ce = 1.0 / r_vi
        self.__h_re = 0.0

        # Initialise the base BuildingElement class
        super().__init__(area, pitch, a_sol, f_sky)

        # Calculate node conductances (h_pli) and node heat capacities (k_pli)
        # according to BS EN ISO 52016-1:2017, section 6.5.7.3

        def init_h_pli():
            r_c = 1.0 / u_value
            h_4 = 4.0 / r_c
            h_3 = 2.0 / r_c
            h_2 = 1.0 / (r_c / 4 + r_gr / 2)
            h_1 = 2.0 / r_gr
            return [h_1, h_2, h_3, h_4]

        self.h_pli = init_h_pli()

        def init_k_pli():
            if   mass_distribution_class == 'I':
                return [0.0, k_gr, 0.0, 0.0, k_m]
            elif mass_distribution_class == 'E':
                return [0.0, k_gr, k_m, 0.0, 0.0]
            elif mass_distribution_class == 'IE':
                k_ie = k_m / 2.0
                return [0.0, k_gr, k_ie, 0.0, k_ie]
            elif mass_distribution_class == 'D':
                k_inner = k_m / 2.0
                k_outer = k_m / 4.0
                return [0.0, k_gr, k_outer, k_inner, k_outer]
            elif mass_distribution_class == 'M':
                return [0.0, k_gr, 0.0, k_m, 0.0]
            else:
                sys.exit("Mass distribution class ("+str(mass_distribution_class)+") not valid")
                # TODO Exit just the current case instead of whole program entirely?

        self.k_pli = init_k_pli()

    def h_ce(self):
        """ Return external convective heat transfer coefficient, in W / (m2.K) """
        return self.__h_ce

    def h_re(self):
        """ Return external radiative heat transfer coefficient, in W / (m2.K) """
        return self.__h_re

    def temp_ext(self):
        """ Return the temperature of the air on the other side of the building element """
        return self.__external_conditions.ground_temp()


class BuildingElementTransparent(BuildingElement):
    """ A class to represent transparent building elements (windows etc.) """

    def __init__(self,
            area,
            pitch,
            r_c,
            ext_cond,
            ):
        """ Construct a BuildingElementTransparent object

        Arguments (names based on those in BS EN ISO 52016-1:2017):
        area     -- area (in m2) of this building element
        pitch    -- pitch, in degrees, where 0 means facing down, and 90 means vertical
        r_c      -- thermal resistance, in m2.K / W
        ext_cond -- reference to ExternalConditions object

        Other variables:
        f_sky -- view factor to the sky (see BS EN ISO 52016-1:2017, section 6.5.13.3)
        """
        self.__external_conditions = ext_cond

        # Solar absorption coefficient is zero because element is transparent
        a_sol = 0.0

        # This is the f_sky value for an unshaded surface
        f_sky = sky_view_factor(pitch)

        # Initialise the base BuildingElement class
        super().__init__(area, pitch, a_sol, f_sky)

        # Calculate node conductances (h_pli) and node heat capacities (k_pli)
        # according to BS EN ISO 52016-1:2017, section 6.5.7.4
        self.h_pli = [1.0 / r_c]
        self.k_pli = [0.0, 0.0]

    def temp_ext(self):
        """ Return the temperature of the air on the other side of the building element """
        return self.__external_conditions.air_temp()
        # TODO For now, this only handles building elements to the outdoor
        #      environment, not e.g. elements to adjacent zones.
