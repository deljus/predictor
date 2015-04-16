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
from math import sqrt, ceil
import numpy as np
import xmltodict as x2d


def getmodelset(conffile):
        conf = x2d.parse(open(conffile, 'r').read())['models']['model']
        if not isinstance(conf, list):
            conf = [conf]
        return {x['name']: [x['script']['exec_path']] + [y['name'] for y in x['script']['params']['param']] for x in
                conf}


class consensus_dragos():
    def __init__(self):
        self.TRUST = 5
        self.INlist = []
        self.ALLlist = []

    def cumulate(self, P, AD):
        if AD:
            self.INlist.append(P)
        self.ALLlist.append(P)

    def report(self):
        if not self.ALLlist:
            return False #break if all models fails to predict

        reason = []
        result = []
        INarr = np.array(self.INlist)
        ALLarr = np.array(self.ALLlist)

        PavgALL = ALLarr.mean()
        sigmaALL = sqrt((ALLarr ** 2).mean() - PavgALL ** 2)

        if self.INlist:
            PavgIN = INarr.mean()
            sigmaIN = sqrt((INarr ** 2).mean() - PavgIN ** 2)
            pavgdiff = PavgIN - PavgALL
            if pavgdiff > self.TOL:
                reason.append(self.errors.get('diff', '%.2f') % pavgdiff)
                self.TRUST -= 1
        else:
            self.TRUST -= 1
            reason.append(self.errors.get('zad', ''))

        proportion = len(self.INlist) / len(self.ALLlist)
        if proportion > self.Nlim:
            sigma = sigmaIN
            Pavg = PavgIN
        else:
            sigma = sigmaALL
            Pavg = PavgALL
            self.TRUST -= 1
            if self.INlist:
                reason.append(self.errors.get('lad', '%d') % ceil(100 * proportion))

        proportion = sigma / self.TOL
        if proportion >= 1:
            self.TRUST -= int(proportion)
            reason.append(self.errors.get('stp', '%d') % (proportion * 100 - 100))

        result.append(dict(type='text', attrib='predicted value ± sigma', value='%.2f ± %.2f' % (Pavg, sigma)))
        result.append(dict(type='text', attrib='prediction trust', value=self.trustdesc.get(self.TRUST, 'None')))
        if reason:
            result.append(dict(type='text', attrib='reason', value='<br>'.join(reason)))

        return result

    errors = dict(lad='Too few (less than %d %%) local models have applicability domains covering this structure',
                  diff='The other local models disagree (prediction value difference = %.2f) with the prediction of the'
                       ' minority containing structure inside their applicability domain',
                  stp='Individual models failed to reach unanimity - prediction variance exceeds %d %%'
                      'of the property range width',
                  zad='None of the local models have applicability domains covering this structure')

    trustdesc = {5: 'Optimal', 4: 'Good', 3: 'Medium', 2: 'Low'}
