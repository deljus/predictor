# -*- coding: utf-8 -*-
import time

__author__ = 'stsouko'
from .config import UPLOAD_PATH, REQ_MAPPING, MOLCONVERT
import subprocess as sp
import xml.etree.ElementTree as ET
import re


def create_task_from_file(pdb, file_path, task_id):
    tmp_file = '%stmp-%d.mrv' % (UPLOAD_PATH, task_id)
    temp = 298
    sp.call([MOLCONVERT, 'mrv', file_path, '-o', tmp_file])
    file = open(tmp_file, 'r')
    solv = {x['name'].lower(): x['id'] for x in pdb.get_solvents()}
    t1 = time.time()
    for mol in file:
        t2 = time.time()
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
            #time.sleep(.1)
            print('==============>parsing time', time.time() - t2)
            t3 = time.time()
            pdb.insert_reaction(task_id=task_id, reaction_structure=mol.rstrip(), solvent=solvlist, temperature=temp)
            print('==============>update db time', time.time() - t3)
    pdb.update_task_status(task_id, REQ_MAPPING)
    print('==============>total parsing time', time.time() - t1)