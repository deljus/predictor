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
from itertools import product
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
import xml.etree.ElementTree as ET
from utils.mappercore import remove_namespace


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
        self.__markerrule, self.__markers = self.__dumprules(markerrule)
        self.__config = os.path.join(workpath, 'iam')
        self.__loadrules()

    @staticmethod
    def __dumprules(rules):
        rules = open(rules).read()
        marks = list(set(x.get('Symbol') for x in remove_namespace(ET.fromstring(rules),
                                                                   'http://www.chemaxon.com').iter('AtomSet')))
        return rules, marks

    def setworkpath(self, workpath):
        self.__config = os.path.join(workpath, 'iam')
        self.__loadrules()

    def __loadrules(self):
        with open(self.__config, 'w') as f:
            f.write(self.__markerrule)

    def getcount(self):
        return len(self.__markers)

    def get(self, structure):
        """
        marks atoms in 7th col of sdf.
        if molecule has atom mapping - will be used mapping.
        :type structure: nx.Graph or list(nx.Graph)
        """
        p = Popen([PMAPPER, '-c', self.__config], stdout=PIPE, stdin=PIPE, stderr=STDOUT)
        with StringIO() as f:
            tmp = SDFwrite(f)
            for x in (structure if isinstance(structure, list) else [structure]):
                tmp.writedata(x)

            marks = p.communicate(input=f.getvalue().encode())[0].decode().split()

        if p.returncode == 0:
            output = []
            for s, mark in zip((structure if isinstance(structure, list) else [structure]), marks):
                found = [[] for _ in range(self.getcount())]
                for n, m in zip(s.nodes(), mark.split(';')):
                    if m:
                        tmp = s.copy()
                        tmp.node[n]['mark'] = '1'
                        found[self.__markers.index(m)].append(tmp)

                for x in found:
                    if not x:
                        x.append(s)

                result = [[] for _ in range(self.getcount())]
                for x in product(*found):
                    for y, z in zip(result, x):
                        y.append(z)

                output.append(result)
            return output
        return False


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

    @staticmethod
    def __processor_s(structure, rules, remap=True):
        with StringIO() as f:
            RDFwrite(f).writedata(structure)
            structure = f.getvalue()
        res = chemaxpost('calculate/molExport',
                         {"structure": structure, "parameters": "rdf",
                          "filterChain": [{"filter": "standardizer",
                                           "parameters": {"standardizerDefinition": rules}}]})
        if res:
            res = json.loads(res)
            if 'isReaction' in res:
                structure = next(RDFread(StringIO(res['structure'])).readdata(remap=remap), None)
                if structure:
                    return structure
        return False

    @staticmethod
    def __processor_m(structure, rules, remap=True):
        p = Popen([STANDARDIZER, '-c', rules, '-f', 'rdf'], stdout=PIPE, stdin=PIPE, stderr=STDOUT)
        with StringIO() as f:
            tmp = RDFwrite(f)
            for x in structure:
                tmp.writedata(x)

            res = p.communicate(input=f.getvalue().encode())[0].decode()
            if p.returncode == 0:
                return list(RDFread(StringIO(res)).readdata(remap=remap))
        return False

    def get(self, structure):
        if self.__stdprerules:
            structure = self.__processor_m(structure, self.__stdprerules) if isinstance(structure, list) \
                else self.__processor_s(structure, self.__stdprerules)
            if not structure:
                return False
        markslist = []
        gs = [self.__cgr.getCGR(x) for x in (structure if isinstance(structure, list) else [structure])]
        for g in gs:
            marks = []
            for i in self.__patterns:
                pattern = set()
                for match in i(g):
                    pattern.add(tuple(sorted(match['products'].nodes())))
                marks.append(pattern)

            if 0 == len(set(len(x) for x in marks)) > 1:
                return False
            markslist.append(marks)

        if self.__stdpostrules:
            structure = self.__processor_m(structure, self.__stdpostrules, remap=False) if isinstance(structure, list) \
                else self.__processor_s(structure, self.__stdpostrules, remap=False)

            if not structure:
                return False

        output = []
        for s, marks in zip(structure if isinstance(structure, list) else [structure], markslist):
            ss = nx.union_all(s['substrats'])
            ss.graph['meta'] = s['meta'].copy()

            result = []
            for pattern in marks:
                marked_graphs = []
                for match in pattern:
                    tmp = ss.copy()
                    for atom in match:
                        tmp.node[atom]['mark'] = '1'
                    marked_graphs.append(tmp)

                result.append(marked_graphs)
            output.append(result)
        return output


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
            for i in (structure if isinstance(structure, list) else [structure]):
                SDFwrite(f).writedata(i)

        if call([self.__starter, self.__inputfile, self.__outfile]) == 0:
            with open(self.__outfile) as f:
                res = list(SDFread(f).readdata(remap=False))
                if res:
                    return res if isinstance(structure, list) else res[0]

        return False
