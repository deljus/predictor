# -*- coding: utf-8 -*-
#
#  Copyright 2016 Ramil Nugmanov <stsouko@live.ru>
#  This file is part of MWUI.
#
#  MWUI is free software; you can redistribute it and/or modify
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
import pickle
from collections import defaultdict
from datetime import datetime
from uuid import uuid4
from redis import Redis, ConnectionError
from rq import Queue
from .config import TaskStatus, StructureStatus, ModelType


class RedisCombiner(object):
    def __init__(self, host='localhost', port=6379, password=None, result_ttl=86400, job_timeout=3600):
        self.__result_ttl = result_ttl
        self.__job_timeout = job_timeout

        self.__tasks = Redis(host=host, port=port, password=password)

    def __new_worker(self, destinations):
        for x in destinations:
            return x, self.__get_queue(x)  # todo: check for free machines. len(q) - number of tasks
        return None

    def __get_queue(self, destination):
        r = Redis(host=destination['host'], port=destination['port'], password=destination['password'])
        try:
            r.ping()
            return Queue(connection=r, name=destination['name'], default_timeout=self.__job_timeout)
        except ConnectionError:
            return None

    def new_job(self, task):
        if task['status'] not in (TaskStatus.NEW, TaskStatus.PREPARING, TaskStatus.MODELING):
            return None  # for api check.

        try:
            self.__tasks.ping()
        except ConnectionError:
            return None

        model_worker = {}
        model_struct = defaultdict(list)
        tmp = []

        for s in task['structures']:
            # check for models in structures
            if task['status'] == TaskStatus.MODELING:
                models = ((x['model'], x) for x in s.pop('models') if x['type'] != ModelType.PREPARER)
            elif s['status'] == StructureStatus.RAW:
                models = ((x['model'], x) for x in s.pop('models') if x['type'] == ModelType.PREPARER)
            else:
                models = []

            populate = [model_struct[m].append(s) for m, model in models
                        if (model_worker.get(m) or
                            model_worker.setdefault(m, (self.__new_worker(model.pop('destinations')), model)))[0]
                        is not None]

            if not populate and not isinstance(s['data'], dict):  # second cond ad-hoc for file upload.
                s.setdefault('models', [])
                tmp.append(s)

        task['structures'] = tmp
        new_job = ((w, {'structures': s, 'model': m})
                   for (w, m), s in ((model_worker[m], s) for m, s in model_struct.items()))

        try:
            jobs = [(dest, w.enqueue_call('redis_worker.run', kwargs=d, result_ttl=self.__result_ttl).id)
                    for (dest, w), d in new_job]

            task['jobs'] = jobs
            task['status'] = TaskStatus.DONE if task['status'] == TaskStatus.MODELING else TaskStatus.PREPARED

            _id = str(uuid4())
            self.__tasks.set(_id, pickle.dumps((task, datetime.utcnow())), ex=self.__result_ttl)
            return dict(id=_id, created_at=datetime.utcnow())
        except Exception as err:
            print("new_job->ERROR:", err)
            return None

    def fetch_job(self, task):
        try:
            self.__tasks.ping()
        except ConnectionError:
            return False

        job = self.__tasks.get(task)
        if job is None:
            return None

        result, ended_at = pickle.loads(job)

        sub_jobs_fin = []
        sub_jobs_unf = []
        for dest, sub_task in result['jobs']:
            worker = self.__get_queue(dest)
            if worker is not None:  # skip lost workers
                tmp = worker.fetch_job(sub_task)
                if tmp is not None:
                    if tmp.is_finished:
                        sub_jobs_fin.append(tmp)
                    elif tmp.is_failed:  # skip failed jobs
                        pass
                    else:
                        sub_jobs_unf.append((dest, sub_task))

        if sub_jobs_fin:
            tmp = {s['structure']: s for s in result['structures']}  # not modeled structures
            for j in sub_jobs_fin:
                for s in j.result:
                    if s['structure'] in tmp:
                        tmp[s['structure']]['models'].extend(s['models'])
                    else:
                        tmp[s['structure']] = s
                j.delete()

            result['structures'] = list(tmp.values())
            result['jobs'] = sub_jobs_unf
            ended_at = max(x.ended_at for x in sub_jobs_fin)

            self.__tasks.set(task, pickle.dumps((result, ended_at)), ex=self.__result_ttl)

        if sub_jobs_unf:
            return dict(is_finished=False)

        return dict(is_finished=True, ended_at=ended_at, result=result)
