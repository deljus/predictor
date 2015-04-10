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
from math import sqrt
import numpy as np
import xmltodict as x2d
import time
import subprocess as sp


class Model():
    def __init__(self):
        self.modelpath = os.path.join(os.path.dirname(__file__), 'azide')
        self.Nlim = .6  # NLIM fraction
        self.TOL = .8
        self.models = self.getmodelset()
        self.trustdesc = {5: 'Optimal', 4: 'Good', 3: 'Medium', 2: 'Low'}

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
        TRUST = 5
        nin = ''
        data = {"structure": chemical['structure'], "parameters": "mol"}
        structure = chemaxpost('calculate/stringMolExport', data)
        temperature = str(chemical['temperature']) if chemical['temperature'] else '298'
        solvent = chemical['solvents'][0]['name'] if chemical['solvents'] else 'Undefined'

        if structure:
            result = []
            INlist = []
            ALLlist = []
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
                    print('YOU DO IT WRONG')
                else:
                    with open(temp_file_res, 'r') as f:
                        res = json.load(f)
                        AD = True if res['applicability_domain'].lower() == 'true' else False
                        P = float(res['predicted_value'])

                    if AD:
                        INlist.append(P)

                    ALLlist.append(P)

            INarr = np.array(INlist)
            ALLarr = np.array(ALLlist)

            PavgIN = INarr.mean()
            PavgALL = ALLarr.mean()

            if len(INlist) > self.Nlim * len(ALLlist):
                sigma = sqrt((INarr ** 2).mean() - PavgIN ** 2)
                Pavg = PavgIN
            else:
                sigma = sqrt((ALLarr ** 2).mean() - PavgALL ** 2)
                Pavg = PavgALL
                nin = 'not enought models include structure in their applicability domain<br>'
                TRUST -= 1

            if not (len(INlist) > 0 and PavgIN - PavgALL < self.TOL):
                nin += 'prediction within and outside applicability domain differ more then TOL<br>'
                TRUST -= 1

            proportion = int(sigma / self.TOL)
            if proportion:
                TRUST -= proportion
                nin += 'proportionally to the ratio of sigma/tol'

            result.append(dict(type='text', attrib='predicted value ± sigma', value='%.2f ± %.2f' % (Pavg, sigma)))
            result.append(dict(type='text', attrib='prediction trust', value=self.trustdesc.get(TRUST, 'None')))
            if nin:
                result.append(dict(type='text', attrib='reason', value=nin))
            os.remove(temp_file_mol)
            os.remove(temp_file_res)

            return result
        else:
            return False

    def getmodelset(self):
        conffile = os.path.join(self.modelpath, "conf.xml")
        conf = x2d.parse(open(conffile, 'r').read())['models']['model']
        if not isinstance(conf, list):
            conf = [conf]
        return {x['name']: [x['script']['exec_path']] + [y['name'] for y in x['script']['params']['param']] for x in
                conf}


model = Model()

if __name__ == '__main__':
    print(model.getresult({'temperature': '300', 'solvents': [{'name': 'water'}],
                           'structure': '''$RDFILE 1
$DATM    04/10/15 16:36
$RFMT
$RXN

  Marvin       041001151636

  1  1
$MOL

Mrv1532 04101516362D

  2  1  0  0  0  0            999 V2000
   -0.9708   -0.5920    0.0000 Br  0  0  0  0  0  0  0  0  0  1  0  0
   -1.6853   -1.0045    0.0000 C   0  0  0  0  0  0  0  0  0  2  0  0
  2  1  1  0  0  0  0
M  END
$MOL

Mrv1532 04101516362D

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

'''}))

else:
    from modelset import register_model, chemaxpost

    register_model(model.getname(), model)