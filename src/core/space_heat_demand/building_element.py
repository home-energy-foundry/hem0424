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

    def __init__(self, area, h_ci, h_ri, h_ce, h_re, a_sol):
        """ Initialisation common to all building element types

        Arguments (names based on those in BS EN ISO 52016-1:2017):
        area  -- area (in m2) of this building element
        h_ci  -- internal convective heat transfer coefficient, in W / (m2.K)
        h_ri  -- internal radiative heat transfer coefficient, in W / (m2.K)
        h_ce  -- external convective heat transfer coefficient, in W / (m2.K)
        h_re  -- external radiative heat transfer coefficient, in W / (m2.K)
        a_sol -- solar absorption coefficient at the external surface (dimensionless)
        """
        self.area  = area
        self.h_ci  = h_ci
        self.h_ri  = h_ri
        self.h_ce  = h_ce
        self.h_re  = h_re
        self.a_sol = a_sol

        # TODO beta_eli and gamma_eli are defined under eqn 41 in BS EN ISO 52016-1:2017.
        #      Where are they used?

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
            h_ci,
            h_ri,
            h_ce,
            h_re,
            a_sol,
            r_c,
            k_m,
            mass_distribution_class,
            ext_cond,
            ):
        """ Construct a BuildingElementOpaque object

        Arguments (names based on those in BS EN ISO 52016-1:2017):
        area     -- area (in m2) of this building element
        h_ci     -- internal convective heat transfer coefficient, in W / (m2.K)
        h_ri     -- internal radiative heat transfer coefficient, in W / (m2.K)
        h_ce     -- external convective heat transfer coefficient, in W / (m2.K)
        h_re     -- external radiative heat transfer coefficient, in W / (m2.K)
        a_sol    -- solar absorption coefficient at the external surface (dimensionless)
        r_c      -- thermal resistance, in m2.K / W
        k_m      -- areal heat capacity, in J / (m2.K)
        ext_cond -- reference to ExternalEnvironment object
        mass_distribution_class
                 -- distribution of mass in building element, one of:
                    - 'I':  mass concentrated on internal side
                    - 'E':  mass concentrated on external side
                    - 'IE': mass divided over internal and external side
                    - 'D':  mass equally distributed
                    - 'M':  mass concentrated inside
        """
        self.__external_conditions = ext_cond

        # Initialise the base BuildingElement class
        super().__init__(area, h_ci, h_ri, h_ce, h_re, a_sol)

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

