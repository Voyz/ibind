from distutils.core import setup

from setuptools import find_packages


setup(
    name='ibind',
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests", "examples", "docs", "out", "dist"])
)
