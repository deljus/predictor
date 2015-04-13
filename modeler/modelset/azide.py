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
if __name__ == '__main__':
    from mutils.concensus import concensus_dragos, getmodelset
else:
    from .mutils.concensus import concensus_dragos, getmodelset


class Model(concensus_dragos):
    def __init__(self):
        super().__init__()
        self.modelpath = os.path.join(os.path.dirname(__file__), 'azide')
        self.models = getmodelset(os.path.join(self.modelpath, "conf.xml"))
        self.Nlim = .6
        self.TOL = .8

    def getdesc(self):
        desc = 'sn2 reactions of azides salts with halogen alkanes constants prediction'
        return desc

    def getname(self):
        name = 'azide-halogen substitution'
        return name

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
        structure = chemaxpost('calculate/stringMolExport', data) if __name__ != '__main__' else chemical['structure']
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

if __name__ == '__main__':

    print(model.getresult({'temperature': '30', 'solvents': [{'name': 'water'}],
                           'structure': '''$RDFILE 1
$DATM    04/13/15 15:31
$RFMT
$RXN

  Marvin       041301151531

  2  2
$MOL

  Mrv0541 04131515312D

  3  2  0  0  0  0            999 V2000
   -4.9623    0.4615    0.0000 N   0  5  0  0  0  0  0  0  0  5  0  0
   -4.2478    0.0491    0.0000 N   0  3  0  0  0  0  0  0  0  4  0  0
   -4.2478   -0.7759    0.0000 N   0  5  0  0  0  0  0  0  0  3  0  0
  2  1  2  0  0  0  0
  3  2  2  0  0  0  0
M  CHG  3   1  -1   2   1   3  -1
M  END
$MOL

  Mrv0541 04131515312D

  2  1  0  0  0  0            999 V2000
   -0.9708   -0.2384    0.0000 Cl  0  0  0  0  0  0  0  0  0  1  0  0
   -1.6853   -0.6509    0.0000 C   0  0  0  0  0  0  0  0  0  2  0  0
  2  1  1  0  0  0  0
M  END
$MOL

  Mrv0541 04131515312D

  4  3  0  0  0  0            999 V2000
    4.6319   -0.6812    0.0000 N   0  0  0  0  0  0  0  0  0  3  0  0
    3.9174   -1.0937    0.0000 C   0  0  0  0  0  0  0  0  0  2  0  0
    4.6319    0.1438    0.0000 N   0  3  0  0  0  0  0  0  0  4  0  0
    3.9174    0.5562    0.0000 N   0  5  0  0  0  0  0  0  0  5  0  0
  2  1  1  0  0  0  0
  1  3  2  0  0  0  0
  3  4  2  0  0  0  0
M  CHG  2   3   1   4  -1
M  END
$MOL

  Mrv0541 04131515312D

  1  0  0  0  0  0            999 V2000
    6.1875   -0.3315    0.0000 Cl  0  5  0  0  0  0  0  0  0  1  0  0
M  CHG  1   1  -1
M  END
'''}))

else:
    from modelset import register_model, chemaxpost
    register_model(model.getname(), Model)