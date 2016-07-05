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
from modeler.structprepare import Pharmacophoreatommarker, StandardizeDragos, CGRatommarker
from io import StringIO
from CGRtools.SDFread import SDFread
from CGRtools.SDFwrite import SDFwrite
from CGRtools.RDFread import RDFread
from subprocess import Popen, PIPE, STDOUT
from utils.config import CXCALC
import os


class Pkab(object):
    def __init__(self, workpath='.', marker_rules=None, standardize=None,
                 cgr_marker=None, cgr_marker_prepare=None, cgr_marker_postprocess=None, cgr_stereo=False):
        self.__dragos_marker = Pharmacophoreatommarker(marker_rules, workpath) if marker_rules else None

        self.__cgr_marker = CGRatommarker(cgr_marker, prepare=cgr_marker_prepare,
                                          postprocess=cgr_marker_postprocess,
                                          stereo=cgr_stereo) if cgr_marker else None

        self.__dragos_std = StandardizeDragos(standardize) if standardize and not self.__cgr_marker else None
        self.__workpath = workpath

    def setworkpath(self, workpath):
        self.__workpath = workpath
        if self.__dragos_marker:
            self.__dragos_marker.setworkpath(workpath)

    def get(self, structures, **kwargs):
        reader = RDFread(structures) if self.__cgr_marker else SDFread(structures)
        data = list(reader.readdata())

        if self.__dragos_std:
            data = self.__dragos_std.get(data)

        if not data:
            return False

        if self.__cgr_marker:
            data = self.__cgr_marker.get(data)

        elif self.__dragos_marker:
            data = self.__dragos_marker.get(data)

        if not data:
            return False

        doubles = []

        with StringIO() as f:
            writer = SDFwrite(f)
            for s_numb, s in enumerate(data):
                d = s[0][1] if isinstance(s, list) else s
                writer.writedata(d)
                    doubles.append([s_numb])

        p = Popen([CXCALC], stdout=PIPE, stdin=PIPE, stderr=STDOUT)
        with StringIO() as f:
            tmp = SDFwrite(f)
            for x in structure:
                tmp.writedata(x)

            res = p.communicate(input=f.getvalue().encode())[0].decode()
            if p.returncode == 0:
                return list(RDFread(StringIO(res)).readdata(remap=remap))

        with StringIO() as f:
            writer = SDFwrite(f)

        for n, workfile in enumerate(workfiles):
            if not self.__genheader:
                self.__prepareheader(n)

            execparams = [self.__fragmentor(), '-i', workfile, '-o', outputfile]
            execparams.extend(self.__execparams)
            print(' '.join(execparams), file=sys.stderr)
            exitcode = sp.call(execparams) == 0

            if exitcode and os.path.exists(outputfile + '.svm') and os.path.exists(outputfile + '.hdr'):
                if self.__genheader:  # dump header if don't set on first run
                    self.__dumpheader(n, outputfile + '.hdr')
                    if n + 1 == len(workfiles):  # disable header generation
                        self.__genheader = False
                        self.__execparams.insert(self.__execparams.index('-t'), '-h')
                        self.__execparams.insert(self.__execparams.index('-t'), '')

                print('parsing fragmentor output', file=sys.stderr)
                X, Y, D = self.__parsefragmentoroutput(n, outputfile)
                tX.append(X)
                tY = Y
                tD.append(D)
            else:
                return False

        res = dict(X=pd.concat(tX, axis=1, keys=range(len(tX))), AD=reduce(operator.and_, tD), Y=tY)
        if self.__cgr_marker or self.__dragos_marker:
            i = pd.MultiIndex.from_tuples(doubles, names=['structure'] + ['c.%d' % x for x in range(len(workfiles))])
        else:
            i = pd.Index(doubles, name='structure')

        res['X'].index = res['AD'].index = res['Y'].index = i
        return res
