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
import json
import uuid
import os
from app.config import UPLOAD_PATH
from app.models import Tasks, Structures, Additives, Models
from flask_login import current_user
from flask_restful import reqparse, Resource, fields, marshal, abort
from functools import wraps
from pony.orm import db_session, select, left_join
from redis import Redis
from rq import Queue
from rq.exceptions import NoSuchJobError
from werkzeug import datastructures

redis = Queue(connection=Redis(), default_timeout=3600)


def authenticate(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated:
            return func(*args, **kwargs)

        abort(400, message=dict(user='not authenticated'))
    return wrapper


class CResource(Resource):
    method_decorators = [authenticate]


parser = reqparse.RequestParser()

taskstructurefields = dict(structure=fields.Integer, data=fields.String, temperature=fields.Float(298),
                           pressure=fields.Float(1),
                           todelete=fields.Boolean(default=False),
                           additives=fields.List(fields.Nested(dict(additive=fields.Integer, amount=fields.Float))),
                           models=fields.List(fields.Integer))

''' ===================================================
    collector of modeled tasks (individually). return json
    ===================================================
'''
mr_get = parser.copy()
mr_get.add_argument('task', type=int, location='args', required=True)


class ModelingResult(CResource):
    def get(self):
        args = mr_get.parse_args()
        with db_session:
            task = Tasks.get(id=args['task'])
            if not task:
                return dict(message=dict(task='invalid id')), 400
            if task.user.id != current_user.id:
                return dict(message=dict(task='access denied')), 400

            structures = select(s for s in Structures if s.task == task)
            resulsts = left_join((s.id, r.attrib, r.value, r.type, m.name)
                                 for s in Structures for r in s.results for m in r.model
                                 if s.task == task)
            additives = left_join((s.id, a.amount, p.id, p.name, p.type, p.structure)
                                  for s in Structures for a in s.additives for p in a.additive
                                  if s.task == task)

            tmp1, tmp2 = {}, {}

            for s, ra, rv, rt, m in resulsts:
                tmp1.setdefault(s, {}).setdefault(m, []).append(dict(key=ra, value=rv, type=rt))

            for s, aa, aid, an, at, af in additives:
                if aid:
                    tmp2.setdefault(s, []).append(dict(additive=aid, name=an, structure=af, type=at, amount=aa))
                else:
                    tmp2[s] = []

            return dict(task=task.id, status=task.status, date=task.create_date.strftime("%Y-%m-%d %H:%M:%S"),
                        type=task.task_type, user=task.user.id if task.user else None,
                        structures=[dict(structure=s.id, data=s.structure, is_reaction=s.isreaction,
                                         temperature=s.temperature, pressure=s.pressure, status=s.status,
                                         modeling_results=[dict(model=m, results=r) for m, r in tmp1[s.id].items()],
                                         additives=tmp2[s.id]) for s in structures])

''' ===================================================
    api for task preparation.
    ===================================================
'''
pt_get = parser.copy()
pt_get.add_argument('task', type=str, location='args', required=True)
pt_post = pt_get.copy()
pt_post.add_argument('structures', type=lambda x: marshal(json.loads(x), taskstructurefields),  required=True)


class PrepareTask(CResource):
    @staticmethod
    def __fetchtask(task):
        try:
            job = redis.fetch_job(task)
            if not job.is_finished:
                abort(400, message=dict(task='not ready'))

            result = job.result
            if result['user'] != current_user.id:
                abort(400, message=dict(task='access denied'))
            return result

        except NoSuchJobError:
            abort(400, message=dict(task='invalid id'))

    def get(self):
        args = pt_get.parse_args()

        task = self.__fetchtask(args['task'])
        task['task'] = args['task']
        task['date'] = task['date'].strftime("%Y-%m-%d %H:%M:%S")
        return task

    def post(self):
        args = pt_post.parse_args()

        task = self.__fetchtask(args['task'])

        pure = {x['structure']: x for x in task['structures']}

        structures = args['structures'] if isinstance(args['structures'], list) else [args['structures']]
        tmp = {x['structure']: x for x in structures if x['structure'] in pure}

        with db_session:
            additives = {a.id: dict(additive=a.id, name=a.name, structure=a.structure, type=a.type)
                         for a in select(a for a in Additives)}
            models = {m.id: dict(model=m.id, name=m.name, description=m.description, type=m.model_type)
                      for m in select(m for m in Models)}

        report = False
        for s, d in tmp.items():
            report = True
            if d['todelete']:
                pure.pop(s)
            else:
                if d['additives'] is not None:
                    alist = []
                    for a in d['additives']:
                        if a['additive'] in additives and 0 < a['amount'] < 1:
                            a.update(additives[a['additive']])
                            alist.append(a)
                    pure[s]['additives'] = alist

                if task['type'] == 0 and d['models'] is not None:
                    pure[s]['models'] = [models[m] for m in d['models']
                                         if m in models and pure[s]['is_reaction'] == models[m]['type'] % 2]

                if d['data']:
                    pure[s]['data'] = d['data']
                    pure[s]['status'] = 0

                if d['temperature']:
                    pure[s]['temperature'] = d['temperature']

                if d['pressure']:
                    pure[s]['pressure'] = d['pressure']

        if not report:
            abort(400, message=dict(structures='invalid data'))

        task['status'] = 0
        task['structures'] = list(pure.values())
        newjob = redis.enqueue_call('redis_examp.prep', args=(task,), result_ttl=86400)

        return dict(task=newjob.id, status=0, date=newjob.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    type=task['type'], user=task['user'])

''' ===================================================
    api for task creation.
    ===================================================
'''
ct_post = parser.copy()
ct_post.add_argument('type', type=int, location='args', required=True)
ct_post.add_argument('structures', type=lambda x: marshal(json.loads(x), taskstructurefields), required=True)


class CreateTask(CResource):
    def post(self):
        args = ct_post.parse_args()

        with db_session:
            additives = {a.id: dict(additive=a.id, name=a.name, structure=a.structure, type=a.type)
                         for a in select(a for a in Additives)}

        structures = args['structures'] if isinstance(args['structures'], list) else [args['structures']]

        data = []
        for s, d in enumerate(structures, start=1):
            if d['structure']:
                alist = []
                for a in d['additives'] or []:
                    if a['additive'] in additives and 0 < a['amount'] < 1:
                        a.update(additives[a['additive']])
                        alist.append(a)

                data.append(dict(structure=s, data=d['structure'], status=0, pressure=d['pressure'],
                                 temperature=d['temperature'], additives=alist))

        if not data:
            return dict(message=dict(structures='invalid data')), 400

        task = dict(status=0, type=args['type'], user=current_user.id, structures=data)
        newjob = redis.enqueue_call('redis_examp.prep', args=(task,), result_ttl=86400)

        return dict(task=newjob.id, status=0, date=newjob.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    type=args['type'], user=current_user.id)

uf_post = parser.copy()
uf_post.add_argument('type', type=int, location='args', required=True)
uf_post.add_argument('file.path', type=str)
uf_post.add_argument('structures', type=datastructures.FileStorage, location='files')


class UploadFile(CResource):
    def post(self):
        args = uf_post.parse_args()

        file_path = None
        if args['file.path']:  # костыль. если не найдет этого в аргументах, то мы без NGINX сидим тащемта.
            file_path = args['file.path']
        elif args['structures']:
            file_path = os.path.join(UPLOAD_PATH, str(uuid.uuid4()))
            args['structures'].save(file_path)

        if not file_path:
            return dict(message=dict(structures='invalid data')), 400

        task = dict(status=0, type=args['type'], user=current_user.id, structures=file_path)
        newjob = redis.enqueue_call('redis_examp.file', args=(task,), result_ttl=86400)

        return dict(task=newjob.id, status=0, date=newjob.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    type=args['type'], user=current_user.id)
