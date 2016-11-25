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
import json
from .config import (DEBUG, DB_PASS, DB_HOST, DB_NAME, DB_USER, BlogPost, TaskType, ModelType, AdditiveType,
                     ResultType, StructureType, StructureStatus, UserRole)
from datetime import datetime
from pony.orm import Database, sql_debug, PrimaryKey, Required, Optional, Set, Json


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
    user_role = Required(int)
    tasks = Set("Tasks")
    token = Required(str)
    restore = Optional(str)

    name = Required(str)
    country = Required(str)
    job = Optional(str)
    town = Optional(str)
    status = Optional(str)
    posts = Set("Blog")

    def __init__(self, email, password, role=UserRole.COMMON, **kwargs):
        password = self.__hash_password(password)
        token = self.__gen_token(email, password)
        super(Users, self).__init__(email=email, password=password, token=token, user_role=role.value,
                                    **{x: y for x, y in kwargs.items() if y})

    @staticmethod
    def __hash_password(password):
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(self, password):
        return bcrypt.hashpw(password.encode(), self.password.encode()) == self.password.encode()

    def verify_restore(self, code):
        return self.restore == code

    def gen_restore(self):
        self.restore = self.__gen_token(self.email, str(datetime.utcnow()))[:8]

    def change_password(self, password):
        self.password = self.__hash_password(password)

    @staticmethod
    def __gen_token(email, password):
        return hashlib.md5((email + password).encode()).hexdigest()

    def change_token(self):
        self.token = self.__gen_token(self.email, str(datetime.utcnow()))

    @property
    def role(self):
        return UserRole(self.user_role)


class Tasks(db.Entity):
    id = PrimaryKey(int, auto=True)
    date = Required(datetime, default=datetime.utcnow())
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
        super(Models, self).__init__(model_type=_type, **{x: y for x, y in kwargs.items() if y})

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

    def __init__(self, **kwargs):
        super(Destinations, self).__init__(**{x: y for x, y in kwargs.items() if y})


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


class Blog(db.Entity):
    title = Required(str)
    slug = Optional(str, unique=True)
    body = Required(str)
    banner = Optional(str)
    date = Required(datetime, default=datetime.utcnow())
    special = Optional(Json)
    post_type = Required(int)
    attachment = Optional(str)
    author = Required(Users)

    children = Set("Blog")
    parent = Optional("Blog")

    def __init__(self, **kwargs):
        _type = kwargs.pop('type', BlogPost.COMMON).value
        super(Blog, self).__init__(post_type=_type, **{x: y for x, y in kwargs.items() if y})

    @property
    def type(self):
        return BlogPost(self.post_type)

    @property
    def special_field(self):
        return self.special and json.dumps(self.special)

    @property
    def parent_field(self):
        return self.parent and self.parent.id

db.generate_mapping(create_tables=True)
