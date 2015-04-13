#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2015 Ramil Nugmanov <stsouko@live.ru>
# This file is part of PREDICTOR.
#
# PREDICTOR is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
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
import os
import pickle

import sys
import subprocess as sp

modelpath = os.path.dirname(__file__)
condenser = os.path.join(modelpath, "condenser")
fragmentor = os.path.join(modelpath, "Fragmentor")

model_file = os.path.join(modelpath, sys.argv[1])
solvent_file = os.path.join(modelpath, "solvents.csv")
input_file = sys.argv[2]
result_file = sys.argv[3]
solvent_name = sys.argv[4]
temperature = float(sys.argv[5])
fragopts = sys.argv[6].split(' ')
fragcount = int(sys.argv[7])
condensparams = sys.argv[8].split(' ')
temp_file_sdf = input_file + '.sdf'
temp_file_frag = input_file + '.fra'

fragopts[1] = os.path.join(modelpath, fragopts[1])


def load_solvents():
    solvents = {}
    with open(solvent_file, 'r') as f:
        for line in f:
            key, *value = line.split(';')
            solvents[key.lower()] = [float(x) for x in value]
    return solvents
solvents = load_solvents()

try:
    sp.call([condenser, '-i', input_file, '-o', temp_file_sdf] + condensparams)
    sp.call([fragmentor, '-i', temp_file_sdf, '-o', temp_file_frag] + fragopts)
    with open(temp_file_frag + '.csv', 'r') as f:
        fragments = [int(x) for x in f.readline().split(';')[1:]]
        vector = solvents.get(solvent_name.lower(), [0]*13) + [temperature] + fragments[:fragcount]
except:
    print('YOU DO IT WRONG')
else:
    model = pickle.load(open(model_file, 'rb'))
    result = model.predict(vector)[0]
    if os.path.getsize(fragopts[1]) != os.path.getsize(temp_file_frag + '.hdr'):
        ad = 'false'
    else:
        ad = 'true'

    with open(result_file, 'w') as f:
        f.write('{"predicted_value":"%s","applicability_domain":"%s"}' % (result, ad))
finally:
    try:
        os.remove(temp_file_sdf)
    except:
        pass
    try:
        os.remove(temp_file_frag + '.csv')
    except:
        pass
    try:
        os.remove(temp_file_frag + '.hdr')
    except:
        pass