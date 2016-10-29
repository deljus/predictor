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
from enum import Enum
from datetime import datetime
from pony.orm import Database, sql_debug, PrimaryKey, Required, Optional, Set
from pony.orm.dbapiprovider import IntConverter


if DEBUG:
    db = Database("sqlite", "database.sqlite", create_db=True)
    sql_debug(True)
else:
    db = Database('postgres', user=DB_USER, password=DB_PASS, host=DB_HOST, database=DB_NAME)


class EnumConverter(IntConverter):
    def validate(self, val):
        if not isinstance(val, Enum):
            raise ValueError('Must be an Enum.  Got {}'.format(type(val)))
        return val

    def py2sql(self, val):
        return val.value

    def sql2py(self, val):
        return self.py_type(val)

db.provider.converter_classes.append((Enum, EnumConverter))


class Users(db.Entity):
    id = PrimaryKey(int, auto=True)
    email = Required(str, unique=True)
    password = Required(str)
    active = Required(bool, default=True)
    token = Required(str)
    tasks = Set("Tasks")

    def __init__(self, email, password):
        self.email = email
        self.password = self.hash_password(password)
        self.token = self.gen_token(email, password)

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
    user = Optional(Users)
    structures = Set("Structures")
    date = Required(datetime, default=datetime.now())
    task_type = Required(TaskType, default=TaskType.MODELING)


class Structures(db.Entity):
    id = PrimaryKey(int, auto=True)
    structure = Optional(str)
    structure_type = Required(StructureType, default=StructureType.MOLECULE)
    temperature = Optional(float)
    pressure = Optional(float)
    additives = Set("Additivesets")

    task = Required(Tasks)
    status = Required(StructureStatus, default=StructureStatus.CLEAR)
    results = Set("Results")
    models = Set("Models")


class Results(db.Entity):
    id = PrimaryKey(int, auto=True)
    structure = Required(Structures)
    model = Required("Models")

    attrib = Required(str)
    value = Required(str)
    type = Required(ResultType)


class Models(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str, unique=True)
    description = Optional(str)
    example = Optional(str)
    destinations = Set("Destinations")
    model_type = Required(ModelType, default=ModelType.MOLECULE_MODELING)

    structures = Set(Structures)
    results = Set(Results)


class Destinations(db.Entity):
    id = PrimaryKey(int, auto=True)
    model = Required(Models)
    host = Required(str)
    port = Required(int, default=6379)
    password = Optional(str)
    name = Required(str)


class Additives(db.Entity):
    id = PrimaryKey(int, auto=True)
    structure = Optional(str)
    name = Required(str, unique=True)
    additive_type = Required(AdditiveType, default=AdditiveType.SOLVENT)
    additivesets = Set("Additivesets")


class Additivesets(db.Entity):
    amount = Required(float, default=1)
    additive = Required(Additives)
    structure = Required(Structures)


db.generate_mapping(create_tables=True)
