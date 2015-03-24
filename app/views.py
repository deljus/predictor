# -*- coding: utf-8 -*-
import threading
import subprocess as sp

from flask import render_template, url_for, redirect
from app import app
from flask.ext.restful import reqparse, abort, Api, Resource, fields, marshal
#from flask.ext import excel

import sys
import os
from app.models import PredictorDataBase as pdb
from flask import (request, render_template, jsonify)

import requests
import json
from xml.dom.minidom import parse, parseString



basedir = os.path.abspath(os.path.dirname(__file__))
molconvert = '/home/stsouko/.ChemAxon/JChem/bin/molconvert'

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
    #todo: надо добавить изменение статуса на готовое к маппингу
    tmp_file = '/tmp/tmp-%d.mrv' % task_id
    sp.call([molconvert, 'mrv', file_path, '-o', tmp_file])
    file = open(tmp_file, 'r')
    next(file)

    for mol in file:
        pdb.insert_reaction(task_id=task_id, reaction_structure=mol, temperature=298)



class UploadFile(Resource):
    def __init__(self):
        parser = reqparse.RequestParser()
        parser.add_argument('filename.path', type=str)

        self.parser = parser

    def post(self):
        args = self.parser.parse_args()
        task_id = pdb.insert_task()
        t = threading.Thread(target=create_task_from_file, args=(args['filename.path'], task_id))
        t.daemon = True
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

WEBSERVICES_SERVER_NAME = "http://localhost:8080/webservices"
WEBSERVICES = {"molconvertws": WEBSERVICES_SERVER_NAME+"/rest-v0/util/calculate/molExport"}


def allowed_file(filename):
    """TODO: чек файла сделает мой парсер."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']


parser = reqparse.RequestParser()
parser.add_argument('reaction_structure', type=str)
parser.add_argument('temperature', type=str)
parser.add_argument('solvent', type=str)
parser.add_argument('task_status', type=int)
parser.add_argument('model_id', type=int)
parser.add_argument('param', type=str)
parser.add_argument('value', type=float)


class ReactionStructureAPI(Resource):
    def get(self, reaction_id):
        return pdb.get_reaction_structure(reaction_id)

    def put(self, reaction_id):
        args = parser.parse_args()
        pdb.update_reaction_structure(reaction_id, args['reaction_structure'])
        return reaction_id, 201


class ReactionResultAPI(Resource):
    def get(self, reaction_id):
        return pdb.get_reaction_structure(reaction_id)

    def post(self, reaction_id):
        args = parser.parse_args()
        pdb.update_reaction_result(reaction_id=reaction_id, model_id=args['model_id'], param=args['param'], value=args['value'])
        return reaction_id, 201




class ReactionAPI(Resource):
    def get(self, reaction_id):
        return pdb.get_reaction(reaction_id), 201

    def put(self, reaction_id):
        _parser = reqparse.RequestParser()
        _parser.add_argument('temperature', type=str)
        _parser.add_argument('solvent', type=str)
        _parser.add_argument('models', type=str)
        args = _parser.parse_args()
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
                print('model='+_m)
                print('solvent='+_s)
                print('temp='+_t)
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


class ReactionImgAPI(Resource):
    def get(self, reaction_id):
        try:
            url = WEBSERVICES['molconvertws']
            structure = pdb.get_reaction_structure(reaction_id)
            conversionOptions = {
                "structure": structure,
                "parameters": "png",
                "width": 500,
                "height": 150
            }
            headers = {'content-type': 'application/json'}
            result = requests.post(url, data=json.dumps(conversionOptions), headers=headers)
            return result.text, 201
        except:
            print('ReactionImgAPI->get->', sys.exc_info()[0])



##
## Actually setup the Api resource routing here
##
api.add_resource(ReactionListAPI, '/reactions')

api.add_resource(ReactionAPI, '/reaction/<reaction_id>')
api.add_resource(ReactionStructureAPI, '/reaction_structure/<reaction_id>')
api.add_resource(ReactionResultAPI, '/reaction_result/<reaction_id>')
api.add_resource(ReactionImgAPI, '/reaction_img/<reaction_id>')

# работа со статусами задач
api.add_resource(TaskStatusAPI, '/task_status/<task_id>')

# получение задач
api.add_resource(TaskListAPI, '/tasks')

api.add_resource(TaskReactionsAPI, '/task_reactions/<task_id>')

api.add_resource(TaskModellingAPI, '/task_modelling/<task_id>')

api.add_resource(ModelListAPI, '/models')
api.add_resource(ModelAPI, '/model/<model_id>')


api.add_resource(SolventsAPI, '/solvents')


api.add_resource(UploadFile, '/upload')