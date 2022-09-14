#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides the entry point to the program and defines the command-line interface.
"""

# Standard library imports
import sys
import json
import csv
import os

# Local imports
from core.project import Project

# TODO Rewrite this module with argparse library

inp_filename = sys.argv[1]
file_path = os.path.splitext(inp_filename)
output_file = file_path[0] + '_results.csv'

with open(inp_filename) as json_file:
    project_dict = json.load(json_file)

project = Project(project_dict)
timestep_array, results_totals, results_end_user, zone_dict, zone_list, hc_system_dict = project.run()

with open(output_file, 'w') as f:
    writer = csv.writer(f)

    headings = ['Timestep']
    for totals_key in results_totals.keys():
        totals_header = str(totals_key)
        totals_header = totals_header + ' total'
        headings.append(totals_header)
        for end_user_key in results_end_user[totals_key].keys():
            headings.append(end_user_key)

    for zone in zone_list:
        for zone_outputs in zone_dict.keys():
            zone_headings = zone_outputs + ' ' + zone
            headings.append(zone_headings)

    for system in hc_system_dict:
        for hc_name in hc_system_dict[system].keys():
            if hc_name == None:
                hc_name = 'None'
                hc_system_headings = system + ' ' + hc_name
            else:
                hc_system_headings = system + ' ' + hc_name
            headings.append(hc_system_headings)

    writer.writerow(headings)

    for t_idx, timestep in enumerate(timestep_array):
        energy_use_row = []
        zone_row = []
        hc_system_row = []
        i = 0
        # Loop over end use totals
        for totals_key in results_totals:
            energy_use_row.append(results_totals[totals_key][t_idx])
            for end_user_key in results_end_user[totals_key]:
                energy_use_row.append(results_end_user[totals_key][end_user_key][t_idx])
            # Loop over results separated by zone
        for zone in zone_list:
            for zone_outputs in zone_dict:
                zone_row.append(zone_dict[zone_outputs][zone][t_idx])
            # Loop over heating and cooling system demand
        for system in hc_system_dict:
            for hc_name in hc_system_dict[system]:
                hc_system_row.append(hc_system_dict[system][hc_name][t_idx])

        row = [t_idx] + energy_use_row + zone_row + hc_system_row
        writer.writerow(row)
