#!/usr/bin/env python3
# -*- coding: utf8 -*-

from __future__ import print_function

import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname),'r',encoding='utf-8').read()

setup(
    name = "CLAM2Switchboard",
    version = "0.2.2",
    author = "Maarten van Gompel",
    author_email = "proycon@anaproy.nl",
    description = ("Generate CLARIN Switchboard registry entries given a CLAM webservice"),
    license = "GPL",
    keywords = "software metadata pypi distutils",
    url = "https://github.com/proycon/clam2switchboard",
    packages=['clam2switchboard'],
    long_description=read('README.rst'),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Software Development",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Operating System :: POSIX",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
    zip_safe=False,
    include_package_data=True,
    install_requires=[ 'clam >= 3.0.18', 'codemetapy', 'iso-639'],
    entry_points = {    'console_scripts': [ 'clam2switchboard = clam2switchboard.clam2switchboard:main' ] },
)
