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

redis = Queue(connection=Redis(), default_timeout=3600)

parser = reqparse.RequestParser()
parser.add_argument('task', type=int, required=True)
parser.add_argument('auth', type=int, required=True)


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
                return dict(message=dict(task='invalid id or access denied')), 400

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
taskstructure = parser.copy()
taskstructure.add_argument('structures', type=lambda x: marshal(json.loads(x), taskstructurefields))
taskstructure.add_argument('operation', type=int, choices=[0, 1])  # 0 - insert, 1 - update


class TaskStructure(Resource):
    def get(self):
        args = taskstructure.parse_args()
        try:
            job = redis.fetch_job(args['task'])
            if job.is_finished:
                pass
            else:
                return dict(message=dict(task='not ready')), 400
        except:
            return dict(message=dict(task='invalid id or access denied')), 400

                structures = select(s for s in Structures if s.task == task)
                models = left_join((s.id, m.id, m.name, m.description, m.model_type)
                                   for s in Structures for m in s.models if s.task == task)

                tmp1 = collectadditives(task)
                tmp2 = {}
                for s, mid, mn, md, mt in models:
                    tmp2.setdefault(s, []).append(dict(mid=mid, name=mn, description=md, type=mt))

            return dict(tid=task.id, status=task.status, date=task.create_date.timestamp(), type=task.task_type,
                        uid=task.user.id if task.user else None,
                        structures=[dict(sid=s.id, structure=s.structure, is_reaction=s.isreaction,
                                         temperature=s.temperature, pressure=s.pressure, status=s.status,
                                         additives=tmp1[s.id], models=tmp2[s.id]) for s in structures])

    def post(self):
        args = taskstructure.parse_args()
        r = redis.enqueue_call('', args=(args,), result_ttl=86400)
        print(args)
        if not args['structures']:
            return dict(message=dict(structure='structures missing')), 400

        with db_session:
            task = Tasks.get(id=args['task'])
            if not task:
                return dict(message=dict(task='invalid id or access denied')), 400

            _s = args['structures'] if isinstance(args['structures'], list) else [args['structures']]
            if args['operation'] == 0:
                pairs = ((Structures(task=task), x) for x in _s)
            elif args['operation'] == 1:
                tmp1 = {x['sid']: x for x in _s}
                pairs = ((s, tmp1[s.id]) for s in
                         select(s for s in Structures if s.task == task and s.id in tmp1.keys()))
            else:
                return dict(message=dict(operation='invalid operation')), 400

            report = []
            for s, d in pairs:
                if d.get('additives'):
                    s.additives.clear()
                    for a in d['additives']:
                        _a = Additives.get(id=a['aid'])
                        if _a:
                            Additiveset(additive=_a, structure=s, amount=a['amount'])
                elif d.get('models') and task.task_type == 0:
                    s.models.clear()
                    for m in d['models']:
                        _m = Models.get(id=m)
                        if _m and s.isreaction == _m.model_type % 2:
                            s.models.add(_m)
                elif d.get('structure'):
                    s.status = 3
                    s.structure = d['structure']
                    # todo: start machine recheck for tmp1[s.id].get('structure')
                elif d.get('temperature'):
                    s.temperature = d['temperature']
                elif d.get('pressure'):
                    s.pressure = d['pressure']
                report.append(s.id)
            return dict(message=dict(structures=dict(updated=report))) if report else (
                dict(message=dict(structures='invalid structures id')), 400)

    def delete(self):
        args = taskstructure.parse_args()
        with db_session:
            task = Tasks.get(id=args['task'])
            if not task:
                return dict(message=dict(task='invalid id or access denied')), 400

            sid = [x['sid'] for x in
                   (args['structures'] if isinstance(args['structures'], list) else [args['structures']])]
            report = delete(s for s in Structures if s.task == task and s.id in sid)
            return dict(message=dict(structures=dict(deleted=report))) if report else (
                dict(message=dict(structures='invalid structures id')), 400)

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
