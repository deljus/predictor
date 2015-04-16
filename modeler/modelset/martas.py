# -*- coding: utf-8 -*-
#
# Copyright 2015 Ramil Nugmanov <stsouko@live.ru>
# This file is part of PREDICTOR.
#
# PREDICTOR is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
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
import json
import os
import time
import subprocess as sp
from modelset import consensus_dragos, getmodelset, register_model, chemaxpost, standardize_dragos


class Model(consensus_dragos, standardize_dragos):
    def __init__(self):
        super().__init__()
        self.modelpath = os.path.join(os.path.dirname(__file__), 'martas')
        self.models = getmodelset(os.path.join(self.modelpath, "conf.xml"))
        self.Nlim = .6
        self.TOL = .8

    def getdesc(self):
        desc = 'example model with Dragos like consensus and structure prepare'
        return desc

    def getname(self):
        name = 'example mol'
        return name

    def is_reation(self):
        return 0

    def gethashes(self):
        hashlist = []
        return hashlist

    def getresult(self, chemical):
        structure = chemical['structure']
        temperature = str(chemical['temperature']) if chemical['temperature'] else '298'
        solvent = chemical['solvents'][0]['name'] if chemical['solvents'] else 'Undefined'

        if structure != ' ':
            fixtime = int(time.time())
            temp_file_mol = os.path.join(self.modelpath, "structure-%d.mol" % fixtime)
            temp_file_res = os.path.join(self.modelpath, "structure-%d.res" % fixtime)

            replace = {'input_file': temp_file_mol, 'output_file': temp_file_res,
                       'temperature': temperature, 'solvent': solvent}

            with open(temp_file_mol, 'w') as f:
                f.write(structure)

            """
            self.standardize() method prepares structure for modeling and return True if OK else False
            """
            if self.standardize(temp_file_mol):
                for model, params in self.models.items():
                    try:
                        params = [replace.get(x, x) for x in params]
                        params[0] = os.path.join(self.modelpath, params[0])
                        sp.call(params)
                    except:
                        print('model execution failed')
                    else:
                        try:
                            with open(temp_file_res, 'r') as f:
                                res = json.load(f)
                                AD = True if res['applicability_domain'].lower() == 'true' else False
                                P = float(res['predicted_value'])
                                self.cumulate(P, AD)
                        except:
                            print('model result file broken or don\'t exist')
                        finally:
                            try:
                                os.remove(temp_file_res)
                            except:
                                pass

            os.remove(temp_file_mol)

            return self.report()
        else:
            return False

model = Model()
register_model(model.getname(), Model)