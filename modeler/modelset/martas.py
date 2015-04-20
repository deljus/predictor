# -*- coding: utf-8 -*-
#
# Copyright 2015 Ramil Nugmanov <stsouko@live.ru>
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
import json
import os
import time
import subprocess as sp
from modelset import consensus_dragos, getmodelset, register_model, chemaxpost, standardize_dragos, ISIDAatommarker, \
    bondbox


class Model(consensus_dragos, standardize_dragos, ISIDAatommarker):
    def __init__(self):
        self.modelpath = os.path.join(os.path.dirname(__file__), 'martas')
        self.models = getmodelset(os.path.join(self.modelpath, "conf.xml"))
        self.Nlim = .6
        self.TOL = .8
        self.markerrule = os.path.join(self.modelpath, 'HalbondPharmFlags.xml')
        super().__init__()

    def getdesc(self):
        desc = 'example model with Dragos like consensus and structure prepare'
        return desc

    def getname(self):
        name = 'hb'
        return name

    def is_reation(self):
        return 0

    def gethashes(self):
        hashlist = []
        return hashlist

    def getresult(self, chemical):
        structure = chemical['structure']

        if structure != ' ':
            fixtime = int(time.time())
            temp_file_mol = "structure-%d.sdf" % fixtime
            temp_file_mol_path = os.path.join(self.modelpath, temp_file_mol)
            temp_file_res = "structure-%d.res" % fixtime
            temp_file_res_path = os.path.join(self.modelpath, temp_file_res)

            """
            self.standardize() method prepares structure for modeling and return True if OK else False
            """
            if self.standardize(structure, temp_file_mol_path, mformat="sdf"):
                """
                self.markatoms() create atom marking 7th column in SDF based on pmapper.
                need self.markerrule var with path to config.xml
                work like Utils/HBMap + map2markedatom.pl
                """
                self.markatoms(temp_file_mol_path)

                for model, params in self.models.items():
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
                            print(execparams)
                            # call fragmentor, smv prepare, svm-predict
                            sp.call(execparams, cwd=self.modelpath)
                    except:
                        print('model execution failed')
                    else:
                        try:
                            boxfile = os.path.join(self.modelpath, 'models', 'brute%s.range' % model)
                            fragments = os.path.join(self.modelpath, '%s.frag.svm' % temp_file_mol)
                            AD = bondbox(boxfile, fragments, 'svm')
                            with open(temp_file_res_path, 'r') as f:
                                for line in f:
                                    P = float(line)
                                    self.cumulate(P, AD)
                        except:
                            print('modeling results files broken or don\'t exist. skipped')

                files = os.listdir(self.modelpath)
                for x in files:
                    if 'structure-%d' % fixtime in x:
                        try:
                            os.remove(os.path.join(self.modelpath, x))
                        except:
                            print('something is very bad. file %s undeletable' % x)

                return self.report()
            else:
                return False
        else:
            return False


model = Model()
register_model(model.getname(), Model)