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
import gzip
import dill
import hashlib
import os
import subprocess as sp
import pandas as pd
from collections import defaultdict
from math import ceil
from functools import reduce
from io import StringIO
from MODtools.config import MOLCONVERT
from MODtools.consensus import ConsensusDragos
from CGRtools.files.SDFrw import SDFread
from CGRtools.files.RDFrw import RDFread
from . import chemaxpost, ModelType, ResultType


class Model(ConsensusDragos):
    def __init__(self, file):
        tmp = dill.load(gzip.open(file, 'rb'))
        self.__models = tmp['models']
        self.__conf = tmp['config']
        self.__workpath = '.'

        self.Nlim = self.__conf.get('nlim', 1)
        self.TOL = self.__conf.get('tol', 1e10)
        self.__units = self.__conf.get('report_units')
        self.__show_structures = self.__conf.get('show_structures')

    def get_example(self):
        return self.__conf.get('example')

    def get_description(self):
        return self.__conf.get('desc')

    def get_name(self):
        return self.__conf['name']

    def get_type(self):
        return ModelType(self.__conf['type'])

    def set_work_path(self, workpath):
        self.__workpath = workpath
        for m in self.__models:
            m.setworkpath(workpath)

    @property
    def __format(self):
        return "rdf" if self.get_type() == ModelType.REACTION_MODELING else "sdf"

    @staticmethod
    def __merge_wrap(x, y):
        return pd.merge(x, y, how='outer', left_index=True, right_index=True)

    @staticmethod
    def __report_atoms(atoms):
        return atoms and ' [Modeled site atoms: %s]' % ', '.join(atoms) or ''

    def get_results(self, structures):
        # prepare input file
        if len(structures) == 1:
            chemaxed = chemaxpost('calculate/molExport',
                                  dict(structure=structures[0]['data'], parameters=self.__format))
            if not chemaxed:
                return False
            additions = dict(pressure=structures[0]['pressure'], temperature=structures[0]['temperature'])
            for n, a in enumerate(structures[0]['additives'], start=1):
                additions['additive.%d' % n] = a['name']
                additions['amount.%d' % n] = a['amount']

            data_str = chemaxed['structure']
        else:
            with sp.Popen([MOLCONVERT, self.__format],
                          stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.STDOUT, cwd=self.__workpath) as convert_mol:
                data_str = convert_mol.communicate(input=''.join(s['data'] for s in structures).encode())[0].decode()
                if convert_mol.returncode != 0:
                    return False

            additions = dict(pressure=[], temperature=[])
            for m, s in enumerate(structures):
                additions['pressure'].append(s['pressure'])
                additions['temperature'].append(s['temperature'])
                for n, a in enumerate(s['additives']):
                    additions.setdefault('additive.%d' % n, {})[m] = a['name']
                    additions.setdefault('amount.%d' % n, {})[m] = a['amount']

        res = []
        with StringIO(data_str) as f:
            data = (RDFread(f) if self.get_type() == ModelType.REACTION_MODELING else SDFread(f)).read()

        for m in self.__models:
            res.append(m.predict(data, **additions))

        # all_y_domains = reduce(merge_wrap, (x['y_domain'] for x in res))
        all_domains = reduce(self.__merge_wrap, (x['domain'] for x in res)).fillna(False)

        all_predictions = reduce(self.__merge_wrap, (x['prediction'] for x in res))
        in_predictions = all_predictions.mask(all_domains ^ True)

        trust = pd.Series(5, index=all_predictions.index)
        report = pd.Series('', index=all_predictions.index)

        # mean predicted property
        avg_all = all_predictions.mean(axis=1)
        sigma_all = all_predictions.var(axis=1)

        avg_in = in_predictions.mean(axis=1)
        sigma_in = in_predictions.var(axis=1)

        avg_diff = (avg_in - avg_all).abs()  # difference bt in AD and all predictions. NaN for empty in predictions.
        avg_diff_tol = avg_diff > self.TOL  # ignore NaN
        trust.loc[avg_diff_tol] -= 1
        report.loc[avg_diff_tol] += [self.errors['diff'] % x for x in avg_diff.loc[avg_diff_tol]]

        avg_in_nul = avg_in.isnull()
        trust.loc[avg_in_nul] -= 2  # totally not in domain
        report.loc[avg_in_nul] += [self.errors['zad']] * len(avg_in_nul.loc[avg_in_nul].index)

        avg_domain = all_domains.mean(axis=1)
        avg_domain_bad = (avg_domain < self.Nlim) ^ avg_in_nul  # ignore totally not in domain
        trust.loc[avg_domain_bad] -= 1
        report.loc[avg_domain_bad] += [self.errors['lad'] % ceil(100 * x) for x in avg_domain.loc[avg_domain_bad]]

        # update avg and sigma based on consensus
        good = avg_domain >= self.Nlim
        avg_all.loc[good] = avg_in.loc[good]
        sigma_all.loc[good] = sigma_in.loc[good]

        proportion = sigma_all / self.TOL
        proportion_bad = proportion > 1
        trust.loc[proportion_bad] -= 1
        report.loc[proportion_bad] += [self.errors['stp'] % (x * 100 - 100) for x in proportion.loc[proportion_bad]]

        collector = defaultdict(list)
        for r, d in trust.items():
            s, *n = r if isinstance(r, tuple) else (r,)
            atoms = self.__report_atoms(n)
            collector[s].extend([dict(key='Predicted ± sigma%s%s' % ((self.__units and ' (%s)' % self.__units or ''),
                                                                     atoms),
                                      value='%.2f ± %.2f' % (avg_all.loc[r], sigma_all.loc[r]), type=ResultType.TEXT),
                                 dict(key='Trust of prediction%s' % atoms, value=self.trust_desc[d],
                                      type=ResultType.TEXT),
                                 dict(key='Distrust reason%s' % atoms, value=report.loc[r], type=ResultType.TEXT)])

        if len(structures) == len(collector):
            out = []
            for s in sorted(collector):
                out.append(dict(results=collector[s]))
            return out

        return False


class ModelLoader(object):
    def __init__(self, fast_load=True):
        self.__skip_md5 = fast_load
        self.__models_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'modelbuilder'))
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
                                                   description=model.get_description(),
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
