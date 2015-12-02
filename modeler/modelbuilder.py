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
from mutils.fragmentor import Fragmentor
from mutils.svrmodel import Model
import argparse
import pickle


def parseext(rawext):
    extdata = {}
    for e in rawext:
        record = None
        ext, *file = e.split(':')
        if file:
            record = {}
            with open(file[0]) as f:
                for i in f:
                    key, *values = i.split()
                    tmp = {}
                    for j in values:
                        dkey, dval = j.split(':')
                        dkey = int(dkey)
                        dval = float(dval)
                        tmp[dkey] = dval
                    record[key] = tmp
        extdata[ext] = record
    return extdata


def drange(start, stop, step):
    r = start
    s = (stop - start) / (step - 1)
    res = []
    while r <= stop:
        res.append(r)
        r += s
    return res


def parsesvm(param, op, unpac=lambda x: x):
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
                res.extend([unpac(x) for x in drange(op(ddotparam[0][1:]), op(ddotparam[1]), int(ddotparam[2]))])
            else:
                res.extend([x for x in drange(op(ddotparam[0]), op(ddotparam[1]), int(ddotparam[2]))])

    return res


def pow10(x):
    return pow(10, x)


kernel = {'0': 'linear', '1': 'poly', '2': 'rbf', '3': 'sigmoid'}
repl = {'-t': ('kernel', lambda x: [kernel[i] for i in x.split(',')]),
        '-c': ('C', lambda x: parsesvm(x, float, unpac=pow10)),
        '-d': ('degree', lambda x: parsesvm(x, int)),
        '-e': ('tol', lambda x: parsesvm(x, float, unpac=pow10)),
        '-p': ('epsilon', lambda x: parsesvm(x, float, unpac=pow10)),
        '-g': ('gamma', lambda x: parsesvm(x, float, unpac=pow10)),
        '-r': ('coef0', lambda x: parsesvm(x, float))}


def main():
    rawopts = argparse.ArgumentParser(description="Model Builder",
                                      epilog="Copyright 2015 Ramil Nugmanov <stsouko@live.ru>")
    rawopts.add_argument("--input", "-i", type=str, default='input.sdf', help="input SDF ")
    rawopts.add_argument("--output", "-o", type=str, default=None, help="output SVM|HDR")
    rawopts.add_argument("--header", "-d", type=str, default=None, help="input header")
    rawopts.add_argument("--model", "-m", type=str, default=None, help="output model")
    rawopts.add_argument("--extention", "-e", action='append', type=str, default=None,
                         help="extention data files. -e extname:filename [-e extname2:filename2]")
    rawopts.add_argument("--fragments", "-f", type=str, default='input.param', help="fragmentor keys file")
    rawopts.add_argument("--svm", "-s", type=str, default='input.cfg', help="SVM params")
    rawopts.add_argument("--nfold", "-n", type=int, default=5, help="number of folds")
    rawopts.add_argument("--repetition", "-r", type=int, default=1, help="number of repetitions")
    rawopts.add_argument("--fit", "-t", type=str, default='rmse',
                         help="crossval score for parameters fit/ (rmse|r2)")
    rawopts.add_argument("--dispcoef", "-p", type=float, default=0,
                         help="score parameter. mean(rmse|r2) - dispcoef * dispertion(rmse|r2)")

    rawopts.add_argument("--normalize", "-N", action='store_true', help="normalize vector to range(0, 1)")

    options = vars(rawopts.parse_args())

    with open(options['fragments']) as f:
        tmp = {}
        for x in f:
            key, value = x.split('=')
            tmp[key] = value.strip()
        options['fragments'] = tmp

    extdata = parseext(options['extention']) if options['extention'] else {}
    frag = Fragmentor(workpath='.', header=options['header'], extention=extdata, **options['fragments'])

    if not options['output']:
        svm = {}
        if options['header'] is None:
            frag.genheader()
        with open(options['svm']) as f:
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
                            svm['linear'] = dict(kernel='linear', C=tmp['C'], epsilon=tmp['epsilon'], tol=tmp['tol'])
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
                            svm['sigmoid'] = dict(kernel='sigmoid', C=tmp['C'], epsilon=tmp['epsilon'], tol=tmp['tol'],
                                                  gamma=tmp['gamma'], coef0=tmp['coef0'])
                    elif i == 'poly':  # (gamma*u'*v + coef0)^degree
                        if svm.get('poly'):
                            for k in ('C', 'epsilon', 'tol', 'gamma', 'coef0', 'degree'):
                                svm['poly'][k].extend(tmp[k])
                        else:
                            svm['poly'] = dict(kernel='poly', C=tmp['C'], epsilon=tmp['epsilon'], tol=tmp['tol'],
                                               gamma=tmp['gamma'], coef0=tmp['coef0'], degree=tmp['degree'])

        model = Model(frag, svm.values(), inputfile=options['input'], parsesdf=True, dispcoef=options['dispcoef'],
                      fit=options['fit'],
                      nfold=options['nfold'], repetitions=options['repetition'], normalize=options['normalize'])
        pickle.dump(model, open(options['model'], 'wb'))
    else:
        frag.get(inputfile=options['input'], parsesdf=True, outputfile=options['output'])


if __name__ == '__main__':
    main()
