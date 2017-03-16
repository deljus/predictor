#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright 2017 Ramil Nugmanov <stsouko@live.ru>
#  This file is part of MWUI.
#
#  MWUI is free software; you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
from MWUI.version import version
from setuptools import setup, find_packages

setup(
    name='MWUI',
    version=version(),
    packages=find_packages(),
    url='https://github.com/stsouko/predictor',
    license='AGPLv3',
    author='Dr. Ramil Nugmanov',
    author_email='stsouko@live.ru',
    description='MWUI',
    package_data={'': ['templates/*.html', 'static/css/*.css', 'static/js/*.js', 'static/js/predictor/*.js',
                       'static/js/predictor/result.htm', 'static/marvinjs/js/webservices.js',
                       'static/favicon.ico', 'static/logo.png', 'static/start.svg']},
    scripts=['mwui.py'],
    install_requires=['networkx>=2.0.dev', 'CGRtools>=2.6', 'CIMtools>=1.2', 'bitstring', 'redis', 'rq', 'bcrypt',
                      'cffi', 'psycopg2cffi', 'pony', 'validators', 'requests', 'pycountry', 'wtforms', 'dominate',
                      'misaka', 'werkzeug', 'jinja2', 'flask', 'flask-misaka', 'flask-nav', 'flask-restful',
                      'flask-resize', 'flask-wtf', 'flask-bootstrap', 'flask-login', 'flask-restful-swagger'],
    dependency_links=['git+https://github.com/networkx/networkx.git@master#egg=networkx-2.0.dev',
                      'git+https://github.com/stsouko/CGRtools.git@2.6#egg=CGRtools-2.6',
                      'git+https://github.com/stsouko/MODtools.git@1.2#egg=CIMtools-1.2'],
    long_description="MWUI - DataBase Management system and WEB QSPR predictor with Blog and Meeting's Management",

    keywords="MWUI database QSPR predictions interface WEB",
    classifiers=['Environment :: Web Environment',
                 'Intended Audience :: Science/Research',
                 'Intended Audience :: Developers',
                 'Topic :: Scientific/Engineering :: Chemistry',
                 'Topic :: Software Development :: Libraries :: Python Modules',
                 'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
                 'Operating System :: OS Independent',
                 'Programming Language :: Python',
                 'Programming Language :: Python :: 3',
                 'Programming Language :: Python :: 3.4',
                 'Programming Language :: Python :: 3.5',
                 ]
)
