# -*- coding: utf-8 -*-
#
# Copyright 2015, 2016 Ramil Nugmanov <stsouko@live.ru>
# This file is part of PREDICTOR.
#
# PREDICTOR is free software; you can redistribute it and/or modify
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
import json
import re
import requests
import subprocess as sp
from io import StringIO, BufferedReader
from os import path
from CGRtools.CGRpreparer import CGRcombo
from CGRtools.FEAR import FEAR
from CGRtools.files.RDFrw import RDFread, RDFwrite
from CGRtools.files.SDFrw import SDFwrite
from MODtools.config import MOLCONVERT
from MODtools.utils import get_additives, chemaxpost
from MWUI.config import ModelType, ResultType, StructureType, StructureStatus


class Model(CGRcombo):
    def __init__(self):
        self.__additives = {x['name'].lower(): x for x in get_additives()}

        config_path = path.join(path.dirname(__file__), 'preparer')
        b_path = path.join(config_path, 'b_templates.rdf')
        m_path = path.join(config_path, 'm_templates.rdf')

        b_templates = open(b_path) if path.exists(b_path) else None
        m_templates = open(m_path) if path.exists(m_path) else None

        CGRcombo.__init__(self, cgr_type='0',
                          extralabels=True, isotop=False, element=True, deep=0, stereo=False,
                          b_templates=b_templates, m_templates=m_templates, speed=False)

        self.__fear = FEAR(isotop=False, stereo=False, hyb=False, element=True, deep=0)
        self.__workpath = '.'

        with open(path.join(config_path, 'preparer.xml')) as f:
            self.__pre_rules = f.read()
        self.__pre_filter_chain = [dict(filter="standardizer",
                                        parameters=dict(standardizerDefinition=self.__pre_rules)),
                                   dict(filter="clean", parameters=dict(dim=2))]

        self.__post_rules = None
        self.__post_filter_chain = [dict(filter="clean", parameters=dict(dim=2))]
        if path.exists(path.join(config_path, 'postprocess.xml')):
            with open(path.join(config_path, 'postprocess.xml')) as f:
                self.__post_rules = f.read()
            self.__post_filter_chain.insert(0, dict(filter="standardizer",
                                                    parameters=dict(standardizerDefinition=self.__post_rules)))

    @staticmethod
    def get_example():
        return None

    @staticmethod
    def get_description():
        return 'Structure checking and possibly restoring'

    @staticmethod
    def get_name():
        return 'Preparer'

    @staticmethod
    def get_type():
        return ModelType.PREPARER

    def setworkpath(self, workpath):
        self.__workpath = workpath

    def get_results(self, structures):
        result = []
        for s in structures:
            if isinstance(s['data'], dict):
                if 'url' in s['data'] and len(structures) == 1:
                    result = self.__parsefile(s['data']['url'])
                break
            parsed = self.__parse_structure(s)
            if parsed:
                result.append(parsed)
        return result

    def __parse_structure(self, structure):
        chemaxed = chemaxpost('calculate/molExport',
                              dict(structure=structure['data'], parameters="mol", filterChain=self.__pre_filter_chain))
        if not chemaxed:
            return False

        with StringIO(chemaxed['structure']) as in_file, StringIO() as out_file:
            try:
                results = self.__prepare(in_file, out_file)[0]
            except IndexError:
                return False
            prepared = out_file.getvalue()

        chemaxed = chemaxpost('calculate/molExport',
                              dict(structure=prepared, parameters="mrv", filterChain=self.__post_filter_chain))
        if not chemaxed:
            return False

        return dict(data=chemaxed['structure'], status=results['status'], type=results['type'],
                    results=results['results'])

    def __prepare(self, in_file, out_file, first_only=True):
        mark = 0
        report = []
        rdf = RDFwrite(out_file)
        sdf = SDFwrite(out_file)
        for r in RDFread(in_file).read():
            _meta, r['meta'] = r['meta'], {}
            if mark in (0, 1) in r['products'] and r['substrats']:  # ONLY FULL REACTIONS
                mark = 1
                g = self.getCGR(r)
                _type = StructureType.REACTION
                _report = g.graph.get('CGR_REPORT')
                _status = StructureStatus.HAS_ERROR if any('ERROR:' in x for x in _report) else StructureStatus.CLEAR
                rdf.write(self.dissCGR(g))
            elif mark in (0, 2) and r['substrats']:  # MOLECULES AND MIXTURES
                mark = 2
                _type = StructureType.MOLECULE
                _report = []
                _status = StructureStatus.CLEAR
                sdf.write(self.merge_mols(r)['substrats'])  # todo: molecules checks.
            else:
                continue

            additives = []
            for k, v in _meta.items():
                if 'additive.amount.' in k:
                    try:
                        a_name, *_, a_amount = re.split('[:=]+', v)
                        additive = self.__additives.get(a_name.strip().lower())
                        if additive:
                            if '%' in a_amount:
                                v = a_amount.replace('%', '')
                                grader = 100
                            else:
                                v = a_amount
                                grader = 1

                            tmp = dict(amount=float(v) / grader)
                            tmp.update(additive)
                            additives.append(tmp)
                    except:
                        pass

            tmp = _meta.pop('pressure', 1)
            try:
                pressure = float(tmp)
            except ValueError:
                pressure = 1

            tmp = _meta.pop('temperature', 298)
            try:
                temperature = float(tmp)
            except ValueError:
                temperature = 298

            report.append(dict(results=[dict(key='Processed', value=x, type=ResultType.TEXT) for x in _report],
                               status=_status, type=_type,
                               additives=additives, pressure=pressure, temperature=temperature))
            if first_only:
                break

        return report

    def __parsefile(self, url):
        r = requests.get(url, stream=True)
        if r.status_code != 200:
            return False

        # ANY to MDL converter
        with sp.Popen([MOLCONVERT, 'rdf'], stdin=BufferedReader(r.raw, buffer_size=1024), stdout=sp.PIPE,
                      stderr=sp.STDOUT) as convert_mol:
            res = convert_mol.communicate()[0].decode()
            if convert_mol.returncode != 0:
                return False

        # MAGIC
        with StringIO(res) as mol_in, StringIO() as mol_out:
            results = self.__prepare(mol_in, mol_out)
            res = mol_out.getvalue()

        # MDL to MRV
        with sp.Popen([MOLCONVERT, 'mrv'], stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.STDOUT) as convert_mrv:
            res = convert_mrv.communicate(input=res.encode())[0].decode()
            if convert_mrv.returncode != 0:
                return False

        with StringIO(res) as mrv:
            next(mrv)
            for structure in mrv:
                pass

        dict(structure=structure['structure'],
             data=chemaxed['structure'], status=results['status'], type=results['type'],
             pressure=structure['pressure'], temperature=structure['temperature'],
             additives=structure['additives'], results=results['results'])

        return False

    def chkreaction(self, structure):
        data = {"structure": structure, "parameters": "smiles:u",
                "filterChain": [{"filter": "standardizer", "parameters": {"standardizerDefinition": "unmap"}}]}
        smiles = chemaxpost('calculate/molExport', data)
        if smiles:
            s, p = json.loads(smiles)['structure'].split('>>')
            ss = set(s.split('.'))
            ps = set(p.split('.'))
            if ss == ps:
                return self.__warnings['fe']
            if ss.intersection(ps):
                return self.__warnings['pe']

            st = chemaxpost('calculate/chemicalTerms', {"structure": s, "parameters": "majorTautomer()"})
            pt = chemaxpost('calculate/chemicalTerms', {"structure": p, "parameters": "majorTautomer()"})
            if st and pt:
                st = chemaxpost('calculate/molExport',
                                {"structure": json.loads(st)['result']['structureData']['structure'],
                                 "parameters": "smiles:u"})
                pt = chemaxpost('calculate/molExport',
                                {"structure": json.loads(pt)['result']['structureData']['structure'],
                                 "parameters": "smiles:u"})
                if st and pt:
                    sts = set(json.loads(st)['structure'].split('.'))
                    pts = set(json.loads(pt)['structure'].split('.'))
                    if sts == pts:
                        return self.__warnings['tfe']
                    if ss.intersection(ps):
                        return self.__warnings['tpe']

                    return None

        return 'reaction check failed'

    __warnings = dict(fe='reagents equal to products',
                      pe='part of reagents equal to part of products',
                      tfe='tautomerized and neutralized reagents equal to products',
                      tpe='tautomerized and neutralized part of reagents equal to part of products')


class ModelLoader(object):
    def __init__(self, **kwargs):
        pass

    @staticmethod
    def load_model(name):
        if name == 'Preparer':
            return Model()

    @staticmethod
    def get_models():
        model = Model()
        return [dict(example=model.get_example(), description=model.get_description(),
                     type=model.get_type(), name=model.get_name())]
