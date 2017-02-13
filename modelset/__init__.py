# -*- coding: utf-8 -*-
#
# Copyright 2015, 2016 Ramil Nugmanov <stsouko@live.ru>
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
import json
from requests import post, get
from MWUI.config import AdditiveType, ModelType, ResultType, StructureType, StructureStatus
from os import path, listdir


SERVER_ROOT = 'https://cimm.kpfu.ru'
ADDITIVES = "%s/api/resources/additives" % SERVER_ROOT
CHEMAXON = "%s/webservices" % SERVER_ROOT


class ModelSet(object):
    def __init__(self):
        self.__models = self.__scan_models()

    @staticmethod
    def __loader(module):
        return getattr(__import__('%s.%s' % (__name__, module), globals(), locals()), module).ModelLoader()

    def __scan_models(self):
        models = {}
        for module in listdir(path.dirname(__file__)):
            if module.endswith('.py') and module != '__init__.py':
                try:
                    model_loader = self.__loader(module[:-3])
                    for x in model_loader.get_models():
                        models[x['name']] = (module[:-3], x)
                except:
                    pass
        return models

    def load_model(self, name, workpath='.'):
        if name in self.__models:
            model = self.__loader(self.__models[name][0]).load_model(name)
            model.set_work_path(workpath)
            return model

    def get_models(self):
        return [x for _, x in self.__models.values()]


def chemaxpost(url, data):
    for _ in range(2):
        try:
            q = post("%s/rest-v0/util/%s" % (CHEMAXON, url), data=json.dumps(data),
                     headers={'content-type': 'application/json'}, timeout=20)
        except:
            continue
        else:
            if q.status_code in (201, 200):
                return q.json()
            else:
                continue
    else:
        return False


def get_additives():
    for _ in range(2):
        try:
            q = get(ADDITIVES, timeout=20)
        except:
            continue
        else:
            if q.status_code in (201, 200):
                res = q.json()
                for a in res:
                    a['type'] = AdditiveType(a['type'])
                return res
            else:
                continue
    else:
        return []
