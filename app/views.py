# -*- coding: utf-8 -*-
from flask import render_template
from app import app
from flask.ext.restful import reqparse, abort, Api, Resource
import time
import hashlib
import sys
import os
from app.models import PredictorDataBase as pdb
from random import randint
from flask import (request, render_template, jsonify)

basedir = os.path.abspath(os.path.dirname(__file__))


@app.route('/')
@app.route('/index')
def index():
    return render_template("index.html")


@app.route('/uploadajax', methods=['POST'])
def uploadfile():
    if request.method == 'POST':
        files = request.files['file']
        if files and allowed_file(files.filename):
            filename = files.filename
            updir = os.path.join(basedir, 'upload/')
            file_path = os.path.join(updir, filename)
            files.save(file_path)
            parse_file(file_path)
            return 'OK'
    return 'ERROR'

api = Api(app)
pdb = pdb()


TASK_CREATED    = 0
REQ_MAPPING     = 1
LOCK_MAPPING    = 2
MAPPING_DONE    = 3
REQ_MODELLING   = 4
LOCK_MODELLING  = 5
MODELLING_DONE  = 6

import requests
import json
from xml.dom.minidom import parse, parseString

def parse_file(file_path):
    try:
        url="http://localhost:8080/webservices/rest-v0/util/calculate/stringMolExport"
        file_str = open('c://temp//1.rdf', 'r').read()
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


class ReactionStructureAPI(Resource):
    def get(self, reaction_id):
        return pdb.get_reaction_structure(reaction_id)

    def put(self, reaction_id):
        args = parser.parse_args()
        pdb.update_reaction_structure(reaction_id, args['reaction_structure'])
        return reaction_id, 201


class ReactionAPI(Resource):
    def get(self, reaction_id):
        return pdb.get_reaction(reaction_id), 201

    def put(self, reaction_id):
        args = parser.parse_args()
        pdb.update_reaction_conditions(reaction_id, temperature=args['temperature'], solvent=args['solvent'])
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
        pdb.update_task_status(task_id,task_status)
        return task_id, 201


class TaskReactionsAPI (Resource):
    def get(self, task_id):
        return pdb.get_reactions_by_task(task_id)


class ModelsAPI(Resource):
    def get(self):
        return pdb.get_models()


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
        reaction_ids = args['task_reaction_ids'];
        for r_id in reaction_ids.split(','):
            try:
                _m = 'model_'+r_id
                _s = 'solvent_'+r_id
                _t = 'temperature_'+r_id
                _parser.add_argument(_m, type=str)
                _parser.add_argument(_s, type=str)
                _parser.add_argument(_t, type=str)
                args = _parser.parse_args()
                pdb.update_reaction_conditions(r_id, solvent=args[_s], temperature=args[_t], model=args[_m])
                _parser.remove_argument(_m)
                _parser.remove_argument(_s)
                _parser.remove_argument(_t)
            except:
                print('TaskModellingAPI->PUT->', sys.exc_info()[0])
                pass
        return 'OK'


##
## Actually setup the Api resource routing here
##
api.add_resource(ReactionAPI, '/reaction/<reaction_id>')
api.add_resource(ReactionStructureAPI, '/reaction_structure/<reaction_id>')

api.add_resource(ReactionListAPI, '/reactions')

# работа со статусами задач
api.add_resource(TaskStatusAPI, '/task_status/<task_id>')

# получение задач
api.add_resource(TaskListAPI, '/tasks')

api.add_resource(TaskReactionsAPI, '/task_reactions/<task_id>')

api.add_resource(TaskModellingAPI, '/task_modelling/<task_id>')

api.add_resource(ModelsAPI, '/models')
api.add_resource(SolventsAPI, '/solvents')

