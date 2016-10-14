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
import json
import os
from utils.utils import chemaxpost
import pickle
import gzip
from modeler.consensus import ConsensusDragos


class Model(ConsensusDragos):
    def __init__(self, workpath, file):
        tmp = pickle.load(gzip.open(file, 'rb'))
        self.__models = tmp['models']
        self.__conf = tmp['config']
        self.__workpath = workpath

        self.Nlim = self.__conf.get('nlim', 1)
        self.TOL = self.__conf.get('tol', 1e10)

        ConsensusDragos.__init__(self)

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
        solvents = chemical['solvents'][0]['name'] if chemical['solvents'] else 'Water'
        # [dict(id=y.solvent.id, name=y.solvent.name, amount=y.amount)]
        temperature = chemical['temperature']

        if structure != ' ':
            q = chemaxpost('calculate/molExport', {"structure": structure, "parameters": "mol"})
            if q:
                structure = json.loads(q)['structure']
                res = [dict(type='structure', attrib='used structure', value=structure)]
                for model in self.__models:
                    model.setworkpath(self.__workpath)
                    pred = model.predict(structure, temperature=temperature, solvent=solvents)
                    # dict(prediction=pd.concat(pred, axis=1),
                    #      domain=pd.concat(dom, axis=1), y_domain=pd.concat(ydom, axis=1))
                    model.delworkpath()
                    print(pred)
                    for P, AD in zip((x for x in pred['prediction'].loc[0, :]),
                                     (x for x in pred['domain'].loc[0, :])):
                        self.cumulate(P, AD)

                return res + self.report(units=self.__unit)
            else:
                return False
        else:
            return False


def get_models():
    script_path = os.path.join(os.path.dirname(__file__), 'modelbuilder')
    files = os.listdir(script_path)
    models = []
    for m in (os.path.join(script_path, f) for f in files if os.path.splitext(f)[1] == '.model'):
        try:
            model = Model('/tmp', m)
            print('model name:', model.getname())
            models.append((model.getname(), Model, m))
        except:
            pass
    return models
