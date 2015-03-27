# -*- coding: utf-8 -*-
import re
import threading
import subprocess as sp
import xml.etree.ElementTree as ET
from werkzeug import secure_filename

from flask import render_template, url_for, redirect
from app import app
from flask.ext.restful import reqparse, abort, Api, Resource, fields, marshal
from flask.ext import excel
#import pyexcel.ext.xls
#import pyexcel.ext.xlsx


import sys
import os
from app.models import PredictorDataBase as pdb
from flask import (request, render_template, jsonify)

import requests
import json
from xml.dom.minidom import parse, parseString

UPLOAD_PATH = '/home/server/upload/'

basedir = os.path.abspath(os.path.dirname(__file__))
molconvert = '/home/server/ChemAxon/JChem/bin/molconvert'

@app.route('/')
@app.route('/index')
@app.route('/home/')
@app.route('/predictor/')
def index():
    #return render_template("index.html")
    return redirect(url_for('static', filename='index.html'))


@app.route("/download", methods=['GET'])
def download_file():
    return excel.make_response_from_array([[1,2], [3, 4]], "xls")


def create_task_from_file(file_path, task_id):
    tmp_file = '%stmp-%d.mrv' % (UPLOAD_PATH, task_id)
    temp = 298
    sp.call([molconvert, 'mrv', file_path, '-o', tmp_file])
    file = open(tmp_file, 'r')
    solv = {x['name'].lower(): x['id'] for x in pdb.get_solvents()}

    for mol in file:
        if '<MDocument>' in mol:
            tree = ET.fromstring(mol)
            prop = {x.get('title').lower(): x.find('scalar').text.lower().strip() for x in tree.iter('property')}

            solvlist = {}
            for i, j in prop.items():
                if 'solvent.amount.' in i:
                    k = re.split('[:=]', j)
                    id = solv.get(k[0].strip()) # ебаный велосипед.
                    if id:
                        if '%' in k[-1]:
                            v = k[-1].replace('%', '')
                            grader = 100
                        else:
                            v = k[-1]
                            grader = 1
                        try:
                            v = float(v) / grader
                        except ValueError:
                            v = 1
                        solvlist[id] = v
                elif 'temperature' == i:
                    try:
                        temp = float(j)
                    except ValueError:
                        temp = 298

            pdb.insert_reaction(task_id=task_id, reaction_structure=mol.rstrip(), solvent=solvlist, temperature=temp)
    pdb.update_task_status(task_id, REQ_MAPPING)


class UploadFile(Resource):
    def __init__(self):
        parser = reqparse.RequestParser()
        parser.add_argument('file.path', type=str)
        self.parser = parser

    def post(self):
        args = self.parser.parse_args()
        task_id = pdb.insert_task()
        if not args['file.path']: # костыль. если не найдет этого в аргументах, то мы без NGINX сидим тащемта.
            f = request.files['file']
            reaction_file = UPLOAD_PATH + secure_filename(f.filename)
            f.save(reaction_file)
        else:
            reaction_file = args['file.path']

        t = threading.Thread(target=create_task_from_file, args=(reaction_file, task_id))
        t.start()
        return str(task_id), 201


api = Api(app)
pdb = pdb()


TASK_CREATED    = 0
REQ_MAPPING     = 1
LOCK_MAPPING    = 2
MAPPING_DONE    = 3
REQ_MODELLING   = 4
LOCK_MODELLING  = 5
MODELLING_DONE  = 6



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
        return pdb.get_reaction_structure(reaction_id)

    def put(self, reaction_id):
        args = parser.parse_args()
        pdb.update_reaction_structure(reaction_id, args['reaction_structure'])
        return reaction_id, 201


class ReactionResultAPI(Resource):
    def __init__(self):
        parser = reqparse.RequestParser()
        parser.add_argument('modelid', type=str)
        parser.add_argument('params', type=str, action='append')
        parser.add_argument('values', type=str, action='append')
        self.parser = parser

    def get(self, reaction_id): # что это тут делает то???
        return pdb.get_reaction_results(reaction_id)

    def post(self, reaction_id):
        args = self.parser.parse_args()
        for x, y in zip(args['params'], args['values']):
            pdb.update_reaction_result(reaction_id=reaction_id, model_id=args['modelid'], param=x, value=y)
        return reaction_id, 201


class ReactionAPI(Resource):
    def get(self, reaction_id):
        return pdb.get_reaction(reaction_id), 201

    def put(self, reaction_id):
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
        return pdb.get_reactions()


class TaskListAPI(Resource):
    def get(self):
        args = parser.parse_args()
        return pdb.get_tasks(status=args['task_status'])

    def post(self):
        task_id = pdb.insert_task()
        args = parser.parse_args()
        pdb.insert_reaction(task_id, args['reaction_structure'])
        pdb.update_task_status(task_id, REQ_MAPPING)
        return task_id, 201


class TaskStatusAPI (Resource):
    def get(self, task_id):
        return pdb.get_task_status(task_id)

    def put(self,task_id):
        args = parser.parse_args()
        task_status = args['task_status']
        pdb.update_task_status(task_id, task_status)
        return task_id, 201


class TaskReactionsAPI (Resource):
    def get(self, task_id):
        return pdb.get_reactions_by_task(task_id)


class ModelListAPI(Resource):
    def __init__(self):
        parserget = reqparse.RequestParser()
        parserget.add_argument('hash', type=str)

        parserdel = reqparse.RequestParser()
        parserdel.add_argument('id', type=int)

        parserpost = reqparse.RequestParser()
        parserpost.add_argument('name', type=str)
        parserpost.add_argument('desc', type=str)
        parserpost.add_argument('hashes', type=str, action='append')
        parserpost.add_argument('is_reaction', type=bool)

        self.parser = dict(get=parserget, post=parserpost, delete=parserdel)

    def get(self):
        args = self.parser['get'].parse_args()
        model_hash = args['hash']
        models = pdb.get_models(model_hash=model_hash)
        return models, 201


    def delete(self):
        """TODO:
        удалить модель по ее id."""
        args = self.parser['delete'].parse_args()
        model_id = args['id']
        pdb.delete_model(model_id)

    def post(self):
        args = self.parser['post'].parse_args()
        model_id = pdb.insert_model(name=args['name'], is_reaction=args['is_reaction'], reaction_hashes=args['hashes'])
        return model_id, 201


class SolventsAPI(Resource):
    def get(self):
        return pdb.get_solvents()


class TaskModellingAPI(Resource):
    def get(self, task_id):
        return pdb.get_results_by_task(task_id)


    def put(self, task_id):
        _parser = reqparse.RequestParser()
        _parser.add_argument('task_reaction_ids', type=str)
        args = _parser.parse_args()
        reaction_ids = args['task_reaction_ids']
        for r_id in reaction_ids.split(','):
            try:
                _m = 'model_'+r_id
                _s = 'solvent_'+r_id
                _t = 'temperature_'+r_id
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
        return 'OK'


class ModelAPI (Resource):
    def get(self, model_id):
        return pdb.get_model(model_id)


class DownloadResultsAPI(Resource):
    def get(self, task_id):
        parser.add_argument('format', type=str)
        args = parser.parse_args()
        format = args['format']
        reactions = pdb.get_results_by_task(task_id)
        arr = []
        count = 0
        for _reaction in reactions:
            count += 1
            _results = _reaction.get('results')
            if _results:
                for _result in _results:
                    arr.append(dict(reaction_numer=count,
                                    model=_result.get('model'),
                                    parameter=_result.get('param'),
                                    value=_result.get('value'))
                    )
        return excel.make_response_from_records(arr, format)


##
## Actually setup the Api resource routing here
##
api.add_resource(ReactionListAPI, '/reactions')

api.add_resource(ReactionAPI, '/reaction/<reaction_id>')
api.add_resource(ReactionStructureAPI, '/reaction_structure/<reaction_id>')
api.add_resource(ReactionResultAPI, '/reaction_result/<reaction_id>')

# работа со статусами задач
api.add_resource(TaskStatusAPI, '/task_status/<task_id>')

# получение задач
api.add_resource(TaskListAPI, '/tasks')

api.add_resource(TaskReactionsAPI, '/task_reactions/<task_id>')

api.add_resource(TaskModellingAPI, '/task_modelling/<task_id>')

api.add_resource(ModelListAPI, '/models')
api.add_resource(ModelAPI, '/model/<model_id>')


api.add_resource(SolventsAPI, '/solvents')

api.add_resource(DownloadResultsAPI, '/download/<task_id>')


api.add_resource(UploadFile, '/upload')