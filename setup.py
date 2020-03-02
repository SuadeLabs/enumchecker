import os
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))

# Copy description from README.md
with open(os.path.join(here, "README.md"), "r") as f:
    DESCRIPTION = f.read()


setup(
    name="enumchecker",
    version="1.0.0",
    author="Suade Labs",
    py_modules=["enumchecker"],
    description="Checks your python enums. Eliminates common errors.",
    long_description=DESCRIPTION,
    classifiers=["Topic :: Software Development :: Testing"],
    entry_points={"console_scripts": ["enumchecker = enumchecker:main"]},
)
