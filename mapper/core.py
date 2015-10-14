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
import os
from utils.config import LOCK_MAPPING, STANDARD, MAPPING_DONE, UPLOAD_PATH, STANDARDIZER
from utils.utils import getsolvents, chemaxpost, serverpost, serverput, serverget
import subprocess as sp
import xml.etree.ElementTree as ET
import re
import json

#TODO
from utils.FEAR.RDFread import RDFread
from utils.FEAR.CGR import CGR
fear = CGR()


def create_task_from_file(task):
    file_path = task['file']
    task_id = task['id']
    tmp_file = '%stmp-%d.mrv' % (UPLOAD_PATH, task_id)
    tmp_fear_file = '%stmp-%d.rxn' % (UPLOAD_PATH, task_id)
    sp.call([STANDARDIZER, file_path, '-c', STANDARD, '-f', 'mrv', '-o', tmp_file])
    solv = {x['name'].lower(): x['id'] for x in getsolvents()}

    with open(tmp_file, 'r') as file:
        for mol in file:
            if '<MDocument>' in mol:
                tree = ET.fromstring(mol)
                prop = {x.get('title').lower(): x.find('scalar').text.lower().strip() for x in tree.iter('property')}
                solvlist = {}
                temp = 298
                for i, j in prop.items():
                    if 'solvent.amount.' in i:
                        k = re.split('[:=]', j)
                        id = solv.get(k[0].strip())
                        if id:
                            if '%' in k[-1]:
                                v = k[-1].replace('%', '')
                                grader = 100
                            else:
                                v = k[-1]
                                grader = 1
                            try:
                                v = float(v) / grader
                            except ValueError:
                                v = 1
                            solvlist[id] = v
                    elif 'temperature' == i:
                        try:
                            temp = float(j)
                        except ValueError:
                            temp = 298

                data = {"structure": mol.rstrip(), "parameters": {"method": "DEHYDROGENIZE"}}
                structure = chemaxpost('convert/hydrogenizer', data)
                if structure:
                    data = dict(task_id=task_id, structure=structure, solvents=json.dumps(solvlist), temperature=temp)
                    q = serverpost('parser', data)
                    if q.isdigit(): # проверка на корректный ответ. по сути не нужна. но да пох.
                        data = {"structure": mol, "parameters": "rxn"}
                        structure = chemaxpost('calculate/stringMolExport', data)
                        if '$RXN' in structure:
                            with open(tmp_fear_file, 'w') as tmp:
                                tmp.write(structure)
                            FEAR(tmp_fear_file, int(q))
                            os.remove(tmp_fear_file)
                        else:
                            pass
                            # todo: тут надо для молекул заморочиться.

    os.remove(tmp_file)
    serverput("task_status/%s" % task_id, {'task_status': MAPPING_DONE})


def mapper(task):
    if serverput("task_status/%s" % (task['id']), {'task_status': LOCK_MAPPING}):
        chemicals = serverget("task_reactions/%s" % (task['id']), None)
        for j in chemicals:
            structure = serverget("reaction_structure/%s" % (j['reaction_id']), None)
            data = {"structure": structure, "parameters": "rxn",
                    "filterChain": [{"filter": "clean", "parameters": {"dim": 2}},
                                    {"filter": "standardizer", "parameters": {"standardizerDefinition": STANDARD}}]}
            structure = chemaxpost('calculate/molExport', data)
            if structure:
                structure = json.loads(structure)
                file_path = '%stmp-%d.rxn' % (UPLOAD_PATH, task['id'])

                if 'isReaction' in structure:
                    with open(file_path, 'w') as tmp:
                        tmp.write(structure['structure'])
                    FEAR(file_path, j['reaction_id'])
                    os.remove(file_path)
                else:
                    pass
                        # todo: тут надо для молекул заморочиться.

                data = {"structure": structure['structure'], "parameters": {"method": "DEHYDROGENIZE"}}
                structure = chemaxpost('convert/hydrogenizer', data)
                if structure:
                    serverpost("reaction_structure/%s" % (j['reaction_id']), {'reaction_structure': structure})
            else:
                serverpost("reaction_structure/%s" % (j['reaction_id']), {'reaction_structure': ' '})

    serverput("task_status/%s" % (task['id']), {'task_status': MAPPING_DONE})


def FEAR(file_path, reaction_id):
    fearinput = RDFread(file_path)
    try:
        fearinput = next(fearinput.readdata())
        res = fear.firstcgr(fearinput)
        if not res:
            models = set()
            for x, y in fearinput['meta'].items():
                if '!reaction_center_hash' in x:
                    rhash = y.split("'")[0][5:]
                    mset = serverget("models", {'hash': rhash})
                    models.update([str(z['id']) for z in mset])
            # todo: переписать вьюшку на нормальные грабли.
            serverpost("reaction/%s" % reaction_id, {'models': ','.join(models)})
    except:
        pass
