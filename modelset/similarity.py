# -*- coding: utf-8 -*-
#
# Copyright 2016 Ramil Nugmanov <stsouko@live.ru>
# This file is part of PREDICTOR.
#
# PREDICTOR is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
import subprocess as sp
from io import StringIO
from CGRtools.CGRcore import CGRcore
from CGRtools.files.RDFrw import RDFread
from MWUI.config import ModelType, ResultType
from MODtools.utils import chemaxpost
from MODtools.config import MOLCONVERT


model_name = 'Reaction Similarity'


class Model(CGRcore):
    def __init__(self):
        self.__workpath = '.'

        CGRcore.__init__(self, cgr_type='0', extralabels=True)

        config_path = path.join(path.dirname(__file__), 'preparer')

    @staticmethod
    def get_example():
        return None

    @staticmethod
    def get_description():
        return 'Reaction similarity wrapper'

    @staticmethod
    def get_name():
        return model_name

    @staticmethod
    def get_type():
        return ModelType.REACTION_SIMILARITY

    def setworkpath(self, workpath):
        self.__workpath = workpath

    def get_results(self, structures):
        # prepare input file
        if len(structures) == 1:
            chemaxed = chemaxpost('calculate/molExport',
                                  dict(structure=structures[0]['data'],
                                       parameters='rdf'))
            if not chemaxed:
                return False

            data = chemaxed['structure']
        else:
            with sp.Popen([MOLCONVERT, 'rdf'],
                          stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.STDOUT, cwd=self.__workpath) as convert_mol:
                data = convert_mol.communicate(input=''.join(s['data'] for s in structures).encode())[0].decode()
                if convert_mol.returncode != 0:
                    return False

        with StringIO(data) as f:
            for reaction in RDFread(f).read():
                pass


class ModelLoader(object):
    def __init__(self, **kwargs):
        pass

    @staticmethod
    def load_model(name):
        if name == model_name:
            return Model()

    @staticmethod
    def get_models():
        model = Model()
        return [dict(example=model.get_example(), description=model.get_description(),
                     type=model.get_type(), name=model_name)]
