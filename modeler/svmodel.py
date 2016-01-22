# -*- coding: utf-8 -*-
#
# Copyright 2015, 2016 Ramil Nugmanov <stsouko@live.ru>
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
from collections import defaultdict
from itertools import product
from sklearn.externals.joblib import Parallel, delayed
from sklearn.svm import SVR, SVC
from sklearn.feature_extraction import DictVectorizer
from sklearn.utils import shuffle
from sklearn.cross_validation import KFold
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, r2_score, confusion_matrix
from math import sqrt, ceil
import numpy as np


def _kfold(est, x, y, train, test, svmparams, normalize):
    x_train, y_train = x[train], y[train]
    x_test, y_test = x[test], list(y[test])
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

    model = est(**svmparams)
    model.fit(x_train, y_train)
    y_pred = list(model.predict(x_test))
    return dict(model=model, normal=normal, x_min=x_min, x_max=x_max, y_min=y_min, y_max=y_max,
                y_test=y_test, y_pred=y_pred, y_index=test)


class Model(object):
    def __init__(self, descriptorgen, svmparams, nfold=5, repetitions=1, rep_boost=25, dispcoef=0,
                 fit='rmse', estimator='svr', scorers=('rmse', 'r2'),
                 normalize=False, n_jobs=2, smartcv=False, descriptors=None, **kwargs):
        _scorers = dict(rmse=lambda y_test, y_pred: sqrt(mean_squared_error(y_test, y_pred)),
                        r2=lambda y_test, y_pred: r2_score(y_test, y_pred),
                        kappa=self.__kappa_stat, ba=self.__balance_acc)

        self.__sparse = DictVectorizer(sparse=False)
        self.__descriptorgen = descriptorgen
        self.__estimator = self.__estimators.get(estimator, SVR)

        self.__nfold = nfold
        self.__repetitions = repetitions
        self.__rep_boost = ceil(repetitions * (rep_boost % 100) / 100)

        if descriptors:
            y, x = descriptors
        else:
            y, x, _ = descriptorgen.get(**kwargs)
        self.__sparse.fit(x)
        self.__x, self.__y = self.__sparse.transform(x), np.array(y)

        self.__normalize = normalize
        self.__dispcoef = dispcoef
        self.__scorers = {x: _scorers[x] for x in scorers if x in _scorers}
        self.__fitscore = 'C' + (fit if fit in scorers else scorers[0])
        self.__scorereporter = '\n'.join(['{0} +- variance = %({0})s +- %(v{0})s'.format(i) for i in self.__scorers])
        self.__smartcv = smartcv

        self.__n_jobs = n_jobs
        self.__crossval(svmparams)

    __estimators = dict(svr=SVR, svc=SVC)

    @staticmethod
    def __kappa_stat(y_test, y_pred):
        (tn, fp), (fn, tp) = confusion_matrix(y_test, y_pred)
        a = len(y_test)
        pe = ((tp + fp) * (tp + fn) + (fn + tn) * (fp + tn)) / (a**2)
        return ((tp + tn) / a - pe)/(1 - pe)

    @staticmethod
    def __balance_acc(y_test, y_pred):
        (tn, fp), (fn, tp) = confusion_matrix(y_test, y_pred)
        return 0.5 * tp / (tp + fn) + (0.5 * tn / (tn + fp) if (tn + fp) else .5)

    def setworkpath(self, path):
        self.__descriptorgen.setpath(path)

    def getmodelstats(self):
        return dict(r2=self.__model['r2'], rmse=self.__model['rmse'],
                    vr2=self.__model['vr2'], vrmse=self.__model['vrmse'],
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
                    fittedmodel = self.__fit(i, self.__rep_boost)
                    print(self.__scorereporter % fittedmodel)
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

        if self.__repetitions > self.__rep_boost:
            bestmodel = self.__fit(bestmodel['params'], self.__repetitions)
        print('========================================\n'
              'SVM params %(params)s\n' +
              self.__scorereporter % bestmodel)
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

    def __fit(self, svmparams, repetitions):
        models, y_test, y_pred = [], [], []
        scorers = defaultdict(list)
        parallel = Parallel(n_jobs=self.__n_jobs)
        kf = list(KFold(len(self.__y), n_folds=self.__nfold))
        setindexes = np.arange(len(self.__y))
        folds = parallel(delayed(_kfold)(self.__estimator, self.__x, self.__y, s[train], s[test], svmparams, self.__normalize)
                         for s in (self.__shuffle(setindexes, i) for i in range(repetitions))
                         for train, test in kf)
        # todo: запилить анализ аутов. y_index - indexes of test elements
        #  street magic. split folds to repetitions
        for kfold in zip(*[iter(folds)] * self.__nfold):
            ky_pred, ky_test = [], []
            for fold in kfold:
                ky_pred.extend(fold.pop('y_pred'))
                ky_test.extend(fold.pop('y_test'))
                models.append(fold)

            for s, f in self.__scorers.items():
                scorers[s].append(f(ky_test, ky_pred))

            y_pred.extend(ky_pred)
            y_test.extend(ky_test)

        res = dict(model=models, params=svmparams,)
        for s, v in scorers.items():
            m, v = np.mean(v), sqrt(np.var(v))
            c = (1 if s in ('rmse',) else -1) * m + self.__dispcoef * v
            res.update({s: m, 'C' + s: c, 'v' + s: v})

        return res

    def __shuffle(self, setindexes, seed):
        if self.__smartcv:
            shuffled = None
        else:
            shuffled = shuffle(setindexes, random_state=seed)
        return shuffled

    def predict(self, structure, **kwargs):
        _, d_x, d_ad = self.__descriptorgen.get(inputfile=structure, **kwargs)
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
