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
from modeler.consensus import consensus_dragos, getmodelset
from utils.utils import chemaxpost
from modeler.modelset import register_model


class Model(consensus_dragos):
    def __init__(self):
        self.modelpath = os.path.join(os.path.dirname(__file__), 'azide')
        self.models = getmodelset(os.path.join(self.modelpath, "conf.xml"))[0]
        self.Nlim = .6
        self.TOL = .8
        super().__init__()

    def getdesc(self):
        desc = 'sn2 reactions of azides salts with halogen alkanes constants prediction'
        return desc

    def getname(self):
        name = 'azide-halogen substitution'
        return name

    def getexample(self):
        return '[I:8][CH2:2][c:1]1[cH:3][cH:4][cH:5][cH:6][cH:7]1.[N-:9]=[N+:10]=[N-:11]>>[N-:11]=[N+:10]=[N:9][CH2:2][c:1]1[cH:7][cH:6][cH:5][cH:4][cH:3]1.[I-:8]'

    def is_reation(self):
        return 1

    def gethashes(self):
        hashlist = ['1006099,1017020,2007079', '1006099,1035020,2007079', '1006099,1053020,2007079',  # balanced fp
                    '1006099,1017018,2007079', '1006099,1035018,2007079', '1006099,1053018,2007079',  #unbal leaving gr
                    '1006099,1017018,2007081', '1006099,1035018,2007081',
                    '1006099,1053018,2007081']  #unbal leav and nuc
        return hashlist

    def getresult(self, chemical):
        data = {"structure": chemical['structure'], "parameters": "rdf"}
        structure = chemaxpost('calculate/stringMolExport', data)
        temperature = str(chemical['temperature']) if chemical['temperature'] else '298'
        solvent = chemical['solvents'][0]['name'] if chemical['solvents'] else 'Undefined'

        if structure:
            fixtime = int(time.time())
            temp_file_mol = os.path.join(self.modelpath, "structure-%d.mol" % fixtime)
            temp_file_res = os.path.join(self.modelpath, "structure-%d.res" % fixtime)

            replace = {'input_file': temp_file_mol, 'output_file': temp_file_res,
                       'temperature': temperature, 'solvent': solvent}

            with open(temp_file_mol, 'w') as f:
                f.write(structure)

            for model, params in self.models.items():
                try:
                    params = [replace.get(x, x) for x in params[0]]
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