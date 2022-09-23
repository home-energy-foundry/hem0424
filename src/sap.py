#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides the entry point to the program and defines the command-line interface.
"""

# Standard library imports
import sys
import json
import csv
import os
import argparse

# Local imports
from core.project import Project
from read_weather_file import weather_data_to_dict


def run_project(inp_filename, external_conditions_dict):
    file_path = os.path.splitext(inp_filename)
    output_file = file_path[0] + '_results.csv'

    with open(inp_filename) as json_file:
        project_dict = json.load(json_file)

    if external_conditions_dict is not None:
        project_dict["ExternalConditions"] = external_conditions_dict

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

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SAP 11')
    parser.add_argument(
        '--epw-file', '-w',
        action='store',
        default=None,
        help=('path to weather file in .epw format'),
        )
    parser.add_argument(
        'input_file',
        nargs='+',
        help=('path(s) to file(s) containing building specifications to run'),
        )
    parser.add_argument(
        '--parallel', '-p',
        action='store_true',
        default=False,
        help='run calculations for different input files in parallel',
        )
    cli_args = parser.parse_args()

    inp_filenames = cli_args.input_file
    epw_filename = cli_args.epw_file

    if epw_filename is not None:
        external_conditions_dict = weather_data_to_dict(epw_filename)
    else:
        external_conditions_dict = None

    if not cli_args.parallel:
        print('Running '+str(len(inp_filenames))+' cases in series')
        for inpfile in inp_filenames:
            run_project(inpfile, external_conditions_dict)
    else:
        import multiprocessing as mp
        print('Running '+str(len(inp_filenames))+' cases in parallel')
        run_project_args = [(inpfile, external_conditions_dict) for inpfile in inp_filenames]
        with mp.Pool() as p:
            p.starmap(run_project, run_project_args)

