# -*- coding: utf-8 -*-
#
#  Copyright 2015-2017 Ramil Nugmanov <stsouko@live.ru>
#  Copyright 2015 Oleg Varlamov <ovarlamo@gmail.com>
#  This file is part of MWUI.
#
#  MWUI is free software; you can redistribute it and/or modify
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
    from CGRdb import Loader
    from datetime import datetime
    from flask import Flask
    from flask_bootstrap import Bootstrap
    from flask_login import LoginManager
    from flask_misaka import Misaka
    from flask_nav import Nav, register_renderer
    from flask_resize import Resize
    from misaka import HTML_ESCAPE
    from os.path import join
    from pony.orm import sql_debug
    from .API import api_bp
    from .bootstrap import top_nav, CustomBootstrapRenderer, CustomMisakaRenderer
    from .config import (PORTAL_NON_ROOT, SECRET_KEY, DEBUG, LAB_NAME, RESIZE_URL, UPLOAD_PATH, IMAGES_ROOT,
                         MAX_UPLOAD_SIZE, YANDEX_METRIKA)
    from .logins import load_user
    from .models import db, User
    from .views import view_bp

    if DEBUG:
        sql_debug(True)
        db.bind('sqlite', 'database.sqlite')
        db.generate_mapping(create_tables=True)
    else:
        from .config import DB_PASS, DB_HOST, DB_USER, DB_NAME
        db.bind('postgres', user=DB_USER, password=DB_PASS, host=DB_HOST, database=DB_NAME)
        db.generate_mapping()

    Loader.load_schemas(user_entity=User)

    app = Flask(__name__)

    app.config['DEBUG'] = DEBUG
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['BOOTSTRAP_SERVE_LOCAL'] = DEBUG
    app.config['ERROR_404_HELP'] = False
    app.config['RESIZE_URL'] = RESIZE_URL
    app.config['RESIZE_ROOT'] = IMAGES_ROOT
    app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE

    app.jinja_env.globals.update(year=datetime.utcnow, laboratory=LAB_NAME, yandex=YANDEX_METRIKA)

    Resize(app)

    register_renderer(app, 'myrenderer', CustomBootstrapRenderer)
    nav = Nav(app)
    nav.register_element('top_nav', top_nav)
    Bootstrap(app)

    Misaka(app, renderer=CustomMisakaRenderer(flags=0 | HTML_ESCAPE), tables=True,
           underline=True, math=True, strikethrough=True, superscript=True, footnotes=True, smartypants=False)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = '.login'
    login_manager.user_loader(load_user)

    app.register_blueprint(api_bp, url_prefix=join('/', PORTAL_NON_ROOT, 'api'))
    app.register_blueprint(view_bp, url_prefix=join('/', PORTAL_NON_ROOT) if PORTAL_NON_ROOT else None)

    return app
