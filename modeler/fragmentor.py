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
import subprocess as sp
from itertools import count
import numpy as np
import pandas as pd
from modeler.structprepare import ISIDAatommarker, StandardizeDragos
from CGRtools.main_condenser import condenser_core
from io import StringIO
from sklearn.feature_extraction import DictVectorizer
from utils.config import FRAGMENTOR


class CGRWrapper(object):
    def __init__(self, **kwargs):
        self.__kwargs = kwargs

    def get(self, structure):
        output = StringIO()
        condenser_core(input=structure, output=output, **self.__kwargs)
        return output.getvalue()


class Fragmentor(object):
    def __init__(self, workpath='.', version='last', s_option=None, fragment_type='3', min_length='2', max_length='10',
                 colorname=None, marked_atom=None, cgr_dynbonds=None, xml=None, doallways=False,
                 useformalcharge=False, atompairs=False, fragmentstrict=False, getatomfragment=False,
                 overwrite=True, header=None, extention=None, marker_rules=None, standardize=None,
                 cgr_type=None, cgr_stereo=False, cgr_balance=0, cgr_b_templates=None,
                 cgr_e_rules=None, cgr_c_rules=None):

        self.__marker = ISIDAatommarker(marker_rules, workpath) if marker_rules else None
        self.__standardize = StandardizeDragos(standardize) if standardize else None

        self.__cgr = CGRWrapper(type=cgr_type, stereo=cgr_stereo, balance=int(cgr_balance),
                                b_templates=open(cgr_b_templates) if cgr_b_templates else None,
                                e_rules=open(cgr_e_rules) if cgr_e_rules else None,
                                c_rules=open(cgr_c_rules) if cgr_c_rules else None) if cgr_type else None

        self.__sparse = DictVectorizer(sparse=False)

        self.__extention = extention
        if extention:
            self.__prepareextheader()

        self.__genheader = False
        self.__headpath = None

        self.__workpath = workpath
        self.__fragversion = version
        tmp = ['-f', 'SVM']
        if s_option: tmp.extend(['-s', s_option])
        if header and os.path.exists(header):
            self.__dumpheader(header)
            tmp.extend(['-h', ''])
        else:
            self.__genheader = True

        tmp.extend(['-t', fragment_type, '-l', min_length, '-u', max_length])

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
        return '%s-%s' % (FRAGMENTOR, self.__fragversion)

    def __dumpheader(self, header):
        with open(header) as f:
            self.__headdump = f.read()
            lines = self.__headdump.splitlines()
            self.__headsize = len(lines)
            self.__headdict = {int(k[:-1]): v for k, v in (i.split() for i in lines)}
            self.__headcolumns = list(self.__headdict.values())

    def setworkpath(self, workpath):
        self.__workpath = workpath
        if self.__marker:
            self.__marker.setworkpath(workpath)

    def __prepareheader(self):
        header = os.path.join(self.__workpath, "model.hdr")
        with open(header, 'w') as f:
            f.write(self.__headdump)
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

    def get(self, inputfile=None, outputfile=None, inputstring=None, **kwargs):
        """
        :param inputstring: sdf, mol or rdf, rxn as string
        :param outputfile: output svm file
        :param inputfile: input sdf or rdf file
        """

        """ PMAPPER and Standardizer works only with molecules. NOT CGR!
        """
        def splitter(f):  # MEMORY EATER
            return ''.join(f.get(x + '\n$$$$\n') for x in
                           (inputstring or open(inputfile).read()).rstrip('$\n ').split('\n$$$$\n'))

        if self.__marker:
            inputstring = splitter(self.__marker)
        if self.__standardize:
            inputstring = splitter(self.__standardize)
            inputfile = None

        if self.__cgr:
            inputstring = self.__cgr.get(StringIO(inputstring) if inputstring else open(inputfile))
            inputfile = None
        """ END
        """
        if inputstring:
            inputfile = os.path.join(self.__workpath, "frg.sdf")
            with open(inputfile, 'w') as f:
                f.write(inputstring)
        elif not inputfile:
            return False

        parser = False
        if not outputfile:
            outputfile = os.path.join(self.__workpath, "frg")
            parser = True

        if self.__extention:
            if kwargs.get('parsesdf'):
                extblock = self.parsesdf(inputfile)

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
        if not self.__genheader:
            self.__prepareheader()

        execparams = [self.__fragmentor(), '-i', inputfile, '-o', outputfile]
        execparams.extend(self.__execparams)
        print(' '.join(execparams))
        exitcode = sp.call(execparams) == 0

        if exitcode and os.path.exists(outputfile + '.svm') and os.path.exists(outputfile + '.hdr'):
            if self.__genheader:
                self.__genheader = False
                self.__dumpheader(outputfile + '.hdr')
                self.__execparams.insert(self.__execparams.index('-t'), '-h')
                self.__execparams.insert(self.__execparams.index('-t'), '')
            print('parsing fragmentor output')
            X, Y, D = self.__parsefragmentoroutput(outputfile)
            print('parsing done')
            if parser:
                return pd.concat([X, extblock], axis=1), Y, D
            else:
                return self.__savesvm(outputfile, pd.concat([X, extblock], axis=1), Y)

        return False

    def __parsefragmentoroutput(self, outputfile):
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
                    if k <= self.__headsize:
                        tmp[self.__headdict[k]] = v
                    else:
                        ad[-1] = False
                        break
                vector.append(tmp)

        return pd.DataFrame(vector, columns=self.__headcolumns).fillna(0), pd.Series(prop), pd.Series(ad)

    def __savesvm(self, outputfile, X, Y):
        k2nd = {}
        k2nc = count(1)

        def k2n(k):
            n = k2nd.get(k)
            if n is None:
                n = next(k2nc)
                k2nd[k] = n
            return n
        with open(outputfile + '.svm', 'w') as f:
            f.write(' '.join(['Property'] + ['%s:%s' % (k2n(i), i) for i in X.T.to_dict()[0]]) + '\n')
            for i, j in zip(X.T.to_dict().values(), Y.tolist()):
                f.write(' '.join(['%s ' % j] + ['%s:%s' % (k2n(k), v) for k, v in i.items()]) + '\n')
        return True
