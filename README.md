# Introduction 
The Standard Assessment Procedure (SAP) is the UK Government’s National Calculation Methodology 
for assessing the energy performance of dwellings. It is used to facilitate various national, 
devolved and local government policies including Building Regulations and for the production of 
Energy Performance Certificates (EPCs).

SAP 11 is a version of SAP currently in development and should not be used for any official purpose.

# Getting Started
In order to run the code in this repository, it is recommended that you set up a Python Virtual
Environment and install the dependencies listed in the requirements.txt file.

You can do this as follows: with the top level of the repository as your working directory, set up
the Virtual Environment by running:

	# RHEL 7 / CentOS 7:
	python3 -m venv venv
	source ./venv/bin/activate
	pip install -r requirements.txt

	# Other systems:
	# TODO

To run the program, activate the Virtual Environment if it is not active already, and run the sap.py
file, e.g. (assuming the working directory is the top-level folder of the repository):

	# RHEL 7 / CentOS 7:
	python3 src/sap.py test/demo.json

	# Other systems
	# TODO

# Build and Test
TODO: Describe and show how to build your code and run the tests. 

# Contribute
SAP 11 is currently not at a stage where we are in a position to accept external contributions 
to the codebase.
