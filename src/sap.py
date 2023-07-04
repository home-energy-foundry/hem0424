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
import core.units as units
from read_weather_file import weather_data_to_dict
from read_CIBSE_weather_file import CIBSE_weather_data_to_dict
from wrappers.future_homes_standard.future_homes_standard import \
    apply_fhs_preprocessing, apply_fhs_postprocessing
from wrappers.future_homes_standard.future_homes_standard_FEE import \
    apply_fhs_FEE_preprocessing, apply_fhs_FEE_postprocessing


def run_project(
        inp_filename,
        external_conditions_dict,
        preproc_only=False,
        fhs_assumptions=False,
        fhs_FEE_assumptions=False,
        heat_balance=False,
        use_fast_solver=False,
        ):
    file_path = os.path.splitext(inp_filename)
    output_file = file_path[0] + '_results.csv'
    output_file_static = file_path[0] + '_results_static.csv'
    output_file_summary = file_path[0] + '_results_summary.csv'

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

    project = Project(project_dict, heat_balance, use_fast_solver)

    # Calculate static parameters and output
    heat_trans_coeff, heat_loss_param = project.calc_HTC_HLP()
    thermal_mass_param = project.calc_TMP()
    heat_loss_form_factor = project.calc_HLFF()
    write_static_output_file(
        output_file_static,
        heat_trans_coeff,
        heat_loss_param,
        thermal_mass_param,
        heat_loss_form_factor,
        )

    # Run main simulation
    timestep_array, results_totals, results_end_user, \
        energy_import, energy_export, energy_generated_consumed, betafactor, \
        zone_dict, zone_list, hc_system_dict, hot_water_dict,\
        ductwork_gains, heat_balance_dict \
        = project.run()

    write_core_output_file(
        output_file,
        timestep_array,
        results_totals,
        results_end_user,
        energy_import,
        energy_export,
        energy_generated_consumed,
        betafactor,
        zone_dict,
        zone_list,
        hc_system_dict,
        hot_water_dict,
        ductwork_gains
        )

    if heat_balance:
        hour_per_step = project_dict['SimulationTime']['step']
        for hb_name, hb_dict in heat_balance_dict.items():
            heat_balance_output_file = file_path[0] + '_results_heat_balance_' + hb_name + '.csv'
            write_heat_balance_output_file(
                heat_balance_output_file,
                timestep_array,
                hour_per_step,
                hb_dict,
                )

    # Sum per-timestep figures as needed
    space_heat_demand_total = sum(sum(h_dem) for h_dem in zone_dict['Space heat demand'].values())
    space_cool_demand_total = sum(sum(c_dem) for c_dem in zone_dict['Space cool demand'].values())

    write_core_output_file_summary(
        output_file_summary,
        space_heat_demand_total,
        space_cool_demand_total,
        )

    # Apply required postprocessing steps, if any
    if fhs_assumptions:
        apply_fhs_postprocessing(
            project_dict,
            results_totals,
            energy_import,
            energy_export,
            results_end_user,
            timestep_array,
            file_path[0],
            )
    elif fhs_FEE_assumptions:
        postprocfile = file_path[0] + '_postproc.csv'
        total_floor_area = project.total_floor_area()
        apply_fhs_FEE_postprocessing(
            postprocfile,
            total_floor_area,
            space_heat_demand_total,
            space_cool_demand_total,
            )

def write_static_output_file(output_file, heat_trans_coeff, heat_loss_param, thermal_mass_param,heat_loss_form_factor):
    # Note: need to specify newline='' below, otherwise an extra carriage return
    # character is written when running on Windows
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Heat transfer coefficient', 'W / K', heat_trans_coeff])
        writer.writerow(['Heat loss parameter', 'W / m2.K', heat_loss_param])
        writer.writerow(['Thermal mass parameter', 'kJ / m2.K', thermal_mass_param])
        writer.writerow(['Heat loss form factor','',heat_loss_form_factor])

def write_heat_balance_output_file(
        heat_balance_output_file,
        timestep_array,
        hour_per_step,
        heat_balance_dict,
        ):
    with open(heat_balance_output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        headings = ['Timestep']
        units_row = ['index']
        rows = ['']

        headings_annual = ['']
        units_annual = ['']

        nbr_of_zones = 0
        for z_name, heat_loss_gain_dict in heat_balance_dict.items():
            for heat_loss_gain_name in heat_loss_gain_dict.keys():
                headings.append(z_name+': '+heat_loss_gain_name)
                units_row.append('[W]')
            nbr_of_zones += 1

        for z_name, heat_loss_gain_dict in heat_balance_dict.items():
            annual_totals = [0]*(len(heat_loss_gain_dict.keys())*nbr_of_zones)
            annual_totals.insert(0,'')
            for heat_loss_gain_name in heat_loss_gain_dict.keys():
                headings_annual.append(z_name+': total '+heat_loss_gain_name)
                units_annual.append('[kWh]')

        for t_idx, timestep in enumerate(timestep_array):
            row = [t_idx]
            annual_totals_index = 1
            for z_name, heat_loss_gain_dict in heat_balance_dict.items():
                for heat_loss_gain_name in heat_loss_gain_dict.keys():
                    row.append(heat_loss_gain_dict[heat_loss_gain_name][t_idx])
                    annual_totals[annual_totals_index] += \
                        heat_loss_gain_dict[heat_loss_gain_name][t_idx]*hour_per_step/units.W_per_kW
                    annual_totals_index += 1
            rows.append(row)

        writer.writerow(headings_annual)
        writer.writerow(units_annual)
        writer.writerow(annual_totals)
        writer.writerow([''])
        writer.writerow(headings)
        writer.writerow(units_row)
        writer.writerows(rows)

def write_core_output_file(
        output_file,
        timestep_array,
        results_totals,
        results_end_user,
        energy_import,
        energy_export,
        energy_generated_consumed,
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
        units_row = ['[count]']
        for totals_key in results_totals.keys():
            totals_header = str(totals_key)
            totals_header = totals_header + ' total'
            headings.append(totals_header)
            units_row.append('[kWh]')
            for end_user_key in results_end_user[totals_key].keys():
                headings.append(end_user_key)
                units_row.append('[kWh]')
            headings.append(str(totals_key) + ' import')
            units_row.append('[kWh]')
            headings.append(str(totals_key) + ' export')
            units_row.append('[kWh]')
            headings.append(str(totals_key) + ' generated and consumed')
            units_row.append('[kWh]')
            headings.append(str(totals_key) + ' beta factor')
            units_row.append('[ratio]')

        # Dictionary for most of the units (future output headings need respective units)
        unitsDict = {
            'Internal gains': '[W]',
            'Solar gains': '[W]',
            'Operative temp': '[deg C]',
            'Internal air temp': '[deg C]',
            'Space heat demand': '[kWh]',
            'Space cool demand': '[kWh]',
            'Hot water demand': '[litres]',
            'Hot water energy demand': '[kWh]',
            'Hot water duration': '[mins]',
            'Hot Water Events': '[count]',
            'Pipework losses': '[kWh]'
        }

        for zone in zone_list:
            for zone_outputs in zone_dict.keys():
                zone_headings = zone_outputs + ' ' + zone
                headings.append(zone_headings)
                if zone_outputs in unitsDict:
                    units_row.append(unitsDict.get(zone_outputs))
                else:
                    units_row.append('Unit not defined (unitsDict sap.py)')

        for system in hc_system_dict:
            for hc_name in hc_system_dict[system].keys():
                if hc_name == None:
                    hc_name = 'None'
                    hc_system_headings = system + ' ' + hc_name
                else:
                    hc_system_headings = system + ' ' + hc_name
                headings.append(hc_system_headings)
                units_row.append('[kWh]')
        #Hot_water_dict headings
        for system in hot_water_dict:
            headings.append(system)
            if system in unitsDict:
                units_row.append(unitsDict.get(system))
            else:
                units_row.append('Unit not defined (add to unitsDict sap.py)')

        headings.append('Ductwork gains')
        units_row.append('[kWh]')

        # Write headings & units to output file
        writer.writerow(headings)
        writer.writerow(units_row)

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
                energy_use_row.append(energy_generated_consumed[totals_key][t_idx])
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

            # create row of outputs and write to output file
            row = [t_idx] + energy_use_row + zone_row + hc_system_row + \
            hw_system_row + hw_system_row_energy + hw_system_row_duration + \
            hw_system_row_events + pw_losses_row + ductwork_row + energy_shortfall
            writer.writerow(row)

def write_core_output_file_summary(
        output_file_summary,
        space_heat_demand_total,
        space_cool_demand_total,
        ):
    # Note: need to specify newline='' below, otherwise an extra carriage return
    # character is written when running on Windows
    with open(output_file_summary, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['', '', 'Total'])
        writer.writerow(['Space heat demand', 'kWh', space_heat_demand_total])
        writer.writerow(['Space cool demand', 'kWh', space_cool_demand_total])


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
        action='store',
        type=int,
        default=0,
        help=('run calculations for different input files in parallel'
              '(specify no of files to run simultaneously)'),
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
    parser.add_argument(
        '--heat-balance',
        action='store_true',
        default=False,
        help='output heat balance for each zone',
        )
    parser.add_argument(
        '--no-fast-solver',
        action='store_true',
        default=False,
        help=('disable optimised solver (results may differ slightly due '
              'to reordering of floating-point ops); this option is '
              'provided to facilitate verification and debugging of the '
              'optimised version')
        )
    cli_args = parser.parse_args()

    inp_filenames = cli_args.input_file
    epw_filename = cli_args.epw_file
    cibse_weather_filename = cli_args.CIBSE_weather_file
    fhs_assumptions = cli_args.future_homes_standard
    fhs_FEE_assumptions = cli_args.future_homes_standard_FEE
    preproc_only = cli_args.preprocess_only
    heat_balance = cli_args.heat_balance
    use_fast_solver = not cli_args.no_fast_solver

    if epw_filename is not None:
        external_conditions_dict = weather_data_to_dict(epw_filename)
    elif cibse_weather_filename is not None:
        external_conditions_dict = CIBSE_weather_data_to_dict(cibse_weather_filename)
    
    else:
        external_conditions_dict = None

    if cli_args.parallel == 0:
        print('Running '+str(len(inp_filenames))+' cases in series')
        for inpfile in inp_filenames:
            run_project(
                inpfile,
                external_conditions_dict,
                preproc_only,
                fhs_assumptions,
                fhs_FEE_assumptions,
                heat_balance,
                use_fast_solver,
                )
    else:
        import multiprocessing as mp
        print('Running '+str(len(inp_filenames))+' cases in parallel'
              ' ('+str(cli_args.parallel)+' at a time)')
        run_project_args = [
            ( inpfile,
              external_conditions_dict,
              preproc_only,
              fhs_assumptions,
              fhs_FEE_assumptions,
              heat_balance,
              use_fast_solver,
            )
            for inpfile in inp_filenames
            ]
        with mp.Pool(processes=cli_args.parallel) as p:
            p.starmap(run_project, run_project_args)

