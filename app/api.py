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
from pony.orm import db_session, select, left_join
from app.models import Tasks, Structures, Results, Additiveset, Additives, Models, Users
from werkzeug import datastructures


redis = Queue(connection=Redis(), default_timeout=3600)

parser = reqparse.RequestParser()
parser.add_argument('task', type=int, required=True)

taskstructurefields = dict(sid=fields.Integer, structure=fields.String, temperature=fields.Float(298),
                           pressure=fields.Float(1),
                           todelete=fields.Boolean(default=False),
                           additives=fields.List(fields.Nested(dict(aid=fields.Integer, amount=fields.Float))),
                           models=fields.List(fields.Integer))

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
            additives = left_join((s.id, a.amount, p.id, p.name, p.type, p.structure)
                                  for s in Structures for a in s.additives for p in a.additive
                                  if s.task == task)

            tmp1, tmp2 = {}, {}

            for s, ra, rv, rt, m in resulsts:
                tmp1.setdefault(s, {}).setdefault(m, []).append(dict(param=ra, value=rv, type=rt))

            for s, aa, aid, an, at, af in additives:
                if aid:
                    tmp2.setdefault(s, []).append(dict(aid=aid, name=an, structure=af, type=at, amount=aa))
                else:
                    tmp2[s] = []

            return dict(tid=task.id, status=task.status, date=task.create_date.timestamp(), type=task.task_type,
                        uid=task.user.id if task.user else None,
                        structures=[dict(sid=s.id, structure=s.structure, is_reaction=s.isreaction,
                                         temperature=s.temperature, pressure=s.pressure, status=s.status,
                                         modeling_results=[dict(model=m, results=r) for m, r in tmp1[s.id].items()],
                                         additives=tmp2[s.id]) for s in structures])

''' ===================================================
    api for task preparation.
    ===================================================
'''
pt_get = reqparse.RequestParser()
pt_get.add_argument('task', type=str, required=True)
pt_post = pt_get.copy()
pt_post.add_argument('structures', type=lambda x: marshal(json.loads(x), taskstructurefields),  required=True)


class PrepareTask(Resource):
    def get(self):
        args = pt_get.parse_args()

        try:
            job = redis.fetch_job(args['task'])
        except:
            return dict(message=dict(task='invalid id')), 400

        if not job.is_finished:
            return dict(message=dict(task='not ready')), 400

        result = job.result
        result['tid'] = args['task']
        return result

    def post(self):
        args = pt_post.parse_args()

        try:
            job = redis.fetch_job(args['task'])
        except:
            return dict(message=dict(task='invalid id')), 400

        if not job.is_finished:
            return dict(message=dict(task='not ready')), 400

        structures = args['structures'] if isinstance(args['structures'], list) else [args['structures']]
        tmp = {x['sid']: x for x in structures if x['sid']}

        task = job.result
        pure = {x['sid']: x for x in task['structures']}

        with db_session:
            additives = {a.id: dict(aid=a.id, name=a.name, structure=a.structure, type=a.type)
                         for a in select(a for a in Additives)}
            models = {m.id: dict(mid=m.id, name=m.name, description=m.description, type=m.model_type)
                      for m in select(m for m in Models)}

        report = False
        for s, d in tmp.items():
            if s in pure:
                report = True
                if d['todelete']:
                    pure.pop(s)
                else:
                    if d['additives'] is not None:
                        alist = []
                        for a in d['additives']:
                            if a['aid'] in additives and 0 < a['amount'] < 1:
                                a.update(additives[a['aid']])
                                alist.append(a)
                        pure[s]['additives'] = alist

                    if task['type'] == 0 and d['models'] is not None:
                        pure[s]['models'] = [models[m] for m in d['models']
                                             if m in models and pure[s]['is_reaction'] == models[m]['type'] % 2]

                    if d['structure']:
                        pure[s]['structure'] = d['structure']
                        pure[s]['status'] = 0

                    if d['temperature']:
                        pure[s]['temperature'] = d['temperature']

                    if d['pressure']:
                        pure[s]['pressure'] = d['pressure']

        if report:
            task['structures'] = list(pure.values())
            newjob = redis.enqueue_call('redis_examp.prep', args=(task,), result_ttl=86400)

            return dict(tid=newjob.id, status=task['status'], date=newjob.created_at.timestamp(), type=task['type'],
                        uid=task['uid'])
        else:
            return dict(message=dict(structures='invalid data')), 400

''' ===================================================
    api for task creation.
    ===================================================
'''
ct_post = reqparse.RequestParser()
ct_post.add_argument('type', type=int, required=True)
ct_post.add_argument('structures', type=lambda x: marshal(json.loads(x), taskstructurefields), required=True)


class CreateTask(Resource):
    def post(self):
        args = ct_post.parse_args()

        with db_session:
            additives = {a.id: dict(aid=a.id, name=a.name, structure=a.structure, type=a.type)
                         for a in select(a for a in Additives)}

        structures = args['structures'] if isinstance(args['structures'], list) else [args['structures']]

        data = []
        for s, d in enumerate(structures, start=1):
            if d['structure']:
                alist = []
                for a in d['additives'] or []:
                    if a['aid'] in additives and 0 < a['amount'] < 1:
                        a.update(additives[a['aid']])
                        alist.append(a)

                data.append(dict(sid=s, structure=d['structure'], status=0, pressure=d['pressure'],
                                 temperature=d['temperature'], additives=alist))

        if not data:
            return dict(message=dict(structures='invalid data')), 400

        task = dict(status=0, type=args['type'], uid=None, structures=data)
        newjob = redis.enqueue_call('redis_examp.prep', args=(task,), result_ttl=86400)

        return dict(tid=newjob.id, status=0, date=newjob.created_at.timestamp(), type=args['type'], uid=None)

uf_post = reqparse.RequestParser()
uf_post.add_argument('type', type=int, required=True)
ct_post.add_argument('file.path', type=str)
ct_post.add_argument('structures', type=datastructures.FileStorage, location='files')


class UploadFile(Resource):
    def post(self):
        args = ct_post.parse_args()

        file_path = None
        if args['file.path']:  # костыль. если не найдет этого в аргументах, то мы без NGINX сидим тащемта.
            file_path = args['file.path']
        elif args['file']:
            file_path = os.path.join(UPLOAD_PATH, str(uuid.uuid4()))
            args['file'].save(file_path)

        if not file_path:
            return dict(message=dict(structures='invalid data')), 400

        task = dict(status=0, type=args['type'], uid=None, structures=file_path)
        newjob = redis.enqueue_call('redis_examp.file', args=(task,), result_ttl=86400)

        return dict(tid=newjob.id, status=0, date=newjob.created_at.timestamp(), type=args['type'], uid=None)
