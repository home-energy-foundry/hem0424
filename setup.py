from setuptools import setup
from Cython.Build import cythonize
from setuptools.command.build_ext import build_ext
import os

current_path = os.path.dirname(os.path.abspath(__file__))
target_path = os.path.join(current_path, "src")

class BuildExtCustom(build_ext):
    def finalize_options(self):
        super().finalize_options()
        self.build_lib = os.path.join(current_path, 'build_directory')
        self.build_temp = os.path.join(current_path, 'build_directory')


if __name__ == "__main__":
    print('Building project, converting to C')
    os.chdir(target_path)

    setup(
        name='sap',
        cmdclass={'build_ext': BuildExtCustom},
        ext_modules=cythonize([
                os.path.join(target_path, "core", "space_heat_demand", "zone.py"),
            ],
            language_level=3,
            exclude=["**/__init__.py"]
        ),
    )
