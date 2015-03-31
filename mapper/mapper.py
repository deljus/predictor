# -*- coding: utf-8 -*-
import os
from FEAR.RDFread import RDFread
from FEAR.CGR import CGR
import sched
import time

__author__ = 'stsouko'
import requests
import json

SERVER = "http://arsole.u-strasbg.fr"
PORT = 80
CHEMAXON = "%s:80/webservices" % SERVER
STANDARD = open(os.path.join(os.path.dirname(__file__), "std_rules.xml")).read()

INTERVAL = 3

REQ_MAPPING = 1
LOCK_MAPPING = 2
MAPPING_DONE = 3


def serverget(url, params):
    for _ in range(10):
        try:
            q = requests.get("%s:%d/%s" % (SERVER, PORT, url), params=params, timeout=20)
        except:
            continue
        else:
            return q.json()
    else:
        return []


def serverput(url, params):
    for _ in range(10):
        try:
            requests.put("%s:%d/%s" % (SERVER, PORT, url), params=params, timeout=20)
        except:
            continue
        else:
            return True
    else:
        return False


def serverpost(url, params):
    for _ in range(10):
        try:
            q = requests.post("%s:%d/%s" % (SERVER, PORT, url), data=params, timeout=20)
        except:
            continue
        else:
            return q.text
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
            return q.text
    else:
        return False


def gettask():
    return serverget('tasks', {'task_status': REQ_MAPPING})


fear = CGR()


def run():
    tasks = gettask()
    for i in tasks:
        print(i)
        if serverput("task_status/%s" % (i['id']), {'task_status': LOCK_MAPPING}):
            chemicals = serverget("task_reactions/%s" % (i['id']), None)
            for j in chemicals:
                structure = serverget("reaction_structure/%s" % (j['reaction_id']), None)

                data = {"structure": structure, "parameters": {"standardizerDefinition": STANDARD}}
                standardised = chemaxpost('convert/standardizer', data)

                data = {"structure": standardised, "parameters": {"autoMappingStyle": "OFF"}}
                r_structure = chemaxpost('convert/reactionConverter', data)

                data = {"structure": r_structure, "parameters": "rxn"}
                structure = chemaxpost('calculate/stringMolExport', data)

                with open('/tmp/tmp_standard.rxn', 'w') as tmp:
                    tmp.write(structure)

                if '$RXN' in structure:
                    fearinput = RDFread('/tmp/tmp_standard.rxn')
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
                            #todo: переписать вьюшку на нормальные грабли.
                            serverput("reaction/%s" % (i['id']), {'models': ','.join(models)})
                    except:
                        pass
                else:
                    pass
                    #todo: тут надо для молекул заморочиться.

                data = {"structure": r_structure, "parameters": {"method": "DEHYDROGENIZE"}}
                structure = chemaxpost('convert/hydrogenizer', data)
                if structure:
                    serverpost("reaction_structure/%s" % (j['reaction_id']), {'reaction_structure': structure})

        serverput("task_status/%s" % (i['id']), {'task_status': MAPPING_DONE})


class PeriodicScheduler(object):
    def __init__(self):
        self.scheduler = sched.scheduler(time.time, time.sleep)

    def setup(self, interval, action, actionargs=()):
        action(*actionargs)
        self.scheduler.enter(interval, 1, self.setup, (interval, action, actionargs))

    def run(self):
        self.scheduler.run()


def main():
    periodic_scheduler = PeriodicScheduler()
    periodic_scheduler.setup(INTERVAL, run)
    periodic_scheduler.run()

if __name__ == '__main__':
    main()