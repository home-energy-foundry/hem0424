#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides the entry point to the program and defines the command-line interface.
"""

# Standard library imports
import sys
import json

# Local imports
from core.project import Project


# TODO Rewrite this module with argparse library

with open(sys.argv[1]) as json_file:
    project_dict = json.load(json_file)

project = Project(project_dict)
print(project.run())
