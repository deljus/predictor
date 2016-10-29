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
import hashlib
import json
import os
from utils.utils import chemaxpost
import dill
import gzip
from MODtools.consensus import ConsensusDragos


class Model(ConsensusDragos):
    def __init__(self, file):
        tmp = dill.load(gzip.open(file, 'rb'))
        self.__models = tmp['models']
        self.__conf = tmp['config']
        self.__workpath = '.'

        self.Nlim = self.__conf.get('nlim', 1)
        self.TOL = self.__conf.get('tol', 1e10)
        self.unit = self.__conf.get('report_units')

        ConsensusDragos.__init__(self)

    def get_example(self):
        return self.__conf.get('example')

    def get_desc(self):
        return self.__conf.get('desc')

    def get_name(self):
        return self.__conf.get('name')

    def get_hashes(self):
        return self.__conf.get('hashes')

    def get_type(self):
        return self.__conf.get('type')

    def setworkpath(self, workpath):
        self.__workpath = workpath

    def get_results(self, structures):
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

                return res + self.report()
            else:
                return False
        else:
            return False


class ModelLoader(object):
    def __init__(self, skip_md5=True):
        self.__skip_md5 = skip_md5
        self.__models_path = os.path.join(os.path.dirname(__file__), 'modelbuilder')
        self.__cache_path = os.path.join(self.__models_path, '.cache')
        self.__models = self.__scan_models()

    @staticmethod
    def __md5(name):
        hash_md5 = hashlib.md5()
        with open(name, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def __scan_models(self):
        files = {x['file']: x for x in
                 dill.load(open(self.__cache_path, 'rb'))} if os.path.exists(self.__cache_path) else {}
        cache = {}
        for file in (os.path.join(self.__models_path, f) for f in os.listdir(self.__models_path)
                     if os.path.splitext(f)[-1] == '.model'):

            if file not in files or files[file]['size'] != os.path.getsize(file) or \
                            not self.__skip_md5 and self.__md5(file) != files[file]['hash']:
                try:
                    model = Model(file)
                    cache[model.get_name()] = dict(file=file, hash=self.__md5(file), example=model.get_example(),
                                                   desc=model.get_desc(), hashes=model.get_hashes(),
                                                   size=os.path.getsize(file),
                                                   type=model.get_type(), name=model.get_name())
                except:
                    pass
            else:
                cache[files[file]['name']] = files[file]

        dill.dump(list(cache.values()), open(self.__cache_path, 'wb'))
        return cache

    def load_model(self, name):
        if name in self.__models:
            return Model(self.__models[name]['file'])

    def get_models(self):
        return list(self.__models.values())
