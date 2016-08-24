# -*- coding: utf-8 -*-
#
# Copyright 2015 Ramil Nugmanov <stsouko@live.ru>
# Copyright 2015 Oleg Varlamov <ovarlamo@gmail.com>
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
__author__ = 'stsouko'

TASK_CREATED = 0
REQ_MAPPING = 1
LOCK_MAPPING = 2
MAPPING_DONE = 3
REQ_MODELLING = 4
LOCK_MODELLING = 5
MODELLING_DONE = 6

SEARCH_TASK_CREATED = 10
LOCK_SEARCHING = 11
SEARCHING_DONE = 12

UPLOAD_PATH = './upload/'
ALLOWED_EXTENSIONS = ('rdf', 'sdf', 'mol', 'mrv', 'smi', 'smiles', 'rxn')

PORTAL_BASE = '/qspr'


UPLOAD_FOLDER = '/upload/'

SECRET_KEY = 'development key'
DEBUG = True
HOST = '0.0.0.0'
PORT = 5000

DB_USER = 'postgres'
DB_PASS = 'jyvt0n3'
DB_HOST = 'localhost'
DB_NAME = 'predictor'
