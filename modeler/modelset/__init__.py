# -*- coding: utf-8 -*-
#
# Copyright 2015 Ramil Nugmanov <stsouko@live.ru>
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
import os
import pkgutil
from importlib import reload, import_module

MODELS = {}
imports = {}


def register_model(name, model, init=None):
    MODELS[name] = (model, init)


def find_models():
    for mloader, pname, ispkg in pkgutil.iter_modules([os.path.dirname(__file__)]):
        try:
            print('found model: ', pname)
            if pname in imports:
                print('reload existing model')
                reload(imports[pname])
            else:
                print('import new model')
                imports[pname] = import_module('modeler.modelset.%s' % pname)
        except Exception:
            pass
