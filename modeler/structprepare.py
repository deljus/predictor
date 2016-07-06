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
from itertools import product
from operator import itemgetter
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
            ruless = f.read()
        return ruless

    def __loadunwanted(self):
        return set(open(os.path.join(os.path.dirname(__file__), "unwanted.elem")).read().split())

    def __processor_m(self, structure):
        p = Popen([STANDARDIZER, '-c', self.__stdrules, '-f', 'SDF'], stdout=PIPE, stdin=PIPE, stderr=STDOUT)
        with StringIO() as f:
            tmp = SDFwrite(f)
            for x in structure:
                tmp.writedata(x)

            res = p.communicate(input=f.getvalue().encode())[0].decode()

        if p.returncode == 0:
            with StringIO(res) as f:
                return list(SDFread(f).readdata())
        return False

    def __processor_s(self, structure):
        data = {"structure": structure, "parameters": "smiles",
                "filterChain": [{"filter": "standardizer",
                                 "parameters": {"standardizerDefinition": self.__stdrules}}]}
        res = chemaxpost('calculate/molExport', data)
        if res:
            res = json.loads(res)
            if 'isReaction' not in res:
                with StringIO(res['structure']) as f:
                    return list(SDFread(f).readdata())
        return False

    def get(self, structure):
        """
        step 1. canonical smiles, dearomatized & dealkalinized
        neutralize all species, except for FOUR-LEGGED NITROGEN, which has to be positive for else chemically incorrect
        Automatically represent N-oxides, incl. nitros, as N+-O-.
        generate major tautomer & aromatize
        """

        structure = self.__processor_m(structure) if isinstance(structure, list) else self.__processor_s(structure)
        if structure:
            """
            step 2. check for bizzare salts or mixtures
            strip mixtures
            """
            output = []
            for s in structure:
                species = sorted(((len([n for n, d in x.nodes(data=True) if d['element'] != 'H']), x) for x in
                                  nx.connected_component_subgraphs(s)), key=itemgetter(0))
                if species[-1][0] <= self.__maxmainsize \
                        and (len(species) == 1 or
                             (species[-1][0] / species[-2][0] >= self.__minratio and
                              species[-2][0] <= self.__maxionsize and
                              species[-1][0] >= self.__minmainsize)) \
                        and not self.__unwanted.intersection(species[-1][1]):
                    output.append(species[-1][1])
                else:
                    return False

            return output
        return False


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
                        found[self.__markers.index(m)].append([n, tmp])

                for x in found:
                    if not x:
                        x.append([None, s])

                output.append([list(x) for x in product(*found)])
            return output
        return False


class CGRatommarker(object):
    def __init__(self, patterns, prepare=None, postprocess=None, stereo=False):
        self.__cgr = CGRcore(type='0', stereo=stereo, balance=0, b_templates=None, e_rules=None, c_rules=None)
        self.__stdprerules = self.__loadrules(prepare)
        self.__stdpostrules = self.__loadrules(postprocess)
        self.__patterns, self.__marks = self.__loadpatterns(patterns)

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
        marks = 0
        for i in patterns:
            with open(i) as f:
                templates = self.__cgr.gettemplates(f)
                rules.append(self.__cgr.searchtemplate(templates, speed=False))
                marks = len(templates[0]['products'])
        return rules, marks

    def getcount(self):
        return self.__marks

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
                return list(RDFread(StringIO(res['structure'])).readdata(remap=remap))
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
            marks = []  # list of list of tuples(atom, mark) of matched centers
            for i in self.__patterns:
                for match in i(g):
                    marks.append([[x, y['mark']] for x, y in match['products'].nodes(data=True)])
            markslist.append(marks)

        if self.__stdpostrules:
            structure = self.__processor_m(structure, self.__stdpostrules, remap=False) if isinstance(structure, list) \
                else self.__processor_s(structure, self.__stdpostrules, remap=False)

            if not structure:
                return False

        output = []
        for s, marks in zip((structure if isinstance(structure, list) else [structure]), markslist):
            ss = nx.union_all(s['substrats'])
            ss.graph['meta'] = s['meta'].copy()

            result = []
            for match in marks:
                tmp = []
                for atom, a_mark in match:
                    ssc = ss.copy()  # todo: сплиттить молекулы. ибо кемаксон косячит.
                    ssc.node[atom]['mark'] = '1'
                    tmp.append([a_mark, atom, ssc])

                result.append([[x, y] for _, x, y in sorted(tmp)])

            output.append(result if result else [[[None, ss]] * self.getcount()])
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
                    return res
        return False
