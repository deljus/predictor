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
from modeler.fragmentor import Fragmentor
from modeler.svmodel import Model as SVM
import argparse
import pickle
import gzip
from itertools import repeat
import subprocess as sp


class Modelbuilder(object):
    def __init__(self):
        self.__options = self.__argparser()

        if self.__options['fragments']:
            descgenparams = self.__parsefragmentoropts(self.__options['fragments'])
            descgenerator = Fragmentor
        else:
            return

        """ kostyl. for old model compatability
        """
        if self.__options['descriptors']:
            if len(self.__options['descriptors']) != len(descgenparams):
                print('number of descriptors files SHOULD BE EQUAL to number of descriptor generator params')
                return
            descriptors = []

            for x, y in zip(self.__options['descriptors'], descgenparams):
                descriptors.append(self.__parsesvm(x + '.svm'))
                if self.__options['fragments']:
                    y['header'] = x + '.hdr'
        else:
            descriptors = repeat(None)

        extdata = self.__parseext(self.__options['extention']) if self.__options['extention'] else {}

        self.__descgens = [descgenerator(workpath=self.__options['workpath'], extention=extdata, **x)
                           for x in descgenparams]

        if not self.__options['output']:
            if self.__options['svm']:
                estimatorparams = self.__getsvmparam(self.__options['svm'])
                estimator = SVM
            else:
                estimatorparams, descriptors = self.__dragossvmfit()
                estimator = SVM

            if 1 < len(estimatorparams) < len(self.__descgens) or \
                    len(estimatorparams) > len(self.__descgens) or not estimatorparams:
                print('NUMBER of estimator params files SHOULD BE EQUAL to '
                      'number of descriptor generator params files or to 1')
                return

            if len(estimatorparams) == 1:
                estimatorparams *= len(self.__descgens)

            if not os.path.isdir(self.__options['model']) and \
                    (os.path.exists(self.__options['model']) and os.access(self.__options['model'], os.W_OK) or
                     os.access(os.path.dirname(self.__options['model']), os.W_OK)):
                models = [estimator(x, y.values(), inputfile=self.__options['input'], parsesdf=True,
                                    dispcoef=self.__options['dispcoef'], fit=self.__options['fit'],
                                    scorers=self.__options['scorers'], estimator=self.__options['estimator'],
                                    n_jobs=self.__options['n_jobs'], nfold=self.__options['nfold'],
                                    smartcv=self.__options['smartcv'], rep_boost=self.__options['rep_boost'],
                                    repetitions=self.__options['repetition'], normalize=self.__options['normalize'],
                                    descriptors=z) for x, y, z in zip(self.__descgens, estimatorparams, descriptors)]

                # todo: удалять совсем плохие фрагментации. добавлять описание модели.
                pickle.dump([models, {}], gzip.open(self.__options['model'], 'wb'))
            else:
                print('path for model saving not writable')

        else:
            self.__gendesc(self.__options['output'])

    def __gendesc(self, output):
        for n, dgen in enumerate(self.__descgens, start=1):
            if not dgen.get(inputfile=self.__options['input'], parsesdf=True,
                            outputfile='%s.%d' % (output, n)):
                print('BAD Descriptor generator params in %d line' % n)
                return False
        return True

    def __dragossvmfit(self):
        """ files - basename for descriptors.
        """
        files = os.path.join(self.__options['workpath'], "dragos-%d" % int(time.time()))
        execparams = ['dragosgfstarter', files, self.__options['estimator']]
        if self.__gendesc(files):
            """ parse descriptors for speedup
            """
            if sp.call(execparams) == 0:
                svm = self.__getsvmparam(['%s.%d.result' % (files, x + 1) for x in range(len(self.__descgens))])
                descriptors = [self.__parsesvm('%s.%d.svm' % (files, x + 1)) for x in range(len(self.__descgens))]
                return svm, descriptors
        return [], None

    @staticmethod
    def __parsesvm(file):
        prop, vector = [], []
        with open(file) as f:
            for frag in f:
                y, *x = frag.split()
                prop.append(float(y) if y.strip() != '?' else 0)
                vector.append({int(k): float(v) for k, v in (i.split(':') for i in x)})

        return prop, vector

    @staticmethod
    def __argparser():
        rawopts = argparse.ArgumentParser(description="Model Builder",
                                          epilog="Copyright 2015, 2016 Ramil Nugmanov <stsouko@live.ru>",
                                          formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        rawopts.add_argument("--workpath", "-w", type=str, default='.', help="work path")

        rawopts.add_argument("--input", "-i", type=str, default='input.sdf', help="input SDF ")
        rawopts.add_argument("--output", "-o", type=str, default=None, help="output SVM|HDR")

        rawopts.add_argument("--descriptors", "-D", action='append', type=str, default=None,
                             help="input SVM|HDR with precalculated descriptors for fitting. "
                                  "-D filename{without .svm|hdr} [-D next filename if used more than 1 fragmentation]")

        rawopts.add_argument("--model", "-m", type=str, default='output.model', help="output model")
        rawopts.add_argument("--extention", "-e", action='append', type=str, default=None,
                             help="extention data files. -e extname:filename [-e extname2:filename2]")
        rawopts.add_argument("--fragments", "-f", type=str, default=None, help="ISIDA Fragmentor keys file")
        rawopts.add_argument("--svm", "-s", action='append', type=str, default=None,
                             help="SVM params. use Dragos Genetics if don't set."
                                  "can be multiple [-s 1 -s 2 ...]"
                                  "(number of files should be equal to number of fragments params) or single for all")
        rawopts.add_argument("--nfold", "-n", type=int, default=5, help="number of folds")
        rawopts.add_argument("--repetition", "-r", type=int, default=1, help="number of repetitions")
        rawopts.add_argument("--rep_boost", "-R", type=int, default=25,
                             help="percentage of repetitions for use in greed search for optimization speedup")
        rawopts.add_argument("--n_jobs", "-j", type=int, default=2, help="number of parallel fit jobs")

        rawopts.add_argument("--estimator", "-E", type=str, default='svr', help="estimator [svr, svc]")
        rawopts.add_argument("--scorers", "-T", action='append', type=str, default=['rmse', 'r2'],
                             help="needed scoring functions. -T rmse [-T r2]")
        rawopts.add_argument("--fit", "-t", type=str, default='rmse',
                             help="crossval score for parameters fit. (rmse|r2|ba|kappa)")
        rawopts.add_argument("--dispcoef", "-p", type=float, default=0,
                             help="score parameter. mean(score) - dispcoef * dispertion(score)")

        rawopts.add_argument("--normalize", "-N", action='store_true', help="normalize X vector to range(0, 1)")
        rawopts.add_argument("--smartcv", "-S", action='store_true', help="smart crossvalidation [NOT implemented]")

        return vars(rawopts.parse_args())

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
