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
from modeler.consensus import ConsensusDragos, getmodelset, standardize_dragos, ISIDAatommarker, bondbox
script_path = os.path.dirname(__file__)


class Model(ConsensusDragos, standardize_dragos, ISIDAatommarker):
    def __init__(self, file):
        self.__models, self.__conf = pickle.load(gzip.open(file, 'rb'))

        cons = self.__conf.get('consensus', dict(nlim=0, tol=1000000))
        self.Nlim = float(cons.get('nlim', 0))
        self.TOL = float(cons.get('tol', 1000000))

        if 'markerrule' in self.__conf:
            self.markerrule = self.__conf.get('markerrule')
            self.__markatoms = self.markatoms
        else:
            self.__markatoms = lambda x: None

        self.__unit = self.__conf.get('report_units', None)

        super().__init__()

    def getexample(self):
        desc = self.__conf.get('example', ' ')
        return desc

    def getdesc(self):
        desc = self.__conf.get('desc', 'no description')
        return desc

    def getname(self):
        name = self.__conf.get('name', 'no name')
        return name

    def is_reation(self):
        is_reaction = self.__conf.get('is_reaction', 'false').lower()
        return 1 if is_reaction == 'true' else 0

    def gethashes(self):
        hashlist = self.__conf.get('hashes', '').split()
        return hashlist

    def getresult(self, chemical):
        structure = chemical['structure']

        if structure != ' ':
            fixtime = int(time.time())
            temp_file_mol = "structure-%d.sdf" % fixtime
            temp_file_mol_path = os.path.join(self.__modelpath, temp_file_mol)
            temp_file_res = "structure-%d.res" % fixtime
            temp_file_res_path = os.path.join(self.__modelpath, temp_file_res)

            """
            self.standardize() method prepares structure for modeling and return True if OK else False
            """
            if self.standardize(structure, temp_file_mol_path, mformat=self.__std_out):
                """
                self.markatoms() create atom marking 7th column in SDF based on pmapper.
                need self.markerrule var with path to config.xml
                work like Utils/HBMap + map2markedatom.pl
                """
                self.__markatoms(temp_file_mol_path)

                with open(temp_file_mol_path) as f:
                    structure = dict(type='structure', attrib='used structure', value=f.read())

                for model, params in self.__models.items():
                    try:
                        for execparams in params:
                            tmp = []
                            for x in execparams:
                                if 'input_file' in x:
                                    x = x.replace('input_file', temp_file_mol)
                                elif 'output_file' in x:
                                    x = x.replace('output_file', temp_file_res)
                                tmp.append(x)
                            execparams = tmp
                            sp.call(execparams, cwd=self.__modelpath)
                    except:
                        print('model execution failed')
                    else:
                        try:


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
            model = Model(i)
            register_model(model.getname(), Model, init=i)
        except:
            pass
