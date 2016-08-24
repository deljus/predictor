# -*- coding: utf-8 -*-
#
# Copyright 2016 Ramil Nugmanov <stsouko@live.ru>
# This file is part of PREDICTOR.
#
# PREDICTOR is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
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
import uuid
import json
from redis import Redis
from rq import Queue
from app.config import UPLOAD_PATH
from flask_restful import reqparse, Resource, fields, marshal
from pony.orm import db_session, select, commit, left_join, delete, count
from app.models import Tasks, Structures, Results, Additiveset, Additives, Models, Users
from werkzeug import datastructures
from itertools import count as counter

redis = Queue(connection=Redis(), default_timeout=3600)

parser = reqparse.RequestParser()
parser.add_argument('task', type=int, required=True)


def collectadditives(task):
    additives = left_join((s.id, a.amount, p.id, p.name, p.type, p.structure)
                          for s in Structures for a in s.additives for p in a.additive
                          if s.task == task)
    tmp = {}
    for s, aa, aid, an, at, af in additives:
        if aid:
            tmp.setdefault(s, []).append(dict(aid=aid, name=an, structure=af, type=at, amount=aa))
        else:
            tmp[s] = []
    return tmp

''' ===================================================
    collector of modeled tasks (individually). return json
    ===================================================
'''
modelingresult = parser.copy()


class ModelingResult(Resource):
    def get(self):
        args = modelingresult.parse_args()
        with db_session:
            task = Tasks.get(id=args['task'])
            if not task:
                return dict(message=dict(task='invalid id')), 400

            structures = select(s for s in Structures if s.task == task)
            resulsts = left_join((s.id, r.attrib, r.value, r.type, m.name)
                                 for s in Structures for r in s.results for m in r.model
                                 if s.task == task)

            tmp1, tmp2 = {}, collectadditives(task)
            for s, ra, rv, rt, m in resulsts:
                tmp1.setdefault(s, {}).setdefault(m, []).append(dict(param=ra, value=rv, type=rt))

            return dict(tid=task.id, status=task.status, date=task.create_date.timestamp(), type=task.task_type,
                        uid=task.user.id if task.user else None,
                        structures=[dict(sid=s.id, structure=s.structure, is_reaction=s.isreaction,
                                         temperature=s.temperature, pressure=s.pressure, status=s.status,
                                         modeling_results=[dict(model=m, results=r) for m, r in tmp1[s.id].items()],
                                         additives=tmp2[s.id]) for s in structures])

''' ===================================================
    task get and update api.
    ===================================================
'''
taskstructurefields = dict(sid=fields.Integer, structure=fields.String, temperature=fields.Float, pressure=fields.Float,
                           additives=fields.List(fields.Nested(dict(aid=fields.Integer, amount=fields.Float))),
                           models=fields.List(fields.Integer))
ps_get = reqparse.RequestParser()
ps_get.add_argument('task', type=str, required=True)
ps_post = ps_get.copy()
ps_post.add_argument('structures', type=lambda x: marshal(json.loads(x), taskstructurefields),  required=True)


class PrepareStructure(Resource):
    def get(self):
        args = ps_get.parse_args()
        job = next((redis.fetch_job(x) for x in redis.job_ids() if x == args['task']), None)
        if not job:
            return dict(message=dict(task='invalid id')), 400

        if job.is_finished:
            result = job.result
            result['tid'] = args['task']
            return result
        else:
            return dict(message=dict(task='not ready')), 400

    def post(self):
        args = ps_post.parse_args()

        job = next((redis.fetch_job(x) for x in redis.job_ids() if x == args['task']), None)
        if not job:
            return dict(message=dict(task='invalid id')), 400

        if not job.is_finished:
            return dict(message=dict(task='not ready')), 400

        structures = args['structures'] if isinstance(args['structures'], list) else [args['structures']]
        tmp = {x['sid']: x for x in structures if x['sid']}

        result = job.result
        pure = {x['sid']: x for x in result['structures']}

        with db_session:
            additives = {a.id: dict(aid=a.id, name=a.name, structure=a.structure, type=a.type)
                         for a in select(a for a in Additives)}
            models = {m.id: dict(mid=m.id, name=m.name, description=m.description, type=m.type)
                      for m in select(m for m in Models)}

        report = []
        for s, d in tmp.items():
            if s in pure:
                alist = []
                for a in d.get('additives') or []:
                    if a['aid'] in additives and 0 < a['amount'] < 1:
                        a.update(additives[a['aid']])
                        alist.append(a)
                pure[s]['additives'] = alist

                if result['type'] == 0:
                    pure[s]['models'] = [models[m] for m in d.get('models') or []
                                         if m in models and pure[s]['is_reaction'] == models[m]['type'] % 2]

                if d.get('structure'):
                    pure[s]['structure'] = d['structure']

                if d.get('temperature'):
                    pure[s]['temperature'] = d['temperature']

                if d.get('pressure'):
                    pure[s]['pressure'] = d['pressure']

                report.append(s)

        if report:
            result['structures'] = list(pure.values())
            newjob = redis.enqueue_call('redis_examp.test', args=(result,), result_ttl=86400)

            return dict(tid=newjob.id, status=result['status'], date=newjob.created_at.timestamp(), type=result['type'],
                        uid=result['uid'])
        else:
            dict(message=dict(structures='invalid data')), 400

''' ===================================================
    task status api.
    ===================================================
'''
taskststatus = parser.copy()


class TaskStatus(Resource):
    def get(self):
        args = taskststatus.parse_args()
        with db_session:
            task = Tasks.get(id=args['task'])
            if task:
                return dict(tid=task.id, status=task.status, date=task.create_date.timestamp(), type=task.task_type,
                            uid=task.user.id if task.user else None)
        return dict(message=dict(task='invalid id or access denied')), 400

    def put(self):
        """ switch task status to 'ready for modeling' if task populated and contains only machine checked structures
        """
        args = taskststatus.parse_args()
        with db_session:
            task = Tasks.get(id=args['task'])
            if task and task.status == 1 and count(s for s in Structures if s.task == task and s.status != 1) == 0:
                task.status = 2
                return dict(message=dict(task='updated'))
        return dict(message=dict(task='invalid id or access denied')), 400

''' ===================================================
    structure or file upload api.
    ===================================================
'''
createtask = reqparse.RequestParser()
createtask.add_argument('auth', type=int, required=True)
createtask.add_argument('type', type=int, required=True)
createtask.add_argument('file.path', type=str)
createtask.add_argument('file', type=datastructures.FileStorage, location='files')
createtask.add_argument('structures', type=lambda x: marshal(json.loads(x), taskstructurefields))


class CreateTask(Resource):
    def post(self):
        args = createtask.parse_args()

        file_path = None
        if args['file.path']:  # костыль. если не найдет этого в аргументах, то мы без NGINX сидим тащемта.
            file_path = args['file.path']
        elif args['file']:
            file_path = os.path.join(UPLOAD_PATH, str(uuid.uuid4()))
            args['file'].save(file_path)

        if file_path:
            with db_session:
                task = Tasks(task_type=args['type'])
                # todo: populate task
            return dict(tid=task.id, status=task.status, date=task.create_date.timestamp(), type=task.task_type,
                        uid=task.user.id if task.user else None)

        return dict(message='invalid file or access denied'), 400
