#!/usr/bin/env python3
# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
import os
import re

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


def find_version(fname):
    with open(fname, 'rt') as fd:
        contents = fd.read()
        match = re.search(r"^PNG_RECON_VERSION = ['\"]([^'\"]*)['\"]",
                          contents, re.M)
        if match:
            return match.group(1)
        raise RuntimeError('Unable to find version string')


setup(
    name='pngrecon',
    version=find_version('pngrecon/__main__.py'),
    description='PNG Recon',
    long_description=long_description,
    # url='',
    author='Matt Traudt',
    author_email='sirmatt@ksu.edu',
    # license='MIT',
    # https://packaging.python.org/tutorials/distributing-packages/#id48
    # https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',
    ],
    packages=find_packages(),
    keywords='steganography',
    python_requires='>=3',
    # test_suite='test',
    entry_points={
        'console_scripts': [
            'pngrecon = pngrecon.__main__:main',
        ]
    },
    install_requires=[
    ],
)
