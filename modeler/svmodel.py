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
import tempfile
import shutil
from collections import defaultdict
from itertools import product
import pandas as pd
from sklearn.externals.joblib import Parallel, delayed
from sklearn.svm import SVR, SVC
from sklearn.utils import shuffle
from sklearn.cross_validation import KFold
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, r2_score, confusion_matrix
from math import sqrt, ceil
import numpy as np


def _kfold(est, x, y, train, test, svmparams, normalize):
    x_train, y_train = x.loc[train], y[train]
    x_test, y_test = x.loc[test], y[test]
    x_min = x_train.min()
    x_max = x_train.max()
    y_min = y_train.min()
    y_max = y_train.max()

    if normalize:
        normal = MinMaxScaler()
        x_train = pd.DataFrame(normal.fit_transform(x_train), columns=x_train.columns)
        x_test = pd.DataFrame(normal.transform(x_test), columns=x_train.columns)
    else:
        normal = None

    model = est(**svmparams)
    model.fit(x_train, y_train)
    y_pred = pd.Series(model.predict(x_test), index=test)
    return dict(model=model, normal=normal, x_min=x_min, x_max=x_max, y_min=y_min, y_max=y_max,
                y_test=y_test, y_pred=y_pred)


def _rmse(y_test, y_pred):
    return sqrt(mean_squared_error(y_test, y_pred))


def _kappa_stat(y_test, y_pred):
    (tn, fp), (fn, tp) = confusion_matrix(y_test, y_pred)
    a = len(y_test)
    pe = ((tp + fp) * (tp + fn) + (fn + tn) * (fp + tn)) / (a**2)
    return ((tp + tn) / a - pe)/(1 - pe)


def _balance_acc(y_test, y_pred):
    (tn, fp), (fn, tp) = confusion_matrix(y_test, y_pred)
    return (0.5 * tp / (tp + fn) if (tp + fn) else .5) + (0.5 * tn / (tn + fp) if (tn + fp) else .5)


class Model(object):
    def __init__(self, descriptorgen, svmparams, nfold=5, repetitions=1, rep_boost=25, dispcoef=0,
                 fit='rmse', estimator='svr', scorers=('rmse', 'r2'), workpath='.',
                 normalize=False, n_jobs=2, smartcv=False, **kwargs):
        _scorers = dict(rmse=_rmse,
                        r2=r2_score,
                        kappa=_kappa_stat, ba=_balance_acc)

        self.__descriptorgen = descriptorgen
        self.setworkpath(workpath)

        self.__estimator = self.__estimators.get(estimator, SVR)

        self.__nfold = nfold
        self.__repetitions = repetitions
        self.__rep_boost = ceil(repetitions * (rep_boost % 100) / 100)
        print("Descriptors generation start")
        self.__x, self.__y, *_ = descriptorgen.get(**kwargs)
        print("Descriptors generated")

        self.__normalize = normalize
        self.__dispcoef = dispcoef
        self.__scorers = {x: _scorers[x] for x in scorers if x in _scorers}
        self.__fitscore = 'C' + (fit if fit in scorers else scorers[0])
        self.__scorereporter = '\n'.join(['{0} +- variance = %({0})s +- %(v{0})s'.format(i) for i in self.__scorers])
        self.__smartcv = smartcv

        self.__n_jobs = n_jobs
        self.__crossval(svmparams)
        self.delworkpath()

    __estimators = dict(svr=SVR, svc=SVC)

    def setworkpath(self, workpath):
        self.__workpath = tempfile.mkdtemp(dir=workpath)
        self.__descriptorgen.setworkpath(self.__workpath)

    def delworkpath(self):
        shutil.rmtree(self.__workpath)

    def getmodelstats(self):
        stat = {x: self.__model[x] for x in self.__scorers}
        stat.update(dict(fitparams=self.__model['params'], repetitions=self.__repetitions,
                         nfolds=self.__nfold, normalize=self.__normalize,
                         dragostolerance=sqrt(self.__y.var())))
        return stat

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
        print('list of svm params:')
        print(pd.DataFrame(list(svmparams)))
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
        print('========================================\n' +
              ('SVM params %(params)s\n' + self.__scorereporter) % bestmodel)
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
                ky_pred.append(fold.pop('y_pred'))
                ky_test.append(fold.pop('y_test'))
                models.append(fold)

            ky_pred = pd.concat(ky_pred)
            ky_test = pd.concat(ky_test)
            for s, f in self.__scorers.items():
                scorers[s].append(f(ky_test, ky_pred))

            #y_pred.append(ky_pred)
            #y_test.append(ky_test)

        #y_pred = pd.concat(y_pred, axis=1)
        #y_test = pd.concat(y_test, axis=1)

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
        d_x, _, d_ad = self.__descriptorgen.get(inputstring=structure, **kwargs)

        pred, dom, ydom = [], [], []
        for i, model in enumerate(self.__model['model']):
            x_t = pd.DataFrame(model['normal'].transform(d_x), columns=d_x.columns) if model['normal'] else d_x
            dom.append(((d_x - model['x_min']).min(axis=1) >= 0) & ((model['x_max'] - d_x).min(axis=1) >= 0) & d_ad)
            pred.append(pd.Series(model['model'].predict(x_t)))
            ydom.append((pred[-1] >= model['y_min']) & (pred[-1] <= model['y_max']))

        res = dict(prediction=pd.concat(pred, axis=1),
                   domain=pd.concat(dom, axis=1), y_domain=pd.concat(ydom, axis=1))

        return res
