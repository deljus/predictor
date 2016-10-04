#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-
#
#  Copyright 2016 Ramil Nugmanov <stsouko@live.ru>
#  This file is part of predictor.
#
#  predictor 
#  is free software; you can redistribute it and/or modify
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
from collections import defaultdict
from redis import Redis
from rq import Queue
from pony.orm import db_session
from app.config import TaskStatus, StructureStatus
from app.models import Models, Destinations


class RedisCombiner(object):
    def __init__(self, host='localhost', port=6379, password=None, result_ttl=86400, job_timeout=3600):
        self.__result_ttl = result_ttl
        self.__job_timeout = job_timeout
        self.__tasks = Queue(name='redis_combiner', connection=Redis(host=host, port=port, password=password),
                             default_timeout=job_timeout + result_ttl)

    def __new_worker(self, model):
        with db_session:
            _model = Models.get(id=model)
            if _model:
                return self.__get_queue(_model.destinations)
        return None

    def __fetch_worker(self, dest):
        with db_session:
            _dest = Destinations.get(id=dest)
            if _dest:
                return self.__get_queue([_dest])
        return None

    def __get_queue(self, destinations):
        for x in destinations:
            r = Redis(host=x.host, port=x.port, password=x.password)
            try:
                if r.ping():  # todo: check for free machines
                    q = Queue(connection=r, default_timeout=self.__job_timeout)
                    return x.id, q
            except:
                pass
        return None

    def new_job(self, task):
        if task['status'] not in (TaskStatus.NEW, TaskStatus.PREPARING, TaskStatus.MODELING):
            return None

        if 'structuresfile' in task:
            tmp = task.pop('structuresfile')
            mid = tmp['model']['model']
            model_worker = self.__new_worker(mid)
            task['structures'] = []
            new_job = [(model_worker, {'structuresfile': tmp['url'],
                                       'model': tmp['model']})] if model_worker is not None else []

        else:
            model_worker = {}
            model_struct = defaultdict(list)
            tmp = []

            for s in task['structures']:
                # check for models in structures
                models = ((x['model'], x) for x in s.pop('models') if x['type'] != 0) \
                    if task['status'] == TaskStatus.MODELING else \
                    ((x['model'], x) for x in s.pop('models') if x['type'] == 0) \
                    if s['status'] == StructureStatus.RAW else []

                populate = [model_struct[m].append(s) for m, model in models
                            if (model_worker.get(m) or model_worker.setdefault(m, (self.__new_worker(m), model)))[0]
                            is not None]

                if not populate:
                    tmp.append(s)

            task['structures'] = tmp
            new_job = ((w, {'structures': s, 'model': m})
                       for (w, m), s in ((model_worker[m], s) for m, s in model_struct.items()))

        jobs = [(n, w.enqueue_call('redis_worker.run', kwargs=d, result_ttl=self.__result_ttl).id)
                for (n, w), d in new_job]

        task['jobs'] = jobs
        task['status'] = TaskStatus.DONE if task['status'] == TaskStatus.MODELING else TaskStatus.PREPARED

        return self.__tasks.enqueue_call('redis_worker.combiner', args=(task,), result_ttl=self.__result_ttl)

    def fetch_job(self, task):  # potentially cachable
        job = self.__tasks.fetch_job(task)
        if job is None:
            return None
        elif not job.is_finished:
            return dict(is_finished=False)

        result = job.result
        sub_jobs_fin = []
        sub_jobs_unf = []
        for worker, sub_task in result.pop('jobs'):
            _worker = self.__fetch_worker(worker)
            if _worker:  # skip lost workers
                tmp = _worker[1].fetch_job(sub_task)
                if tmp.is_finished:
                    sub_jobs_fin.append(tmp)
                else:
                    sub_jobs_unf.append((worker, sub_task))

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

        if sub_jobs_unf:
            result['jobs'] = sub_jobs_unf

        ended_at = max(x.ended_at for x in sub_jobs_fin)
        job.save()

        if sub_jobs_unf:
            return dict(is_finished=False)

        return dict(is_finished=True, ended_at=ended_at, result=result)
