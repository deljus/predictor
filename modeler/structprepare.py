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
from subprocess import Popen, PIPE, STDOUT, call
from utils.config import PMAPPER, STANDARDIZER
from utils.utils import chemaxpost
from CGRtools.CGRcore import CGRcore
from CGRtools.RDFread import RDFread
from CGRtools.SDFread import SDFread
from CGRtools.SDFwrite import SDFwrite
from CGRtools.RDFwrite import RDFwrite
from io import StringIO
import networkx as nx


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


class Pharmacophoreatommarker(object):
    def __init__(self, markerrule, workpath):
        self.__markerrule = self.__dumprules(markerrule)
        self.__config = os.path.join(workpath, 'iam')
        self.__loadrules()

    def __dumprules(self, rules):
        return open(rules).read()

    def setworkpath(self, workpath):
        self.__config = os.path.join(workpath, 'iam')
        self.__loadrules()

    def __loadrules(self):
        with open(self.__config, 'w') as f:
            f.write(self.__markerrule)

    def get(self, structure):
        """
        marks atoms in 7th col of sdf.
        if molecule has atom mapping - will be used mapping.
        :type structure: str
        """

        p = Popen([PMAPPER, '-c', self.__config], stdout=PIPE, stdin=PIPE, stderr=STDOUT)
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
    def __init__(self, patterns, prepare=None, postprocess=None, stereo=False):
        self.__cgr = CGRcore(type='0', stereo=stereo, balance=0, b_templates=None, e_rules=None, c_rules=None)
        self.__stdprerules = self.__loadrules(prepare)
        self.__stdpostrules = self.__loadrules(postprocess)
        self.__patterns = self.__loadpatterns(patterns)

    @staticmethod
    def __loadrules(rules):
        if rules:
            with open(rules) as f:
                ruless = f.read().rstrip()
        else:
            ruless = None
        return ruless

    def __loadpatterns(self, patterns):
        rules = []
        for i in patterns:
            with open(i) as f:
                rules.append(self.__cgr.searchtemplate(self.__cgr.gettemplates(f), speed=False))
        return rules

    def getcount(self):
        return len(self.__patterns)

    def __getchemax(self, structure, rules):
        return ('calculate/molExport',
                {"structure": structure, "parameters": "rdf",
                 "filterChain": [{"filter": "standardizer",
                                  "parameters": {"standardizerDefinition": rules}}]})

    def get(self, structure):
        if self.__stdprerules:
            res = chemaxpost(*self.__getchemax(structure, self.__stdprerules))
            if res:
                res = json.loads(res)
                if 'isReaction' not in res:
                    return False
                structure = res['structure']
            else:
                return False

        data = next(RDFread(StringIO(structure)).readdata(), None)
        if not data:
            return False

        g = self.__cgr.getCGR(data)
        marks = []
        for i in self.__patterns:
            patterns = set()
            for match in i(g):
                patterns.add(tuple(sorted(match['products'].nodes())))
            marks.append(patterns)

        if 0 == len(set(len(x) for x in marks)) > 1:
            return False

        if self.__stdpostrules:
            with StringIO() as f:
                RDFwrite(f).writedata(data)
                structure = f.getvalue()

            res = chemaxpost(*self.__getchemax(structure, self.__stdpostrules))
            if res:
                data = next(RDFread(StringIO(json.loads(res)['structure'])).readdata(remap=False), None)
                if not data:
                    return False
            else:
                return False

        structure = nx.union_all(data['substrats'])
        structure.graph['meta'] = data['meta'].copy()

        result = []
        for pattern in marks:
            with StringIO() as f:
                sdf = SDFwrite(f)

                for match in pattern:
                    tmp = structure.copy()
                    for atom in match:
                        tmp.node[atom]['mark'] = '1'

                    sdf.writedata(tmp)

                result.append(f.getvalue())

        return result


class Colorize(object):
    def __init__(self, starter, workpath):
        self.__starter = starter
        self.setworkpath(workpath)

    def setworkpath(self, workpath):
        self.__inputfile = os.path.join(workpath, 'colorin.sdf')
        self.__outfile = os.path.join(workpath, 'colorout.sdf')

    def get(self, structure):
        if os.path.exists(self.__outfile):
            os.remove(self.__outfile)
        with open(self.__inputfile, 'w') as f:
            SDFwrite(f).writedata(structure)

        if call([self.__starter, self.__inputfile, self.__outfile]) == 0:
            with open(self.__outfile) as f:
                return next(SDFread(f).readdata(), False)
        return False
