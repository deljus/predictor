# -*- coding: utf-8 -*-
import os

__author__ = 'stsouko'
import requests

SERVER = "http://130.79.41.70"
PORT = 5000
CHEMAXON = "%s:8080/webservices" % SERVER
STANDARD = open(os.path.join(os.path.dirname(__file__), "std_rules.xml")).read()

TASK_CREATED = 0
REQ_MAPPING = 1
LOCK_MAPPING = 2
MAPPING_DONE = 3
REQ_MODELLING = 4
LOCK_MODELLING = 5
MODELLING_DONE = 6

task = requests.get("%s:%d/tasks" % (SERVER, PORT), params={'task_status': REQ_MAPPING})
print(task.json())
for i in task.json():
    #requests.put("%s:%d/task_status/%s" % (SERVER, PORT, i['id']), params={'task_status': LOCK_MAPPING})
    chemicals = requests.get("%s:%d/task_reactions/%s" % (SERVER, PORT, i['id']))
    for j in chemicals.json():
        structure = requests.get("%s:%d/reaction_structure/%s" % (SERVER, PORT, j['reaction_id']))
        standardised = requests.post("%s/rest-v0/util/convert/standardizer" % CHEMAXON,
                                     params={"structure": structure.text,
                                             "parameters": {"standardizerDefinition": STANDARD}})
        print(standardised.text)
        out = requests.post("%s/rest-v0/util/calculate/stringMolExport" % CHEMAXON,
                            params={"structure": standardised.text,
                                    "parameters": "rxn"})
        print(out.text)

        #requests.put("%s:%d/task_status/%s" % (SERVER, PORT, i['id']), params={'task_status': MAPPING_DONE})
