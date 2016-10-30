#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-
#
# Copyright 2016 Ramil Nugmanov <stsouko@live.ru>
# This file is part of MODtools.
#
# MODtools is free software; you can redistribute it and/or modify
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
import pandas as pd
from functools import reduce
from io import StringIO
from subprocess import Popen, PIPE
from CGRtools.RDFrw import RDFread
from CGRtools.SDFrw import SDFread, SDFwrite
from ..config import EED
from .descriptoragregator import Propertyextractor
from ..structprepare import Pharmacophoreatommarker, StandardizeDragos, CGRatommarker


class Eed(Propertyextractor):
    def __init__(self, workpath='.', s_option=None, marker_rules=None, standardize=None, cgr_reverse=False,
                 cgr_marker=None, cgr_marker_prepare=None, cgr_marker_postprocess=None, cgr_stereo=False):
        Propertyextractor.__init__(self, s_option, isreaction=cgr_marker)
        self.__dragos_marker = Pharmacophoreatommarker(marker_rules, workpath) if marker_rules else None

        self.__cgr_marker = CGRatommarker(cgr_marker, prepare=cgr_marker_prepare,
                                          postprocess=cgr_marker_postprocess,
                                          stereo=cgr_stereo, reverse=cgr_reverse) if cgr_marker else None

        self.__dragos_std = StandardizeDragos(standardize) \
            if standardize is not None and not self.__cgr_marker else None
        self.__workpath = workpath

    def setworkpath(self, workpath):
        self.__workpath = workpath
        if self.__dragos_marker:
            self.__dragos_marker.setworkpath(workpath)

    def get(self, structures, **kwargs):
        reader = RDFread(structures) if self.__cgr_marker else SDFread(structures)
        data = list(reader.read())
        structures.seek(0)  # ad-hoc for rereading

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

        workfiles = [StringIO() for _ in range(self.__cgr_marker.getcount() if self.__cgr_marker
                                               else self.__dragos_marker.getcount() if self.__dragos_marker else 1)]
        writers = [SDFwrite(x, mark_to_map=True) for x in workfiles]
        tX, tD = [], []
        for s_numb, s in enumerate(data):
            if isinstance(s, list):
                for d in s:
                    tmp = [s_numb]
                    for w, x in zip(writers, d):
                        w.writedata(x[1])
                        tmp.append(x[0])
                    doubles.append(tmp)
            else:
                writers[0].write(s)
                doubles.append(s_numb)

        for n, f in enumerate(workfiles):
            p = Popen([EED], stdout=PIPE, stdin=PIPE)
            res = p.communicate(input=f.getvalue().encode())[0].decode()

            if p.returncode != 0:
                return False

            X, D = self.__parseeedoutput(res)
            tX.append(X)
            tD.append(D)

        res = dict(X=pd.concat(tX, axis=1, keys=range(len(tX))), AD=reduce(operator.and_, tD))
        if self.__cgr_marker or self.__dragos_marker:
            i = pd.MultiIndex.from_tuples(doubles, names=['structure'] + ['c.%d' % x for x in range(len(workfiles))])
        else:
            i = pd.Index(doubles, name='structure')

        res['Y'] = self.get_property(structures) * pd.Series(1, index=i)
        res['X'].index = res['AD'].index = i
        return res

    @staticmethod
    def __parseeedoutput(output):
        vector, ad = [], []
        for frag in StringIO(output):
            _, *x = frag.split()
            ad.append(True)
            tmp = {}  # X vector
            for i in x:
                k, v = i.split(':')
                tmp[int(k)] = float(v.replace(',', '.'))
            if len(tmp) <= 2:
                ad[-1] = False
            vector.append(tmp)

        x = pd.DataFrame(vector, columns=range(1, 705)).fillna(0)
        x.columns = ['eed.%d' % x for x in range(1, 705)]
        return x, pd.Series(ad)
