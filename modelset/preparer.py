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
from itertools import chain

import re
import requests
import tempfile
import subprocess as sp
import xml.etree.ElementTree as ET
from io import StringIO, TextIOWrapper, BufferedReader, IOBase, BytesIO
from os import path
from CGRtools.CGRpreparer import CGRcombo
from CGRtools.FEAR import FEAR
from CGRtools.RDFrw import RDFread, RDFwrite
from MODtools.config import MOLCONVERT
from MODtools.utils import getsolvents, chemaxpost, serverpost, serverput, serverget, serverdel
from app.config import ModelType, ResultType, StructureType, StructureStatus


class ByteLoop(IOBase):
    __data = b''

    def read(self, n=-1):
        data = BytesIO(self.__data)
        out = data.read(n)
        self.__data = self.__data[len(out):]
        return out

    def write(self, data):
        self.__data += data
        return len(data)

    def seekable(self):
        return False

    def writable(self):
        return True

    def readable(self):
        return True


class Model(CGRcombo):
    def __init__(self):
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
    def get_hashes():
        return None

    @staticmethod
    def get_type():
        return ModelType.PREPARER

    def setworkpath(self, workpath):
        self.__workpath = workpath

    def get_results(self, structures):
        result = []
        for s in structures:
            if 'url' in s:
                result = self.__parsefile(s['url'])
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

        if 'isReaction' in chemaxed:
            structure_type = StructureType.REACTION

            with StringIO(chemaxed['structure']) as in_file, StringIO() as out_file:
                parse_results = self.__prepare_reaction(in_file, out_file)[0]
                prepared = out_file.getvalue()

        else:
            structure_type = StructureType.MOLECULE
            parse_results = []
            prepared = chemaxed['structure']

        chemaxed = chemaxpost('calculate/molExport',
                              dict(structure=prepared, parameters="mrv", filterChain=self.__post_filter_chain))
        if not chemaxed:
            return False

        structure_data = chemaxed['structure']
        structure_status = StructureStatus.CLEAR

        return dict(structure=structure['structure'],
                    data=structure_data, status=structure_status, type=structure_type,
                    pressure=structure['pressure'], temperature=structure['temperature'],
                    additives=structure['additives'], models=[dict(results=parse_results)])

    def __prepare_reaction(self, in_file, out_file):
        report = []
        out = RDFwrite(out_file)
        for r in RDFread(in_file).read():
            g = self.getCGR(r)
            g.graph['meta'] = {}
            out.write(g)
            report.append([dict(key='Processed', value=x, type=ResultType.TEXT)
                           for x in g.graph.get('CGR_REPORT')])

        return report

    def __parsefile(self, url):
        r = requests.get(url, stream=True)
        if r.status_code != 200:
            return False

        with sp.Popen([MOLCONVERT, 'mol'], stdin=BufferedReader(r.raw, buffer_size=1024), stdout=sp.PIPE,
                      stderr=sp.STDOUT) as convert1, \
                TextIOWrapper(convert1.stdout) as data1, \
                ByteLoop() as loop, \
                sp.Popen([MOLCONVERT, 'mrv'], stdin=BufferedReader(loop, buffer_size=1024), stdout=sp.PIPE,
                         stderr=sp.STDOUT) as convert2, \
                TextIOWrapper(convert2.stdout) as data2:

            header = next(data1)

            if '$RXN' in header:
                structure_type = StructureType.REACTION
                parse_results = self.__prepare_reaction(chain([header], data1), TextIOWrapper(loop))

        try:
            mrv = remove_namespace(ET.fromstring(p.communicate()[0].decode()), 'http://www.chemaxon.com')
            solv = {x['name'].lower(): x['id'] for x in getsolvents()}

            for i in mrv.getchildren():
                solvlist = {}
                temp = 298
                prop = {x.get('title').lower(): x.find('scalar').text.lower().strip() for x in i.iter('property')}
                for k, v in prop.items():
                    if 'additive.amount.' in k:
                        try:
                            sname, *_, samount = re.split('[:=]', v)
                            sid = solv.get(sname.strip())
                            if sid:
                                if '%' in samount:
                                    v = samount.replace('%', '')
                                    grader = 100
                                else:
                                    v = samount
                                    grader = 1

                                solvlist[sid] = float(v) / grader
                        except:
                            pass
                    elif 'temperature' == k:
                        try:
                            temp = float(v)
                        except ValueError:
                            temp = 298

                standardized = self.standardize(ET.tostring(i, encoding='utf8', method='xml').decode())
                if standardized:
                    data = dict(task_id=task['id'], structure=standardized['structure'],
                                isreaction=standardized['isreaction'],
                                solvents=json.dumps(solvlist), temperature=temp, status=standardized['status'])
                    q = serverpost('parser', data)
                    if q.isdigit():
                        serverpost("reaction/%s" % int(q), {'models': ','.join(standardized['models'])})
        except:
            pass

        if serverput("task_status/%s" % task['id'], {'task_status': MAPPING_DONE}):
            return True
        return False

    def mapper(self, task):
        if serverput("task_status/%s" % (task['id']), {'task_status': LOCK_MAPPING}):
            chemicals = serverget("task_reactions/%s" % (task['id']), None)
            for j in chemicals:
                structure = serverget("reaction_structure/%s" % (j['reaction_id']), None)
                standardized = self.standardize(structure)
                if standardized:
                    serverpost("reaction_structure/%s" % (j['reaction_id']),
                               {'reaction_structure': standardized['structure'],
                                'status': standardized['status'],
                                'isreaction': standardized['isreaction']})
                    serverpost("reaction/%s" % j['reaction_id'], {'models': ','.join(standardized['models'])})
                else:
                    serverdel("reaction/%s" % (j['reaction_id']), None)

            if serverput("task_status/%s" % task['id'], {'task_status': MAPPING_DONE}):
                return True
        return False

    def standardize(self, structure):
        data = dict(structure=structure, parameters="mol",
                    filterChain=[dict(filter="standardizer", parameters=dict(standardizerDefinition=self.__standard)),
                                 dict(filter="clean", parameters=dict(dim=2))])
        structure = chemaxpost('calculate/molExport', data)
        status = None
        if structure:
            structure = json.loads(structure)
            if 'isReaction' in structure:
                is_reaction = True
                print('!! std reaction')
                with StringIO(structure['structure']) as in_file, StringIO() as out_file:
                    for r in RDFread(in_file).read():
                        g = self.getCGR(r)
                        status = g.graph.get('CGR_REPORT')

                    RDFwrite(out).writedata(self.__cgr.dissCGR(g))
                    mol = out.getvalue()

                chk = self.chkreaction(mol)
                if chk:
                    if status:
                        status = '%s, %s' % (status, chk)
                    else:
                        status = chk
                        # todo: get reaction hashes etc
            else:
                is_reaction = False
                print('!! std molecule')
                mol = structure['structure']
                # todo: тут надо для молекул заморочиться. mb

            structure = chemaxpost('calculate/molExport', {"structure": mol, "parameters": "mrv",
                                                           "filterChain": [{"filter": "clean",
                                                                            "parameters": {"dim": 2}}]})
            if structure:
                structure = json.loads(structure)
                return dict(structure=structure['structure'], models=models, status=status, isreaction=isreaction)

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
        return [dict(example=model.get_example(), description=model.get_description(), hashes=model.get_hashes(),
                     type=model.get_type(), name=model.get_name())]
