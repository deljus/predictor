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
import copy
import os
import subprocess as sp
import time


class Fragmentor(object):
    def __init__(self, workpath, version, s_option=None, fragment_type=3, min_length=2, max_length=10,
                 colorname=None, marked_atom=None, cgr_dynbonds=None, xml=None, doallways=None,
                 useformalcharge=None, atompairs=None, fragmentstrict=None, getatomfragment=None,
                 overwrite=True, header=None):
        self.__header = None
        self.__workpath = workpath
        self.__fragmentor = os.path.join(os.path.dirname(__file__), 'Fragmentor%s' % version)
        tmp = ['-f', 'SVM']
        if s_option: tmp.extend(['-s', s_option])
        if header:
            self.__header = os.path.join(workpath, header)
            tmp.extend(['-s', self.__header])

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

    def getfragments(self, inputfile=None, outputfile=None, inputstring=None, extention=None):
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
            if extention:
                self.__extendvector(outputfile + '.svm', extention)
            if parser:
                return self.__parser(outputfile)
            return True
        return False

    def __parser(self, file):
        prop, vector = [], []
        with open(file + '.svm') as f:
            line = f.readline().split()
            prop.append(float(vector[0]))
            vector.append({int(x.split(':')[0]): float(x.split(':')[1]) for x in line[1:]})

        ad = os.path.getsize(self.__header) != os.path.getsize(file + '.hdr') if self.__header else True
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
