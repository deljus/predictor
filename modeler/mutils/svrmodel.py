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
from sklearn.externals.joblib import Parallel, delayed
from sklearn.svm import SVR
from sklearn.feature_extraction import DictVectorizer
from sklearn.utils import shuffle
from sklearn.cross_validation import KFold
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, r2_score
from math import sqrt
import numpy as np


def _kfold(xs, ys, train, test, svmparams, normalize):
    x_train, y_train = xs[train], ys[train]
    x_test, y_test = xs[test], list(ys[test])
    x_min = x_train.min(axis=0)
    x_max = x_train.max(axis=0)
    y_min = y_train.min()
    y_max = y_train.max()

    if normalize:
        normal = MinMaxScaler()
        normal.fit(x_train)
        x_test = normal.transform(x_test)
        x_train = normal.transform(x_train)
    else:
        normal = None

    model = SVR(**svmparams)
    model.fit(x_train, y_train)
    y_pred = list(model.predict(x_test))
    return dict(model=model, normal=normal, x_min=x_min, x_max=x_max, y_min=y_min, y_max=y_max,
                y_test=y_test, y_pred=y_pred)


class Model(object):
    def __init__(self, descriptors, svmparams, nfold=5, repetitions=1, dispcoef=0,
                 fit='rmse', normalize=False, n_jobs=2, **kwargs):
        self.__sparse = DictVectorizer(sparse=False)
        self.__descriptors = descriptors
        self.__nfold = nfold
        self.__repetitions = repetitions

        y, x, _ = descriptors.get(**kwargs)
        self.__sparse.fit(x)
        self.__x, self.__y = self.__sparse.transform(x), np.array(y)
        self.__normalize = normalize
        self.__dispcoef = dispcoef
        self.__fitscore = 'C' + fit

        self.__n_jobs = n_jobs
        self.__crossval(svmparams)

    def setworkpath(self, path):
        self.__descriptors.setpath(path)

    def getmodelstats(self):
        return dict(r2=self.__model['r2'], rmse=self.__model['rmse'],
                    vr2=self.__model['vr2'], vrmse=self.__model['vrmse'],
                    dragos_rmse=self.__model['dragos_rmse'], dragos_r2=self.__model['dragos_r2'],
                    drmse=self.__model['drmse'], dr2=self.__model['dr2'],
                    fitparams=self.__model['params'],
                    repetitions=self.__repetitions, nfolds=self.__nfold, normalize=self.__normalize)

    def __splitrange(self, param, dep=0):
        tmp = {}
        fdep = dep
        stepindex = list(range(0, len(param), round(len(param)/10) or 1))
        stepindex.insert(0, -1)
        stepindex.append(len(param))
        for i, j, k in zip(stepindex, stepindex[1:], stepindex[2:]):
            tmp[param[j]], tmpd = self.__splitrange(param[i+1:j] + param[j+1:k], dep=dep+1)
            if tmpd > fdep:
                fdep = tmpd
        return tmp, fdep

    def __crossval(self, svmparams):
        fcount = 0
        depindex = []
        maxdep = []
        for param in svmparams:
            di = {}
            md = 0
            for i in param:
                if i != 'kernel':
                    param[i], di[i] = self.__splitrange(param[i])
                    if di[i] > md:
                        md = di[i]
            depindex.append(di)
            maxdep.append(md)

        print('========================================\n'
              'Y mean +- variance = %s +- %s\n'
              '  max = %s, min = %s\n'
              '========================================' %
              (self.__y.mean(), sqrt(self.__y.var()), self.__y.max(), self.__y.min()))

        bestmodel = dict(model=None, Cr2=np.inf, Crmse=np.inf)
        for param, md, di in zip(svmparams, maxdep, depindex):
            var_kern_model = dict(model=None, Cr2=np.inf, Crmse=np.inf)
            while True:
                var_param_model = dict(model=None, Cr2=np.inf, Crmse=np.inf)
                tmp = self.__prepareparams(param)
                for i in tmp:
                    fcount += 1
                    print('%d: fit model with params:' % fcount, i)
                    fittedmodel = self.__fit(i)
                    print('R2 +- variance = %(r2)s +- %(vr2)s\nRMSE +- variance = %(rmse)s +- %(vrmse)s' % fittedmodel)
                    if fittedmodel[self.__fitscore] < var_param_model[self.__fitscore]:
                        var_param_model = fittedmodel

                if var_param_model[self.__fitscore] < var_kern_model[self.__fitscore]:
                    var_kern_model = var_param_model
                    tmp = {}
                    for i, j in var_kern_model['params'].items():
                        if i == 'kernel':
                            tmp[i] = j
                        elif di[i] < md and not param[i][j]:
                            tmp[i] = param[i]
                        else:
                            tmp[i] = param[i][j]
                    param = tmp
                else:
                    break
            if var_kern_model[self.__fitscore] < bestmodel[self.__fitscore]:
                bestmodel = var_kern_model

        print('========================================\nSVM params %(params)s\n'
              'R2 +- variance = %(r2)s +- %(vr2)s\nRMSE +- variance = %(rmse)s +- %(vrmse)s\n'
              'Dragos_RMSE = %(dragos_rmse)s\nDragos_RMSE - RMSE = %(drmse)s\n'
              'Dragos_R2 = %(dragos_r2)s\nDragos_R2 - R2 = %(dr2)s' % bestmodel)
        print('========================================\n%s variants checked' % fcount)
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
        models, y_test, y_pred, kr2, krmse = [], [], [], [], []
        parallel = Parallel(n_jobs=self.__n_jobs)
        kf = list(KFold(len(self.__y), n_folds=self.__nfold))
        folds = parallel(delayed(_kfold)(xs, ys, train, test, svmparams, self.__normalize)
                         for xs, ys in
                         (shuffle(self.__x, self.__y, random_state=i) for i in range(self.__repetitions))
                         for train, test in kf)

        #  street magic. split folds to repetitions
        for kfold in zip(*[iter(folds)] * self.__nfold):
            ky_pred, ky_test = [], []
            for fold in kfold:
                ky_pred.extend(fold.pop('y_pred'))
                ky_test.extend(fold.pop('y_test'))
                models.append(fold)

            krmse.append(sqrt(mean_squared_error(ky_test, ky_pred)))
            kr2.append(r2_score(ky_test, ky_pred))
            y_pred.extend(ky_pred)
            y_test.extend(ky_test)

        rmse, vrmse = np.mean(krmse), sqrt(np.var(krmse))
        r2, vr2 = np.mean(kr2), sqrt(np.var(kr2))
        dragos_rmse = sqrt(mean_squared_error(y_test, y_pred))
        dragos_r2 = r2_score(y_test, y_pred)
        return dict(model=models, rmse=rmse, r2=r2, vrmse=vrmse, vr2=vr2, params=svmparams,
                    Crmse=rmse + self.__dispcoef * vrmse, Cr2=-r2 + self.__dispcoef * vr2,
                    dragos_rmse=dragos_rmse, dragos_r2=dragos_r2, drmse=rmse-dragos_rmse, dr2=r2-dragos_r2)

    def predict(self, structure, **kwargs):
        _, d_x, d_ad = self.__descriptors.get(inputfile=structure, **kwargs)
        res = []
        for i in d_x:
            tmp = []
            x_test = self.__sparse.transform([i])
            for model in self.__model['model']:
                x_ad = d_ad and (x_test - model['x_min']).min() >= 0 and (model['x_max'] - x_test).min() >= 0
                x_t = model['normal'](x_test) if model['normal'] else x_test
                y_pred = model['model'].predict(x_t)
                y_ad = model['y_min'] <= y_pred <= model['y_max']

                tmp.append(dict(prediction=y_pred, domain=x_ad, y_domain=y_ad))
            res.append(tmp)
        return res
