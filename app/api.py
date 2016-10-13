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
import uuid
import os
from app.config import UPLOAD_PATH, StructureStatus, TaskStatus, ModelType, TaskType
from app.models import Tasks, Structures, Additives, Models, Additiveset
from app.redis import RedisCombiner
from flask import Blueprint
from flask_login import current_user
from flask_restful import reqparse, Resource, fields, marshal, abort, Api
from functools import wraps
from pony.orm import db_session, select, left_join
from werkzeug import datastructures


api_bp = Blueprint('api', __name__)
api = Api(api_bp)

redis = RedisCombiner()

taskstructurefields = dict(structure=fields.Integer, data=fields.String, temperature=fields.Float(298),
                           pressure=fields.Float(1),
                           todelete=fields.Boolean(False),
                           additives=fields.List(fields.Nested(dict(additive=fields.Integer, amount=fields.Float))),
                           models=fields.List(fields.Integer))


def get_preparer_model():
    with db_session:
        return next(dict(model=m.id, name=m.name, description=m.description, type=ModelType(m.model_type),
                         destinations=[dict(host=x.host, port=x.port, password=x.password) for x in m.destinations])
                    for m in select(m for m in Models if m.model_type == ModelType.PREPARER.value))


def get_additives():
    with db_session:
        return {a.id: dict(additive=a.id, name=a.name, structure=a.structure, type=a.type)
                for a in select(a for a in Additives)}


def get_models():
    with db_session:
        return {m.id: dict(model=m.id, name=m.name, description=m.description, type=ModelType(m.model_type),
                           destinations=[dict(host=x.host, port=x.port, password=x.password) for x in m.destinations])
                for m in select(m for m in Models)}


def fetchtask(task, status):
    job = redis.fetch_job(task)
    if job is None:
        abort(403, message=dict(task='invalid id'))

    if not job:
        abort(500, message=dict(server='error'))

    if not job['is_finished']:
        abort(403, message=dict(task='not ready'))

    if job['result']['status'] != status:
        abort(403, message=dict(task=dict(status='incorrect')))

    if job['result']['user'] != current_user.id:
        abort(403, message=dict(task='access denied'))

    return job['result'], job['ended_at']


def format_results(task, status):
    result, ended_at = fetchtask(task, status)
    result['task'] = task
    result['date'] = ended_at.strftime("%Y-%m-%d %H:%M:%S")
    result['status'] = result['status'].value
    result['type'] = result['type'].value
    for s in result['structures']:
        s['status'] = s['status'].value
        for m in s['models']:
            m['type'] = m['type'].value
    return result


def authenticate(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated:
            return func(*args, **kwargs)

        abort(401, message=dict(user='not authenticated'))
    return wrapper


class CResource(Resource):
    method_decorators = [authenticate]


''' ===================================================
    collector of modeled tasks (individually). return json
    ===================================================
'''


class ResultsTask(CResource):
    def get(self, task):
        try:
            task = int(task)
        except ValueError:
            abort(403, message=dict(task='invalid id'))

        with db_session:
            result = Tasks.get(id=task)
            if not result:
                return dict(message=dict(task='invalid id')), 403
            if result.user.id != current_user.id:
                return dict(message=dict(task='access denied')), 403

            structures = select(s for s in Structures if s.task == result)
            resulsts = left_join((s.id, r.attrib, r.value, r.type, m.name)
                                 for s in Structures for r in s.results for m in r.model
                                 if s.task == result)
            additives = left_join((s.id, a.amount, p.id, p.name, p.type, p.structure)
                                  for s in Structures for a in s.additives for p in a.additive
                                  if s.task == result)

            tmp1, tmp2 = {}, {}

            # todo: result refactoring
            for s, ra, rv, rt, m in resulsts:
                tmp1.setdefault(s, {}).setdefault(m, []).append(dict(key=ra, value=rv, type=rt))

            for s, aa, aid, an, at, af in additives:
                if aid:
                    tmp2.setdefault(s, []).append(dict(additive=aid, name=an, structure=af, type=at, amount=aa))
                else:
                    tmp2[s] = []

            return dict(task=result.id, status=TaskStatus.DONE.value,
                        date=result.create_date.strftime("%Y-%m-%d %H:%M:%S"),
                        type=result.task_type, user=result.user.id if result.user else None,
                        structures=[dict(structure=s.id, data=s.structure, is_reaction=s.isreaction,
                                         temperature=s.temperature, pressure=s.pressure, status=s.status,
                                         models=[dict(model=m, results=r) for m, r in tmp1[s.id].items()],
                                         additives=tmp2[s.id]) for s in structures])

    def post(self, task):
        result, ended_at = fetchtask(task, TaskStatus.DONE)

        with db_session:
            _task = Tasks(task_type=result['type'], date=ended_at)
            for s in result['structures']:
                _structure = Structures(structure=s['data'], isreaction=s['is_reaction'], temperature=s['temperature'],
                                        pressure=s['pressure'], status=s['status'])
                for a in s['additives']:
                    Additiveset(additive=Additives[a['additive']], structure=_structure, amount=a['amount'])

                # todo: save results

        return dict(task=_task.id, status=TaskStatus.DONE.value, date=ended_at.strftime("%Y-%m-%d %H:%M:%S"),
                    type=_task.task_type, user=_task.user.id)

''' ===================================================
    api for task modeling.
    ===================================================
'''


class StartTask(CResource):
    def get(self, task):
        return format_results(task, TaskStatus.DONE)

    def post(self, task):
        result = fetchtask(task, TaskStatus.PREPARED)[0]
        result['status'] = TaskStatus.MODELING
        newjob = redis.new_job(result)
        return dict(task=newjob.id, status=result['status'].value, type=result['type'].value,
                    date=newjob.created_at.strftime("%Y-%m-%d %H:%M:%S"), user=result['user'])

''' ===================================================
    api for task preparation.
    ===================================================
'''
pt_post = reqparse.RequestParser()
pt_post.add_argument('structures', type=lambda x: marshal(x, taskstructurefields),  required=True)


class PrepareTask(CResource):
    def get(self, task):
        return format_results(task, TaskStatus.PREPARED)

    def post(self, task):
        args = pt_post.parse_args()

        additives = get_additives()
        models = get_models()
        preparer = get_preparer_model()

        result = fetchtask(task, TaskStatus.PREPARED)[0]
        prepared = {}
        for s in result['structures']:
            if s['status'] == StructureStatus.RAW:  # for raw structures restore preparer if failed
                s['models'] = [preparer]
            prepared[s['structure']] = s

        structures = args['structures'] if isinstance(args['structures'], list) else [args['structures']]
        tmp = {x['structure']: x for x in structures if x['structure'] in prepared}

        report = False
        for s, d in tmp.items():
            report = True
            if d['todelete']:
                prepared.pop(s)
            else:
                if d['additives'] is not None:
                    alist = []
                    for a in d['additives']:
                        if a['additive'] in additives and 0 < a['amount'] < 1:
                            a.update(additives[a['additive']])
                            alist.append(a)
                    prepared[s]['additives'] = alist

                if result['type'] == TaskType.MODELING and d['models'] is not None and \
                        not d['data'] and prepared[s]['status'] != StructureStatus.RAW:
                    prepared[s]['models'] = [models[m] for m in d['models']
                                             if m in models and prepared[s]['is_reaction'] == models[m]['type'] % 2]

                if d['data']:
                    prepared[s]['data'] = d['data']
                    prepared[s]['status'] = StructureStatus.RAW
                    prepared[s]['models'] = [preparer]

                if d['temperature']:
                    prepared[s]['temperature'] = d['temperature']

                if d['pressure']:
                    prepared[s]['pressure'] = d['pressure']

        if not report:
            abort(415, message=dict(structures='invalid data'))

        result['structures'] = list(prepared.values())
        result['status'] = TaskStatus.PREPARING
        new_job = redis.new_job(result)

        if new_job is None:
            abort(500, message=dict(server='error'))

        return dict(task=new_job.id, status=result['status'].value,  type=result['type'],
                    date=new_job.created_at.strftime("%Y-%m-%d %H:%M:%S"), user=result['user'])

''' ===================================================
    api for task creation.
    ===================================================
'''
ct_post = reqparse.RequestParser()
ct_post.add_argument('structures', type=lambda x: marshal(x, taskstructurefields), required=True)


class CreateTask(CResource):
    def post(self, _type):
        try:
            _type = TaskType(_type)
        except ValueError:
            abort(403, message=dict(task=dict(type='invalid id')))

        args = ct_post.parse_args()

        additives = get_additives()

        preparer = get_preparer_model()
        structures = args['structures'] if isinstance(args['structures'], list) else [args['structures']]

        data = []
        for s, d in enumerate(structures, start=1):
            if d['data']:
                alist = []
                for a in d['additives'] or []:
                    if a['additive'] in additives and 0 < a['amount'] < 1:
                        a.update(additives[a['additive']])
                        alist.append(a)

                data.append(dict(structure=s, data=d['data'], status=StructureStatus.RAW, pressure=d['pressure'],
                                 temperature=d['temperature'], additives=alist, models=[preparer]))

        if not data:
            return dict(message=dict(structures='invalid data')), 415

        new_job = redis.new_job(dict(status=TaskStatus.NEW, type=_type, user=current_user.id, structures=data))

        if new_job is None:
            abort(500, message=dict(server='error'))

        return dict(task=new_job.id, status=TaskStatus.PREPARING.value, type=_type.value,
                    date=new_job.created_at.strftime("%Y-%m-%d %H:%M:%S"), user=current_user.id)

uf_post = reqparse.RequestParser()
uf_post.add_argument('file.path', type=str)
uf_post.add_argument('structures', type=datastructures.FileStorage, location='files')


class UploadTask(CResource):
    def post(self, _type):
        try:
            _type = TaskType(_type)
        except ValueError:
            abort(403, message=dict(task=dict(type='invalid id')))

        args = uf_post.parse_args()

        file_path = None
        if args['file.path']:  # костыль. если не найдет этого в аргументах, то мы без NGINX-upload.
            file_path = args['file.path']
        elif args['structures']:
            file_path = os.path.join(UPLOAD_PATH, str(uuid.uuid4()))
            args['structures'].save(file_path)

        if not file_path:
            return dict(message=dict(structures='invalid data')), 415

        file_url = os.path.basename(file_path)

        new_job = redis.new_job(dict(status=TaskStatus.NEW, type=_type, user=current_user.id,
                                     structuresfile=dict(url=file_url, model=get_preparer_model())))
        if new_job is None:
            abort(500, message=dict(server='error'))

        return dict(task=new_job.id, status=TaskStatus.PREPARING.value, type=_type.value,
                    date=new_job.created_at.strftime("%Y-%m-%d %H:%M:%S"), user=current_user.id)


api.add_resource(CreateTask, '/task/create/<int:_type>')
api.add_resource(UploadTask, '/task/upload/<int:_type>')
api.add_resource(PrepareTask, '/task/prepare/<string:task>')
api.add_resource(StartTask, '/task/modeling/<string:task>')
api.add_resource(ResultsTask, '/task/results/<string:task>')
