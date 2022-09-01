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
timestep_array, results_totals, results_end_user, temp_operative_array, temp_internal_air_array, z_name, space_heat_demand_array, space_cool_demand_array, h_name, space_heat_system_array, cooling_name, space_cool_system_array = project.run()

with open(output_file, 'w') as f:
    writer = csv.writer(f)

    headings = []
    i = 0
    for totals_key in results_totals.keys():
        totals_header = str(totals_key)
        totals_header = totals_header + ' total'
        headings.insert(i, totals_header)
        for end_user_key in results_end_user[totals_key].keys():
            headings.append(end_user_key)
            i = i + 1
    headings.insert(0, 'Timestep')
    headings.extend(['Operative temp', 'Internal air temp', 'Zone name', 'Space heat demand', 'Space cool demand', 'Heating system', 'Sum of space heating', 'Cooling system', 'Sum of cooling system'])
    writer.writerow(headings)

    j = 0
    for t_idx, timestep in enumerate(timestep_array):
        row = []
        i = 0
        for totals_key in results_totals:
            row.insert(i, results_totals[totals_key][t_idx])
            for end_user_key in results_end_user[totals_key]:
                row.append(results_end_user[totals_key][end_user_key][t_idx])
                i = i + 1

        row = [t_idx] + row + [temp_operative_array[j], temp_internal_air_array[j], z_name, space_heat_demand_array[j], space_cool_demand_array[j], h_name, space_heat_system_array[j], cooling_name, space_cool_system_array[j]]
        writer.writerow(row)
        j = j + 1
