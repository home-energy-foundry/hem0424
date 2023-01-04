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
from read_CIBSE_weather_file import CIBSE_weather_data_to_dict
from wrappers.future_homes_standard.future_homes_standard import \
    apply_fhs_preprocessing, apply_fhs_postprocessing
from wrappers.future_homes_standard.future_homes_standard_FEE import \
    apply_fhs_FEE_preprocessing


def run_project(
        inp_filename,
        external_conditions_dict,
        preproc_only=False,
        fhs_assumptions=False,
        fhs_FEE_assumptions=False,
        ):
    file_path = os.path.splitext(inp_filename)
    output_file = file_path[0] + '_results.csv'
    output_file_static = file_path[0] + '_results_static.csv'

    with open(inp_filename) as json_file:
        project_dict = json.load(json_file)

    if external_conditions_dict is not None:
        # Note: Shading segments are an assessor input regardless, so save them
        # before overwriting the ExternalConditions and re-insert after
        shading_segments = project_dict["ExternalConditions"]["shading_segments"]
        project_dict["ExternalConditions"] = external_conditions_dict
        project_dict["ExternalConditions"]["shading_segments"] = shading_segments

    # Apply required preprocessing steps, if any
    if fhs_assumptions:
        project_dict = apply_fhs_preprocessing(project_dict)
    elif fhs_FEE_assumptions:
        project_dict = apply_fhs_FEE_preprocessing(project_dict)

    if preproc_only:
        with open(file_path[0] + '_preproc.json', 'w') as preproc_file:
            json.dump(project_dict, preproc_file, sort_keys=True, indent=4)
        return # Skip actual calculation if preproc only option has been selected

    project = Project(project_dict)

    # Calculate static parameters and output
    heat_trans_coeff, heat_loss_param = project.calc_HTC_HLP()
    thermal_mass_param = project.calc_TMP()
    write_static_output_file(
        output_file_static,
        heat_trans_coeff,
        heat_loss_param,
        thermal_mass_param,
        )

    # Run main simulation
    timestep_array, results_totals, results_end_user, \
        energy_import, energy_export, betafactor, \
        zone_dict, zone_list, hc_system_dict, hot_water_dict,\
        ductwork_gains \
        = project.run()

    write_core_output_file(
        output_file,
        timestep_array,
        results_totals,
        results_end_user,
        energy_import,
        energy_export,
        betafactor,
        zone_dict,
        zone_list,
        hc_system_dict,
        hot_water_dict,
        ductwork_gains
        )

    # Apply required postprocessing steps, if any
    if fhs_assumptions:
        apply_fhs_postprocessing(project_dict, results_totals, energy_import, energy_export, timestep_array, file_path[0])

def write_static_output_file(output_file, heat_trans_coeff, heat_loss_param, thermal_mass_param):
    # Note: need to specify newline='' below, otherwise an extra carriage return
    # character is written when running on Windows
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Heat transfer coefficient', 'W / K', heat_trans_coeff])
        writer.writerow(['Heat loss parameter', 'W / m2.K', heat_loss_param])
        writer.writerow(['Thermal mass parameter', 'kJ / m2.K', thermal_mass_param])

def write_core_output_file(
        output_file,
        timestep_array,
        results_totals,
        results_end_user,
        energy_import,
        energy_export,
        betafactor,
        zone_dict,
        zone_list,
        hc_system_dict,
        hot_water_dict,
        ductwork_gains
        ):
    # Note: need to specify newline='' below, otherwise an extra carriage return
    # character is written when running on Windows
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)

        headings = ['Timestep']
        for totals_key in results_totals.keys():
            totals_header = str(totals_key)
            totals_header = totals_header + ' total'
            headings.append(totals_header)
            for end_user_key in results_end_user[totals_key].keys():
                headings.append(end_user_key)
            headings.append(str(totals_key) + ' import')
            headings.append(str(totals_key) + ' export')
            headings.append(str(totals_key) + ' beta factor')

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
        for system in hot_water_dict:
            headings.append(system)
        headings.append('Ductwork gains')
        writer.writerow(headings)

        for t_idx, timestep in enumerate(timestep_array):
            energy_use_row = []
            zone_row = []
            hc_system_row = []
            hw_system_row = []
            hw_system_row_energy = []
            hw_system_row_duration = []
            hw_system_row_events = []
            pw_losses_row = []
            ductwork_row = []
            energy_shortfall = []
            i = 0
            # Loop over end use totals
            for totals_key in results_totals:
                energy_use_row.append(results_totals[totals_key][t_idx])
                for end_user_key in results_end_user[totals_key]:
                    energy_use_row.append(results_end_user[totals_key][end_user_key][t_idx])
                energy_use_row.append(energy_import[totals_key][t_idx])
                energy_use_row.append(energy_export[totals_key][t_idx])
                energy_use_row.append(betafactor[totals_key][t_idx])
                # Loop over results separated by zone
            for zone in zone_list:
                for zone_outputs in zone_dict:
                    zone_row.append(zone_dict[zone_outputs][zone][t_idx])
                # Loop over heating and cooling system demand
            for system in hc_system_dict:
                for hc_name in hc_system_dict[system]:
                    hc_system_row.append(hc_system_dict[system][hc_name][t_idx])

            # loop over hot water demand
            hw_system_row.append(hot_water_dict['Hot water demand']['demand'][t_idx])
            hw_system_row_energy.append(hot_water_dict['Hot water energy demand']['energy_demand'][t_idx])
            hw_system_row_duration.append(hot_water_dict['Hot water duration']['duration'][t_idx])
            pw_losses_row.append(hot_water_dict['Pipework losses']['pw_losses'][t_idx])
            hw_system_row_events.append(hot_water_dict['Hot Water Events']['no_events'][t_idx])
            ductwork_row.append(ductwork_gains['ductwork_gains'][t_idx])

            row = [t_idx] + energy_use_row + zone_row + hc_system_row + \
            hw_system_row + hw_system_row_energy + hw_system_row_duration + \
            hw_system_row_events + pw_losses_row + ductwork_row + energy_shortfall
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
        '--CIBSE-weather-file',
        action='store',
        default=None,
        help=('path to CIBSE weather file in .csv format'),
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
    parser.add_argument(
        '--preprocess-only',
        action='store_true',
        default=False,
        help='run prepocessing step only',
        )
    wrapper_options = parser.add_mutually_exclusive_group()
    wrapper_options.add_argument(
        '--future-homes-standard',
        action='store_true',
        default=False,
        help='use Future Homes Standard calculation assumptions',
        )
    wrapper_options.add_argument(
        '--future-homes-standard-FEE',
        action='store_true',
        default=False,
        help='use Future Homes Standard Fabric Energy Efficiency assumptions',
        )
    cli_args = parser.parse_args()

    inp_filenames = cli_args.input_file
    epw_filename = cli_args.epw_file
    cibse_weather_filename = cli_args.CIBSE_weather_file
    fhs_assumptions = cli_args.future_homes_standard
    fhs_FEE_assumptions = cli_args.future_homes_standard_FEE
    preproc_only = cli_args.preprocess_only

    if epw_filename is not None:
        external_conditions_dict = weather_data_to_dict(epw_filename)
    elif cibse_weather_filename is not None:
        external_conditions_dict = CIBSE_weather_data_to_dict(cibse_weather_filename)
    
    else:
        external_conditions_dict = None

    if not cli_args.parallel:
        print('Running '+str(len(inp_filenames))+' cases in series')
        for inpfile in inp_filenames:
            run_project(
                inpfile,
                external_conditions_dict,
                preproc_only,
                fhs_assumptions,
                fhs_FEE_assumptions,
                )
    else:
        import multiprocessing as mp
        print('Running '+str(len(inp_filenames))+' cases in parallel')
        run_project_args = [
            (inpfile, external_conditions_dict, preproc_only, fhs_assumptions, fhs_FEE_assumptions)
            for inpfile in inp_filenames
            ]
        with mp.Pool() as p:
            p.starmap(run_project, run_project_args)

