# -*- coding: utf-8 -*-
#
# Copyright 2015 Ramil Nugmanov <stsouko@live.ru>
# This file is part of PREDICTOR.
#
# PREDICTOR is free software; you can redistribute it and/or modify
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
import os

SERVER = "http://arsole.u-strasbg.fr"
PORT = 80
CHEMAXON = "%s:80/webservices" % SERVER
JCHEMBIN = '/home/server/ChemAxon/JChem/bin'
UPLOAD_PATH = '/home/server/upload/'
WORK_PATH = '/tmp'

INTERVAL = 3
THREAD_LIMIT = 5

STANDARD = open(os.path.join(os.path.dirname(__file__), "std_rules.xml")).read()

REQ_MAPPING = 1
LOCK_MAPPING = 2
MAPPING_DONE = 3
REQ_MODELLING = 4
LOCK_MODELLING = 5
MODELLING_DONE = 6

MOLCONVERT = os.path.join(JCHEMBIN, 'molconvert')
STANDARDIZER = os.path.join(JCHEMBIN, 'standardize')
CXCALC = os.path.join(JCHEMBIN, 'cxcalc')
REACTOR = os.path.join(JCHEMBIN, 'react')
JCSEARCH = os.path.join(JCHEMBIN, 'jcsearch')
PMAPPER = os.path.join(JCHEMBIN, 'pmapper')
