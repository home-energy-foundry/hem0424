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

	# Windows 10:
	python -m venv venv
	venv\Scripts\activate.bat
	pip install -r requirements.txt

To run the program, activate the Virtual Environment if it is not active already, and run the sap.py
file, e.g. (assuming the working directory is the top-level folder of the repository):

	# RHEL 7 / CentOS 7:
	python3 src/sap.py test/demo.json

	# Windows 10:
	python src\sap.py test\demo.json

Note that the above requires an entire year's weather data to be provided in the input file.
Alternatively, a weather file can be provided in EnergyPlus (epw) format, after the appropriate
flag, e.g.:

	# RHEL 7 / CentOS 7:
	python3 src/sap.py test/demo.json --epw-file /path/to/weather_files/GBR_ENG_Leeds.Wea.Ctr.033470_TMYx.epw

	# Windows 10:
	python src\sap.py test\demo.json --epw-file C:\path\to\weather_files\GBR_ENG_Leeds.Wea.Ctr.033470_TMYx.epw

For a full list of command-line options, run the following:

	# RHEL 7 / CentOS 7:
	python3 src/sap.py --help

	# Windows 10:
	python src\sap.py --help


# Build and Test
## Unit tests
This project makes use of the unittest module in the Python standard library.

To run all unit tests (with the top level of the repository as your working directory), run:

	# RHEL 7 / CentOS 7:
	python3 -m unittest discover test/
	
	# Windows 10:
	python -m unittest discover test\

If the tests were successful, you should see output that looks similar to the below:

	Ran 4 tests in 0.001s
	
	OK

Make sure that the number of tests that ran is greater than zero. If any of the tests failed, the
output from running the unittest module should indicate the issue(s) that need to be resolved.

# Running using Cython
Cython can be used to compile Python code to C to improve the runtime of SAP. To do this you need to run slightly different commands.

Note. before running make sure you install cython.
```bash
pip install cython==0.29.35
```

Then you run the following commands to convert and run the C version of SAP.

### RHEL 7 / CentOS 7:
1. Cython compiler converting specific .py files to C and saving them to a new directory called "build_directory"
```bash
python3 setup.py build_ext -–inplace
``````

2. Then you can run SAP with a similar command, but looking at the build_directory/ rather than src/.
```bash
python3 build_directory/sap.py test/demo.json
```
	
### Windows 10:
1. Cython compiler converting specific .py files to C and saving them to a new directory called "build_directory"
```bash
python setup.py build_ext -–inplace
```
	
2. Then you can run SAP with a similar command, but looking at the build_directory/ rather than src/.
```bash
python build_directory\sap.py test\demo.json
```


# Contribute
SAP 11 is currently not at a stage where we are in a position to accept external contributions 
to the codebase.
