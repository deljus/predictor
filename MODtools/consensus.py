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


class ConsensusDragos(object):
    def __init__(self):
        self.__TRUST = 5
        self.__INlist = []
        self.__ALLlist = []

    def cumulate(self, P, AD):
        if AD:
            self.__INlist.append(P)
        self.__ALLlist.append(P)

    def report(self):
        if not self.__ALLlist:
            return False  # break if all models fails to predict

        reason = []
        result = []
        INarr = np.array(self.__INlist)
        ALLarr = np.array(self.__ALLlist)

        PavgALL = ALLarr.mean()
        sigmaALL = sqrt(ALLarr.var())

        if self.__INlist:
            PavgIN = INarr.mean()
            sigmaIN = sqrt(INarr.var())
            pavgdiff = abs(PavgIN - PavgALL)
            if pavgdiff > self.TOL:
                reason.append(self.__errors['diff'] % pavgdiff)
                self.__TRUST -= 1
        else:
            self.__TRUST -= 1
            reason.append(self.__errors['zad'])

        proportion = len(self.__INlist) / len(self.__ALLlist)
        if proportion > self.Nlim:
            sigma = sigmaIN
            Pavg = PavgIN
        else:
            sigma = sigmaALL
            Pavg = PavgALL
            self.__TRUST -= 1
            if self.__INlist:
                reason.append(self.__errors['lad'] % ceil(100 * proportion))

        proportion = sigma / self.TOL
        if proportion > 1:
            self.__TRUST -= int(proportion)
            reason.append(self.__errors['stp'] % (proportion * 100 - 100))

        result.append(dict(type='text',
                           attrib='predicted value ± sigma%s' % (' (%s)' % self.units if self.units else ''),
                           value='%.2f ± %.2f' % (Pavg, sigma)))
        result.append(dict(type='text', attrib='prediction trust', value=self.__trustdesc.get(self.__TRUST, 'None')))
        if reason:
            result.append(dict(type='text', attrib='reason', value='. '.join(reason)))

        return result

    __errors = dict(lad='Too few (less than %d %%) local models have applicability domains covering this structure',
                    diff='The other local models disagree (prediction value difference = %.2f) with the prediction of '
                         'the minority containing structure inside their applicability domain',
                    stp='Individual models failed to reach unanimity - prediction variance exceeds %d %% '
                        'of the property range width',
                    zad='None of the local models have applicability domains covering this structure')

    __trustdesc = {5: 'Optimal', 4: 'Good', 3: 'Medium', 2: 'Low'}
