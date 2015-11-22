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
import os
import subprocess as sp
import time
from itertools import chain, repeat


class Fragmentor(object):
    def __init__(self, workpath='/tmp', version='last', s_option=None, fragment_type=3, min_length=2, max_length=10,
                 colorname=None, marked_atom=None, cgr_dynbonds=None, xml=None, doallways=False,
                 useformalcharge=False, atompairs=False, fragmentstrict=False, getatomfragment=False,
                 overwrite=True, header=None, extention=None):

        self.__extention = extention
        self.__extshift = {}
        shift = 0
        for i in sorted(extention):
            self.__extshift[i] = shift
            if extention[i]:
                for j in extention[i].values():
                    shift += max(j)
                    break
            else:
                shift += 1

        self.__workpath = workpath
        self.__fragmentor = 'Fragmentor-%s' % version
        tmp = ['-f', 'SVM']
        if s_option: tmp.extend(['-s', s_option])
        if header:
            header = os.path.join(workpath, header)
            with open(header) as f:
                self.__headdump = f.read()
            self.__headsize = os.path.getsize(header)
            tmp.extend(['-h', header])
        else:
            self.__headsize = None

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

    def setpath(self, path):
        self.__workpath = path
        header = os.path.join(path, "model-%d.hdr" % int(time.time()))
        with open(header, 'w') as f:
            f.write(self.__headdump)
        self.__execparams[self.__execparams.index('-h') + 1] = header

    def parsesdf(self, inputfile):
        extblock = []
        flag = False
        tmp = {}
        with open(inputfile) as f:
            for i in f:
                if '>  <' in i[:4]:
                    key = i.strip()[4:-1]
                    if key in self.__extention:
                        flag = key
                elif flag:
                    tmp[flag] = self.__extention[flag][i.strip()] if self.__extention[flag] else {1: float(i.strip())}
                    flag = False
                elif '$$$$' in i:
                    extblock.append(tmp)
                    tmp = {}
        return extblock

    def get(self, inputfile=None, outputfile=None, inputstring=None, **kwargs):
        timestamp = int(time.time())
        if inputstring:
            inputfile = os.path.join(self.__workpath, "structure-%d.sdf" % timestamp)
            with open(inputfile, 'w') as f:
                f.write(inputstring)
        elif not inputfile:
            return False

        parser = False
        if not outputfile:
            outputfile = os.path.join(self.__workpath, "structure-%d" % timestamp)
            parser = True

        execparams = [self.__fragmentor, '-i', inputfile, '-o', outputfile]
        execparams.extend(self.__execparams)
        sp.call(execparams, cwd=self.__workpath)
        if os.path.exists(outputfile + '.svm'):
            if kwargs.get('parsesdf'):
                extblock = self.parsesdf(inputfile)
            elif all(isinstance(x, list) or isinstance(x, dict) for x in kwargs.values()):
                extblock = []
                for i, j in kwargs.items():
                    if isinstance(j, list):
                        for n, k in enumerate(j):
                            data = {i: self.__extention[i][k] if self.__extention[i] else {1: k}}
                            if len(extblock) > n:
                                extblock[n].update(data)
                            else:
                                extblock.append(data)
                    elif isinstance(j, dict):
                        for n, k in j.items():
                            data = {i: self.__extention[i][k] if self.__extention[i] else {1: k}}
                            if len(extblock) > n:
                                extblock[n].update(data)
                            else:
                                extblock.extend([{} for _ in range(n - len(extblock))] + [data])
            else:
                extblock = [{i: self.__extention[i][j] if self.__extention[i] else {1: j} for i, j in kwargs.items()}]

            if kwargs:
                self.__extendvector(outputfile + '.svm', extblock)

            if parser:
                return self.__parser(outputfile)
            return True
        return False

    def __parser(self, file):
        prop, vector = [], []
        with open(file + '.svm') as f:
            key, *values = f.readline().split()
            prop.append(float(key) if key.strip() != '?' else 0)
            vector.append({int(x.split(':')[0]): float(x.split(':')[1]) for x in values})
        ad = self.__headsize == os.path.getsize(file + '.hdr') if self.__headsize else True
        os.remove(file + '.svm')
        os.remove(file + '.hdr')
        return prop, vector, ad

    def __extendvector(self, descfile, extention):
        tmp = []
        last = False

        with open(descfile) as f:
            for vector, ext in zip(f.readlines(), chain(extention, repeat({}))):
                svector = vector.split()
                if not last:
                    last = svector[-1].split(':')[0]
                etmp = {int(last) + self.__extshift[k] + x: y for k, v in ext.items() for x, y in v.items()}

                tmp.append(' '.join(svector + ['%s:%s' % x for x in etmp.items()]))

        with open(descfile, 'w') as f:
            f.write('\n'.join(tmp))
