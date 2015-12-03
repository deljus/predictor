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
from itertools import product
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

    def __splitrange(self, param):
        stepindex = list(range(0, len(param), round(len(param)/10) or 1))
        print(stepindex)
        if len(stepindex) == len(param):
            tmp = {x: {} for x in param}
        else:
            tmp = {}
            stepindex.insert(0, -1)
            stepindex.append(len(param))
            for i, j, k in zip(stepindex, stepindex[1:], stepindex[2:]):
                tmp[param[j]] = self.__splitrange(param[i+1:j] + param[j+1:k])
        print(tmp)
        return tmp

    def __crossval(self, svmparams):
        for param in svmparams:
            for i in param:
                if i != 'kernel':
                    param[i] = self.__splitrange(param[i])
        print(param)
        bestmodel = dict(model=None, r2=np.inf, rmse=np.inf)
        for param in svmparams:
            model = dict(model=None, r2=np.inf, rmse=np.inf)
            while True:
                stepmodel = dict(model=None, r2=np.inf, rmse=np.inf)
                tmp = self.__prepareparams(param)
                for i in tmp:
                    print('fit model with params:', i)
                    fittedmodel = self.__fit(i)
                    print('R2 = -%(r2)s\nRMSE = %(rmse)s' % fittedmodel)
                    if fittedmodel[self.__fitscore] < stepmodel[self.__fitscore]:
                        stepmodel = fittedmodel

                if stepmodel[self.__fitscore] < model[self.__fitscore]:
                    model = stepmodel
                    tmp = {}
                    for i, j in model['params'].items():
                        if i == 'kernel':
                            tmp[i] = j
                        else:
                            tmp[i] = param[i][j]
                    param = tmp
                else:
                    break
            if model[self.__fitscore] < bestmodel[self.__fitscore]:
                bestmodel = model

        print('========\nSVM params %(params)s\nR2 = -%(r2)s\nRMSE = %(rmse)s' % bestmodel)
        self.__model = bestmodel

    @staticmethod
    def __prepareparams(param):
        tmp = []
        baseparams = [x for x in product(param['C'], param['epsilon'], param['tol'])]
        if param['kernel'] == 'linear':  # u'*v
            tmp.extend([dict(kernel='linear', C=c, epsilon=e, tol=t) for c, e, t in baseparams])
        elif param['kernel'] == 'rbf':  # exp(-gamma*|u-v|^2)
            tmp.extend([dict(kernel='rbf', C=c, epsilon=e, tol=t, gamma=g) for g, (c, e, t)
                        in product(param['gamma'], baseparams)])
        elif param['kernel'] == 'sigmoid':  # tanh(gamma*u'*v + coef0)
            tmp.extend([dict(kernel='sigmoid', C=c, epsilon=e, tol=t, gamma=g, coef0=f) for g, f, (c, e, t)
                        in product(param['gamma'], param['coef0'], baseparams)])
        elif param['kernel'] == 'poly':  # (gamma*u'*v + coef0)^degree
            tmp.extend([dict(kernel='poly', C=c, epsilon=e, tol=t, gamma=g, coef0=f, degree=d)
                        for g, f, d, (c, e, t)
                        in product(param['gamma'], param['coef0'], param['degree'], baseparams)])
        return tmp

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
            print('repetition No %s completed' % (i + 1))
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
