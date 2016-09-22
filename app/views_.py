# -*- coding: utf-8 -*-
#
# Copyright 2015 Ramil Nugmanov <stsouko@live.ru>
# Copyright 2015 Oleg Varlamov <ovarlamo@gmail.com>
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
import re
import sys
import json
import uuid

from .config import UPLOAD_PATH, REQ_MAPPING, LOCK_MODELLING, PORTAL_BASE, ALLOWED_EXTENSIONS
from app import app
from flask.ext.restful import reqparse, Api, Resource
from flask import redirect, url_for

from flask import request, render_template, flash
from app.forms import Registration, Login
from app.logins import User
from flask_login import login_user, login_required, logout_user, current_user
from utils.utils import chemaxpost


from app import api

def get_cur_user():
    user_data = None
    if current_user.is_authenticated:
        user_data = dict(id=current_user.get_id(), email=current_user.get_email())
    return user_data

# Этот роут для infochim.u-strasbg.fr нужно закомментить
@app.route(PORTAL_BASE+'/', methods=['GET', 'POST'])
@app.route(PORTAL_BASE+'/predictor', methods=['GET', 'POST'])
def predictor():
    return render_template("predictor.html", user_data=get_cur_user())

@app.route(PORTAL_BASE+'/cimm_predictor', methods=['GET'])
def cimm_predictor():
    return render_template("cimm_predictor.html", user_data=get_cur_user())

@app.route(PORTAL_BASE+'/cimm_search', methods=['GET'])
def cimm_search():
    return render_template("cimm_search.html", user_data=get_cur_user())


@app.route(PORTAL_BASE+'/home', methods=['GET'])
def home():
    return render_template("home.html", user_data=get_cur_user())


@app.route(PORTAL_BASE+'/predictor/task/<int:task>', methods=['GET', 'POST'])
@login_required
def task(task=0):
    return render_template("predictor.html", task=task, user_data=get_cur_user())

@app.route(PORTAL_BASE+'/predictor/model_example/<int:model>', methods=['GET', 'POST'])
def model_example(model=0):
    return render_template("predictor.html", model=model, user_data=get_cur_user())


#@app.route(PORTAL_BASE+'/predictor/download', methods=['GET'])
#def download_file():
#    return excel.make_response_from_array([[1, 2], [3, 4]], "xls")


@app.route(PORTAL_BASE+'/predictor/solvents', methods=['GET'])
def solvents():
    solvents = pdb.get_solvents()
    return render_template("solvents.html", solvents=solvents, user_data=get_cur_user())


@app.route(PORTAL_BASE+'/predictor/models', methods=['GET'])
def models():
    models = pdb.get_models()
    return render_template("models.html", models=models, user_data=get_cur_user())


@app.route(PORTAL_BASE+'/user', methods=['GET'])
@login_required
def user():
    return render_template('user.html',  user_data=get_cur_user())


@app.route(PORTAL_BASE+'/user/my_tasks', methods=['GET'])
@login_required
def my_tasks():
    user_data = get_cur_user()
    my_tasks = pdb.get_user_tasks(user_email=user_data['email'])
    if user_data:
        return render_template('my_tasks.html',  user_data=user_data, my_tasks=my_tasks)
    return render_template('login.html', form=Login())


@app.route(PORTAL_BASE+'/user/login', methods=['GET', 'POST'])
def login():
    form = Login()
    if form.validate_on_submit():
        user = pdb.get_user(email=form.email.data)
        if user and pdb.check_password(user['id'], form.password.data):
            login_user(User(**user), remember=True)
            #flash('Logged in successfully.')
            return redirect(url_for('predictor'))
    return render_template('login.html', form=form)


@app.route(PORTAL_BASE+'/user/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route(PORTAL_BASE+'/user/registration', methods=['GET', 'POST'])
def registration():
    form = Registration()
    if form.validate_on_submit():
        if pdb.add_user(form.email.data, form.password.data):
            return redirect(url_for('predictor'))
    return render_template('registration.html', form=form)


@app.route(PORTAL_BASE+'/search', methods=['GET'])
def search():
    return render_template("search.html", user_data=get_cur_user())

UploadFileParser = reqparse.RequestParser()
UploadFileParser.add_argument('file.path', type=str)
FILEList = {}



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

    def delete(self, reaction_id):
        pdb.delete_reaction(reaction_id)
        return '', 201



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
ModelListparserpost.add_argument('example', type=str)


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
        data = {"structure": args['example'], "parameters": "mrv"}
        example = chemaxpost('calculate/stringMolExport', data)
        model_id = pdb.insert_model(args['name'], args['desc'], example or '', args['is_reaction'], args['hashes'])
        return model_id, 201


class SolventsAPI(Resource):
    def get(self):
        return pdb.get_solvents(), 201

class UsersAPI(Resource):
    def get(self):
        return pdb.get_users(), 201


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
                reactionres = [dict(reaction_numer=count + 1, model=result.get('model'),
                                    parameter=re.sub('<[^>]*>', '', result.get('param')),
                                    value=re.sub('<[^>]*>', '', result.get('value'))) for result in results if
                               result.get('type') == 0]
                arr.extend(reactionres)
        return excel.make_response_from_records(arr, format)


##
## Actually setup the Api resource routing here
##
# api.add_resource(ReactionListAPI, PORTAL_BASE+'/api/reactions')
#
# api.add_resource(ReactionAPI, PORTAL_BASE+'/api/reaction/<reaction_id>')
# api.add_resource(ReactionStructureAPI, PORTAL_BASE+'/api/reaction_structure/<reaction_id>')
# api.add_resource(ReactionResultAPI, PORTAL_BASE+'/api/reaction_result/<reaction_id>')
#
# # работа со статусами задач
# api.add_resource(TaskStatusAPI, PORTAL_BASE+'/api/task_status/<task_id>')
#
# # получение задач
# api.add_resource(TaskListAPI, PORTAL_BASE+'/api/tasks')
#
# api.add_resource(TaskReactionsAPI, PORTAL_BASE+'/api/task_reactions/<task_id>')
#
# api.add_resource(TaskModellingAPI, PORTAL_BASE+'/api/task_modelling/<task_id>')
#
# api.add_resource(ModelListAPI, PORTAL_BASE+'/api/models')
# api.add_resource(ModelAPI, PORTAL_BASE+'/api/model/<model_id>')
#
# api.add_resource(SolventsAPI, PORTAL_BASE+'/api/solvents')
#
# api.add_resource(DownloadResultsAPI, PORTAL_BASE+'/api/download/<task_id>')
#
# api.add_resource(UploadFile, PORTAL_BASE+'/api/upload')
# api.add_resource(ParserAPI, PORTAL_BASE+'/api/parser')
#
# api.add_resource(UsersAPI, PORTAL_BASE+'/api/users')
