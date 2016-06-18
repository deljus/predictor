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
from itertools import tee
import numpy as np
import pandas as pd
from functools import reduce
from modeler.structprepare import Pharmacophoreatommarker, StandardizeDragos, CGRatommarker, Colorize
from CGRtools.CGRcore import CGRcore
from CGRtools.SDFread import SDFread
from CGRtools.SDFwrite import SDFwrite
from CGRtools.RDFread import RDFread
from sklearn.feature_extraction import DictVectorizer
from utils.config import FRAGMENTOR


class openFiles(object):
    def __init__(self, files, flags):
        if isinstance(files, str):
            files = [files]
        if isinstance(flags, str):
            flags = [flags]
        assert len(flags) == len(files)
        self.files = files
        self.flags = flags

    def __enter__(self):
        self.fhs = []
        for f, fl in zip(self.files, self.flags):
            self.fhs.append(open(f, fl))
        return self.fhs

    def __exit__(self, type, value, traceback):
        for f in self.fhs:
            f.close()


def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


class Fragmentor(object):
    def __init__(self, workpath='.', version=None, s_option=None, fragment_type=3, min_length=2, max_length=10,
                 colorname=None, marked_atom=0, cgr_dynbonds=0, xml=None, doallways=False,
                 useformalcharge=False, atompairs=False, fragmentstrict=False, getatomfragment=False,
                 overwrite=True, headers=None,
                 marker_rules=None, standardize=None,
                 cgr_marker=None, cgr_marker_prepare=None, cgr_marker_postprocess=None,
                 cgr_type=None, cgr_stereo=False, cgr_balance=0, cgr_b_templates=None,
                 cgr_e_rules=None, cgr_c_rules=None, docolor=None):

        self.__prepocess = any(x is not None for x in (marker_rules, standardize, cgr_type, cgr_marker, docolor))

        self.__dragos_marker = Pharmacophoreatommarker(marker_rules, workpath) if marker_rules else None

        self.__cgr = CGRcore(type=cgr_type, stereo=cgr_stereo, balance=int(cgr_balance),
                             b_templates=open(cgr_b_templates) if cgr_b_templates else None,
                             e_rules=open(cgr_e_rules) if cgr_e_rules else None,
                             c_rules=open(cgr_c_rules) if cgr_c_rules else None) if cgr_type is not None else None

        self.__cgr_marker = CGRatommarker(cgr_marker, prepare=cgr_marker_prepare,
                                          postprocess=cgr_marker_postprocess,
                                          stereo=cgr_stereo) if cgr_marker else None

        self.__dragos_std = StandardizeDragos(standardize) if standardize and not (self.__cgr or
                                                                                   self.__cgr_marker) else None
        self.__do_color = Colorize(docolor, workpath) if docolor else None

        self.__sparse = DictVectorizer(sparse=False)

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
        if marked_atom: tmp.extend(['-m', str(marked_atom)])
        if cgr_dynbonds: tmp.extend(['-d', str(cgr_dynbonds)])
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
        with open(header, encoding='utf-8') as f:
            self.__headdump[n] = f.read()
            lines = self.__headdump[n].splitlines()
            self.__headsize[n] = len(lines)
            self.__headdict[n] = {int(k[:-1]): v for k, v in (i.split() for i in lines)}
            self.__headcolumns[n] = list(self.__headdict[n].values())

    def setworkpath(self, workpath):
        self.__workpath = workpath
        if self.__dragos_marker:
            self.__dragos_marker.setworkpath(workpath)
        if self.__do_color:
            self.__do_color.setworkpath(workpath)

    def __prepareheader(self, n):
        header = os.path.join(self.__workpath, "model.hdr")
        with open(header, 'w', encoding='utf-8') as f:
            f.write(self.__headdump[n])
        self.__execparams[self.__execparams.index('-h') + 1] = header

    def get(self, structures):
        """ PMAPPER and Standardizer works only with molecules. NOT CGR!
        :param structures: opened file or string io in sdf, mol or rdf, rxn formats
        rdf, rxn work only in CGR or reagent marked atoms mode
        """
        workfiles = [os.path.join(self.__workpath, "frg_%d.sdf" % x)
                     for x in range(self.__cgr_marker.getcount() if self.__cgr_marker
                                    else self.__dragos_marker.getcount() if self.__dragos_marker else 1)]
        outputfile = os.path.join(self.__workpath, "frg")

        if self.__prepocess:
            with openFiles(workfiles, ['w']*len(workfiles)) as f:
                writers = [SDFwrite(x) for x in f]
                reader = RDFread(structures) if self.__cgr or self.__cgr_marker else SDFread(structures)
                data = list(reader.readdata())
                if self.__dragos_std:
                    data = self.__dragos_std.get(data)

                if self.__do_color:
                    if self.__cgr or self.__cgr_marker:
                        for i in ('substrats', 'products'):
                            mols, shifts = [], [0]
                            for x in data:
                                shifts.append(len(x[i]) + shifts[-1])
                                mols.extend(x[i])

                            colored = self.__do_color.get(mols)
                            if not colored:
                                return False

                            for (y, z), x in zip(pairwise(shifts), data):
                                x[i] = colored[y: z]
                    else:
                        data = self.__do_color.get(data)

                if not data:
                    return False

                if self.__cgr:
                    data = [self.__cgr.getCGR(x) for x in data]

                elif self.__cgr_marker:
                    data = self.__cgr_marker.get(data)

                elif self.__dragos_marker:
                    data = self.__dragos_marker.get(data)

                if not data:
                    return False

                for s in data:
                    for w, d in zip(writers, s if isinstance(s, list) else [s]):
                        for x in (d if isinstance(d, list) else [d]):
                            w.writedata(x)

        else:
            with open(workfiles[0], 'w') as f:
                for i in structures:
                    f.write(i)

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
                tX.append(X)
                tY = Y
                tD.append(D)
            else:
                return False

        return pd.concat(tX, axis=1), tY, reduce(operator.mul, tD)

    def __parsefragmentoroutput(self, n, outputfile):
        prop, vector, ad = [], [], []
        with open(outputfile + '.svm') as sf:
            for frag in sf:
                y, *x = frag.split()
                prop.append(float(y) if y.strip() != '?' else np.NaN)
                ad.append(True)
                tmp = {}  # X vector
                for i in x:
                    k, v = (int(x) for x in i.split(':'))
                    if k <= self.__headsize[n]:
                        tmp[self.__headdict[n][k]] = v
                    else:
                        ad[-1] = False
                        break
                vector.append(tmp)

        return (pd.DataFrame(vector, columns=self.__headcolumns[n]).fillna(0),
                pd.Series(prop, name='Property'), pd.Series(ad))
