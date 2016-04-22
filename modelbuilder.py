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
import os
import time
from copy import deepcopy
import pandas as pd
from modeler.fragmentor import Fragmentor
from modeler.svmodel import Model as SVM
import argparse
import pickle
import gzip
import subprocess as sp


class DefaultList(list):
    @staticmethod
    def __copy__():
        return []


class Modelbuilder(object):
    def __init__(self):
        self.__options = self.__argparser()

        """ Descriptor generator Block
        """
        descgenerator = []
        if self.__options['fragments']:
            descgenerator.extend([(Fragmentor, x, 'fragments') for x in
                                  self.__parsefragmentoropts(self.__options['fragments'])])
        else:
            return

        extdata = self.__parseext(self.__options['extention']) if self.__options['extention'] else {}
        self.__descgens = [g(extention=extdata, **x)
                           for g, x, _ in descgenerator]

        description = self.__parsemodeldescription()

        if not self.__options['output']:
            ests = []
            svm = {'svr', 'svc'}.intersection(self.__options['estimator']).pop()
            if svm:
                if self.__options['svm']:
                    estparams = self.__getsvmparam(self.__options['svm'])
                else:
                    estparams = self.__dragossvmfit(svm)

                estparams = self.__chkest(estparams)
                if not estparams:
                    return
                ests.append((lambda *vargs, **kwargs: SVM(*vargs, estimator=svm, **kwargs),
                             estparams))
            else:
                return

            if not os.path.isdir(self.__options['model']) and \
                    (os.path.exists(self.__options['model']) and os.access(self.__options['model'], os.W_OK) or
                     os.access(os.path.dirname(self.__options['model']), os.W_OK)):
                models = [g(x, y.values(), inputfile=self.__options['input'], parsesdf=True,
                            dispcoef=self.__options['dispcoef'], fit=self.__options['fit'],
                            scorers=self.__options['scorers'],
                            n_jobs=self.__options['n_jobs'], nfold=self.__options['nfold'],
                            smartcv=self.__options['smartcv'], rep_boost=self.__options['rep_boost'],
                            repetitions=self.__options['repetition'],
                            normalize=self.__options['normalize']) for g, e in ests
                          for x, y in zip(self.__descgens, e)]

                # todo: удалять совсем плохие фрагментации. добавлять описание модели.
                if 'tol' not in description:
                    description['tol'] = models[0].getmodelstats()['dragostolerance']
                pickle.dump(dict(models=models, config=description),
                            gzip.open(self.__options['model'], 'wb'))
            else:
                print('path for model saving not writable')

        else:
            self.__gendesc(self.__options['output'])

    def __chkest(self, estimatorparams):
        if 1 < len(estimatorparams) < len(self.__descgens) or \
               len(estimatorparams) > len(self.__descgens) or not estimatorparams:
            print('NUMBER of estimator params files SHOULD BE EQUAL to '
                  'number of descriptor generator params files or to 1')
            return False

        if len(estimatorparams) == 1:
            tmp = []
            for i in range(len(self.__descgens)):
                tmp.append(deepcopy(estimatorparams[0]))
            estimatorparams = tmp
        return estimatorparams

    def __gendesc(self, output):
        for n, dgen in enumerate(self.__descgens, start=1):
            if not dgen.get(inputfile=self.__options['input'], parsesdf=True,
                            outputfile='%s.%d' % (output, n)):
                print('BAD Descriptor generator params in %d line' % n)
                return False
        return True

    def __dragossvmfit(self, tasktype):
        """ files - basename for descriptors.
        """
        files = os.path.join(self.__options['workpath'], "dragos-%d" % int(time.time()))
        execparams = ['dragosgfstarter', files, tasktype]
        if self.__gendesc(files):
            """ parse descriptors for speedup
            """
            if sp.call(execparams) == 0:
                svm = self.__getsvmparam(['%s.%d.result' % (files, x + 1) for x in range(len(self.__descgens))])
                for x in range(len(self.__descgens)):
                    os.remove('%s.%d.svm' % (files, x + 1))
                    os.remove('%s.%d.hdr' % (files, x + 1))
                    os.remove('%s.%d.result' % (files, x + 1))
                return svm
        return []

    @staticmethod
    def __argparser():
        rawopts = argparse.ArgumentParser(description="Model Builder",
                                          epilog="Copyright 2015, 2016 Ramil Nugmanov <stsouko@live.ru>",
                                          formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        rawopts.add_argument("--workpath", "-w", type=str, default='.', help="work path")

        rawopts.add_argument("--input", "-i", type=str, default='input.sdf', help="input SDF or RDF")

        rawopts.add_argument("--dragosmolstd", action='store_true',
                             help="prepare molecules with Dragos approach [NOT for REACTIONS]")
        rawopts.add_argument("--markatoms", type=str, default=None,
                             help="prepare molecules with JChem pmapper [NOT for REACTIONS]")

        rawopts.add_argument("--output", "-o", type=str, default=None, help="output SVM|HDR")

        rawopts.add_argument("--model", "-m", type=str, default='output.model', help="output model")
        rawopts.add_argument("--extention", "-e", action='append', type=str, default=None,
                             help="extention data files. -e extname:filename [-e extname2:filename2]")

        rawopts.add_argument("--fragments", "-f", type=str, default=None, help="ISIDA Fragmentor keys file")

        rawopts.add_argument("--description", "-ds", type=str, default='model.dsc', help="model description file")

        rawopts.add_argument("--svm", "-s", action='append', type=str, default=None,
                             help="SVM params. use Dragos Genetics if don't set."
                                  "can be multiple [-s 1 -s 2 ...]"
                                  "(number of files should be equal to number of configured descriptor generators) "
                                  "or single for all")

        rawopts.add_argument("--nfold", "-n", type=int, default=5, help="number of folds")
        rawopts.add_argument("--repetition", "-r", type=int, default=1, help="number of repetitions")
        rawopts.add_argument("--rep_boost", "-R", type=int, default=25,
                             help="percentage of repetitions for use in greed search for optimization speedup")
        rawopts.add_argument("--n_jobs", "-j", type=int, default=2, help="number of parallel fit jobs")

        rawopts.add_argument("--estimator", "-E", action='append', type=str, default=DefaultList(['svr']),
                             choices=['svr', 'svc'],
                             help="estimator")
        rawopts.add_argument("--scorers", "-T", action='append', type=str, default=DefaultList(['rmse', 'r2']),
                             choices=['rmse', 'r2', 'ba', 'kappa'],
                             help="needed scoring functions. -T rmse [-T r2]")
        rawopts.add_argument("--fit", "-t", type=str, default='rmse', choices=['rmse', 'r2', 'ba', 'kappa'],
                             help="crossval score for parameters fit. (should be in selected scorers)")

        rawopts.add_argument("--dispcoef", "-p", type=float, default=0,
                             help="score parameter. mean(score) - dispcoef * sqrt(variance(score)). -score for rmse")

        rawopts.add_argument("--normalize", "-N", action='store_true', help="normalize X vector to range(0, 1)")
        rawopts.add_argument("--smartcv", "-S", action='store_true', help="smart crossvalidation [NOT implemented]")

        return vars(rawopts.parse_args())

    def __parsemodeldescription(self):
        tmp = {}
        with open(self.__options['description']) as f:
            for line in f:
                k, v = line.split(':=')
                k = k.strip()
                v.strip()
                if k == 'hashes':
                    v = v.split()
                elif k == 'is_reaction':
                    v = True if v.lower() == 'true' else False
                elif k in ('nlim', 'tol'):
                    v = float(v)
                tmp[k] = v
        return tmp

    def __parsefragmentoropts(self, file):
        params = []
        with open(file) as f:
            for line in f:
                opts = line.split()
                tmp = {}
                for x in opts:
                    key, value = x.split('=')
                    tmp[key.strip()] = value.strip()
                params.append(tmp)
        return params

    @staticmethod
    def __parseext(rawext):
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
    def __drange(start, stop, step):
        r = start
        s = (stop - start) / (step - 1)
        res = []
        while r <= stop:
            res.append(r)
            r += s
        return res

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
    def __pow10(x):
        return pow(10, x)

    __kernel = {'0': 'linear', '1': 'poly', '2': 'rbf', '3': 'sigmoid'}

    def __getsvmparam(self, files):
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


if __name__ == '__main__':
    main = Modelbuilder()
