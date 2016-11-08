# -*- coding: utf-8 -*-
#
# Copyright 2016 Ramil Nugmanov <stsouko@live.ru>
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
import dill
import subprocess as sp
from io import StringIO
from itertools import count
from MODtools.consensus import ConsensusDragos
from MODtools.config import MOLCONVERT
from MODtools.utils import chemaxpost
from CGRtools.files.RDFrw import RDFread, RDFwrite
from CGRtools.files.SDFrw import SDFwrite


class Model(ConsensusDragos):
    def __init__(self, directory):
        self.__conf = self.__load_model(directory)
        self.__workpath = '.'

        self.Nlim = self.__conf.get('nlim', 1)
        self.TOL = self.__conf.get('tol', 1e10)
        self.unit = self.__conf.get('report_units')

        ConsensusDragos.__init__(self)

    @staticmethod
    def __load_model(directory):
        with open(os.path.join(directory, 'model.json')) as f:
            tmp = json.load(f)
        return tmp

    def get_example(self):
        return self.__conf.get('example')

    def get_description(self):
        return self.__conf.get('desc')

    def get_name(self):
        return self.__conf.get('name')

    def get_type(self):
        return self.__conf.get('type')

    def setworkpath(self, workpath):
        self.__workpath = workpath

    def get_results(self, structures):
        structure_file = os.path.join(self.__workpath, 'structures')
        results_file = os.path.join(self.__workpath, 'results.csv')

        # prepare input file
        if len(structures) == 1:
            chemaxed = chemaxpost('calculate/molExport',
                                  dict(structure=structures[0]['data'], parameters="rdf"))
            if not chemaxed:
                return False
            data = chemaxed['structure']
        else:
            with sp.Popen([MOLCONVERT, 'rdf'], stdin=sp.PIPE, stdout=sp.PIPE,
                          stderr=sp.STDOUT, cwd=self.__workpath) as convert_mol:
                data = convert_mol.communicate(input=''.join(s['data'] for s in structures).encode())[0].decode()
                if convert_mol.returncode != 0:
                    return False

        mark = 0
        counter = count()
        with StringIO(data) as in_file, open(structure_file, 'w') as out_file:
            rdf = RDFwrite(out_file)
            sdf = SDFwrite(out_file)
            for r, meta in zip(RDFread(in_file).read(), structures):
                next(counter)
                r['meta'] = dict(pressure=meta['pressure'], temperature=meta['temperature'])
                for n, a in enumerate(meta['additives'], start=1):
                    r['meta']['additive.amount.%d' % n] = '%s: %f' % (a['name'], a['amount'])

                if mark in (0, 1) and r['products'] and r['substrats']:  # ONLY FULL REACTIONS
                    mark = 1
                    rdf.write(r)
                elif mark in (0, 2) and r['substrats']:  # MOLECULES AND MIXTURES
                    mark = 2
                    g = r['substrats'][0]
                    g.graph['meta'] = r['meta']
                    sdf.write(g)

        if len(structures) != next(counter):
            return False

        if sp.call([self.__conf['start']], cwd=self.__workpath) == 0:
            # parese output file
            return  # result

        return False


class ModelLoader(object):
    def __init__(self, **kwargs):
        self.__models_path = os.path.join(os.path.dirname(__file__), 'custommodel')
        self.__cache_path = os.path.join(self.__models_path, '.cache')
        self.__models = self.__scan_models()

    def __scan_models(self):
        directories = {x['directory']: x for x in
                       dill.load(open(self.__cache_path, 'rb'))} if os.path.exists(self.__cache_path) else {}
        cache = {}
        for directory in (os.path.join(self.__models_path, f) for f in os.listdir(self.__models_path)
                          if os.path.splitext(f)[-1] == '.model'):

            if directory not in directories:
                try:
                    model = Model(directory)
                    cache[model.get_name()] = dict(directory=directory, example=model.get_example(),
                                                   description=model.get_description(),
                                                   type=model.get_type(), name=model.get_name())
                except:
                    pass
            else:
                cache[directories[directory]['name']] = directories[directory]

        dill.dump(list(cache.values()), open(self.__cache_path, 'wb'))
        return cache

    def load_model(self, name):
        if name in self.__models:
            return Model(self.__models[name]['file'])

    def get_models(self):
        return list(self.__models.values())
