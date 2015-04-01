# -*- coding: utf-8 -*-
import os

__author__ = 'stsouko'

SERVER = "http://arsole.u-strasbg.fr"
PORT = 80
CHEMAXON = "%s:80/webservices" % SERVER
STANDARD = open(os.path.join(os.path.dirname(__file__), "std_rules.xml")).read()

INTERVAL = 3

REQ_MAPPING = 1
LOCK_MAPPING = 2
MAPPING_DONE = 3

MOLCONVERT = '/home/server/ChemAxon/JChem/bin/molconvert'
STANDARDIZER = '/home/server/ChemAxon/JChem/bin/standardize'

UPLOAD_PATH = '/home/server/upload/'

THREAD_LIMIT = 3