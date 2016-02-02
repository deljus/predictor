# -*- coding: utf-8 -*-
#
# Copyright 2015, 2016 Ramil Nugmanov <stsouko@live.ru>
# This file is part of PREDICTOR.
#
# PREDICTOR is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
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
import time
import subprocess as sp
import pickle
import gzip
from utils.utils import chemaxpost
from modeler.modelset import register_model
from modeler.consensus import ConsensusDragos
script_path = os.path.dirname(__file__)


class Model(ConsensusDragos, StandardizeDragos, ISIDAatommarker):
    def __init__(self, workpath, file):
        self.__models, self.__conf = pickle.load(gzip.open(file, 'rb'))
        self.__workpath = workpath

        self.Nlim = self.__conf.get('nlim', 0)
        self.TOL = self.__conf.get('tol', 1000000)

        StandardizeDragos.__init__()
        ConsensusDragos.__init__()
        if 'markerrule' in self.__conf:
            ISIDAatommarker.__init__(self.__conf.get('markerrule'), self.__workpath)

        self.__unit = self.__conf.get('report_units', None)

    def getexample(self):
        return self.__conf.get('example', ' ')

    def getdesc(self):
        return self.__conf.get('desc', 'no description')

    def getname(self):
        return self.__conf.get('name', 'no name')

    def is_reation(self):
        return 1 if self.__conf.get('is_reaction', False) else 0

    def gethashes(self):
        return self.__conf.get('hashes', [])

    def getresult(self, chemical):
        structure = chemical['structure']

        if structure != ' ':
            fixtime = int(time.time())
            temp_file_mol = "structure-%d.sdf" % fixtime
            temp_file_mol_path = os.path.join(self.__workpath, temp_file_mol)

            """
            self.standardize() method prepares structure for modeling and return True if OK else False
            """
            if not self.is_reation():
                stdmol = self.standardize(structure, mformat='sdf')
                if stdmol:
                    """
                    self.markatoms() create atom marking 7th column in SDF based on pmapper.
                    need self.markerrule var with path to config.xml
                    work like Utils/HBMap + map2markedatom.pl
                    """
                    if 'markerrule' in self.__conf:
                        stdmol = self.markatoms(stdmol)
                        structure = dict(type='structure', attrib='used structure', value=stdmol)
            else:
                stdmol = # get cgr

            for model in self.__models:
                model.setworkpath(self.__workpath)
                model.predict(stdmol)


                            with open(temp_file_res_path, 'r') as f:
                                for line in f:
                                    P = float(line)
                                    self.cumulate(P, AD)
                        except:
                            print('modeling results files broken or don\'t exist. skipped')

                files = os.listdir(self.__modelpath)
                for x in files:
                    if 'structure-%d' % fixtime in x:
                        try:
                            os.remove(os.path.join(self.__modelpath, x))
                        except:
                            print('something is very bad. file %s undeletable' % x)

                return [structure] + self.report(units=self.__unit)
            else:
                return False
        else:
            return False

files = os.listdir(script_path)
for i in files:
    if os.path.splitext(i)[1] == '.model':
        try:
            model = Model('.', i)
            register_model(model.getname(), Model, init=i)
        except:
            pass
