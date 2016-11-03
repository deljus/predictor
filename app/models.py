# -*- coding: utf-8 -*-
#
# Copyright 2015 Ramil Nugmanov <stsouko@live.ru>
# Copyright 2015 Oleg Varlamov <ovarlamo@gmail.com>
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
import bcrypt
import hashlib
from app.config import (DEBUG, DB_PASS, DB_HOST, DB_NAME, DB_USER,
                        TaskType, ModelType, AdditiveType, ResultType, StructureType, StructureStatus)
from datetime import datetime
from pony.orm import Database, sql_debug, PrimaryKey, Required, Optional, Set


if DEBUG:
    db = Database("sqlite", "database.sqlite", create_db=True)
    sql_debug(True)
else:
    db = Database('postgres', user=DB_USER, password=DB_PASS, host=DB_HOST, database=DB_NAME)


class Users(db.Entity):
    id = PrimaryKey(int, auto=True)
    active = Required(bool, default=True)
    email = Required(str, unique=True)
    password = Required(str)
    tasks = Set("Tasks")
    token = Required(str)

    def __init__(self, email, password):
        password = self.hash_password(password)
        token = self.gen_token(email, password)
        super(Users, self).__init__(email=email, password=password, token=token)

    @staticmethod
    def hash_password(password):
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(self, password):
        return bcrypt.hashpw(password.encode(), self.password.encode()) == self.password.encode()

    @staticmethod
    def gen_token(email, password):
        return hashlib.md5((email + password).encode()).hexdigest()


class Tasks(db.Entity):
    id = PrimaryKey(int, auto=True)
    date = Required(datetime, default=datetime.now())
    structures = Set("Structures")
    task_type = Required(int)
    user = Optional(Users)

    def __init__(self, **kwargs):
        _type = kwargs.pop('type', TaskType.MODELING).value
        super(Tasks, self).__init__(task_type=_type, **kwargs)

    @property
    def type(self):
        return TaskType(self.task_type)


class Structures(db.Entity):
    id = PrimaryKey(int, auto=True)
    additives = Set("Additivesets")
    models = Set("Models")
    pressure = Optional(float)
    results = Set("Results")
    structure = Optional(str)
    structure_type = Required(int)
    structures_status = Required(int)
    task = Required(Tasks)
    temperature = Optional(float)

    def __init__(self, **kwargs):
        _type = kwargs.pop('type', StructureType.MOLECULE).value
        status = kwargs.pop('status', StructureStatus.CLEAR).value
        super(Structures, self).__init__(structure_type=_type, structures_status=status, **kwargs)

    @property
    def type(self):
        return StructureType(self.structure_type)

    @property
    def status(self):
        return StructureStatus(self.structures_status)


class Results(db.Entity):
    id = PrimaryKey(int, auto=True)
    key = Required(str)
    model = Required("Models")
    result_type = Required(int)
    structure = Required(Structures)
    value = Required(str)

    def __init__(self, **kwargs):
        _type = kwargs.pop('type', ResultType.TEXT).value
        super(Results, self).__init__(result_type=_type, **kwargs)

    @property
    def type(self):
        return ResultType(self.result_type)


class Models(db.Entity):
    id = PrimaryKey(int, auto=True)
    description = Optional(str)
    destinations = Set("Destinations")
    example = Optional(str)
    model_type = Required(int)
    name = Required(str, unique=True)
    results = Set(Results)
    structures = Set(Structures)

    def __init__(self, **kwargs):
        _type = kwargs.pop('type', ModelType.MOLECULE_MODELING).value
        super(Models, self).__init__(model_type=_type, **kwargs)

    @property
    def type(self):
        return ModelType(self.model_type)


class Destinations(db.Entity):
    id = PrimaryKey(int, auto=True)
    host = Required(str)
    model = Required(Models)
    name = Required(str)
    password = Optional(str)
    port = Required(int, default=6379)


class Additives(db.Entity):
    id = PrimaryKey(int, auto=True)
    additive_type = Required(int)
    additivesets = Set("Additivesets")
    name = Required(str, unique=True)
    structure = Optional(str)

    def __init__(self, **kwargs):
        _type = kwargs.pop('type', AdditiveType.SOLVENT).value
        super(Additives, self).__init__(additive_type=_type, **kwargs)

    @property
    def type(self):
        return AdditiveType(self.additive_type)


class Additivesets(db.Entity):
    additive = Required(Additives)
    amount = Required(float, default=1)
    structure = Required(Structures)


db.generate_mapping(create_tables=True)
