# -*- coding: utf-8 -*-
#
# Copyright 2015 Ramil Nugmanov <stsouko@live.ru>
# This file is part of PREDICTOR.
#
# PREDICTOR is free software; you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
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
import os
from math import sqrt
import numpy as np
import xmltodict as x2d
import time
from modelset import register_model, chemaxpost
import subprocess as sp


class Model():
    def __init__(self):
        self.modelpath = os.path.join(os.path.dirname(__file__), 'ansamble')
        self.Nlim = .8 # NLIM fraction
        self.TOL = 1
        self.models = self.getmodelset()
        self.trustdesc = {5: 'Optimal', 4: 'Good', 3: 'Medium', 2: 'Low'}

    def getdesc(self):
        desc = 'sn2 reactions of azides salts with halogen alkanes constants prediction'
        return desc

    def getname(self):
        name = 'sn2 halogens-azides'
        return name

    def is_reation(self):
        return 0

    def gethashes(self):
        hashlist = []
        return hashlist

    def getresult(self, chemical):
        TRUST = 5
        nin = ''
        data = {"structure": chemical['structure'], "parameters": "mol"}
        structure = chemaxpost('calculate/stringMolExport', data)

        if structure:
            result = []
            INlist = []
            ALLlist = []
            fixtime = int(time.time())
            temp_file_mol = os.path.join(self.modelpath, "structure-%d.mol" % fixtime)
            temp_file_res = os.path.join(self.modelpath, "structure-%d.res" % fixtime)
            with open(temp_file_mol, 'w') as f:
                f.write(structure)

            for model in self.models:
                try:
                    sp.call([model['exec'], temp_file_mol, temp_file_res])
                except:
                    print('YOU DO IT WRONG')
                else:
                    with open(temp_file_res, 'r') as f:
                        P, AD = f.readline().strip().split(' ')

                    if AD == 1:
                        INlist.append(P)

                    ALLlist.append(P)

            INarr = np.array(INlist)
            ALLarr = np.array(ALLlist)

            PavgIN = INarr.mean()
            PavgALL = ALLarr.mean()

            if len(INlist) > self.Nlim * len(ALLlist):
                sigma = sqrt((INarr**2).mean() - PavgIN**2)
                Pavg = PavgIN
            else:
                sigma = sqrt((ALLarr**2).mean() - PavgALL**2)
                Pavg = PavgALL
                nin = 'not enought models include structure in their applicability domain<br>'
                TRUST -= 1

            result.append(dict(type='text', attrib='predicted value ± sigma', value='%.2f ± %.2f' % (Pavg, sigma)))

            if len(INlist) > 0 and PavgIN - PavgALL < self.TOL:
                TRUST -= int(sigma/self.TOL)
            else:
                nin += 'prediction within and outside applicability domain differ more then TOL'
                TRUST -= 1

            result.append(dict(type='text', attrib='prediction trust', value=self.trustdesc.get(TRUST, 'None')))
            if nin:
                result.append(dict(type='text', attrib='reason', value=nin))
            os.remove(temp_file_mol)
            os.remove(temp_file_res)

            return result
        else:
            return False

    def getmodelset(self):
        conffile = os.path.join(self.modelpath, "conf.xml")
        conf = x2d.parse(open(conffile, 'r').read())
        return {x: y for x in conf['models']}
"""
result - list with data returned by model.
result show on page in same order. [1,2,3] show as:
1
2
3

result items is dicts.
dicts consist next keys:
'value' - text field. use for show result
'attrib' - text field. use as header
'type' - may be 'text', 'link' or 'structure'.
  'text' type show 'value' in page as text
  'link' type show as clickable link
  'structure' type show as picture. it may be in formats recognized by marvin

example:
                result = [dict(type='text', attrib='this string show as description', value='this string show as value'),
                          dict(type='link', attrib='this string show as description for link', value='download/1427724576.zip'),
                          dict(type='structure', attrib='this string show as description for structure image', value='<?xml version="1.0" encoding="UTF-8"?><cml xmlns="http://www.chemaxon.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.chemaxon.com/marvin/help/formats/schema/mrvSchema_14_7_14.xsd" version="ChemAxon file format v14.7.14, generated by v14.7.28.0"><MDocument>  <MChemicalStruct>    <molecule molID="m1">      <atomArray atomID="a1 a2 a3 a4 a5 a6 a7 a8 a9 a10 a11 a12 a13 a14 a15 a16 a17 a18" elementType="C C C C C C C C C C C C C C C C C C" x2="-1.278749942779541 -2.612389942779541 -3.946183942779541 -3.946183942779541 -2.612389942779541 -1.278749942779541 0.05489005722045892 1.388684057220459 1.388684057220459 0.05489005722045892 2.722324057220459 1.388684057220459 0.05489005722045892 2.722324057220459 4.055964057220459 5.389758057220459 5.389758057220459 4.055964057220459" y2="0.8937500011920929 1.663750001192093 0.8937500011920929 -0.6462499988079071 -1.4162499988079071 -0.6462499988079071 -1.4162499988079071 -0.6462499988079071 0.8937500011920929 1.663750001192093 3.203750001192093 3.973750001192093 3.203750001192093 1.663750001192093 0.8937500011920929 1.663750001192093 3.203750001192093 3.973750001192093"/>      <bondArray>        <bond id="b1" atomRefs2="a1 a2" order="2"/>        <bond id="b2" atomRefs2="a1 a6" order="1"/>        <bond id="b3" atomRefs2="a1 a10" order="1"/>        <bond id="b4" atomRefs2="a2 a3" order="1"/>        <bond id="b5" atomRefs2="a3 a4" order="2"/>        <bond id="b6" atomRefs2="a4 a5" order="1"/>        <bond id="b7" atomRefs2="a5 a6" order="2"/>        <bond id="b8" atomRefs2="a6 a7" order="1"/>        <bond id="b9" atomRefs2="a7 a8" order="2"/>        <bond id="b10" atomRefs2="a8 a9" order="1"/>        <bond id="b11" atomRefs2="a9 a10" order="2"/>        <bond id="b12" atomRefs2="a11 a12" order="1"/>        <bond id="b13" atomRefs2="a12 a13" order="2"/>        <bond id="b14" atomRefs2="a15 a16" order="1"/>        <bond id="b15" atomRefs2="a16 a17" order="2"/>        <bond id="b16" atomRefs2="a17 a18" order="1"/>        <bond id="b17" atomRefs2="a11 a14" order="1"/>        <bond id="b18" atomRefs2="a11 a18" order="2"/>        <bond id="b19" atomRefs2="a14 a15" order="2"/>        <bond id="b20" atomRefs2="a9 a14" order="1"/>        <bond id="b21" atomRefs2="a13 a10" order="1"/>      </bondArray>    </molecule>  </MChemicalStruct></MDocument></cml>')]
"""
model = Model()
register_model(model.getname(), model)