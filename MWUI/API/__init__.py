# -*- coding: utf-8 -*-
#
#  Copyright 2017 Ramil Nugmanov <stsouko@live.ru>
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
from flask import Blueprint, send_from_directory
from flask_restful import Api
from importlib.util import find_spec
from ..config import UPLOAD_PATH, SWAGGER
from .resources import (CreateTask, UploadTask, PrepareTask, ModelTask, ResultsTask, AvailableAdditives, LogIn,
                        AvailableModels, RegisterModels, MagicNumbers)

api_bp = Blueprint('api', __name__)

if SWAGGER and find_spec('flask_restful_swagger'):
    from flask_restful_swagger import swagger

    api = swagger.docs(Api(api_bp), apiVersion='1.0', description='MWUI API', api_spec_url='/doc/spec')
else:
    api = Api(api_bp)


api.add_resource(CreateTask, '/task/create/<int:_type>')
api.add_resource(UploadTask, '/task/upload/<int:_type>')
api.add_resource(PrepareTask, '/task/prepare/<string:task>')
api.add_resource(ModelTask, '/task/model/<string:task>')
api.add_resource(ResultsTask, '/task/results/<string:task>')
api.add_resource(AvailableAdditives, '/resources/additives')
api.add_resource(AvailableModels, '/resources/models')
api.add_resource(MagicNumbers, '/resources/magic')
api.add_resource(RegisterModels, '/admin/models')
api.add_resource(LogIn, '/auth')


@api_bp.route('/task/batch_file/<string:file>', methods=['GET'])
def batch_file(file):
    return send_from_directory(directory=UPLOAD_PATH, filename=file)
