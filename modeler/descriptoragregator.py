# -*- coding: utf-8 -*-
#
# Copyright 2016 Ramil Nugmanov <stsouko@live.ru>
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
from collections import defaultdict
from functools import reduce
import operator
import pandas as pd
import numpy as np
from CGRtools.SDFread import SDFread
from CGRtools.RDFread import RDFread


class Descriptorchain(object):
    def __init__(self, *args):
        self.__generators = args

    def setworkpath(self, workpath):
        for i in self.__generators:
            if hasattr(i, 'setworkpath'):
                i.setworkpath(workpath)

    def get(self, structures, **kwargs):
        """
        :param structures: opened structure file or stringio
        :param kwargs: generators specific arguments
        :return: dict(X=DataFrame, AD=Series)
        >>> from modeler.fragmentor import Fragmentor
        >>> f = Fragmentor(workpath='tests',version='last', s_option='shift', fragment_type=1, min_length=2, max_length=11, \
        marked_atom=3, marker_rules='tests/test.xml')
        >>> d = Descriptorsdict({'CdId': None, 'Formula': {'key': pd.Series(['H3O4P']), \
        'value': pd.DataFrame([{'form':2.}])}})
        >>> r = Descriptorchain(f, d).get(open('tests/test.sdf'), parsesdf=True)
        >>> print(r) # надо дописать
        """
        res = defaultdict(list)

        def merge_wrap(x, y):
            return pd.merge(x, y, how='outer', left_index=True, right_index=True)

        for gen in self.__generators:
            for k, v in gen.get(structures, **kwargs).items():
                res[k].append(v)
            structures.seek(0)

        res['X'] = reduce(merge_wrap, res['X'])
        res['AD'] = reduce(operator.mul, sorted(res['AD'], key=lambda x: len(x.index), reverse=True))
        res['Y'] = sorted(res['Y'], key=lambda x: len(x.index), reverse=True)[0]
        return dict(res)


class Propertyextractor(object):
    def __init__(self, name, isreaction=False):
        self.__isreaction = isreaction
        self.__name = name

    def get_property(self, structures):
        reader = RDFread(structures) if self.__isreaction else SDFread(structures)
        data = []
        for i in reader.readdata():
            meta = i['meta'] if self.__isreaction else i.graph['meta']
            prop = meta.get(self.__name)
            data.append(float(prop) if prop else np.NaN)
        res = pd.Series(data, name='Property')
        res.index = pd.Index(res.index, name='structure')
        return res


class Descriptorsdict(object):
    def __init__(self, data, isreaction=False):
        self.__isreaction = isreaction
        self.__extention = data
        self.__extheader = self.__prepareextheader(data)

    @staticmethod
    def setworkpath(_):
        return True

    @staticmethod
    def __prepareextheader(data):
        """
        :param data: dict
        :return: list of strings. descriptors header
         >>> sorted(Descriptorsdict({})._Descriptorsdict__prepareextheader({'1': None, '2': \
         {'value': pd.DataFrame([{'3':1}])}}))
         ['1', '3']
        """
        tmp = []
        for i, j in data.items():
            if j:
                tmp.extend(j['value'].columns)
            else:
                tmp.append(i)
        return tmp

    def __parsefile(self, structures):
        """
        parse SDF or RDF on known keys-headers.
        :param structures: opened file
        :return: DataFrame of descriptors. indexes is the numbers of structures in file, columns - names of descriptors
         >>> s = Descriptorsdict({'CdId': None, 'Formula': {'key': pd.Series(['H3O4P']), \
         'value': pd.DataFrame([{'3':1.}])}})._Descriptorsdict__parsefile(open('tests/test_1.sdf'))
         >>> r = pd.DataFrame([{'3': 1., 'CdId': 1.0}], index=pd.Index([0], name='structure'), columns=s.columns)
         >>> s.equals(r)
         True
        """
        extblock = []
        reader = RDFread(structures) if self.__isreaction else SDFread(structures)
        for i in reader.readdata():
            meta = i['meta'] if self.__isreaction else i.graph['meta']
            tmp = []
            for key, value in meta.items():
                if key in self.__extention:
                    data = self.__extention[key]['value'].loc[self.__extention[key]['key'] == value] if \
                        self.__extention[key] else pd.DataFrame([{key: float(value)}])
                    if not data.empty:
                        data.index = [0]
                        tmp.append(data)
            extblock.append(pd.concat(tmp, axis=1) if tmp else pd.DataFrame([{}]))
        res = pd.DataFrame(pd.concat(extblock), columns=self.__extheader)
        res.index = pd.Index(range(len(res.index)), name='structure')
        return res

    def __parseadditions0(self, **kwargs):
        extblock = []
        for i, j in kwargs.items():
            if i in self.__extention:
                for n, k in enumerate(j) if isinstance(j, list) else j.items():
                    data = self.__extention[i]['value'].loc[self.__extention[i]['key'] == k] if \
                        self.__extention[i] else pd.DataFrame([{i: k}])
                    if not data.empty:
                        data.index = [0]
                        if len(extblock) > n:
                            extblock[n].append(data)
                        else:
                            extblock.extend([[] for _ in range(n - len(extblock))] + [[data]])
        res = pd.DataFrame(pd.concat([pd.concat(x, axis=1) if x else pd.DataFrame([{}]) for x in extblock]),
                           columns=self.__extheader)
        res.index = pd.Index(range(len(res.index)), name='structure')
        return res

    def __parseadditions1(self, **kwargs):
        tmp = []
        for i, j in kwargs.items():
            if i in self.__extention:
                data = self.__extention[i]['value'].loc[self.__extention[i]['key'] == j] if \
                       self.__extention[i] else pd.DataFrame([{i: j}])
                if not data.empty:
                    data.index = [0]
                    tmp.append(data)
        return pd.DataFrame(pd.concat(tmp, axis=1) if tmp else pd.DataFrame([{}]), columns=self.__extheader,
                            index=pd.Index([0], name='structure'))

    def get(self, structures=None, **kwargs):
        if kwargs.get('parsesdf'):
            extblock = self.__parsefile(structures)

        elif all(isinstance(x, list) or isinstance(x, dict) for y, x in kwargs.items() if y in self.__extention):
            extblock = self.__parseadditions0(**kwargs)

        elif not any(isinstance(x, list) or isinstance(x, dict) for y, x in kwargs.items() if
                     y in self.__extention):
            extblock = self.__parseadditions1(**kwargs)

        else:
            print('WHAT DO YOU WANT? use correct extentions params')
            return False

        return dict(X=extblock, AD=-extblock.isnull().any(axis=1))

if __name__ == '__main__':
    import doctest
    doctest.testmod()
