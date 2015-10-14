# -*- coding: utf-8 -*-
#
# Copyright 2015 Ramil Nugmanov <stsouko@live.ru>
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
from sklearn.svm import SVR
from sklearn.feature_extraction import DictVectorizer


class Model(object):
    def __init__(self, descriptors, svmparams, trainx, trainy):
        self.__sparse = DictVectorizer(sparse=False)
        self.__descriptors = descriptors
        self.__svm = SVR(**svmparams)
        self.__sparse.fit(trainx)
        self.__fit(self.__sparse.transform(trainx), trainy)

    def setworkpath(self, path):
        self.__descriptors.setpath(path)

    def __fit(self, x, y):
        self.__svm.fit(x, y)

    def predict(self, structure, solvent=None, temperature=None):
        if solvent:
            solvent = [solvent]
        if temperature:
            temperature = [temperature]
        res = self.__descriptors.getfragments(inputfile=structure, solvent=solvent, temperature=temperature)
        return self.__svm.predict(self.__sparse.transform(res[1]))
