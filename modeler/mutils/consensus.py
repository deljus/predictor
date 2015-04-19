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
from math import sqrt, ceil
import numpy as np
import xmltodict as x2d


def getmodelset(conffile):
    conf = x2d.parse(open(conffile, 'r').read())['models']['model']
    if not isinstance(conf, list):
        conf = [conf]
    res = {}
    for x in conf:
        name = x['name']
        execlist = []
        scripts = x['scripts']['script']
        if not isinstance(scripts, list):
            scripts = [scripts]

        for y in scripts:
            params = y['params']['param']
            if not isinstance(params, list):
                params = [params]
            plist = []
            for z in params:
                plist.extend(z['name'].split() if z['type'] == 'list' else [z['name']])

            execlist.append([y['exec_path']] + plist)

        res[name] = execlist

    return res


class consensus_dragos():
    def __init__(self):
        self.__TRUST = 5
        self.__INlist = []
        self.__ALLlist = []
        super().__init__()

    def cumulate(self, P, AD):
        if AD:
            self.__INlist.append(P)
        self.__ALLlist.append(P)

    def report(self):
        if not self.__ALLlist:
            return False  #break if all models fails to predict

        reason = []
        result = []
        INarr = np.array(self.__INlist)
        ALLarr = np.array(self.__ALLlist)

        PavgALL = ALLarr.mean()
        sigmaALL = sqrt((ALLarr ** 2).mean() - PavgALL ** 2)

        if self.__INlist:
            PavgIN = INarr.mean()
            sigmaIN = sqrt((INarr ** 2).mean() - PavgIN ** 2)
            pavgdiff = PavgIN - PavgALL
            if pavgdiff > self.TOL:
                reason.append(self.__errors.get('diff', '%.2f') % pavgdiff)
                self.__TRUST -= 1
        else:
            self.__TRUST -= 1
            reason.append(self.__errors.get('zad', ''))

        proportion = len(self.__INlist) / len(self.__ALLlist)
        if proportion > self.Nlim:
            sigma = sigmaIN
            Pavg = PavgIN
        else:
            sigma = sigmaALL
            Pavg = PavgALL
            self.__TRUST -= 1
            if self.__INlist:
                reason.append(self.__errors.get('lad', '%d') % ceil(100 * proportion))

        proportion = sigma / self.TOL
        if proportion >= 1:
            self.__TRUST -= int(proportion)
            reason.append(self.__errors.get('stp', '%d') % (proportion * 100 - 100))

        result.append(dict(type='text', attrib='predicted value ± sigma', value='%.2f ± %.2f' % (Pavg, sigma)))
        result.append(dict(type='text', attrib='prediction trust', value=self.__trustdesc.get(self.__TRUST, 'None')))
        if reason:
            result.append(dict(type='text', attrib='reason', value='<br>'.join(reason)))

        return result

    __errors = dict(lad='Too few (less than %d %%) local models have applicability domains covering this structure',
                    diff='The other local models disagree (prediction value difference = %.2f) with the prediction of '
                         'the minority containing structure inside their applicability domain',
                    stp='Individual models failed to reach unanimity - prediction variance exceeds %d %%'
                        'of the property range width',
                    zad='None of the local models have applicability domains covering this structure')

    __trustdesc = {5: 'Optimal', 4: 'Good', 3: 'Medium', 2: 'Low'}


def bondbox(boxfile, descfile, dftype):
    box = {}
    AD = True
    with open(boxfile) as f:
        for line in f:
            fragment, *vrange = line.split()
            box[int(fragment)] = [int(x) for x in vrange]

    with open(descfile) as f:
        if dftype == 'svm':
            for fragment in f.read().split()[1:]:
                pos, count = fragment.split(':')
                m, M = box.get(int(pos), [0, 0])
                if not (m <= int(count) <= M):
                    AD = False
                    break
        elif dftype == 'csv':
            for pos, count in enumerate(f.read().split(';')[1:]):
                m, M = box.get(pos + 1, [0, 0])
                if not (m <= int(count) <= M):
                    AD = False
                    break
        else:
            AD = False
    return AD

