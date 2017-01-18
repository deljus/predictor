#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-
#
#  Copyright 2017 Ramil Nugmanov <stsouko@live.ru>
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
from datetime import datetime
from pony.orm import PrimaryKey, Required, Optional, Set
from ..config import TaskType, ResultType, StructureType, StructureStatus


def load_tables(db, schema):
    class Task(db.Entity):
        _table_ = (schema, 'task')
        id = PrimaryKey(int, auto=True)
        date = Required(datetime, default=datetime.utcnow())
        structures = Set('Structure')
        task_type = Required(int)
        user = Required('User')
    
        def __init__(self, **kwargs):
            _type = kwargs.pop('type', TaskType.MODELING).value
            super(Task, self).__init__(task_type=_type, **kwargs)
    
        @property
        def type(self):
            return TaskType(self.task_type)

    class Structure(db.Entity):
        _table_ = (schema, 'structure')
        id = PrimaryKey(int, auto=True)
        additives = Set('Additiveset')
        pressure = Optional(float)
        results = Set('Result')
        structure = Required(str)
        structure_type = Required(int)
        structure_status = Required(int)
        task = Required('Task')
        temperature = Optional(float)
    
        def __init__(self, **kwargs):
            _type = kwargs.pop('type', StructureType.MOLECULE).value
            status = kwargs.pop('status', StructureStatus.CLEAR).value
            super(Structure, self).__init__(structure_type=_type, structure_status=status, **kwargs)
    
        @property
        def type(self):
            return StructureType(self.structure_type)
    
        @property
        def status(self):
            return StructureStatus(self.structure_status)

    class Result(db.Entity):
        _table_ = (schema, 'result')
        id = PrimaryKey(int, auto=True)
        key = Required(str)
        model = Required('Model')
        result_type = Required(int)
        structure = Required('Structure')
        value = Required(str)
    
        def __init__(self, **kwargs):
            _type = kwargs.pop('type', ResultType.TEXT).value
            _model = db.Model[kwargs.pop('model')]
            super(Result, self).__init__(result_type=_type, model=_model, **kwargs)
    
        @property
        def type(self):
            return ResultType(self.result_type)
    
    class Additiveset(db.Entity):
        _table_ = (schema, 'additives')
        id = PrimaryKey(int, auto=True)
        additive = Required('Additive')
        amount = Required(float, default=1)
        structure = Required('Structure')

    return Task, Structure, Result, Additiveset
