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
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_appconfig import AppConfig
from flask_login import LoginManager

login_manager = LoginManager()
from .config import PORTAL_BASE


def create_app(configfile=None):
    app = Flask(__name__, static_url_path=PORTAL_BASE+'/static', static_folder="static")
    AppConfig(app, configfile)
    Bootstrap(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    return app

app = create_app(configfile='config.ini')


from app.models import PredictorDataBase as pdb
pdb = pdb()

from app import views
