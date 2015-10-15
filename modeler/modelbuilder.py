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
from mutils.fragmentor import Fragmentor
from mutils.svrmodel import Model
import argparse
import pickle


def main():
    rawopts = argparse.ArgumentParser(description="Model Builder",
                                      epilog="Copyright 2015 Ramil Nugmanov <stsouko@live.ru>")
    rawopts.add_argument("--input", "-i", type=str, default='input.sdf', help="input SDF ")
    rawopts.add_argument("--output", "-o", type=str, default=None, help="output SVM|HDR")
    rawopts.add_argument("--header", "-d", type=str, default=None, help="input header")
    rawopts.add_argument("--model", "-m", type=str, default=None, help="output model")
    rawopts.add_argument("--extention", "-e", type=str, default=None, help="extention data file")
    rawopts.add_argument("--fragments", "-f", type=str, default='input.param', help="fragmentor keys file")
    rawopts.add_argument("--svm", "-s", type=str, default='input.cfg', help="SVM params")
    rawopts.add_argument("--nfold", "-n", type=int, default=5, help="number of folds")
    rawopts.add_argument("--repetition", "-r", type=int, default=1, help="number of repetitions")
    rawopts.add_argument("--normalize", "-N", action='store_true', help="normalize vector to range(0, 1)")
    options = vars(rawopts.parse_args())

    with open(options['fragments']) as f:
        tmp = {}
        for x in f:
            key, value = x.split('=')
            tmp[key] = value.strip()
        options['fragments'] = tmp

    if options['extention']:
        tmp = {}
        ext = []
        heat = []
        with open(options['extention']) as f:
            for i in f:
                key, *values = i.split()
                tmp[key] = {int(x.split(':')[0]): float(x.split(':')[1]) for x in values}

        with open(options['input']) as f:
            lines = f.readlines()
            for i, j in enumerate(lines, start=1):
                if '>  <solvent>' in j:
                    ext.append(lines[i].strip())
                if '>  <temperature>' in j:
                    heat.append(float(lines[i].strip()))

        options['extention'] = (tmp, ext, heat)

    frag = Fragmentor(workpath='.', header=options['header'], extention=options['extention'][0], **options['fragments'])
    res = frag.getfragments(inputfile=options['input'], outputfile=options['output'], solvent=options['extention'][1],
                            temperature=options['extention'][2])

    if res and not options['output']:
        with open(options['svm']) as f:
            opts = f.readline().split()
            repl = {'-t': ('kernel', lambda x: {'0': 'linear', '1': 'poly', '2': 'rbf', '3': 'sigmoid'}[x]),
                    '-c': ('C', lambda x: float(x)),
                    '-e': ('epsilon', lambda x: float(x)),
                    '-g': ('gamma', lambda x: float(x)),
                    '-r': ('coef0', lambda x: float(x))}
            svm = {}
            for x, y in zip(opts[::2], opts[1::2]):
                z = repl.get(x)
                if z:
                    svm[z[0]] = z[1](y)

        model = Model(frag, svm, res[1], res[0],
                      nfold=options['nfold'], repetitions=options['repetition'], normalize=options['normalize'])
        pickle.dump(model, open(options['model'], 'wb'))

if __name__ == '__main__':
    main()
