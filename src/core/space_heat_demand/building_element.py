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

# Local imports
import core.external_conditions as external_conditions
from core.units import average_monthly_to_annual

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
    
    # Values from BS EN ISO 13789:2017, Table 8: Conventional surface heat
    # transfer coefficients
    __H_CI_UPWARDS = 5.0
    __H_CI_HORIZONTAL = 2.5
    __H_CI_DOWNWARDS = 0.7
    __H_CE = 20.0
    __H_RI = 5.13
    __H_RE = 4.14

    # From BR 443: The values under "horizontal" apply to heat flow
    # directions +/- 30 degrees from horizontal plane.
    __PITCH_LIMIT_HORIZ_CEILING = 60.0
    __PITCH_LIMIT_HORIZ_FLOOR = 120.0

    def __init__(self, area, pitch, a_sol, f_sky):
        """ Initialisation common to all building element types

        Arguments (names based on those in BS EN ISO 52016-1:2017):
        area  -- area (in m2) of this building element
        pitch -- tilt angle of the surface from horizontal, in degrees between 0 and 180,
                 where 0 means the external surface is facing up, 90 means the external
                 surface is vertical and 180 means the external surface is facing down
        a_sol -- solar absorption coefficient at the external surface (dimensionless)
        f_sky -- view factor to the sky (see BS EN ISO 52016-1:2017, section 6.5.13.3)

        Other variables:
        i_sol_dif -- diffuse part (EXCLUDING circumsolar, as specified in ISO 52010) 
                     of the solar irradiance on the element, in W / m2
        i_sol_dir -- direct part (INCLUDING circumsolar, as specified in ISO 52010) 
                     of the solar irradiance on the element, in W / m2
        f_sh_obst -- shading reduction_factor for external obstacles for the element
        therm_rad_to_sky -- thermal radiation to the sky, in W / m2, calculated
                            according to BS EN ISO 52016-1:2017, section 6.5.13.3
        """
        self.area  = area
        self._pitch = pitch
        self.a_sol = a_sol

        # TODO f_sh_obst should be calculated. Set to 1.0 for now (i.e. ignore
        #      shading) until this has been implemented.
        self.f_sh_obst = 1.0

        self.therm_rad_to_sky = f_sky * self.h_re() * temp_diff_sky

    def h_ci(self, temp_int_air, temp_int_surface):
        """ Return internal convective heat transfer coefficient, in W / (m2.K) """
        if self._pitch >= self.__PITCH_LIMIT_HORIZ_CEILING \
        and self._pitch <= self.__PITCH_LIMIT_HORIZ_FLOOR:
            # Horizontal heat flow
            return self.__H_CI_HORIZONTAL
        else:
            inwards_heat_flow = (temp_int_air < temp_int_surface)
            is_floor = (self._pitch > self.__PITCH_LIMIT_HORIZ_FLOOR)
            is_ceiling = (self._pitch < self.__PITCH_LIMIT_HORIZ_CEILING)
            upwards_heat_flow \
                = ( (is_floor and inwards_heat_flow)
                 or (is_ceiling and not inwards_heat_flow)
                  )
            if upwards_heat_flow:
                # Upwards heat flow
                return self.__H_CI_UPWARDS
            else:
                # Downwards heat flow
                return self.__H_CI_DOWNWARDS

    def h_ri(self):
        """ Return internal radiative heat transfer coefficient, in W / (m2.K) """
        return self.__H_RI

    def h_ce(self):
        """ Return external convective heat transfer coefficient, in W / (m2.K) """
        return self.__H_CE

    def h_re(self):
        """ Return external radiative heat transfer coefficient, in W / (m2.K) """
        return self.__H_RE

    def i_sol_dir(self):
        """ Return default of zero for i_sol_dir """
        return 0

    def i_sol_dif(self):
        """ Return default of zero for i_sol_dif """
        return 0

    def solar_gains(self):
        """ Return default of zero for solar gains """
        return 0

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
            orientation,
            ext_cond,
            ):
        """ Construct a BuildingElementOpaque object

        Arguments (names based on those in BS EN ISO 52016-1:2017):
        area     -- area (in m2) of this building element
        pitch -- tilt angle of the surface from horizontal, in degrees between 0 and 180,
                 where 0 means the external surface is facing up, 90 means the external
                 surface is vertical and 180 means the external surface is facing down
        a_sol    -- solar absorption coefficient at the external surface (dimensionless)
        r_c      -- thermal resistance, in m2.K / W
        k_m      -- areal heat capacity, in J / (m2.K)
        orientation -- is the orientation angle of the inclined surface, expressed as the 
                       geographical azimuth angle of the horizontal projection of the inclined 
                       surface normal, -180 to 180, in degrees
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
        self.__orientation = orientation
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

    def i_sol_dir(self):
        """ Return calculated i_sol_dir using pitch and orientation of element """
        return self.__external_conditions.calculated_direct_irradiance(self._pitch, self.__orientation)

    def i_sol_dif(self):
        """ Return calculated i_sol_dif using pitch and orientation of element """
        return self.__external_conditions.calculated_diffuse_irradiance(self._pitch, self.__orientation)

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
        pitch -- tilt angle of the surface from horizontal, in degrees between 0 and 180,
                 where 0 means the external surface is facing up, 90 means the external
                 surface is vertical and 180 means the external surface is facing down
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

    # Assume values for temp_int_annual and temp_int_monthly
    # These are based on SAP 10 notional building runs for 5 archetypes used
    # for inter-model comparison/validation. The average of the monthly mean
    # internal temperatures from each run was taken.
    __TEMP_INT_MONTHLY \
        = [19.46399546, 19.66940204, 19.90785898, 20.19719837, 20.37461865, 20.45679018,
           20.46767703, 20.46860812, 20.43505593, 20.22266322, 19.82726777, 19.45430847,
          ]

    def __init__(self,
            area,
            pitch,
            u_value,
            r_f,
            k_m,
            mass_distribution_class,
            h_pi,
            h_pe,
            perimeter,
            psi_wall_floor_junc,
            ext_cond,
            simulation_time,
            ):
        """ Construct a BuildingElementGround object
    
        Arguments (names based on those in BS EN ISO 52016-1:2017):
        area     -- area (in m2) of this building element
        pitch -- tilt angle of the surface from horizontal, in degrees between 0 and 180,
                 where 0 means the external surface is facing up, 90 means the external
                 surface is vertical and 180 means the external surface is facing down
        u_value  -- steady-state thermal transmittance of floor, including the
                    effect of the ground, in W / (m2.K)
        r_f      -- total thermal resistance of all layers in the floor construction, in (m2.K) / W
        k_m      -- areal heat capacity of the ground floor element, in J / (m2.K)
        h_pi     -- internal periodic heat transfer coefficient, as defined in
                    BS EN ISO 13370:2017 Annex H, in W / K
        h_pe     -- internal periodic heat transfer coefficient, as defined in
                    BS EN ISO 13370:2017 Annex H, in W / K
        perimeter -- perimeter of the floor, in metres
        psi_wall_floor_junc -- linear thermal transmittance of the junction
                               between the floor and the walls, in W / (m.K)
        ext_cond -- reference to ExternalConditions object
        simulation_time -- reference to SimulationTime object
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
        self.__h_pi = h_pi
        self.__h_pe = h_pe
        self.__perimeter = perimeter
        self.__psi_wall_flr_junc = psi_wall_floor_junc
        self.__external_conditions = ext_cond
        self.__simulation_time = simulation_time
        self.__temp_int_annual = average_monthly_to_annual(self.__TEMP_INT_MONTHLY)


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
        """ Return the temperature on the other side of the building element """
        temp_ext_annual = self.__external_conditions.air_temp_annual()
        temp_ext_month = self.__external_conditions.air_temp_monthly()

        current_month = self.__simulation_time.current_month()
        temp_int_month = self.__TEMP_INT_MONTHLY[current_month]

        # BS EN ISO 13370:2017 Eqn C.4
        heat_flow_month \
            = self.__u_value * self.area * (self.__temp_int_annual - temp_ext_annual) \
            + self.__perimeter * self.__psi_wall_flr_junc * (temp_int_month - temp_ext_month) \
            - self.__h_pi * (self.__temp_int_annual - temp_int_month) \
            + self.__h_pe * (temp_ext_annual - temp_ext_month)

        # BS EN ISO 13370:2017 Eqn F.2
        temp_ground_virtual \
            = temp_int_month \
            - ( heat_flow_month
              - ( self.__perimeter * self.__psi_wall_flr_junc 
                * (self.__temp_int_annual - temp_ext_annual)
                )
              ) \
            / (self.area * self.__u_value)

        return temp_ground_virtual


class BuildingElementTransparent(BuildingElement):
    """ A class to represent transparent building elements (windows etc.) """

    def __init__(self,
            area,
            pitch,
            r_c,
            orientation,
            g_value,
            frame_area_fraction,
            ext_cond,
            ):
        """ Construct a BuildingElementTransparent object

        Arguments (names based on those in BS EN ISO 52016-1:2017):
        area     -- area (in m2) of this building element
        pitch -- tilt angle of the surface from horizontal, in degrees between 0 and 180,
                 where 0 means the external surface is facing up, 90 means the external
                 surface is vertical and 180 means the external surface is facing down
        r_c      -- thermal resistance, in m2.K / W
        orientation -- is the orientation angle of the inclined surface, expressed 
                       as the geographical azimuth angle of the horizontal projection 
                       of the inclined surface normal, -180 to 180, in degrees
        g_value -- total solar energy transmittance of the transparent part of the window
        frame_area_fraction -- is the frame area fraction of window wi, ratio of the 
                               projected frame area to the overall projected area of 
                               the glazed element of the window
        ext_cond -- reference to ExternalConditions object

        Other variables:
        f_sky -- view factor to the sky (see BS EN ISO 52016-1:2017, section 6.5.13.3)
        """
        self.__orientation = orientation
        self.__g_value = g_value
        #TODO ISO 52016 offers an input option; either the frame factor directly,
        #or the glazed area of the window and then the frame factor is calculated.
        #assuming for now that frame factor is provided (default 0.25 from App B)
        #need to implement ISO 52016 E.2.1 here if other option given.
        self.__frame_area_fraction = frame_area_fraction
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

    #TODO f_sh_obst set to zero in main Building Element set up.
    #calculate that properly here when implementing shading.
    #self.f_sh_obst

    def convert_g_value(self):
        """return g_value corrected for angle of solar radiation"""

        #TODO for windows with scattering glazing or solar shading provisions
        #there is a different, more complex method for conversion that depends on
        #timestep (via solar altitude).
        #suggest this is implemented at the same time as window shading (devices
        #rather than fixed features) as will also need to link to shading schedule.
        #see ISO 52016 App E. Page 177
        #How do we know whether a window has "scattering glazing"?

        # g_value = agl * g_alt + (1 - agl) * g_dif

        Fw = 0.90 
        #default from ISO 52016 App B Table B.22
        g_value = Fw * self.__g_value

        return g_value

    def solar_gains(self):
        """ Return calculated solar gains using pitch and orientation of element """

        i_sol_dir = self.__external_conditions.calculated_direct_irradiance(self._pitch, self.__orientation)
        i_sol_dif = self.__external_conditions.calculated_diffuse_irradiance(self._pitch, self.__orientation)
        g_value = self.convert_g_value()

        solar_gains = g_value * (i_sol_dif + i_sol_dir * self.f_sh_obst) \
                    * self.area * (1 - self.__frame_area_fraction)

        return solar_gains

    def temp_ext(self):
        """ Return the temperature of the air on the other side of the building element """
        return self.__external_conditions.air_temp()
        # TODO For now, this only handles building elements to the outdoor
        #      environment, not e.g. elements to adjacent zones.
