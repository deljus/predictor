#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-
#
#  Copyright 2016 Ramil Nugmanov <stsouko@live.ru>
#  This file is part of predictor.
#
#  predictor 
#  is free software; you can redistribute it and/or modify
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
import pandas as pd


class MBparser(object):
    def __parsesvmopts(self, param, op, unpac=lambda x: x):
        res = []
        commaparam = param.split(',')
        for i in commaparam:
            ddotparam = i.split(':')
            if len(ddotparam) == 1:
                if i[0] == '^':
                    res.append(unpac(op(i[1:])))
                else:
                    res.append(op(i))
            elif len(ddotparam) >= 3:
                if i[0] == '^':
                    res.extend([unpac(x) for x in self.__drange(op(ddotparam[0][1:]),
                                                                op(ddotparam[1]), int(ddotparam[2]))])
                else:
                    res.extend([x for x in self.__drange(op(ddotparam[0]), op(ddotparam[1]), int(ddotparam[2]))])

        return res

    @staticmethod
    def __drange(start, stop, step):
        r = start
        s = (stop - start) / (step - 1)
        res = []
        while r <= stop:
            res.append(r)
            r += s
        return res

    @staticmethod
    def __pow10(x):
        return pow(10, x)

    __kernel = {'0': 'linear', '1': 'poly', '2': 'rbf', '3': 'sigmoid'}

    def getsvmparam(self, files):
        res = []
        repl = {'-t': ('kernel', lambda x: [self.__kernel[i] for i in x.split(',')]),
                '-c': ('C', lambda x: self.__parsesvmopts(x, float, unpac=self.__pow10)),
                '-d': ('degree', lambda x: self.__parsesvmopts(x, int)),
                '-e': ('tol', lambda x: self.__parsesvmopts(x, float, unpac=self.__pow10)),
                '-p': ('epsilon', lambda x: self.__parsesvmopts(x, float, unpac=self.__pow10)),
                '-g': ('gamma', lambda x: self.__parsesvmopts(x, float, unpac=self.__pow10)),
                '-r': ('coef0', lambda x: self.__parsesvmopts(x, float))}
        for file in files:
            svm = {}
            with open(file) as f:
                for line in f:
                    opts = line.split()
                    tmp = dict(kernel=['rbf'], C=[1.0], epsilon=[.1], tol=[.001], degree=[3], gamma=[0], coef0=[0])
                    for x, y in zip(opts[::2], opts[1::2]):
                        z = repl.get(x)
                        if z:
                            tmp[z[0]] = z[1](y)

                    for i in tmp['kernel']:
                        if i == 'linear':  # u'*v
                            if svm.get('linear'):
                                for k in ('C', 'epsilon', 'tol'):
                                    svm['linear'][k].extend(tmp[k])
                            else:
                                svm['linear'] = dict(kernel='linear', C=tmp['C'], epsilon=tmp['epsilon'],
                                                     tol=tmp['tol'])
                        elif i == 'rbf':  # exp(-gamma*|u-v|^2)
                            if svm.get('rbf'):
                                for k in ('C', 'epsilon', 'tol', 'gamma'):
                                    svm['rbf'][k].extend(tmp[k])
                            else:
                                svm['rbf'] = dict(kernel='rbf', C=tmp['C'], epsilon=tmp['epsilon'], tol=tmp['tol'],
                                                  gamma=tmp['gamma'])
                        elif i == 'sigmoid':  # tanh(gamma*u'*v + coef0)
                            if svm.get('sigmoid'):
                                for k in ('C', 'epsilon', 'tol', 'gamma', 'coef0'):
                                    svm['sigmoid'][k].extend(tmp[k])
                            else:
                                svm['sigmoid'] = dict(kernel='sigmoid', C=tmp['C'], epsilon=tmp['epsilon'],
                                                      tol=tmp['tol'], gamma=tmp['gamma'], coef0=tmp['coef0'])
                        elif i == 'poly':  # (gamma*u'*v + coef0)^degree
                            if svm.get('poly'):
                                for k in ('C', 'epsilon', 'tol', 'gamma', 'coef0', 'degree'):
                                    svm['poly'][k].extend(tmp[k])
                            else:
                                svm['poly'] = dict(kernel='poly', C=tmp['C'], epsilon=tmp['epsilon'], tol=tmp['tol'],
                                                   gamma=tmp['gamma'], coef0=tmp['coef0'], degree=tmp['degree'])
            if svm:
                res.append(svm)
        return res

    @staticmethod
    def parsemodeldescription(file):
        tmp = {}
        with open(file) as f:
            for line in f:
                k, v = line.split(':=')
                k = k.strip()
                v = v.strip()
                if k in ('nlim', 'tol', 'name', 'example', 'desc', 'report_units'):
                    if k in ('nlim', 'tol'):
                        v = float(v)
                    tmp[k] = v
        return tmp

    @staticmethod
    def parsefragmentoropts(file):
        params = []
        with open(file) as f:
            for line in f:
                opts = line.split()
                tmp = {}
                for x in opts:
                    key, value = x.split('=')
                    if 'header' in key:
                        tmp['headers'] = [x.strip() for x in value.split('|')]
                    else:
                        tmp[key.strip()] = value.strip()
                params.append(tmp)
        return params

    @staticmethod
    def parseext(rawext):
        extdata = {}
        for e in rawext:
            record = None
            ext, *file = e.split(':')
            if file:
                v = pd.read_csv(file[0])
                k = v.pop('EXTKEY')
                record = dict(key=k, value=v.rename(columns=lambda x: '%s.%s' % (ext, x)))
            extdata[ext] = record
        return extdata

    @staticmethod
    def savesvm(outputfile, X, Y, header=True):
        with open(outputfile + '.svm', 'w') as f:
            if header:
                f.write(' '.join(['Property'] + ['%s:%s' % i for i in enumerate(X.columns, start=1)]) + '\n')

            for i, j in zip(X.values, Y):
                f.write(' '.join(['%s ' % j] + ['%s:%s' % x for x in enumerate(i, start=1) if x[1] != 0]) + '\n')

    @staticmethod
    def savecsv(outputfile, X, Y, header=True):
        pd.concat([Y, X], axis=1).to_csv(outputfile + '.csv', index=False, header=header)
