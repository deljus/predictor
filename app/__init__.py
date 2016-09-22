# -*- coding: utf-8 -*-
#
# Copyright 2015 Ramil Nugmanov <stsouko@live.ru>
# Copyright 2015 Oleg Varlamov <ovarlamo@gmail.com>
# This file is part of PREDICTOR.
#
# PREDICTOR is free software; you can redistribute it and/or modify
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
from app import views
from app.api import ModelingResult, PrepareTask, CreateTask, UploadFile
from app.bootstrap import top_nav
from app.config import PORTAL_BASE, SECRET_KEY
from app.logins import load_user
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_login import LoginManager
from flask_nav import Nav
from flask_restful import Api

app = Flask(__name__, static_url_path=PORTAL_BASE+'/static', static_folder="static")
app.config['SECRET_KEY'] = SECRET_KEY

app.add_url_rule('/login', methods=['GET', 'POST'], view_func=views.login)
app.add_url_rule('/registration', methods=['GET', 'POST'], view_func=views.registration)
app.add_url_rule('/logout', methods=['GET'], view_func=views.logout)
app.add_url_rule('/index', methods=['GET'], view_func=views.index)


nav = Nav(app)
nav.register_element('top_nav', top_nav)
Bootstrap(app)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.user_loader(load_user)


api = Api(app)
api.add_resource(PrepareTask, '/prepare')
api.add_resource(CreateTask, '/create')
api.add_resource(UploadFile, '/upload')
api.add_resource(ModelingResult, '/result')
