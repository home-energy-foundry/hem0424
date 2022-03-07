#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides objects to represent the thermal zones in the building,
and to calculate the temperatures in the zone and associated building elements.
"""

class Zone:
    """ An object to represent a thermal zone in the building """

    def __init__(self, building_elements, simulation_time):
        """ Construct a Zone object

        Arguments:
        building_elements -- list of BuildingElement objects (walls, floors, windows etc.)
        simulation_time   -- reference to SimulationTime object
        
        Other variables:
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
        
        self.__building_elements = building_elements
        self.__simulation_time   = simulation_time

        # Calculate:
        # - size of required matrix/vectors (total number of nodes across all
        #   building elements + 1 for internal air)
        # - positions of node temperatures in matrix
        self.__element_positions = {}
        n = 0
        for eli in self.__building_elements:
            start_idx = n
            n = n + eli.no_of_nodes()
            end_idx = n - 1
            self.__element_positions[eli] = (start_idx, end_idx)
        self.__zone_idx = n
        self.__no_of_temps = n + 1
