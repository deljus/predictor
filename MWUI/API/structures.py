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
from flask_restful import fields
from importlib.util import find_spec
from ..config import SWAGGER
from ..constants import ModelType


if SWAGGER and find_spec('flask_restful_swagger'):
    from flask_restful_swagger import swagger
else:
    class Swagger:
        @staticmethod
        def nested(*args, **kwargs):
            def decorator(f):
                return f

            return decorator

        @staticmethod
        def model(f):
            return f

    swagger = Swagger()


class ModelTypeField(fields.Raw):
    def format(self, value):
        return ModelType(value)


@swagger.model
class LogInFields:
    resource_fields = dict(user=fields.String, password=fields.String)


@swagger.model
class TaskPostResponseFields:
    resource_fields = dict(task=fields.String, status=fields.Integer, type=fields.Integer,
                           date=fields.String, user=fields.Integer)


@swagger.model
class DestinationsFields:
    resource_fields = dict(host=fields.String, port=fields.Integer(6379), password=fields.String, name=fields.String)


@swagger.model
@swagger.nested(destinations=DestinationsFields.__name__)
class ModelRegisterFields:
    resource_fields = dict(example=fields.String, description=fields.String, type=ModelTypeField, name=fields.String,
                           destinations=fields.List(fields.Nested(DestinationsFields.resource_fields)))


@swagger.model
class AdditivesFields:
    resource_fields = dict(additive=fields.Integer, amount=fields.Float)


@swagger.model
class ModelsFields:
    resource_fields = dict(model=fields.Integer, name=fields.String)


@swagger.model
@swagger.nested(additives=AdditivesFields.__name__, models=ModelsFields.__name__)
class TaskStructureFields:
    resource_fields = dict(structure=fields.Integer, data=fields.String, temperature=fields.Float(298),
                           pressure=fields.Float(1), todelete=fields.Boolean(False),
                           status=fields.Integer, type=fields.Integer,
                           additives=fields.List(fields.Nested(AdditivesFields.resource_fields)),
                           models=fields.List(fields.Nested(ModelsFields.resource_fields)))


@swagger.model
class AdditivesResponseFields:
    resource_fields = dict(additive=fields.Integer, amount=fields.Float, name=fields.String, structure=fields.String,
                           type=fields.Integer)


@swagger.model
class ModelResultsResponseFields:
    resource_fields = dict(type=fields.Integer, key=fields.String, value=fields.String)


@swagger.model
@swagger.nested(results=ModelResultsResponseFields.__name__)
class ModelsResponseFields:
    resource_fields = dict(model=fields.Integer, name=fields.String, type=fields.Integer,
                           results=fields.List(fields.Nested(ModelResultsResponseFields.resource_fields)))


@swagger.model
@swagger.nested(additives=AdditivesResponseFields.__name__, models=ModelsResponseFields.__name__)
class TaskStructureResponseFields:
    resource_fields = dict(structure=fields.Integer, data=fields.String, temperature=fields.Float(298),
                           pressure=fields.Float(1), status=fields.Integer, type=fields.Integer,
                           additives=fields.List(fields.Nested(AdditivesResponseFields.resource_fields)),
                           models=fields.List(fields.Nested(ModelsResponseFields.resource_fields)))


@swagger.model
@swagger.nested(structures=TaskStructureResponseFields.__name__)
class TaskGetResponseFields:
    resource_fields = dict(task=fields.String, date=fields.String, status=fields.Integer,
                           type=fields.Integer, user=fields.Integer,
                           structures=fields.List(fields.Nested(TaskStructureResponseFields.resource_fields)))


@swagger.model
class AdditivesListFields:
    resource_fields = dict(additive=fields.Integer, name=fields.String, structure=fields.String,
                           type=fields.Integer)


@swagger.model
class ModelListFields:
    resource_fields = dict(example=fields.String, description=fields.String, type=ModelTypeField, name=fields.String,
                           model=fields.Integer)
