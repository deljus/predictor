# -*- coding: utf-8 -*-
#
#  Copyright 2017 Ramil Nugmanov <stsouko@live.ru>
#  This file is part of MWUI.
#
#  MWUI is free software; you can redistribute it and/or modify
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
from pony.orm import db_session, select
from ..models import Additive, Model
from ..config import ModelType, BLOG_POSTS_PER_PAGE


def get_model(_type):
    with db_session:
        return next(dict(model=m.id, name=m.name, description=m.description, type=m.type,
                         destinations=[dict(host=x.host, port=x.port, password=x.password, name=x.name)
                                       for x in m.destinations])
                    for m in select(m for m in Model if m.model_type == _type.value))


def get_additives():
    with db_session:
        return {a.id: dict(additive=a.id, name=a.name, structure=a.structure, type=a.type)
                for a in Additive.select()}


def get_models_list(skip_prep=True, skip_destinations=False, skip_example=True):
    with db_session:
        res = {}
        for m in (select(m for m in Model if m.model_type in (ModelType.MOLECULE_MODELING.value,
                                                              ModelType.REACTION_MODELING.value))
                  if skip_prep else select(m for m in Model)):
            res[m.id] = dict(model=m.id, name=m.name, description=m.description, type=m.type)
            if not skip_destinations:
                res[m.id]['destinations'] = [dict(host=x.host, port=x.port, password=x.password, name=x.name)
                                             for x in m.destinations]
            if not skip_example:
                res[m.id]['example'] = m.example
        return res


def format_results(task, fetched_task, page=None):
    result, ended_at = fetched_task
    out = dict(task=task, date=ended_at.strftime("%Y-%m-%d %H:%M:%S"), status=result['status'].value,
               type=result['type'].value, user=result['user'], structures=[])

    for s in result['structures'][(page - 1) * BLOG_POSTS_PER_PAGE: page * BLOG_POSTS_PER_PAGE] \
            if page else result['structures']:
        out['structures'].append(dict(status=s['status'].value, type=s['type'].value, structure=s['structure'],
                                      data=s['data'], pressure=s['pressure'], temperature=s['temperature'],
                                      additives=[dict(additive=a['additive'], name=a['name'], structure=a['structure'],
                                                      type=a['type'].value, amount=a['amount'])
                                                 for a in s['additives']],
                                      models=[dict(type=m['type'].value, model=m['model'], name=m['name'],
                                                   results=[dict(type=r['type'].value, key=r['key'], value=r['value'])
                                                            for r in m.get('results', [])]) for m in s['models']]))
    return out
