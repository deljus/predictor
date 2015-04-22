# -*- coding: utf-8 -*-
#
# Copyright 2015 Ramil Nugmanov <stsouko@live.ru>
# Copyright 2015 Oleg Varlamov <ovarlamo@gmail.com>
# This file is part of PREDICTOR.
#
# PREDICTOR is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
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
from .config import UPLOAD_PATH, REQ_MAPPING
from werkzeug import secure_filename

from app import app
from flask.ext.restful import reqparse, Api, Resource
from flask.ext import excel
import pyexcel.ext.xls

import sys
from app.models import PredictorDataBase as pdb
from flask import request, render_template

import json


api = Api(app)
pdb = pdb()


@app.route('/')
@app.route('/index')
@app.route('/home/')
@app.route('/predictor/')
def index():
    return render_template("index.html")
    #return redirect(url_for('static', filename='index.html'))


@app.route("/download", methods=['GET'])
def download_file():
    return excel.make_response_from_array([[1, 2], [3, 4]], "xls")


@app.route("/solvents", methods=['GET'])
def solvents():
    solvents = pdb.get_solvents()
    return render_template("solvents.html", solvents=solvents)


@app.route("/models", methods=['GET'])
def models():
    models = pdb.get_models()
    return render_template("models.html", models=models)


"""
file uploader
"""
UploadFileParser = reqparse.RequestParser()
UploadFileParser.add_argument('file.path', type=str)
FILEList = {}


class UploadFile(Resource):
    def post(self):
        args = UploadFileParser.parse_args()

        if not args['file.path']:  # костыль. если не найдет этого в аргументах, то мы без NGINX сидим тащемта.
            f = request.files['file']
            reaction_file = UPLOAD_PATH + secure_filename(f.filename)
            f.save(reaction_file)
        else:
            reaction_file = args['file.path']
        task_id = pdb.insert_task()
        FILEList[task_id] = reaction_file
        return str(task_id), 201


"""
метод добавляет новые реакции в существующий таск и отдает файлы на парсер.
"""
ReactionParserparser = reqparse.RequestParser()
ReactionParserparser.add_argument('task_id', type=int)
ReactionParserparser.add_argument('structure', type=str)
ReactionParserparser.add_argument('temperature', type=float)
ReactionParserparser.add_argument('solvents', type=lambda x: json.loads(x))


class ParserAPI(Resource):
    def get(self):
        if FILEList:
            task_id, file = FILEList.popitem()
            return dict(id=task_id, file=file), 201
        else:
            return None, 201

    def post(self):
        args = ReactionParserparser.parse_args()
        reaction_id = pdb.insert_reaction(task_id=args['task_id'], reaction_structure=args['structure'],
                                          solvent=args['solvents'], temperature=args['temperature'])
        if reaction_id:
            return reaction_id, 201
        else:
            return None, 201


parser = reqparse.RequestParser()
parser.add_argument('reaction_structure', type=str)
parser.add_argument('temperature', type=str)
parser.add_argument('solvent', type=str)
parser.add_argument('task_status', type=int)
parser.add_argument('model_id', type=int)
parser.add_argument('param', type=str)
parser.add_argument('value', type=float)
parser.add_argument('models', type=str)


class ReactionStructureAPI(Resource):
    def get(self, reaction_id):
        return pdb.get_reaction_structure(reaction_id), 201

    def post(self, reaction_id):
        args = parser.parse_args()
        pdb.update_reaction_structure(reaction_id, args['reaction_structure'])
        return reaction_id, 201


"""
modeling results updater
"""
ReactionResultparser = reqparse.RequestParser()
ReactionResultparser.add_argument('modelid', type=int)
ReactionResultparser.add_argument('result', type=lambda x: json.loads(x))
ReactionResulttype = {'text': 0, 'structure': 1, 'link': 2}


class ReactionResultAPI(Resource):
    def post(self, reaction_id):
        args = ReactionResultparser.parse_args()
        for x in args['result']:
            pdb.update_reaction_result(reaction_id=reaction_id, model_id=args['modelid'],
                                       param=x['attrib'], value=str(x['value']),
                                       ptype=ReactionResulttype.get(x.get('type'), 0))
        return reaction_id, 201


class ReactionAPI(Resource):
    def get(self, reaction_id):
        return pdb.get_reaction(reaction_id), 201

    def post(self, reaction_id):
        args = parser.parse_args()
        m = args['models']
        if m:
            m = m.split(',')
        t = args['temperature']
        s = args['solvent']
        if s:
            s = s.split(',')
        pdb.update_reaction_conditions(reaction_id, temperature=t, solvent=s, models=m)
        return reaction_id, 201


class ReactionListAPI(Resource):
    def get(self):
        return pdb.get_reactions(), 201


class TaskListAPI(Resource):
    def get(self):
        args = parser.parse_args()
        return pdb.get_tasks(status=args['task_status']), 201

    def post(self):
        task_id = pdb.insert_task()
        args = parser.parse_args()
        pdb.insert_reaction(task_id, args['reaction_structure'])
        pdb.update_task_status(task_id, REQ_MAPPING)
        return task_id, 201


class TaskStatusAPI(Resource):
    def get(self, task_id):
        return pdb.get_task_status(task_id), 201

    def put(self, task_id):
        args = parser.parse_args()
        task_status = args['task_status']
        pdb.update_task_status(task_id, task_status)
        return task_id, 201


class TaskReactionsAPI(Resource):
    def get(self, task_id):
        return pdb.get_reactions_by_task(task_id), 201


"""
api  для добавления и удаления моделей. а также поиск подходящих моделей по ключам.
"""
ModelListparserget = reqparse.RequestParser()
ModelListparserget.add_argument('hash', type=str)

ModelListparserdel = reqparse.RequestParser()
ModelListparserdel.add_argument('id', type=int)

ModelListparserpost = reqparse.RequestParser()
ModelListparserpost.add_argument('name', type=str)
ModelListparserpost.add_argument('desc', type=str)
ModelListparserpost.add_argument('hashes', type=str, action='append')
ModelListparserpost.add_argument('is_reaction', type=int)


class ModelListAPI(Resource):
    def get(self):
        args = ModelListparserget.parse_args()
        model_hash = args['hash']
        models = pdb.get_models(model_hash=model_hash)
        return models, 201

    def delete(self):
        args = ModelListparserdel.parse_args()
        model_id = args['id']
        pdb.delete_model(model_id), 201

    def post(self):
        args = ModelListparserpost.parse_args()
        model_id = pdb.insert_model(args['name'], args['desc'], args['is_reaction'], args['hashes'])
        return model_id, 201


class SolventsAPI(Resource):
    def get(self):
        return pdb.get_solvents(), 201


class TaskModellingAPI(Resource):
    def get(self, task_id):
        return pdb.get_results_by_task(task_id), 201

    def post(self, task_id):
        _parser = reqparse.RequestParser()
        _parser.add_argument('task_reaction_ids', type=str)
        args = _parser.parse_args()
        reaction_ids = args['task_reaction_ids']
        for r_id in reaction_ids.split(','):
            try:
                _m = 'model_' + r_id
                _s = 'solvent_' + r_id
                _t = 'temperature_' + r_id
                _parser.add_argument(_m, type=str)
                _parser.add_argument(_s, type=str)
                _parser.add_argument(_t, type=str)
                args = _parser.parse_args()
                _m = args[_m]
                _s = args[_s]
                _t = args[_t]

                if _m:
                    _m = _m.split(',')
                if _s:
                    _s = _s.split(',')

                pdb.update_reaction_conditions(r_id, solvent=_s, temperature=_t, models=_m)
                _parser.remove_argument(_m)
                _parser.remove_argument(_s)
                _parser.remove_argument(_t)
            except:
                print('TaskModellingAPI->PUT->', sys.exc_info()[0])
                pass
        return 'OK', 201


class ModelAPI(Resource):
    def get(self, model_id):
        return pdb.get_model(model_id), 201


"""
api для скачивания результатов
"""
DownloadResultsparser = reqparse.RequestParser()
DownloadResultsparser.add_argument('format', type=str)


class DownloadResultsAPI(Resource):
    def get(self, task_id):
        args = DownloadResultsparser.parse_args()
        format = args['format']
        reactions = pdb.get_results_by_task(task_id)
        arr = []
        for count, reaction in enumerate(reactions):
            results = reaction.get('results')
            if results:
                reactionres = [dict(reaction_numer=count + 1, model=result.get('model'), parameter=result.get('param'),
                               value=result.get('value')) for result in results if result.get('type') == 0]
                arr.extend(reactionres)
        return excel.make_response_from_records(arr, format)


##
## Actually setup the Api resource routing here
##
api.add_resource(ReactionListAPI, '/api/reactions')

api.add_resource(ReactionAPI, '/api/reaction/<reaction_id>')
api.add_resource(ReactionStructureAPI, '/api/reaction_structure/<reaction_id>')
api.add_resource(ReactionResultAPI, '/api/reaction_result/<reaction_id>')

# работа со статусами задач
api.add_resource(TaskStatusAPI, '/api/task_status/<task_id>')

# получение задач
api.add_resource(TaskListAPI, '/api/tasks')

api.add_resource(TaskReactionsAPI, '/api/task_reactions/<task_id>')

api.add_resource(TaskModellingAPI, '/api/task_modelling/<task_id>')

api.add_resource(ModelListAPI, '/api/models')
api.add_resource(ModelAPI, '/api/model/<model_id>')

api.add_resource(SolventsAPI, '/api/solvents')

api.add_resource(DownloadResultsAPI, '/api/download/<task_id>')

api.add_resource(UploadFile, '/api/upload')
api.add_resource(ParserAPI, '/api/parser')
