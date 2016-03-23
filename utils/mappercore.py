# -*- coding: utf-8 -*-
#
# Copyright 2015 Ramil Nugmanov <stsouko@live.ru>
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
from utils.config import LOCK_MAPPING, STANDARD, MAPPING_DONE, MOLCONVERT
from utils.utils import getsolvents, chemaxpost, serverpost, serverput, serverget, serverdel
import subprocess as sp
import xml.etree.ElementTree as ET
import re
import json


def remove_namespace(doc, namespace):
    """Remove namespace in the passed document in place."""
    ns = u'{%s}' % namespace
    nsl = len(ns)
    for elem in doc.getiterator():
        if elem.tag.startswith(ns):
            elem.tag = elem.tag[nsl:]
    return doc


class Mapper(object):
    def parsefile(self, task):
        if serverput("task_status/%s" % task['id'], {'task_status': LOCK_MAPPING}):
            p = sp.Popen([MOLCONVERT, 'mrv', task['file']], stdout=sp.PIPE, stderr=sp.STDOUT)
            try:
                mrv = remove_namespace(ET.fromstring(p.communicate()[0].decode()), 'http://www.chemaxon.com')

                solv = {x['name'].lower(): x['id'] for x in getsolvents()}

                for i in mrv.getchildren():
                    solvlist = {}
                    temp = 298
                    prop = {x.get('title').lower(): x.find('scalar').text.lower().strip() for x in i.iter('property')}
                    for k, v in prop.items():
                        if 'solvent.amount.' in k:
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

                    standardized = self.standardize(ET.tostring(i, encoding='utf8', method='xml'))
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
        data = {"structure": structure, "parameters": "mrv",
                "filterChain": [{"filter": "standardizer", "parameters": {"standardizerDefinition": STANDARD}},
                                {"filter": "clean", "parameters": {"dim": 2}}]}
        structure = chemaxpost('calculate/molExport', data)
        models = []
        status = None  # ???????????????????????????????????
        isreaction = False
        if structure:
            structure = json.loads(structure)

            if 'isReaction' in structure:
                isreaction = True
                status = self.chkreaction(structure['structure'])
                # todo: get reaction hashes etc
            else:
                pass
                # todo: тут надо для молекул заморочиться. mb

            return dict(structure=structure['structure'], models=models, status=status, isreaction=isreaction)
        else:
            return False

    @staticmethod
    def chkreaction(structure):
        data = {"structure": structure, "parameters": "smiles:u",
                "filterChain": [{"filter": "standardizer", "parameters": {"standardizerDefinition": "unmap"}}]}
        smiles = chemaxpost('calculate/molExport', data)
        if smiles:
            s, p = json.loads(smiles)['structure'].split('>>')
            ss = set(s.split('.'))
            ps = set(p.split('.'))
            if ss == ps:
                return 'reagents equal to products'
            if ss.intersection(ps):
                return 'part of reagents equal to part of products'

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
                        return 'tautomerized and neutralized reagents equal to products'
                    if ss.intersection(ps):
                        return 'tautomerized and neutralized part of reagents equal to part of products'

        return 'reaction check failed'
