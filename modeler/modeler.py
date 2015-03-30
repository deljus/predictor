# -*- coding: utf-8 -*-
import json
import pkgutil
import sched
import threading
import time
import modelset as models
import requests

__author__ = 'stsouko'
SERVER = "http://arsole.u-strasbg.fr"
PORT = 80
INTERVAL = 3
THREAD_LIMIT = 3

REQ_MODELLING = 4
LOCK_MODELLING = 5
MODELLING_DONE = 6

TASKS = []


def serverget(url, params):
    q = requests.get("%s:%d/%s" % (SERVER, PORT, url), params=params)
    return q.json()


def serverdel(url, params):
    requests.delete("%s:%d/%s" % (SERVER, PORT, url), params=params)


def serverput(url, params):
    requests.put("%s:%d/%s" % (SERVER, PORT, url), params=params)


def serverpost(url, params):
    q = requests.post("%s:%d/%s" % (SERVER, PORT, url), data=params)
    return q.text


def gettask():
    #todo: надо со временем сделать лок на стороне ядра. причем с таймаутом.
    return serverget('tasks', {'task_status': REQ_MODELLING})


def taskthread(task_id):
    serverput("task_status/%s" % task_id, {'task_status': LOCK_MODELLING})
    chemicals = serverget("task_reactions/%s" % task_id, None)
    for j in chemicals:
        structure = serverget("reaction/%s" % (j['reaction_id']), None)
        for x, y in structure['models'].items():
            result = dict(modelid=x, result=json.dumps(models.MODELS[y].getresult(structure)))
            serverpost("reaction_result/%s" % (j['reaction_id']), result)

    serverput("task_status/%s" % task_id, {'task_status': MODELLING_DONE})


def run():
    TASKS.extend(gettask()) #todo: надо запилить приоритеты. в начало совать важные в конец остальное
    while TASKS and threading.active_count() < THREAD_LIMIT:
        i = TASKS.pop(0)
        t = threading.Thread(target=taskthread, args=(i['id']))
        t.start()


class PeriodicScheduler(object):
    def __init__(self):
        self.scheduler = sched.scheduler(time.time, time.sleep)

    def setup(self, interval, action, actionargs=()):
        action(*actionargs)
        self.scheduler.enter(interval, 1, self.setup, (interval, action, actionargs))

    def run(self):
        self.scheduler.run()


def main():
    registeredmodels = {x['name']: x['id'] for x in serverget("models", None)}

    todelete = set(registeredmodels).difference(models.MODELS)
    toattach = set(models.MODELS).difference(registeredmodels)

    print('removed models %s' % todelete)
    print('new models %s' % toattach)

    for x in toattach:
        model = models.MODELS[x]
        print(x, model.getdesc(), model.is_reation(), model.gethashes())
        print(serverpost("models", {'name': x, 'desc': model.getdesc(),
                                    'is_reaction': model.is_reation(), 'hashes': model.gethashes()}))

    for x in todelete:
        serverdel("models", {'id': registeredmodels[x]})

    periodic_scheduler = PeriodicScheduler()
    periodic_scheduler.setup(INTERVAL, run)
    periodic_scheduler.run()

if __name__ == '__main__':
    main()