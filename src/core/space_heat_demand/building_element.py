#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides objects to represent building elements such as walls,
floors and windows. Each of these building elements is made up of 2 or more
nodes (at boundaries between layers) and is associated with a thermal zone.

Note that the temperatures at each node for each timestep of the calculation
are calculated and stored in the zone module, not here. This is based on the
method described in BS EN ISO 52016-1:2017, section 6.5.6.
"""

class BuildingElement:
    """ A base class with common functionality for building elements

    Classes for particular types of building element should inherit from this
    one and add/override functionality as required. It is not intended for
    objects of this class to be used directly.
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

        # List of thermal conductances (len = number of nodes - 1). Element 0
        # will be conductance between nodes 0 and 1.
        # Init these figures in relevant subclass __init__ func according to
        # BS EN ISO 52016-1:2017, section 6.5.7, not here.
        # self.h_pli =

        # List of areal heat capacities for each node
        # Init these figures in relevant subclass __init__ func according to
        # BS EN ISO 52016-1:2017, section 6.5.7, not here.
        # self.k_pli =

    def no_of_nodes(self):
        """ Return number of nodes including external and internal layers """
        return len(self.k_pli)

    def no_of_inside_nodes(self):
        """ Return number of nodes excluding external and internal layers """
        return self.no_of_nodes() - 2


