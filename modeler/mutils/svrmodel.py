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
from sklearn.utils import shuffle
from sklearn.cross_validation import KFold
from sklearn.preprocessing import MinMaxScaler
import numpy as np


class Model(object):
    def __init__(self, descriptors, svmparams, nfold=5, repetitions=1, normalize=False, **kwargs):
        self.__sparse = DictVectorizer(sparse=False)
        self.__descriptors = descriptors
        self.__svmparams = svmparams
        self.__models = []
        self.__trainparam = dict(nfold=nfold, repetitions=repetitions)

        trainy, trainx, _ = descriptors.get(**kwargs)
        self.__sparse.fit(trainx)
        self.__normalize = normalize
        self.__fit(self.__sparse.transform(trainx), np.array(trainy))

    def setworkpath(self, path):
        self.__descriptors.setpath(path)

    def __fit(self, x, y):
        for i in range(self.__trainparam['repetitions']):
            xs, ys = shuffle(x, y, random_state=i)
            kf = KFold(len(y), n_folds=self.__trainparam['nfold'])
            for train, _ in kf:
                x_train, y_train = xs[train], ys[train]
                x_min = np.amin(x_train, axis=0)
                x_max = np.amax(x_train, axis=0)
                if self.__normalize:
                    normal = MinMaxScaler()
                    normal.fit(x_train)
                else:
                    normal = None
                model = SVR(**self.__svmparams)
                model.fit(x_train, y_train)
                self.__models.append(dict(model=model, x_min=x_min, x_max=x_max, normal=normal))

    def predict(self, structure, **kwargs):
        desk = self.__descriptors.get(inputfile=structure, **kwargs)
        res = []
        for model in self.__models:
            x_test = self.__sparse.transform(desk[1])
            ad = desk[2] and (x_test - model['x_min']).min() >= 0 and (model['x_max'] - x_test).min() >= 0
            if model['normal'] is not None:
                x_test = model['normal'].transform(x_test)

            res.append(dict(prediction=model['model'].predict(x_test), domain=ad))
        return res
