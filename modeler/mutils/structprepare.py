# -*- coding: utf-8 -*-
#
# Copyright 2015 Ramil Nugmanov <stsouko@live.ru>
# This file is part of PREDICTOR.
#
# PREDICTOR is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
import os
import re
import subprocess as sp
from mutils import STANDARDIZER


class standardize_dragos():
    def __init__(self):
        self.__rules = self.__loadrules()
        self.__unwanted = self.__loadunwanted()
        self.__minratio = 2
        self.__maxionsize = 5
        self.__minmainsize = 6
        self.__maxmainsize = 101

    def __loadrules(self):
        with open(os.path.join(os.path.dirname(__file__), "standardrules_dragos.smarts")) as f:
            rules = '..'.join(f.read().split())
        return rules

    def __loadunwanted(self):
        return '(%s)' % '|'.join(open(os.path.join(os.path.dirname(__file__), "unwanted.elem")).read().strip().split())

    def standardize(self, file_path):
        #step 1. canonical smiles, dearomatized & dealkalinized
        #neutralize all species, except for FOUR-LEGGED NITROGEN, which has to be positive for else chemically incorrect
        # Automatically represent N-oxides, incl. nitros, as N+-O-.
        #generate major tautomer..
        smiles = sp.check_output([STANDARDIZER, file_path, '-c', self.__rules, '-f', 'smiles']).decode().strip()
        if not smiles or '>' in smiles:
            return False

        #step 2. check for bizzare salts or mixtures
        #strip mixtures
        species = sorted([(len(re.findall('[A-G,I-Z]', x)), x) for x in smiles.split('.')], key=lambda x: x[0])
        if (len(species) == 1 or len(species) > 1 and species[-1][0] / species[-2][0] > self.__minratio and species[-2][0] <= self.__maxionsize and species[-1][0] > self.__minmainsize) and species[-1][0] < self.__maxmainsize:
            biggest = species[-1][1]
        else:
            return False

        #false if element in unwanted list
        if re.search(self.__unwanted, biggest):
            return False

        with open(file_path) as f:
            f.write(biggest)

        return True