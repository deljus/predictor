#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-
#
#  Copyright 2016, 2017 Ramil Nugmanov <stsouko@live.ru>
#  This file is part of predictor.
#
#  predictor
#  is free software; you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
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
import shutil
import tempfile
from modelset import ModelSet


def cycle2(structures):
    while True:
        yield structures[0].copy()


def run(structures=None, model=None):
    workpath = tempfile.mkdtemp(dir='/tmp')
    mod = ModelSet().load_model(model['name'], workpath=workpath)

    results = mod.get_results(structures) if mod is not None else None

    if results:
        out = []
        # AD-HOC for preparing model for uploaded files processing.
        tmp = cycle2(structures) if isinstance(structures[0]['data'], dict) else structures

        for s, r in zip(tmp, results):
            _res = dict(results=r.pop('results', []))
            _res.update(model)
            r['models'] = [_res]
            s.update(r)
            out.append(s)
        structures = out
    else:
        # AD-HOC for preparing model for uploaded files processing.
        if isinstance(structures[0]['data'], dict):
            raise Exception('Preparer model failed on file processing')

        # if failed return empty models list
        for s in structures:
            s['models'] = []

    shutil.rmtree(workpath)
    return structures
