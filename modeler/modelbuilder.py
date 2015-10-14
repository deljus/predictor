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
from modeler.mutils.fragmentor import Fragmentor
import argparse


class Model(object):
    def __init__(self, fragmentor):
        self.__fragmentor = fragmentor

    def fit(self,):
        pass

    def predict(self):
        pass


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
    options = vars(rawopts.parse_args())

    with open(options['fragments']) as f:
        tmp = {}
        for x in f:
            key, value = x.split('=')
            tmp[key] = value
        options['fragments'] = tmp

    if options['extention']:
        tmp = {}
        ext = []
        with open(options['extention']) as f:
            for i in f:
                key, *values = i.split()
                tmp[key] = {int(x.split(':')[0]): float(x.split(':')[1]) for x in values}

        with open(options['input']) as f:
            lines = f.readlines()
            for i, j in enumerate(lines, start=1):
                if '>  <solvent>' in j:
                    ext.append(tmp.get(lines[i].strip(), {}))

        options['extention'] = (tmp, ext)

    frag = Fragmentor(workpath='.', header=options['header'], **options['fragments'])
    res = frag.getfragments(options['input'], options['output'], extention=options['extention'][1])
    if res and not options['output']:
        with open(options['svm']) as f:
            f.readline()
        model = Model(frag)
        # todo: build model.


if __name__ == '__main__':
    main()
