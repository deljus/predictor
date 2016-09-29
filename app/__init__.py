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


def init():
    from flask import Flask
    from flask_bootstrap import Bootstrap
    from flask_login import LoginManager
    from flask_nav import Nav, register_renderer

    from app.api import api_bp
    from app.views import view_bp
    from app.bootstrap import top_nav, Customrenderer
    from app.config import PORTAL_BASE, SECRET_KEY, HOST, DEBUG, PORT
    from app.logins import load_user

    app = Flask(__name__)

    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['BOOTSTRAP_SERVE_LOCAL'] = True

    register_renderer(app, 'myrenderer', Customrenderer)
    nav = Nav(app)
    nav.register_element('top_nav', top_nav)
    Bootstrap(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = '.login'
    login_manager.user_loader(load_user)

    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(view_bp)

    # start Flask app
    app.run(HOST, port=PORT, debug=DEBUG)
