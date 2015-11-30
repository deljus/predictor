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
from sklearn.metrics import mean_squared_error, r2_score
from math import sqrt
import numpy as np


class Model(object):
    def __init__(self, descriptors, svmparams, nfold=5, repetitions=1, dispcoef=0,
                 fit='rmse', normalize=False, **kwargs):
        self.__sparse = DictVectorizer(sparse=False)
        self.__descriptors = descriptors
        self.__trainparam = dict(nfold=nfold, repetitions=repetitions)

        y, x, _ = descriptors.get(**kwargs)
        self.__sparse.fit(x)
        self.__x, self.__y = self.__sparse.transform(x), np.array(y)
        self.__normalize = normalize
        self.__dispcoef = dispcoef
        self.__fitscore = fit
        self.__crossval(svmparams)

    def setworkpath(self, path):
        self.__descriptors.setpath(path)

    def __crossval(self, svmparams):
        if any(isinstance(y, list) and len(y) > 1 for x in svmparams for y in x.values()):
            pass
        elif len(svmparams) == 1:
            self.__model = self.__fit({x: y[0] for x, y in svmparams[0].items()})
        else:
            models = dict(model=None, r2=np.inf, rmse=np.inf)
            for params in svmparams:
                params = {x: y[0] for x, y in params.items()}
                print('fit model with params:', params)
                fittedmodel = self.__fit(params)
                if fittedmodel[self.__fitscore] < models[self.__fitscore]:
                    models = fittedmodel
            self.__model = models

        print('========\nSVM params %(params)s\nR2 = -%(r2)s\nRMSE = %(rmse)s' % self.__model)

    def __fit(self, svmparams):
        models = []
        rmse = []
        r2 = []
        y_pred = np.empty_like(self.__y)
        for i in range(self.__trainparam['repetitions']):
            xs, ys = shuffle(self.__x, self.__y, random_state=i)
            kf = KFold(len(self.__y), n_folds=self.__trainparam['nfold'])
            for train, test in kf:
                x_train, y_train = xs[train], ys[train]
                x_test, y_test = xs[test], ys[test]
                x_min = np.amin(x_train, axis=0)
                x_max = np.amax(x_train, axis=0)

                if self.__normalize:
                    normal = MinMaxScaler()
                    normal.fit(x_train)
                    x_test = normal.transform(x_test)
                    x_train = normal.transform(x_train)
                else:
                    normal = None

                model = SVR(**svmparams)
                model.fit(x_train, y_train)

                y_pred[test] = model.predict(x_test)
                models.append(dict(model=model, x_min=x_min, x_max=x_max, normal=normal))
            print('repetition No %s completed' % i)
            rmse.append(sqrt(mean_squared_error(ys, y_pred)))
            r2.append(r2_score(ys, y_pred))

        return dict(model=models,
                    rmse=np.mean(rmse) - self.__dispcoef * np.var(rmse),
                    r2=-np.mean(r2) + self.__dispcoef * np.var(r2),
                    params=svmparams)

    def predict(self, structure, **kwargs):
        _, d_x, d_ad = self.__descriptors.get(inputfile=structure, **kwargs)
        res = []
        for model in self.__model['model']:
            x_test = self.__sparse.transform(d_x)
            ad = d_ad and (x_test - model['x_min']).min() >= 0 and (model['x_max'] - x_test).min() >= 0
            if model['normal']:
                x_test = model['normal'](x_test)

            res.append(dict(prediction=model['model'].predict(x_test), domain=ad))
        return res
