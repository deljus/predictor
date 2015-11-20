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
    rawopts.add_argument("--extention", "-e", action='append', type=str, default=None,
                         help="extention data files. -e extname:filename [-e extname2:filename2]")
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

    extdata = {}
    if options['extention']:
        for e in options['extention']:
            record = None
            ext, *file = e.split(':')
            if file:
                maxkey = 0
                record = {}
                with open(file[0]) as f:
                    for i in f:
                        key, *values = i.split()
                        tmp = {}
                        for j in values:
                            dkey, dval = j.split(':')
                            dkey = int(dkey)
                            dval = float(dval)
                            if dkey > maxkey:
                                maxkey = dkey
                            tmp[dkey] = dval
                        record[key] = tmp
                    for i in record.values():
                        if maxkey not in i:
                            i[maxkey] = 0
            extdata[ext] = record

        extblock = []
        flag = False
        tmp = {}
        with open(options['input']) as f:
            for i in f:
                if '>  <' in i[:4]:
                    key = i.strip()[4:-1]
                    if key in extdata:
                        flag = key
                elif flag:
                    tmp[flag] = extdata[flag][i.strip()] if extdata[flag] else float(i.strip())
                    flag = False
                elif '$$$$' in i:
                    extblock.append(tmp)
        options['extention'] = extblock

    frag = Fragmentor(workpath='.', header=options['header'], extention=extdata, **options['fragments'])
    res = frag.getfragments(inputfile=options['input'], outputfile=options['output'],
                            solvent=options['extention'][1],
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
