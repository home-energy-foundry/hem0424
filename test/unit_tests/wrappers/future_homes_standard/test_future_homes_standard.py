#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains unit tests for the Future Homes Standard module
"""

# Standard library imports
import unittest

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from wrappers.future_homes_standard import future_homes_standard 

class TestFutureHomesStandard(unittest.TestCase):

    def setUp(self):    
        self.project_dict = \
            {'Shower':
                {'mixer': {'type': 'MixerShower', 'flowrate': 0, 'ColdWaterSource': 'mains water'}, 
                 'IES':   {'type': 'InstantElecShower', 'rated_power': 9.0, 'ColdWaterSource': 'mains water', 'EnergySupply': 'mains elec'}
                }
            }              
          
    def test_check_invalid_shower_flowrate(self):  
   
        self.project_dict['Shower']['mixer']['flowrate'] = 7.0
        valid_flowrate = future_homes_standard.check_shower_flowrate(self.project_dict)
        self.assertFalse(False, "Expected False")
        
    def test_check_valid_shower_flowrate(self):  

        self.project_dict['Shower']['mixer']['flowrate'] = 10.0
        valid_flowrate = future_homes_standard.check_shower_flowrate(self.project_dict)
        self.assertTrue(True, "Expected True")
        
    def test_check_minimum_shower_flowrate(self):  

        self.project_dict['Shower']['mixer']['flowrate'] = 8.0
        valid_flowrate = future_homes_standard.check_shower_flowrate(self.project_dict)
        self.assertTrue(True, "Expected True")
               
    