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
from modelset import ModelSet
from MODtools.utils import serverpost


class DefaultList(list):
    @staticmethod
    def __copy__(*_):
        return []


def main(redis):
    destinations = []
    for x in redis['name']:
        tmp = redis.copy()
        tmp['name'] = x
        destinations.append(tmp)

    models = ModelSet().get_models()

    report = []
    for m in models:
        print('found: ', m['name'])
        report.append(dict(type=m['type'].value, name=m['name'], example=m['example'], description=m['description'],
                           destinations=destinations))

    for m in serverpost('admin/models', report):
        print(m)

if __name__ == "__main__":
    rawopts = argparse.ArgumentParser(description="Model Register",
                                      epilog="Copyright 2016 Ramil Nugmanov <stsouko@live.ru>",
                                      formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    rawopts.add_argument("--host", type=str, default='localhost', help="Redis host")
    rawopts.add_argument("--port", "-p", type=int, default=6379, help="Redis port")
    rawopts.add_argument("--password", "-pw", type=str, default=None, help="Redis password")

    rawopts.add_argument("--name", "-n", action='append', type=str, default=DefaultList(['worker']),
                         help="available workers names. -n worker1 [-n worker2]")

    main(vars(rawopts.parse_args()))
