#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module contains unit tests for the notional building
"""

# Standard library imports
import unittest
import json
import os
from copy import deepcopy

# Set path to include modules to be tested (must be before local imports)
from unit_tests.common import test_setup
test_setup()

# Local imports
from core.simulation_time import SimulationTime
from core.space_heat_demand.building_element import HeatFlowDirection
from wrappers.future_homes_standard.future_homes_standard import calc_TFA
from wrappers.future_homes_standard import future_homes_standard_notional



class NotionalBuildingHeatPump(unittest.TestCase):
	""" Unit tests for Notional Building """

	def setUp(self):
		this_directory = os.path.dirname(os.path.relpath(__file__))
		file_path =  os.path.join(this_directory, "test_future_homes_standard_notional_input_data.json")
		with open(file_path) as json_file:
			self.project_dict = json.load(json_file)
		# Determine cold water source
		cold_water_type = list(self.project_dict['ColdWaterSource'].keys())
		if len(cold_water_type) == 1:
			self.cold_water_source = cold_water_type[0]
		else:
			sys.exit('Error: There should be exactly one cold water type')

		# Defaults
		self.hw_timer = "hw timer"
		self.hw_timer_eco7 = "hw timer eco7"
		self.notional_HP = 'notional_HP'
		self.is_notA = True
		self.is_FEE  = False
		self.energysupplyname_main = 'mains elec' 
		self.TFA = calc_TFA(self.project_dict)
		self.opening_lst = ['open_chimneys', 'open_flues', 'closed_fire', 'flues_d', 'flues_e',
						'blocked_chimneys', 'passive_vents', 'gas_fires']
		self.table_R2 = {
			'E1' : 0.05,
			'E2' : 0.05,
			'E3' : 0.05,
			'E4' : 0.05,
			'E5' : 0.16,
			'E19' : 0.07,
			'E20' : 0.32,
			'E21' : 0.32,
			'E22' : 0.07,
			'E6' : 0,
			'E7' : 0.07,
			'E8' : 0,
			'E9' : 0.02,
			'E23' : 0.02,
			'E10' : 0.06,
			'E24' : 0.24,
			'E11' : 0.04,
			'E12' : 0.06,
			'E13' : 0.08,
			'E14' : 0.08,
			'E15' : 0.56,
			'E16' : 0.09,
			'E17' : -0.09,
			'E18' : 0.06,
			'E25' : 0.06,
			'P1' : 0.08,
			'P6' : 0.07,
			'P2' : 0,
			'P3' : 0,
			'P7' : 0.16,
			'P8' : 0.24,
			'P4' : 0.12,
			'P5' : 0.08 ,
			'R1' : 0.08,
			'R2' : 0.06,
			'R3' : 0.08,
			'R4' : 0.08,
			'R5' : 0.04,
			'R6' : 0.06,
			'R7' : 0.04,
			'R8' : 0.06,
			'R9' : 0.04,
			'R10' : 0.08,
			'R11' : 0.08
			}

	def test_edit_lighting_efficacy(self):

		project_dict = deepcopy(self.project_dict)
		future_homes_standard_notional.edit_lighting_efficacy(project_dict)

		for zone in project_dict['Zone'].values():
			self.assertTrue("Lighting" in zone)
			self.assertEqual(zone["Lighting"]["efficacy"], 120)

	def test_edit_infiltration(self):

		project_dict = deepcopy(self.project_dict)
		is_notA = False
		future_homes_standard_notional.edit_infiltration(project_dict, is_notA)
		self.assertEqual(project_dict["Infiltration"]["test_type"], "50Pa")
		self.assertEqual(project_dict["Infiltration"]["test_result"], 5)

		project_dict = deepcopy(self.project_dict)
		is_notA = True
		future_homes_standard_notional.edit_infiltration(project_dict, is_notA)
		self.assertEqual(project_dict["Infiltration"]["test_type"], "50Pa")
		self.assertEqual(project_dict["Infiltration"]["test_result"], 4)

		for opening in self.opening_lst:
			self.assertEqual(project_dict["Infiltration"][opening], 0)

		self.assertTrue("NumberOfWetRooms" in project_dict)
		wet_rooms_count = project_dict["NumberOfWetRooms"]
		self.assertTrue(wet_rooms_count > 1)
		self.assertTrue("extract_fans" in project_dict["Infiltration"])
		self.assertEqual(project_dict["Infiltration"]["extract_fans"], wet_rooms_count)

	def test_edit_opaque_ajdZTU_elements(self):

		project_dict = deepcopy(self.project_dict)
		future_homes_standard_notional.edit_opaque_ajdZTU_elements(project_dict)

		for zone in project_dict["Zone"].values():
			for building_element in zone["BuildingElement"].values():
				if building_element["pitch"] == HeatFlowDirection.DOWNWARDS:
					self.assertEqual(building_element["u_value"], 0.13)
				elif building_element["pitch"] == HeatFlowDirection.UPWARDS:
					self.assertEqual(building_element["u_value"], 0.11)
				elif building_element["pitch"] == HeatFlowDirection.HORIZONTAL:
					if "is_external_door" in building_element:
						if building_element["is_external_door"]:
							self.assertEqual(building_element["u_value"], 1.0)
						else:
							self.assertEqual(building_element["u_value"], 0.18)
					else:
						self.assertEqual(building_element["u_value"], 0.18)

	def test_edit_ground_floors(self):

		project_dict = deepcopy(self.project_dict)
		future_homes_standard_notional.edit_ground_floors(project_dict)

		for zone in project_dict["Zone"].values():
			for building_element in zone["BuildingElement"].values():
				if building_element["type"] == "BuildingElementGround":
					self.assertEqual(building_element["u_value"], 0.13)
					self.assertEqual(building_element["r_f"], 6.12)
					self.assertEqual(building_element["psi_wall_floor_junc"], 0.16)

	def test_edit_thermal_bridging(self):

		project_dict = deepcopy(self.project_dict)
		future_homes_standard_notional.edit_thermal_bridging(project_dict)

		for zone in project_dict["Zone"].values():
			if "ThermalBridging" in zone:
				for thermal_bridge in zone["ThermalBridging"].values():
					if thermal_bridge["type"] == "ThermalBridgePoint":
						self.assertEqual(thermal_bridge["heat_transfer_coeff"], 0.0)
					elif thermal_bridge["type"] == "ThermalBridgeLinear":
						junction_type = thermal_bridge["junction_type"]
						self.assertTrue(junction_type in self.table_R2) 
						self.assertEqual(
							thermal_bridge["linear_thermal_transmittance"],
							self.table_R2[junction_type],
						)


	def test_edit_bath_shower_other(self):

		project_dict = deepcopy(self.project_dict)
		future_homes_standard_notional.edit_bath_shower_other(project_dict, self.cold_water_source)

		expected_bath = {
			"medium": {
				"ColdWaterSource": self.cold_water_source,
				"flowrate": 12,
				"size": 73
			}
		}

		expected_shower = {
			"mixer": {
				"ColdWaterSource": self.cold_water_source,
				"flowrate": 8,
				"type": "MixerShower"
			}
		}

		expected_other = {
			"other": {
				"ColdWaterSource": self.cold_water_source,
				"flowrate": 6
			}
		}

		self.assertDictEqual(project_dict['Bath'], expected_bath)
		self.assertDictEqual(project_dict['Shower'], expected_shower)
		self.assertDictEqual(project_dict['Other'], expected_other)

	def test_add_wwhrs(self):
		project_dict = deepcopy(self.project_dict)
		future_homes_standard_notional.add_wwhrs(project_dict, self.cold_water_source, self.is_notA, self.is_FEE)

		expected_wwhrs = {
			"Notional_Inst_WWHRS": {
				"ColdWaterSource": self.cold_water_source,
				"efficiencies": [50, 50],
				"flow_rates": [0, 100],
				"type": "WWHRS_InstantaneousSystemB",
				"utilisation_factor": 0.98
			}
		}

		if project_dict['Infiltration']['storeys_in_building'] > 1 and self.is_notA and not self.is_FEE:
			self.assertIn("WWHRS", project_dict)
			self.assertDictEqual(project_dict['WWHRS'], expected_wwhrs)
			self.assertEqual(project_dict['Shower']['mixer']["WWHRS"], "Notional_Inst_WWHRS")
		else:
			self.assertNotIn("WWHRS", project_dict)
			self.assertNotIn("WWHRS", project_dict['Shower']['mixer'])

	def test_calculate_daily_losses(self):
		expected_cylinder_vol = 265
		daily_losses = future_homes_standard_notional.calculate_daily_losses(expected_cylinder_vol)
		expected_daily_losses = 1.03685  

		self.assertAlmostEqual(daily_losses, expected_daily_losses, places=5)

	def test_edit_storagetank(self):
		project_dict = deepcopy(self.project_dict)
		future_homes_standard_notional.edit_storagetank(project_dict, self.cold_water_source, self.TFA)
		expected_primary_pipework_dict = {
			"internal_diameter_mm": 25,
			"external_diameter_mm": 27,
			"length": 2.0,
			"insulation_thermal_conductivity": 0.035,
			"insulation_thickness_mm": 25,
			"surface_reflectivity": False,
			"pipe_contents": "water"
		}

		expected_hotwater_source = {
			'hw cylinder': {
				'ColdWaterSource': self.cold_water_source,
				'HeatSource': {
					self.notional_HP: {
						'ColdWaterSource': self.cold_water_source,
						'Control': self.hw_timer,
						'Control_hold_at_setpnt': self.hw_timer_eco7,
						'EnergySupply': self.energysupplyname_main,
						'heater_position': 0.1,
						'name': self.notional_HP,
						'temp_flow_limit_upper': 60,
						'thermostat_position': 0.1,
						'type': 'HeatSourceWet'
					}
				},
				'daily_losses': 0.46660029577109363, 
				'type': 'StorageTank',
				'volume': 80.0,
				'primary_pipework': expected_primary_pipework_dict,
			}
		}
		self.assertDictEqual(project_dict['HotWaterSource'], expected_hotwater_source)

	def test_edit_hot_water_distribution_inner(self):

		project_dict = deepcopy(self.project_dict)
		future_homes_standard_notional.edit_hot_water_distribution_inner(project_dict, self.TFA)

		expected_hot_water_distribution_inner_dict = {
			"external_diameter_mm": 27,
			"insulation_thermal_conductivity": 0.035,
			"insulation_thickness_mm": 38, 
			"internal_diameter_mm": 25, 
			"length": 8.0,
			"pipe_contents": "water",
			"surface_reflectivity": False
		}

		self.assertDictEqual(project_dict['Distribution']['internal'], expected_hot_water_distribution_inner_dict)

	def test_edit_spacecoolsystem(self):

		project_dict = deepcopy(self.project_dict)
		project_dict['PartO_active_cooling_required'] = True

		future_homes_standard_notional.edit_spacecoolsystem(project_dict)

		for space_cooling_name, system in project_dict['SpaceCoolSystem'].items():
			self.assertEqual(system['efficiency'], 5.1)
			self.assertEqual(system['frac_convective'], 0.95)


	def test_add_solar_PV_house_only(self):

		project_dict = deepcopy(self.project_dict)
		expected_result = {'PV1': {
					'EnergySupply': 'mains elec',
					'orientation360': 180, 
					'peak_power': 4.444444444444445,
					'pitch': 45,
					'type': 'PhotovoltaicSystem', 
					'ventilation_strategy': 'moderately_ventilated',
					'base_height': 1,
					'height': 6.324555320336759,
					'width': 3.1622776601683795
					}
			}

		future_homes_standard_notional.add_solar_PV(project_dict, self.is_notA, self.is_FEE, self.TFA)

		self.assertDictEqual(project_dict['OnSiteGeneration'], expected_result)

