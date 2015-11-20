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


class Fragmentor(object):
    def __init__(self, workpath='/tmp', version='last', s_option=None, fragment_type=3, min_length=2, max_length=10,
                 colorname=None, marked_atom=None, cgr_dynbonds=None, xml=None, doallways=False,
                 useformalcharge=False, atompairs=False, fragmentstrict=False, getatomfragment=False,
                 overwrite=True, header=None, extention=None):

        self.__extention = extention
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

    def getfragments(self, inputfile=None, outputfile=None, inputstring=None, **kwargs):
        parser = False
        timestamp = int(time.time())
        if inputstring:
            inputfile = os.path.join(self.__workpath, "structure-%d.sdf" % timestamp)
            with open(inputfile, 'w') as f:
                f.write(inputstring)
        elif not inputfile:
            return False

        if not outputfile:
            outputfile = os.path.join(self.__workpath, "structure-%d" % timestamp)
            parser = True

        execparams = [self.__fragmentor, '-i', os.path.join(self.__workpath, inputfile),
                      '-o', os.path.join(self.__workpath, outputfile)]
        execparams.extend(self.__execparams)

        sp.call(execparams, cwd=self.__workpath)
        if os.path.exists(outputfile + '.svm'):

            extention = []
            if solvent is not None:
                if temperature is not None:
                    for i, j in zip(solvent, temperature):
                        tmp = {x + 1: y for x, y in self.__extention.get(i).items()}
                        tmp.update({1: j})
                        extention.append(tmp)
                else:
                    extention = [self.__extention.get(x) for x in solvent]
            elif temperature is not None:
                extention = [{1: x} for x in temperature]
            if extention:
                self.__extendvector(outputfile + '.svm', extention)

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
        with open(descfile) as f:
            for vector, ext in zip(f.readlines(), extention):
                svector = vector.split()
                last, lval = svector[-1].split(':')
                if lval == '0':
                    svector.pop(-1)
                tmp.append(' '.join(svector + ['%s:%s' % (x + int(last), y) for x, y in ext.items()]))

        with open(descfile, 'w') as f:
            f.write('\n'.join(tmp))
