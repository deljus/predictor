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
import sys
import time
from datetime import datetime
import bcrypt
import hashlib
import os
from app.config import DEBUG, DB_PASS, DB_HOST, DB_NAME, DB_USER
from pony.orm import Database, sql_debug, db_session, PrimaryKey, Required, Optional, Set, select, commit


if DEBUG:
    db = Database("sqlite", "database.sqlite", create_db=True)
    sql_debug(True)
else:
    db = Database('postgres', user=DB_USER, password=DB_PASS, host=DB_HOST, database=DB_NAME)


class Users(db.Entity):
    id = PrimaryKey(int, auto=True)
    email = Required(str, unique=True)
    password = Required(str)
    active = Required(bool, default=True)
    token = Required(str)
    tasks = Set("Tasks")

    @staticmethod
    def hash_password(password):
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(self, password):
        return bcrypt.hashpw(password.encode(), self.password.encode()) == self.password.encode()

    @staticmethod
    def gen_token(password):
        return hashlib.md5(password.encode()).hexdigest()


class Tasks(db.Entity):
    id = PrimaryKey(int, auto=True)
    user = Optional(Users)
    structures = Set("Structures")
    date = Required(datetime, default=datetime.now())
    task_type = Required(int, default=0)  # 0 - common models, 1,2,... - searches


class Structures(db.Entity):
    id = PrimaryKey(int, auto=True)
    structure = Optional(str)
    isreaction = Required(bool, default=False)
    temperature = Optional(float)
    pressure = Optional(float)
    additives = Set("Additiveset")

    task = Required(Tasks)
    status = Required(int, default=0)
    results = Set("Results")
    models = Set("Models")


class Results(db.Entity):
    id = PrimaryKey(int, auto=True)
    structure = Required(Structures)
    model = Required("Models")

    attrib = Required(str)
    value = Required(str)
    type = Required(int)


class Models(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str)
    description = Required(str)
    example = Optional(str)
    destinations = Set("Destinations")
    model_type = Required(int, default=0)  # нечетные для реакций, четные для молекул и 0 для подготовки.

    structures = Set(Structures)
    results = Set(Results)


class Destinations(db.Entity):
    id = PrimaryKey(int, auto=True)
    model = Required(Models)
    host = Required(str)
    port = Optional(int)
    password = Optional(str)


class Additives(db.Entity):
    id = PrimaryKey(int, auto=True)
    structure = Optional(str)
    name = Required(str, unique=True)
    type = Required(int, default=0)
    additivesets = Set("Additiveset")


class Additiveset(db.Entity):
    amount = Required(float, default=1)
    additive = Required(Additives)
    structure = Required(Structures)


db.generate_mapping(create_tables=True)




class PredictorDataBase:






    @db_session
    def update_reaction_result(self, reaction_id, model_id, param, value, ptype):
        '''
        функция записывает в базу данные моделирования
        :return:
        '''
        reaction = Chemicals.get(id=reaction_id)
        model = Models.get(id=model_id)
        if reaction and model:
            Results(chemical=reaction, model=model, attrib=param, value=value, type=ptype)

    @db_session
    def get_solvents(self):
        '''
        функция возвращает список растворителей из базы
        :return: список растворителей
        '''
        query = select((x.id, x.name) for x in Solvents)
        return [{'id': x, 'name': y} for x, y in query]

    @db_session
    def get_models(self, model_hash=None):
        '''
        функция возвращает список доступных моделей
        :return: список моделей
        '''
        try:
            if model_hash:
                models = select(x.models for x in AppDomains if x.hash == model_hash)
                models = [(x.id, x.name, x.is_reaction, x.description, x.example) for x in models]
            else:
                models = select((x.id, x.name, x.is_reaction, x.description, x.example) for x in Models)

            return [{'id': x, 'name': y, 'is_reaction': z, 'description': w, 'example': q} for x, y, z, w, q in models]
        except:
            print('get_models->', sys.exc_info()[0])
        return None

    @db_session
    def get_model(self, model_id):
        '''
        функция возвращает список доступных моделей
        :return: список моделей
        '''
        model = Models.get(id=model_id)
        if model:
            return dict(id=model.id, name=model.name, description=model.description, example=model.example)
        else:
            return None

    @staticmethod
    def insert_model(name, desc, example, is_reaction, reaction_hashes):
        with db_session:
            model = Models(name=name, description=desc, example=example, is_reaction=is_reaction)
            if reaction_hashes:
                for x in reaction_hashes:
                    reaction_hash = AppDomains.get(hash=x)
                    if not reaction_hash:
                        reaction_hash = AppDomains(hash=x)
                    model.app_domains.add(reaction_hash)

        return model.id

    @db_session
    def delete_model(self, model_id):
        model = Models.get(id=model_id)
        if model:
            reaction_hashes = model.app_domains.copy()
            model.delete()

            for x in reaction_hashes:
                if not x.models:
                    x.delete()

        return True
