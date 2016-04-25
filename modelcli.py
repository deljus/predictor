#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-
#
#  Copyright 2016 Ramil Nugmanov <stsouko@live.ru>
#  This file is part of predictor.
#
#  predictor 
#  is free software; you can redistribute it and/or modify
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
import argparse
import modeler.modelset as models


def argparser():
    rawopts = argparse.ArgumentParser(description="Model CLI",
                                      epilog="Copyright 2016 Ramil Nugmanov <stsouko@live.ru>",
                                      formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    rawopts.add_argument("--workpath", "-w", type=str, default='.', help="work path")

    rawopts.add_argument("--input", "-i", type=str, default='input.sdf', help="input SDF or RDF")
    rawopts.add_argument("--output", "-o", type=str, default=None, help="output results")

    rawopts.add_argument("--model", "-m", type=str, default=None, help="model name")
    rawopts.add_argument("--list", "-l", action='store_true', help="list of models")

    return vars(rawopts.parse_args())


def getmodel(model_name, work_path):
    Model, init = models.MODELS[model_name]
    try:
        if init:
            model = Model(work_path, init)
        else:
            model = Model(work_path)
    except:
        model = None
    return model


def main():
    options = argparser()
    if options['list']:
        print(models.MODELS)
    else:
        getmodel(options['model'], options['workpath']).getresult(reaction)
    return

if __name__ == '__main__':
    main()
