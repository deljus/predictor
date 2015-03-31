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

#SERVER = "http://localhost"
#PORT = 5000

INTERVAL = 3
THREAD_LIMIT = 3

REQ_MODELLING = 4
LOCK_MODELLING = 5
MODELLING_DONE = 6

TASKS = []
LOSE = []


def serverdel(url, params):
    for _ in range(1000):
        try:
            requests.delete("%s:%d/%s" % (SERVER, PORT, url), params=params, timeout=20)
        except:
            continue
        else:
            return True
    else:
        return False


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


def gettask():
    #todo: надо со временем сделать лок на стороне ядра. причем с таймаутом.
    return serverget('tasks', {'task_status': REQ_MODELLING})


def taskthread(task_id):
    if serverput("task_status/%s" % task_id, {'task_status': LOCK_MODELLING}):
        chemicals = serverget("task_reactions/%s" % task_id, None)
        for r in chemicals:
            reaction_id = r['reaction_id']
            reaction = serverget("reaction/%s" % reaction_id, None)
            if reaction:
                for model_id, model_name in reaction['models'].items():
                    model_result = models.MODELS[model_name].getresult(reaction)
                    reaction_result = dict(modelid=model_id, result=json.dumps(model_result))
                    if not serverpost("reaction_result/%s" % reaction_id, reaction_result):
                        # если не удалось записать результаты моделирования, то схороним их на повторную отправку.
                        LOSE.append(('post', "reaction_result/%s" % reaction_id, reaction_result))

    if not serverput("task_status/%s" % task_id, {'task_status': MODELLING_DONE}):
        LOSE.append(("put", "task_status/%s" % task_id, {'task_status': MODELLING_DONE}))


def run():
    TASKS.extend(gettask()) #todo: надо запилить приоритеты. в начало совать важные в конец остальное
    if LOSE:
        pass # запилить заливку повторную данных.
    while TASKS and threading.active_count() < THREAD_LIMIT:
        i = TASKS.pop(0)
        t = threading.Thread(target=taskthread, args=([i['id']]))
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
        print(serverpost("models", {'name': x, 'desc': model.getdesc(),
                                    'is_reaction': model.is_reation(), 'hashes': model.gethashes()}))

    for x in todelete:
        serverdel("models", {'id': registeredmodels[x]})

    periodic_scheduler = PeriodicScheduler()
    periodic_scheduler.setup(INTERVAL, run)
    periodic_scheduler.run()

if __name__ == '__main__':
    main()