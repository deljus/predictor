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
import json
import os
import re
from subprocess import Popen, PIPE, STDOUT
import sys
from utils.config import PMAPPER
from utils.utils import chemaxpost
from CGRtools.CGRcore import CGRcore
from CGRtools.RDFread import RDFread
from io import StringIO


class StandardizeDragos(object):
    def __init__(self, rules):
        self.__stdrules = self.__loadrules(rules)
        self.__unwanted = self.__loadunwanted()
        self.__minratio = 2
        self.__maxionsize = 5
        self.__minmainsize = 6
        self.__maxmainsize = 101

    def __loadrules(self, rules):
        with open(rules or os.path.join(os.path.dirname(__file__), "standardrules_dragos.rules")) as f:
            ruless = '..'.join([x.split()[0] for x in f])
        return ruless

    def __loadunwanted(self):
        return '(%s)' % '|'.join(open(os.path.join(os.path.dirname(__file__), "unwanted.elem")).read().split())

    def get(self, structure, mformat="sdf"):
        """
        step 1. canonical smiles, dearomatized & dealkalinized
        neutralize all species, except for FOUR-LEGGED NITROGEN, which has to be positive for else chemically incorrect
        Automatically represent N-oxides, incl. nitros, as N+-O-.
        generate major tautomer & aromatize
        :param mformat: mol return format
        :param structure: chemaxon recognizable structure
        """

        data = {"structure": structure, "parameters": "smiles",
                "filterChain": [{"filter": "standardizer", "parameters": {"standardizerDefinition": self.__stdrules}}]}
        res = chemaxpost('calculate/molExport', data)

        if res:
            res = json.loads(res)
            if 'isReaction' in res:
                return False
            smiles = res['structure']
        else:
            return False

        """
        step 2. check for bizzare salts or mixtures
        strip mixtures
        regex search any atom in aromatic and aliphatic forms exclude H
        """
        regex = re.compile('(\[[A-Z][a-z]?!H|\[as|\[se|C|c|N|n|P|p|O|o|S|s|F|Br|I)')
        species = sorted([(len(regex.findall(x)), x) for x in smiles.split('.')], key=lambda x: x[0])
        if (len(species) == 1 or len(species) > 1 and species[-1][0] / species[-2][0] > self.__minratio and species[-2][0] <= self.__maxionsize and species[-1][0] > self.__minmainsize) and species[-1][0] < self.__maxmainsize:
            biggest = species[-1][1]
        else:
            return False

        # false if element in unwanted list
        if re.search(self.__unwanted, biggest):
            return False

        if mformat != 'smiles':
            data = {"structure": biggest, "parameters": mformat,
                    "filterChain": [{"filter": "clean", "parameters": {"dim": 2}}]}
            res = chemaxpost('calculate/molExport', data)
            if res:
                res = json.loads(res)
                biggest = res['structure']
            else:
                return False

        return biggest


class ISIDAatommarker(object):
    def __init__(self, markerrule, workpath):
        self.__markerrule = self.__dumprules(markerrule)
        self.__workfile = os.path.join(workpath, 'iam')
        self.__loadrules()

    def __dumprules(self, rules):
        return open(rules).read()

    def setworkpath(self, workpath):
        self.__workfile = os.path.join(workpath, 'iam')
        self.__loadrules()

    def __loadrules(self):
        with open(self.__workfile, 'w') as f:
            f.write(self.__markerrule)

    def get(self, structure):
        """
        marks atoms in 7th col of sdf.
        if molecule has atom mapping - will be used mapping.
        :type structure: str
        """

        p = Popen([PMAPPER, '-c', self.__workfile], stdout=PIPE, stdin=PIPE, stderr=STDOUT)
        pout = p.communicate(input=structure.encode())[0]

        marks = []
        flag = 0
        manual = False
        buffer = []

        for x in pout.decode().split():
            marks.extend(x.split(';'))

        marksg = (n for n in marks)

        for line in structure.splitlines(True):
            if '999 V2000' in line:
                flag = int(line[:3])
                b1 = {}
            elif flag:
                if line[60:63] != '  0':
                    manual = True
                    line = line[:51] + '  1' + line[54:]
                elif 'A' in next(marksg):
                    b1[flag] = line
                    line = line[:51] + '  1' + line[54:60] + '  1' + line[63:]
                flag -= 1

            buffer.append(line)
            if manual and not flag:
                manual = False
                for k, v in b1.items():
                    buffer[-k] = v

        return ''.join(buffer)


class CGRatommarker(object):
    def __init__(self, rules):
        self.__stdrules = self.__loadrules(rules)

    def __loadrules(self, rules):
        with open(rules or os.path.join(os.path.dirname(__file__), "taut_marker.rules")) as f:
            ruless = '..'.join([x.split()[0] for x in f])
        return ruless

    def get(self, structure, stereo=False, b_templates=None, e_rules=None, c_rules=None):
        data = {"structure": structure, "parameters": "mol",
                "filterChain": [{"filter": "standardizer", "parameters": {"standardizerDefinition": self.__stdrules}}]}
        res = chemaxpost('calculate/molExport', data)

        if res:
            res = json.loads(res)
            if 'isReaction' in res:
                rxn = res['structure']
                _cgr = CGRcore(type='0', stereo=stereo, balance=0,
                               b_templates=open(b_templates) if b_templates else None,
                               e_rules=open(e_rules) if e_rules else None,
                               c_rules=open(c_rules) if c_rules else None)
                for num, data in enumerate(RDFread(StringIO(rxn)).readdata(), start=1):
                    if num % 10 == 1:
                        print("reaction: %d" % num, file=sys.stderr)
                    g = _cgr.getCGR(data)
                    for n, m in g.edges():
                        if (g.node[n]['element'] == 'H') != (g.node[m]['element'] == 'H'):
                            pass

        return False
