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
import operator
import os
import subprocess as sp
import numpy as np
import pandas as pd
from functools import reduce
from modeler.structprepare import ISIDAatommarker, StandardizeDragos
from CGRtools.main_condenser import condenser_core
from sklearn.feature_extraction import DictVectorizer
from utils.config import FRAGMENTOR


class CGRWrapper(object):
    def __init__(self, **kwargs):
        self.__kwargs = kwargs

    def convert(self, structures, output):
        condenser_core(input=structures, output=output, **self.__kwargs)


class Adhoc(object):
    @staticmethod
    def get(structure):
        return structure


class Fragmentor(object):
    def __init__(self, workpath='.', version=None, s_option=None, fragment_type=3, min_length=2, max_length=10,
                 colorname=None, marked_atom=0, cgr_dynbonds=0, xml=None, doallways=False,
                 useformalcharge=False, atompairs=False, fragmentstrict=False, getatomfragment=False,
                 overwrite=True, headers=None, extention=None, marker_rules=None, standardize=None,
                 cgr_type=None, cgr_stereo=False, cgr_balance=0, cgr_b_templates=None,
                 cgr_e_rules=None, cgr_c_rules=None):

        self.__marker = ISIDAatommarker(marker_rules, workpath) if marker_rules else None
        self.__standardize = StandardizeDragos(standardize) if standardize is not None or marker_rules else None

        self.__cgr = CGRWrapper(type=cgr_type, stereo=cgr_stereo, balance=int(cgr_balance),
                                b_templates=open(cgr_b_templates) if cgr_b_templates else None,
                                e_rules=open(cgr_e_rules) if cgr_e_rules else None,
                                c_rules=open(cgr_c_rules) if cgr_c_rules else None) if cgr_type else None

        self.__sparse = DictVectorizer(sparse=False)

        self.__extention = extention
        if extention:
            self.__prepareextheader()

        self.__headdump = {}
        self.__headsize = {}
        self.__headdict = {}
        self.__headcolumns = {}

        self.__workpath = workpath
        self.__fragversion = ('-%s' % version) if version else ''
        tmp = ['-f', 'SVM']
        if s_option: tmp.extend(['-s', s_option])
        if headers and all(os.path.exists(x) for x in headers):
            self.__genheader = False
            for n, header in enumerate(headers):
                self.__dumpheader(n, header)
            tmp.extend(['-h', ''])
        else:
            self.__genheader = True

        tmp.extend(['-t', str(fragment_type), '-l', str(min_length), '-u', str(max_length)])

        if colorname: tmp.extend(['-c', colorname])
        if marked_atom: tmp.extend(['-m', marked_atom])
        if cgr_dynbonds: tmp.extend(['-d', cgr_dynbonds])
        if xml: tmp.extend(['-x', xml])
        if doallways: tmp.append('--DoAllWays')
        if atompairs: tmp.append('--AtomPairs')
        if useformalcharge: tmp.append('--UseFormalCharge')
        if fragmentstrict: tmp.append('--StrictFrg')
        if getatomfragment: tmp.append('--GetAtomFragment')
        if not overwrite: tmp.append('--Pipe')

        self.__execparams = tmp

    def __fragmentor(self):
        return '%s%s' % (FRAGMENTOR, self.__fragversion)

    def __dumpheader(self, n, header):
        with open(header) as f:
            self.__headdump[n] = f.read()
            lines = self.__headdump[n].splitlines()
            self.__headsize[n] = len(lines)
            self.__headdict[n] = {int(k[:-1]): v for k, v in (i.split() for i in lines)}
            self.__headcolumns[n] = list(self.__headdict[n].values())

    def setworkpath(self, workpath):
        self.__workpath = workpath
        if self.__marker:
            self.__marker.setworkpath(workpath)

    def __prepareheader(self, n):
        header = os.path.join(self.__workpath, "model.hdr")
        with open(header, 'w') as f:
            f.write(self.__headdump[n])
        self.__execparams[self.__execparams.index('-h') + 1] = header

    def __prepareextheader(self):
        tmp = []
        for i, j in self.__extention.items():
            if j:
                tmp.extend(j['value'].columns)
            else:
                tmp.append(i)
        self.__extheader = tmp

    def parsesdf(self, inputfile):
        extblock = []
        flag = False
        tmp = []
        with open(inputfile) as f:
            for i in f:
                if '>  <' in i[:4]:
                    key = i.strip()[4:-1]
                    if key in self.__extention:
                        flag = key
                elif flag:
                    data = self.__extention[flag]['value'].loc[self.__extention[flag]['key'] == i.strip()] if \
                        self.__extention[flag] else pd.DataFrame([{flag: float(i.strip())}])
                    data.index = [0]
                    tmp.append(data)
                    flag = False
                elif '$$$$' in i:
                    extblock.append(pd.concat(tmp, axis=1) if tmp else pd.DataFrame([{}]))
                    tmp = []

        return pd.DataFrame(pd.concat(extblock, ignore_index=True), columns=self.__extheader)

    def __parseadditions0(self, **kwargs):
        extblock = []
        for i, j in kwargs.items():
            if i in self.__extention:
                for n, k in enumerate(j) if isinstance(j, list) else j.items():
                    data = self.__extention[i]['value'].loc[self.__extention[i]['key'] == k] if \
                        self.__extention[i] else pd.DataFrame([{i: k}])
                    data.index = [0]
                    if len(extblock) > n:
                        extblock[n].append(data)
                    else:
                        extblock.extend([[] for _ in range(n - len(extblock))] + [data])

        return pd.DataFrame(pd.concat([pd.concat(x, axis=1) if x else pd.DataFrame([{}]) for x in extblock],
                                      ignore_index=True), columns=self.__extheader)

    def __parseadditions1(self, **kwargs):
        tmp = []
        for i, j in kwargs.items():
            if i in self.__extention:
                data = self.__extention[i]['value'].loc[self.__extention[i]['key'] == j] if \
                       self.__extention[i] else pd.DataFrame([{i: j}])
                data.index = [0]
                tmp.append(data)
        return pd.DataFrame(pd.concat(tmp, axis=1) if tmp else pd.DataFrame([{}]), columns=self.__extheader)

    def get(self, structures, **kwargs):
        """ PMAPPER and Standardizer works only with molecules. NOT CGR!
        :param structures: opened file or string io in sdf, mol or rdf, rxn formats
        rdf, rxn work only in CGR or reagent marked atoms mode
        """
        def splitter(func, output):  # for mol or sdf only!
            flag = False
            with open(output, 'w') as w:
                buffer = []
                for line in structures:
                    buffer.append(line)
                    if '$$$$' in line[:4]:
                        res = func.get(''.join(buffer))
                        if res:
                            flag = True
                            w.write(res)
                        buffer = []
                if buffer:
                    res = func.get(''.join(buffer).rstrip('\n$ ') + '\n$$$$\n')
                    if res:
                        flag = True
                        w.write(res)
            return flag

        adhoc = Adhoc()

        workfiles = [os.path.join(self.__workpath, "frg.sdf")]
        outputfile = os.path.join(self.__workpath, "frg")

        if self.__cgr:
            with open(workfiles[0], 'w') as f:
                self.__cgr.convert(structures, f)

        elif self.__standardize:
            tmpfile = os.path.join(self.__workpath, "tmp.sdf")
            with open(tmpfile, 'w') as f:
                if not splitter(self.__standardize, f):
                    return False

            if self.__marker:
                with open(workfiles[0], 'w') as f, open(tmpfile) as structures:
                    if not splitter(self.__marker, f):
                        return False
            else:
                workfiles[0] = tmpfile

        else:
            with open(workfiles[0], 'w') as f:
                if not splitter(adhoc, f):
                    return False

        if self.__extention:
            if kwargs.get('parsesdf'):
                extblock = self.parsesdf(workfiles[0])

            elif all(isinstance(x, list) or isinstance(x, dict) for y, x in kwargs.items() if y in self.__extention):
                extblock = self.__parseadditions0(**kwargs)

            elif not any(isinstance(x, list) or isinstance(x, dict) for y, x in kwargs.items() if y in self.__extention):
                extblock = self.__parseadditions1(**kwargs)

            else:
                print('WHAT DO YOU WANT? use correct extentions params')
                return False
        else:
            extblock = pd.DataFrame()

        """ prepare header if exist (normally true). run fragmentor.
        """
        tX, tY, tD = [], None, []

        for n, workfile in enumerate(workfiles):
            if not self.__genheader:
                self.__prepareheader(n)

            execparams = [self.__fragmentor(), '-i', workfile, '-o', outputfile]
            execparams.extend(self.__execparams)
            print(' '.join(execparams))
            exitcode = sp.call(execparams) == 0

            if exitcode and os.path.exists(outputfile + '.svm') and os.path.exists(outputfile + '.hdr'):
                if self.__genheader:  # dump header if don't set on first run
                    self.__dumpheader(n, outputfile + '.hdr')
                    if n + 1 == len(workfiles):  # disable header generation
                        self.__genheader = False
                        self.__execparams.insert(self.__execparams.index('-t'), '-h')
                        self.__execparams.insert(self.__execparams.index('-t'), '')

                print('parsing fragmentor output')
                X, Y, D = self.__parsefragmentoroutput(n, outputfile)
                print('parsing done')
                tX.append(X)
                tY = Y
                tD.append(D)
            else:
                return False

        return pd.concat(tX + [extblock], axis=1), tY, reduce(operator.mul, tD)

    def __parsefragmentoroutput(self, n, outputfile):
        prop, vector, ad = [], [], []
        with open(outputfile + '.svm') as sf:
            for frag in sf:
                y, *x = frag.split()
                prop.append(float(y) if y.strip() != '?' else np.NaN)
                ad.append(True)
                tmp = {}  # X vector
                for i in x:
                    k, v = i.split(':')
                    k = int(k)
                    v = int(v)
                    if k <= self.__headsize[n]:
                        tmp[self.__headdict[n][k]] = v
                    else:
                        ad[-1] = False
                        break
                vector.append(tmp)

        return pd.DataFrame(vector, columns=self.__headcolumns[n]).fillna(0), pd.Series(prop), pd.Series(ad)
