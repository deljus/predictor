# -*- coding: utf-8 -*-

from .config import LOCK_MAPPING, STANDARD, MAPPING_DONE, UPLOAD_PATH, REQ_MAPPING, CHEMAXON, SERVER, PORT, STANDARDIZER
import subprocess as sp
import xml.etree.ElementTree as ET
import re

import requests
import json

from .FEAR.RDFread import RDFread
from .FEAR.CGR import CGR

fear = CGR()


def serverget(url, params):
    for _ in range(10):
        try:
            q = requests.get("%s:%d/%s" % (SERVER, PORT, url), params=params, timeout=20)
        except:
            continue
        else:
            if q.status_code in (201, 200):
                return q.json()
            else:
                continue
    else:
        return []


def serverput(url, params):
    for _ in range(10):
        try:
            q = requests.put("%s:%d/%s" % (SERVER, PORT, url), params=params, timeout=20)
        except:
            continue
        else:
            if q.status_code in (201, 200):
                return True
            else:
                continue
    else:
        return False


def serverpost(url, params):
    for _ in range(10):
        try:
            q = requests.post("%s:%d/%s" % (SERVER, PORT, url), data=params, timeout=20)
        except:
            continue
        else:
            if q.status_code in (201, 200):
                return q.text
            else:
                continue
    else:
        return False


def chemaxpost(url, data):
    for _ in range(10):
        try:
            q = requests.post("%s/rest-v0/util/%s" % (CHEMAXON, url), data=json.dumps(data),
                              headers={'content-type': 'application/json'}, timeout=20)
        except:
            continue
        else:
            if q.status_code in (201, 200):
                return q.text
            else:
                continue
    else:
        return False


def gettask():
    return serverget('tasks', {'task_status': REQ_MAPPING})


def getfiletask():
    return serverget('parser', None)


def getsolvents():
    return serverget('solvents', None)


def create_task_from_file(task):
    file_path = task['file']
    task_id = task['id']
    tmp_file = '%stmp-%d.mrv' % (UPLOAD_PATH, task_id)
    tmp_fear_file = '%stmp-%d.rxn' % (UPLOAD_PATH, task_id)
    temp = 298
    sp.call([STANDARDIZER, file_path, '-c', STANDARD, '-f', 'mrv', '-o', tmp_file])

    file = open(tmp_file, 'r')
    solv = {x['name'].lower(): x['id'] for x in getsolvents()}

    for mol in file:
        if '<MDocument>' in mol:
            tree = ET.fromstring(mol)
            prop = {x.get('title').lower(): x.find('scalar').text.lower().strip() for x in tree.iter('property')}
            solvlist = {}
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
                data = dict(task_id=task_id, structure=structure, solvent=json.dumps(solvlist), temperature=temp)
                q = serverpost('parser', data)
                if q.isdigit(): # проверка на корректный ответ. по сути не нужна. но да пох.
                    data = {"structure": mol, "parameters": "rxn"}
                    structure = chemaxpost('calculate/stringMolExport', data)
                    if '$RXN' in structure:
                        with open(tmp_fear_file, 'w') as tmp:
                            tmp.write(structure)
                        FEAR(tmp_fear_file, int(q))
                    else:
                        pass
                        # todo: тут надо для молекул заморочиться.

    serverput("task_status/%s" % task_id, {'task_status': MAPPING_DONE})


def mapper(task):
    if serverput("task_status/%s" % (task['id']), {'task_status': LOCK_MAPPING}):
        chemicals = serverget("task_reactions/%s" % (task['id']), None)
        for j in chemicals:
            structure = serverget("reaction_structure/%s" % (j['reaction_id']), None)

            data = {"structure": structure, "parameters": {"standardizerDefinition": STANDARD}}
            standardised = chemaxpost('convert/standardizer', data)

            data = {"structure": standardised, "parameters": {"autoMappingStyle": "OFF"}}
            r_structure = chemaxpost('convert/reactionConverter', data)

            data = {"structure": r_structure, "parameters": "rxn"}
            structure = chemaxpost('calculate/stringMolExport', data)

            UPLOAD_PATH = '/tmp/'
            file_path = '%stmp-%d.rxn' % (UPLOAD_PATH, task['id'])

            if '$RXN' in structure:
                with open(file_path, 'w') as tmp:
                    tmp.write(structure)
                FEAR(file_path, j['reaction_id'])
            else:
                pass
                    # todo: тут надо для молекул заморочиться.

            data = {"structure": r_structure, "parameters": {"method": "DEHYDROGENIZE"}}
            structure = chemaxpost('convert/hydrogenizer', data)
            if structure:
                serverpost("reaction_structure/%s" % (j['reaction_id']), {'reaction_structure': structure})

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
                    mset = serverget("models", {'model_hash': rhash})
                    models.update([str(z['id']) for z in mset])
            # todo: переписать вьюшку на нормальные грабли.
            serverput("reaction/%s" % reaction_id, {'models': ','.join(models)})
    except:
        pass
