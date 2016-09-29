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
from app.config import TaskStatus, StructureStatus


class RedisCombiner(object):
    def __init__(self, model_destination, host='localhost', port=6379, password=None,
                 result_ttl=86400, job_timeout=3600):
        """
        :type model_destination: Iterable over Tuple(model_id, model_name, model_dest, model_type)
        """
        tmp = {}
        self.__models = {model: [tmp[name] if name in tmp else
                                 tmp.setdefault(name,
                                                Queue(name=name,
                                                      connection=Redis(**dict(zip(('host', 'port', 'password'), x))),
                                                      default_timeout=job_timeout)) for name, x in
                                 (('%s_%d' % (x[0], x[1]), x) for x in dests)]
                         for model, _, dests, _ in model_destination}

        self.__redis = tmp

        self.__models_names = {model: name for model, name, *_ in model_destination}

        self.__preparer = next(model for model, *_, _type in model_destination if _type == 0)

        self.__tasks = Queue(name='redis_combiner', connection=Redis(host=host, port=port, password=password),
                             default_timeout=job_timeout)

        self.__result_ttl = result_ttl

    def __getworker(self, model):
        # ad hoc for future grow. parallel structure preparation on many nodes
        return self.__models.get(model, [None])[0]

    def new_job(self, task):
        if task['status'] == TaskStatus.NEW:
            worker = [self.__getworker(self.__preparer)]
            data = [{'structuresfile': task.pop('structuresfile'),
                     'model': self.__models_names[self.__preparer]} if 'structuresfile' in task else
                    {'structures': task['structures'], 'model': self.__models_names[self.__preparer]}]

            task['structures'] = []

        elif task['status'] == TaskStatus.PREPARING:
            worker = [self.__getworker(self.__preparer)]
            data = [{'structures': [s for s in task['structures'] if s['status'] == StructureStatus.RAW],
                     'model': self.__models_names[self.__preparer]}]

            task['structures'] = [s for s in task['structures'] if s['status'] != StructureStatus.RAW]

        elif task['status'] == TaskStatus.MODELING:
            model_worker = {}
            model_struct = defaultdict(list)

            tmp = []
            for s in task['structures']:
                if s['status'] != StructureStatus.CLEAR or not \
                   [model_struct[m].append(s) for m in (x['model'] for x in s['models'])
                    if (model_worker[m] if m in model_worker else
                        model_worker.setdefault(m, self.__getworker(m))) is not None]:
                    tmp.append(s)

            worker, data = [], []
            for m, s in model_struct.items():
                worker.append(model_worker[m])
                data.append({'structures': s, 'model': self.__models_names[m]})

            task['structures'] = tmp

        else:
            return None  # DEV trigger for bug hunt

        jobs = [(w.name, w.enqueue_call('redis_worker.run', kwargs=d, result_ttl=self.__result_ttl).id)
                for w, d in zip(worker, data)]

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
        sub_jobs = [self.__redis[worker].fetch_job(sub_task) for worker, sub_task in result.pop('jobs')]

        if any(not x.is_finished for x in sub_jobs):
            return dict(is_finished=False)

        ended_at = max(x.ended_at for x in sub_jobs)

        tmp = {s['structure']: s for s in result['structures']}  # not modeled structures
        for s in (s for j in sub_jobs for s in j.result):
            _s = tmp.get(s['structure']) or tmp.setdefault(s['structure'], s)
            _s.setdefault('modeling_results', []).extend(s['modeling_results'])

        result['structures'] = list(tmp.values())

        return dict(is_finished=True, ended_at=ended_at, result=result)
