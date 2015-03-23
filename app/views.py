# -*- coding: utf-8 -*-
from flask import render_template, url_for, redirect
from app import app
from flask.ext.restful import reqparse, abort, Api, Resource, fields, marshal

import sys
import os
from app.models import PredictorDataBase as pdb
from flask import (request, render_template, jsonify)

import requests
import json
from xml.dom.minidom import parse, parseString

basedir = os.path.abspath(os.path.dirname(__file__))


@app.route('/')
@app.route('/index')
@app.route('/home/')
def index():
    #return render_template("index.html")
    return redirect(url_for('static', filename='index.html'))


@app.route('/uploadajax', methods=['POST'])
def uploadfile():
    try:
        files = request.files['file']
        if files:
            filename = files.filename
            updir = os.path.join(basedir, 'upload')
            file_path = os.path.join(updir, filename)
            # сохраним файл на сервере
            files.save(file_path)
            # создадим задачу
            task_id = pdb.insert_task()
            parse_file(task_id, file_path)
        return task_id
    except:
        print('uploadfile->post->', sys.exc_info()[0])
        return 'ERROR', 401


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



def parse_file(task_id, file_path):
    try:
        url = WEBSERVICES_SERVER_NAME + "rest-v0/util/calculate/stringMolExport"
        file_str = open(file_path, 'r').read()
        conversionOptions = {
            "structure": file_str,
            "parameters": "mrv"
        }
        headers = {'content-type': 'application/json'}
        result = requests.post(url, data=json.dumps(conversionOptions), headers=headers)
        xmldoc = parseString(result.text)
        reaction_list = xmldoc.getElementsByTagName('MDocument')
        for _reaction in reaction_list:
            print(_reaction.text())

    except:
        print('parse_file->', sys.exc_info()[0])

    pass


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

    def put(self, reaction_id):
        args = parser.parse_args()
        pdb.update_reaction_result(reaction_id, args['model_id'])
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
        models = pdb.get_models(model_hash=args['hash'])
        return models, 201

    def delete(self):
        """TODO:
        удалить модель по ее id."""
        args = self.parser['delete'].parse_args()
        model_id = args['id']
        pdb.delete_model(model_id)

    def post(self):
        args = self.parser['post'].parse_args()
        model_id = pdb.insert_model(args['name'], args['is_reaction'], args['hashes'])
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

