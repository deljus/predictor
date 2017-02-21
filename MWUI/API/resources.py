# -*- coding: utf-8 -*-
#
#  Copyright 2016, 2017 Ramil Nugmanov <stsouko@live.ru>
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
import uuid
from collections import defaultdict
from os import path
from flask import url_for, request, Response
from werkzeug.exceptions import HTTPException, Aborter
from flask_login import current_user, login_user
from flask_restful import reqparse, marshal, inputs, Resource
from functools import wraps
from pony.orm import db_session, select, left_join
from validators import url
from werkzeug import datastructures
from typing import Dict, Tuple
from flask_restful_swagger import swagger
from .data import get_additives, get_model, get_models_list, format_results
from .structures import (ModelRegisterFields, TaskPostResponseFields, TaskGetResponseFields, TaskStructureFields,
                         LogInFields, AdditivesListFields, ModelListFields)
from ..logins import UserLogin
from ..config import (UPLOAD_PATH, StructureStatus, TaskStatus, ModelType, TaskType, REDIS_HOST, REDIS_JOB_TIMEOUT,
                      REDIS_PASSWORD, REDIS_PORT, REDIS_TTL, StructureType, UserRole, BLOG_POSTS_PER_PAGE, AdditiveType,
                      ResultType)
from ..models import Task, Structure, Additive, Model, Additiveset, Destination, User, Result
from .redis import RedisCombiner


redis = RedisCombiner(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, result_ttl=REDIS_TTL,
                      job_timeout=REDIS_JOB_TIMEOUT)

task_types_desc = ', '.join('{0.value} - {0.name}'.format(x) for x in TaskType)
results_types_desc = ', '.join('{0.value} - {0.name}'.format(x) for x in ResultType)
additives_types_desc = ', '.join('{0.value} - {0.name}'.format(x) for x in AdditiveType)


class Abort512(HTTPException):
    code = 512
    description = 'task not ready'

original_flask_abort = Aborter(extra={512: Abort512})


def abort(http_status_code, **kwargs):
    """ copy-paste from flask-restful
    """
    try:
        original_flask_abort(http_status_code)
    except HTTPException as e:
        if len(kwargs):
            e.data = kwargs
        raise


def fetch_task(task, status):
    job = redis.fetch_job(task)
    if job is None:
        abort(404, message='invalid task id. perhaps this task has already been removed')

    if not job:
        abort(500, message='modeling server error')

    if not job['is_finished']:
        abort(512, message='PROCESSING.Task not ready')

    if job['result']['status'] != status:
        abort(406, message='task status is invalid. task status is [%s]' % job['result']['status'].name)

    if job['result']['user'] != current_user.id:
        abort(403, message='user access deny. you do not have permission to this task')

    return job['result'], job['ended_at']


def dynamic_docstring(*sub):
    def wrapper(f):
        f.__doc__ = f.__doc__.format(*sub)
        return f

    return wrapper


def authenticate(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated:
            return f(*args, **kwargs)

        abort(401, message=dict(user='not authenticated'))

    return wrapper


def auth_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.authorization
        if auth:
            u = UserLogin.get(auth.username.lower(), auth.password)
            if u and u.role_is(UserRole.ADMIN):
                return f(*args, **kwargs)

        return Response('access deny', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

    return wrapper


class AuthResource(Resource):
    method_decorators = [authenticate]


class AdminResource(Resource):
    method_decorators = [auth_admin]


class RegisterModels(AdminResource):
    def post(self):
        data = marshal(request.get_json(force=True), ModelRegisterFields.resource_fields)
        models = data if isinstance(data, list) else [data]
        available = {x['name']: [(d['host'], d['port'], d['name']) for d in x['destinations']]
                     for x in get_models_list(skip_prep=False).values()}
        report = []
        for m in models:
            if m['destinations']:
                if m['name'] not in available:
                    with db_session:
                        new_m = Model(type=m['type'], name=m['name'], description=m['description'],
                                      example=m['example'])

                        for d in m['destinations']:
                            Destination(model=new_m, **d)

                    report.append(dict(model=new_m.id, name=new_m.name, description=new_m.description,
                                       type=new_m.type.value,
                                       example=new_m.example,
                                       destinations=[dict(host=x.host, port=x.port, name=x.name)
                                                     for x in new_m.destinations]))
                else:
                    tmp = []
                    with db_session:
                        model = Model.get(name=m['name'])
                        for d in m['destinations']:
                            if (d['host'], d['port'], d['name']) not in available[m['name']]:
                                tmp.append(Destination(model=model, **d))

                    if tmp:
                        report.append(dict(model=model.id, name=model.name, description=model.description,
                                           type=model.type.value, example=model.example,
                                           destinations=[dict(host=x.host, port=x.port, name=x.name)
                                                         for x in tmp]))
        return report, 201


class AvailableModels(Resource):
    @swagger.operation(
        notes='Get available models',
        nickname='modellist',
        responseClass=ModelListFields.__name__,
        responseMessages=[dict(code=200, message="models list")])
    @dynamic_docstring(ModelType.MOLECULE_MODELING, ModelType.REACTION_MODELING)
    def get(self):
        """
        Get available models list

        response format:
        example - chemical structure in in smiles or marvin or cml format
        description - description of model. in markdown format.
        name - model name
        type - model type: {0.value} [{0.name}] or {1.value} [{1.name}]
        model - id
        """
        out = []
        for x in get_models_list(skip_destinations=True, skip_example=False).values():
            x['type'] = x['type'].value
            out.append(x)
        return out, 200


class AvailableAdditives(Resource):
    @swagger.operation(
        notes='Get available additives',
        nickname='additives',
        responseClass=AdditivesListFields.__name__,
        responseMessages=[dict(code=200, message="additives list")])
    @dynamic_docstring(additives_types_desc)
    def get(self):
        """
        Get available additives list

        response format:
        additive - id
        name - name of additive
        structure - chemical structure in smiles or marvin or cml format
        type - additive type: {0}
        """
        out = []
        for x in get_additives().values():
            x['type'] = x['type'].value
            out.append(x)
        return out, 200


results_fetch = reqparse.RequestParser()
results_fetch.add_argument('page', type=inputs.positive)


class ResultsTask(AuthResource):
    @swagger.operation(
        notes='Get saved modeled task',
        nickname='saved',
        responseClass=TaskGetResponseFields.__name__,
        parameters=[dict(name='task', description='Task ID', required=True,
                         allowMultiple=False, dataType='str', paramType='path')],
        responseMessages=[dict(code=200, message="modeled task"),
                          dict(code=403, message='user access deny. you do not have permission to this task'),
                          dict(code=404, message='invalid task id. perhaps this task has already been removed'),
                          dict(code=406, message='task status is invalid. only validation tasks acceptable'),
                          dict(code=500, message="modeling server error"),
                          dict(code=512, message='task not ready')])
    def get(self, task):
        """
        Task with modeling results of structures with conditions

        all structures include only models with nonempty results lists.
        see /task/model get doc.
        """
        try:
            task = int(task)
        except ValueError:
            abort(404, message='invalid task id. Use int Luke')

        page = results_fetch.parse_args().get('page')
        with db_session:
            result = Task.get(id=task)
            if not result:
                abort(404, message='Invalid task id. Perhaps this task has already been removed')

            if result.user.id != current_user.id:
                abort(403, message='User access deny. You do not have permission to this task')

            models = get_models_list(skip_destinations=True)
            for v in models.values():
                v['type'] = v['type'].value

            additives = get_additives()

            s = select(s for s in Structure if s.task == result).order_by(Structure.id)
            if page:
                s = s.page(page, pagesize=BLOG_POSTS_PER_PAGE)

            structures = {x.id: dict(structure=x.id, data=x.structure, temperature=x.temperature, pressure=x.pressure,
                                     type=x.structure_type, status=x.structure_status, additives=[], models=[])
                          for x in s}

            r = left_join((s.id, r.model.id, r.key, r.value, r.result_type)
                          for s in Structure for r in s.results if s.id in structures.keys() and r is not None)

            a = left_join((s.id, a.additive.id, a.amount)
                          for s in Structure for a in s.additives if s.id in structures.keys() and a is not None)

            for s, a, aa in a:
                tmp = dict(amount=aa)
                tmp.update(additives[a])
                structures[s]['additives'].append(tmp)

            tmp_models = defaultdict(dict)
            for s, m, rk, rv, rt in r:
                tmp_models[s].setdefault(m, []).append(dict(key=rk, value=rv, type=rt))

            for s, mr in tmp_models.items():
                for m, r in mr.items():
                    tmp = dict(results=r)
                    tmp.update(models[m])
                    structures[s]['models'].append(tmp)

        return dict(task=task, status=TaskStatus.DONE.value, date=result.date.strftime("%Y-%m-%d %H:%M:%S"),
                    type=result.task_type, user=result.user.id, structures=list(structures.values())), 200

    @swagger.operation(
        notes='Save modeled task',
        nickname='save',
        responseClass=TaskPostResponseFields.__name__,
        parameters=[dict(name='task', description='Task ID', required=True,
                         allowMultiple=False, dataType='str', paramType='path')],
        responseMessages=[dict(code=201, message="modeled task saved"),
                          dict(code=403, message='user access deny. you do not have permission to this task'),
                          dict(code=404, message='invalid task id. perhaps this task has already been removed'),
                          dict(code=406, message='task status is invalid. only modeled tasks acceptable'),
                          dict(code=500, message="modeling server error"),
                          dict(code=512, message='task not ready')])
    def post(self, task):
        """
        Store in database modeled task

        only modeled tasks can be saved.
        failed models in structures skipped.
        """
        result, ended_at = fetch_task(task, TaskStatus.DONE)

        with db_session:
            _task = Task(type=result['type'], date=ended_at, user=User[current_user.id])
            for s in result['structures']:
                _structure = Structure(structure=s['data'], type=s['type'], temperature=s['temperature'],
                                       pressure=s['pressure'], status=s['status'], task=_task)
                for a in s['additives']:
                    Additiveset(additive=Additive[a['additive']], structure=_structure, amount=a['amount'])

                for m in s['models']:
                    for r in m.get('results', []):
                        Result(model=m['model'], structure=_structure, type=r['type'], key=r['key'], value=r['value'])

        return dict(task=_task.id, status=TaskStatus.DONE.value, date=ended_at.strftime("%Y-%m-%d %H:%M:%S"),
                    type=result['type'].value, user=current_user.id), 201


class ModelTask(AuthResource):
    @swagger.operation(
        notes='Get modeled task',
        nickname='modeled',
        responseClass=TaskGetResponseFields.__name__,
        parameters=[dict(name='task', description='Task ID', required=True,
                         allowMultiple=False, dataType='str', paramType='path')],
        responseMessages=[dict(code=200, message="modeled task"),
                          dict(code=403, message='user access deny. you do not have permission to this task'),
                          dict(code=404, message='invalid task id. perhaps this task has already been removed'),
                          dict(code=406, message='task status is invalid. only validation tasks acceptable'),
                          dict(code=500, message="modeling server error"),
                          dict(code=512, message='task not ready')])
    @dynamic_docstring(results_types_desc)
    def get(self, task):
        """
        Task with results of structures with conditions modeling

        all structures include models with results lists.
        failed models contain empty results lists.

        see also /task/prepare get doc.

        available model results response types: {0}
        """
        page = results_fetch.parse_args().get('page')
        return format_results(task, fetch_task(task, TaskStatus.DONE), page=page), 200

    @swagger.operation(
        notes='Create modeling task',
        nickname='modeling',
        responseClass=TaskPostResponseFields.__name__,
        parameters=[dict(name='task', description='Task ID', required=True,
                         allowMultiple=False, dataType='str', paramType='path'),
                    dict(name='structures', description='Conditions and selected models for structure[s]',
                         required=True, allowMultiple=False, dataType=TaskStructureFields.__name__, paramType='body')],
        responseMessages=[dict(code=201, message="modeling task created"),
                          dict(code=400, message="invalid structure data"),
                          dict(code=403, message='user access deny. you do not have permission to this task'),
                          dict(code=404, message='invalid task id. perhaps this task has already been removed'),
                          dict(code=406, message='task status is invalid. only validation tasks acceptable'),
                          dict(code=500, message="modeling server error"),
                          dict(code=512, message='task not ready')])
    def post(self, task):
        """
        Modeling task structures and conditions

        send only changed conditions or todelete marks. see task/prepare doc.
        data, status and type fields unusable.
        """
        data = marshal(request.get_json(force=True), TaskStructureFields.resource_fields)
        result = fetch_task(task, TaskStatus.PREPARED)[0]

        prepared = {s['structure']: s for s in result['structures']}
        structures = data if isinstance(data, list) else [data]
        tmp = {x['structure']: x for x in structures if x['structure'] in prepared}

        if 0 in tmp:
            abort(400, message='invalid structure data')

        additives = get_additives()
        models = get_models_list()

        for s, d in tmp.items():
            if d['todelete']:
                prepared.pop(s)
            else:
                ps = prepared[s]
                if d['additives'] is not None:
                    alist = []
                    for a in d['additives']:
                        if a['additive'] in additives and (0 < a['amount'] <= 1
                                                           if additives[a['additive']]['type'] == AdditiveType.SOLVENT
                                                           else a['amount'] > 0):
                            a.update(additives[a['additive']])
                            alist.append(a)
                    ps['additives'] = alist

                if result['type'] != TaskType.MODELING:  # for search tasks assign compatible models
                    ps['models'] = [get_model(ModelType.select(ps['type'], result['type']))]

                elif d['models'] is not None and ps['status'] == StructureStatus.CLEAR:
                    ps['models'] = [models[m['model']].copy() for m in d['models'] if m['model'] in models and
                                    models[m['model']]['type'].compatible(ps['type'], TaskType.MODELING)]

                if d['temperature']:
                    ps['temperature'] = d['temperature']

                if d['pressure']:
                    ps['pressure'] = d['pressure']

        result['structures'] = list(prepared.values())
        result['status'] = TaskStatus.MODELING

        new_job = redis.new_job(result)
        if new_job is None:
            abort(500, message='modeling server error')

        return dict(task=new_job['id'], status=result['status'].value, type=result['type'].value,
                    date=new_job['created_at'].strftime("%Y-%m-%d %H:%M:%S"), user=result['user']), 201


class PrepareTask(AuthResource):
    @swagger.operation(
        notes='Get validated task',
        nickname='prepared',
        responseClass=TaskGetResponseFields.__name__,
        parameters=[dict(name='task', description='Task ID', required=True,
                         allowMultiple=False, dataType='str', paramType='path')],
        responseMessages=[dict(code=200, message="validated task"),
                          dict(code=403, message='user access deny. you do not have permission to this task'),
                          dict(code=404, message='invalid task id. perhaps this task has already been removed'),
                          dict(code=406, message='task status is invalid. only validation tasks acceptable'),
                          dict(code=500, message="modeling server error"),
                          dict(code=512, message='task not ready')])
    @dynamic_docstring(ModelType.PREPARER, StructureStatus.CLEAR, StructureStatus.RAW, StructureStatus.HAS_ERROR,
                       ResultType.TEXT, StructureType.REACTION, StructureType.MOLECULE)
    def get(self, task):
        """
        Task with validated structure and conditions data

        all structures has check status = {1.value} [{1.name}] - all checks passed. {3.value} [{3.name}] - structure \
        has errors. {2.value} [{2.name}] - validation failed.
        structure type also autoassigned: {5.value} [{5.name}] or {6.value} [{6.name}].

        all newly validated structures include model with type = {0.value} [{0.name}] with results containing \
        errors or warning information.
        if task not newly created by upload file or create task api it can contain models with types different from \
        {0.value} [{0.name}] which previously selected on revalidaton for structures with status = {1.value} [{1.name}].
        this models contain empty results list.

        if preparer model failed [due to server lag etc] returned structures with status = {2.value} [{2.name}] and\
        {0.name} model with empty results list. In this case possible to resend this task to revalidation as is.
        for upload task failed validation return empty structure list and resend impossible.

        model results response structure:
        key: string - header
        type: data type = {4.value} [{4.name}] - plain text information
        value: string - body
        """
        page = results_fetch.parse_args().get('page')
        return format_results(task, fetch_task(task, TaskStatus.PREPARED), page=page), 200

    @swagger.operation(
        notes='Create revalidation task',
        nickname='prepare',
        responseClass=TaskPostResponseFields.__name__,
        parameters=[dict(name='task', description='Task ID', required=True,
                         allowMultiple=False, dataType='str', paramType='path'),
                    dict(name='structures', description='Structure[s] of molecule or reaction with optional conditions',
                         required=True, allowMultiple=False, dataType=TaskStructureFields.__name__, paramType='body')],
        responseMessages=[dict(code=201, message="revalidation task created"),
                          dict(code=400, message="invalid structure data"),
                          dict(code=403, message='user access deny. you do not have permission to this task'),
                          dict(code=404, message='invalid task id. perhaps this task has already been removed'),
                          dict(code=406, message='task status is invalid. only validation tasks acceptable'),
                          dict(code=500, message="modeling server error"),
                          dict(code=512, message='task not ready')])
    @dynamic_docstring(StructureStatus.CLEAR, StructureType.REACTION, ModelType.REACTION_MODELING,
                       StructureType.MOLECULE, ModelType.MOLECULE_MODELING)
    def post(self, task):
        """
        Revalidate task structures and conditions

        possible to send list of TaskStructureFields.
        send only changed data and structure id's. e.g. if user changed only temperature in structure 4 json should be
        {{"temperature": new_value, "structure": 4}} or in  list [{{"temperature": new_value, "structure": 4}}]

        unchanged data server kept as is.

        structures status and type fields not usable

        todelete field marks structure for delete.
        example json: [{{"structure": 5, "todetele": true}}]
        structure with id 5 in task will be removed from list.

        data field should be a string containing marvin document or cml or smiles/smirks.

        models field usable if structure has status = {0.value} [{0.name}] and don't changed.
        for structure type = {1.value} [{1.name}] acceptable only model types = {2.value} [{2.name}]
        and vice versa for type = {3.value} [{3.name}] only model types = {4.value} [{4.name}].
        only model id field needed. e.g. [{{"models": [{{model: 1}}], "structure": 3}}]

        for SEARCH type tasks models field unusable.

        see also task/create doc.
        """
        data = marshal(request.get_json(force=True), TaskStructureFields.resource_fields)
        result = fetch_task(task, TaskStatus.PREPARED)[0]
        preparer = get_model(ModelType.PREPARER)

        prepared = {s['structure']: s for s in result['structures']}
        structures = data if isinstance(data, list) else [data]
        tmp = {x['structure']: x for x in structures if x['structure'] in prepared}

        if 0 in tmp:
            abort(400, message='invalid structure data')

        additives = get_additives()
        models = get_models_list()

        for s, d in tmp.items():
            if d['todelete']:
                prepared.pop(s)
            else:
                ps = prepared[s]
                if d['additives'] is not None:
                    alist = []
                    for a in d['additives']:
                        if a['additive'] in additives and (0 < a['amount'] <= 1
                                                           if additives[a['additive']]['type'] == AdditiveType.SOLVENT
                                                           else a['amount'] > 0):
                            a.update(additives[a['additive']])
                            alist.append(a)
                    ps['additives'] = alist

                if d['data']:
                    ps['data'] = d['data']
                    ps['status'] = StructureStatus.RAW
                    ps['models'] = [preparer.copy()]
                elif s['status'] == StructureStatus.RAW:  # renew preparer model.
                    ps['models'] = [preparer.copy()]
                elif ps['status'] == StructureStatus.CLEAR:
                    if d['models'] is not None:
                        ps['models'] = [models[m['model']].copy() for m in d['models'] if m['model'] in models and
                                        models[m['model']]['type'].compatible(ps['type'], TaskType.MODELING)]
                    else:  # recheck models for existing
                        ps['models'] = [m.copy() for m in ps['models'] if m['model'] in models]

                if d['temperature']:
                    ps['temperature'] = d['temperature']

                if d['pressure']:
                    ps['pressure'] = d['pressure']

        result['structures'] = list(prepared.values())
        result['status'] = TaskStatus.PREPARING

        new_job = redis.new_job(result)
        if new_job is None:
            abort(500, message='modeling server error')

        return dict(task=new_job['id'], status=result['status'].value, type=result['type'].value,
                    date=new_job['created_at'].strftime("%Y-%m-%d %H:%M:%S"), user=result['user']), 201


class CreateTask(AuthResource):
    @swagger.operation(
        notes='Create validation task',
        nickname='create',
        responseClass=TaskPostResponseFields.__name__,
        parameters=[dict(name='_type', description='Task type ID: %s' % task_types_desc, required=True,
                         allowMultiple=False, dataType='int', paramType='path'),
                    dict(name='structures', description='Structure[s] of molecule or reaction with optional conditions',
                         required=True, allowMultiple=False, dataType=TaskStructureFields.__name__, paramType='body')],
        responseMessages=[dict(code=201, message="validation task created"),
                          dict(code=400, message="invalid structure data"),
                          dict(code=403, message="invalid task type"),
                          dict(code=500, message="modeling server error")])
    @dynamic_docstring(AdditiveType.SOLVENT, TaskStatus.PREPARING,
                       TaskType.MODELING, TaskType.SIMILARITY, TaskType.SUBSTRUCTURE)
    def post(self, _type):
        """
        Create new task

        possible to send list of TaskStructureFields.
        e.g. [TaskStructureFields1, TaskStructureFields2,...]

        todelete, status, type and models fields not usable

        data field is required. field should be a string containing marvin document or cml or smiles/smirks
        additive should be in list of available additives.
        amount should be in range 0 to 1 for additives type = {0.value} [{0.name}], and positive for overs.
        temperature in Kelvin and pressure in Bar also should be positive.

        response include next information:
        date: creation date time
        status: {1.value} [{1.name}]
        task: task id
        type: {2.value} [{2.name}] or {3.value} [{3.name}] or {4.value} [{4.name}]
        user: user id
        """
        try:
            _type = TaskType(_type)
        except ValueError:
            abort(403, message='invalid task type [%s]. valid values are %s' % (_type, task_types_desc))

        data = marshal(request.get_json(force=True), TaskStructureFields.resource_fields)
        additives = get_additives()
        preparer = get_model(ModelType.PREPARER)
        structures = data if isinstance(data, list) else [data]

        data = []
        for s, d in enumerate(structures, start=1):
            if d['data']:
                alist = []
                for a in d['additives'] or []:
                    if a['additive'] in additives and (0 < a['amount'] <= 1
                                                       if additives[a['additive']]['type'] == AdditiveType.SOLVENT
                                                       else a['amount'] > 0):
                        a.update(additives[a['additive']])
                        alist.append(a)

                data.append(dict(structure=s, data=d['data'], status=StructureStatus.RAW, type=StructureType.UNDEFINED,
                                 pressure=d['pressure'], temperature=d['temperature'],
                                 additives=alist, models=[preparer.copy()]))

        if not data:
            abort(400, message='invalid structure data')

        new_job = redis.new_job(dict(status=TaskStatus.NEW, type=_type, user=current_user.id, structures=data))

        if new_job is None:
            abort(500, message='modeling server error')

        return dict(task=new_job['id'], status=TaskStatus.PREPARING.value, type=_type.value,
                    date=new_job['created_at'].strftime("%Y-%m-%d %H:%M:%S"), user=current_user.id), 201


uf_post = reqparse.RequestParser()
uf_post.add_argument('file.url', type=str)
uf_post.add_argument('file.path', type=str)
uf_post.add_argument('structures', type=datastructures.FileStorage, location='files')


class UploadTask(AuthResource):
    @swagger.operation(
        notes='Create validation task from uploaded structures file',
        nickname='upload',
        responseClass=TaskPostResponseFields.__name__,
        parameters=[dict(name='_type', description='Task type ID: %s' % task_types_desc, required=True,
                         allowMultiple=False, dataType='int', paramType='path'),
                    dict(name='structures', description='RDF SDF MRV SMILES file', required=True,
                         allowMultiple=False, dataType='file', paramType='body')],
        responseMessages=[dict(code=201, message="validation task created"),
                          dict(code=400, message="structure file required"),
                          dict(code=403, message="invalid task type"),
                          dict(code=500, message="modeling server error")])
    def post(self, _type: int) -> Tuple[Dict, int]:
        """
        Structures file upload

        Need for batch mode.
        Any chemical structure formats convertable with Chemaxon JChem can be passed.

        conditions in files should be present in next key-value format:
        additive.amount.1 --> string = float [possible delimiters: :, :=, =]
        temperature --> float
        pressure --> float
        additive.2 --> string
        amount.2 --> float
        where .1[.2] is index of additive. possible set multiple additives.

        example [RDF]:
        $DTYPE additive.amount.1
        $DATUM water = .4
        $DTYPE temperature
        $DATUM 298
        $DTYPE pressure
        $DATUM 0.9
        $DTYPE additive.2
        $DATUM DMSO
        $DTYPE amount.2
        $DATUM 0.6

        parsed as:
        temperature = 298
        pressure = 0.9
        additives = [{"name": "water", "amount": 0.4, "type": x, "additive": y1}, \
                     {"name": "DMSO", "amount": 0.6, "type": x, "additive": y2}]
        where "type" and "additive" obtained from DataBase by name

        see task/create doc about acceptable conditions values and additives types and response structure.
        """
        try:
            _type = TaskType(_type)
        except ValueError:
            abort(403, message='invalid task type [%s]. valid values are %s' % (_type, task_types_desc))

        args = uf_post.parse_args()

        file_url = None
        if args['file.url']:  # smart frontend
            if url(args['file.url']):
                file_url = args['file.url']
        elif args['file.path']:  # NGINX upload
            file_name = path.basename(args['file.path'])
            if path.exists(path.join(UPLOAD_PATH, file_name)):
                file_url = url_for('.batch_file', file=file_name, _external=True)
        elif args['structures']:  # flask
            file_name = str(uuid.uuid4())
            args['structures'].save(path.join(UPLOAD_PATH, file_name))
            file_url = url_for('.batch_file', file=file_name, _external=True)

        if file_url is None:
            abort(400, message='structure file required')

        new_job = redis.new_job(dict(status=TaskStatus.NEW, type=_type, user=current_user.id,
                                     structures=[dict(data=dict(url=file_url), status=StructureStatus.RAW,
                                                      type=StructureType.UNDEFINED,
                                                      models=[get_model(ModelType.PREPARER)])]))
        if new_job is None:
            abort(500, message='modeling server error')

        return dict(task=new_job['id'], status=TaskStatus.PREPARING.value, type=_type.value,
                    date=new_job['created_at'].strftime("%Y-%m-%d %H:%M:%S"), user=current_user.id), 201


class LogIn(Resource):
    @swagger.operation(
        notes='App login',
        nickname='login',
        parameters=[dict(name='credentials', description='User credentials', required=True,
                         allowMultiple=False, dataType=LogInFields.__name__, paramType='body')],
        responseMessages=[dict(code=200, message="logged in"),
                          dict(code=400, message="invalid data"),
                          dict(code=403, message="bad credentials")])
    def post(self):
        """
        Get auth token

        Token returned in headers as remember_token.
        for use task api send in requests headers Cookie: 'remember_token=_token_'
        """
        data = request.get_json(force=True)
        if data:
            username = data.get('user')
            password = data.get('password')
            if username and password:
                user = UserLogin.get(username.lower(), password)
                if user:
                    login_user(user, remember=True)
                    return dict(message='logged in'), 200
        return dict(message='bad credentials'), 403
