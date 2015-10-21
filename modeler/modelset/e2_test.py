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
import pickle
from modelset import consensus_dragos, getmodelset, register_model, chemaxpost


class Model(consensus_dragos):
    def __init__(self):
        self.modelpath = os.path.join(os.path.dirname(__file__), 'e2')
        self.Nlim = .6
        self.TOL = .8
        self.__model = pickle.load(open(os.path.join(self.modelpath, 'model.bin'), 'rb'))
        self.__model.setworkpath('/tmp')
        super().__init__()

    def getdesc(self):
        desc = 'e2 testing'
        return desc

    def getname(self):
        name = 'e2 test'
        return name

    def getexample(self):
        return ' '

    def is_reation(self):
        return 1

    def gethashes(self):
        hashlist = []
        return hashlist

    def getresult(self, chemical):
        data = {"structure": chemical['structure'], "parameters": "sdf"}
        structure = chemaxpost('calculate/stringMolExport', data)
        temperature = chemical.get('temperature', 25)
        solvent = chemical['solvents'][0]['name'] if chemical['solvents'] else 'Undefined'

        if structure:
            print(structure, temperature, solvent)
            fixtime = int(time.time())
            temp_file_mol = os.path.join(self.modelpath, "structure-%d.mol" % fixtime)

            with open(temp_file_mol, 'w') as f:
                f.write(structure)

            print(self.__model.predict(temp_file_mol, solvent=solvent, temperature=temperature))
            os.remove(temp_file_mol)

            return self.report()
        else:
            return False

model = Model()
register_model(model.getname(), Model)
