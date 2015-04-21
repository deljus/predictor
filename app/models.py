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
from pony.orm import *
from collections import defaultdict

import time
import os
import sys

#db = Database("sqlite", "database.sqlite", create_db=True)
db = Database('postgres', user='postgres', password='nginxpony', host='localhost', database='predictor')


class Users(db.Entity):
    id = PrimaryKey(int, auto=True)
    email = Required(str, 128, unique=True)
    tasks = Set("Tasks")


class Tasks(db.Entity):
    id = PrimaryKey(int, auto=True)
    user = Optional(Users)
    chemicals = Set("Chemicals")
    status = Required(int, default=0)
    create_date = Required(int)


class Chemicals(db.Entity):
    id = PrimaryKey(int, auto=True)
    status = Required(int, default=0)
    temperature = Optional(float)
    solvents = Set("Solventsets")
    task = Required(Tasks)
    structure = Required("Structures")
    results = Set("Results")
    models = Set("Models")


class Structures(db.Entity):
    id = PrimaryKey(int, auto=True)
    key = Optional(str)
    structure = Required(str)
    chemicals = Set(Chemicals)


class Results(db.Entity):
    id = PrimaryKey(int, auto=True)
    chemical = Required(Chemicals)
    attrib = Required(str)
    value = Required(str)
    type = Required(int)
    model = Required("Models")


class AppDomains(db.Entity):
    id = PrimaryKey(int, auto=True)
    hash = Required(str)
    models = Set("Models")


class Models(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str)
    description = Required(str)
    chemicals = Set(Chemicals)
    results = Set(Results)
    is_reaction = Required(bool, default=False)
    app_domains = Set("AppDomains")


class Solvents(db.Entity):
    id = PrimaryKey(int, auto=True)
    smiles = Optional(str)
    name = Required(str, unique=True)
    solventsets = Set("Solventsets")


class Solventsets(db.Entity):
    amount = Required(float, default=1)
    solvent = Required(Solvents)
    chemical = Required(Chemicals)


#sql_debug(True)
db.generate_mapping(create_tables=True)


class PredictorDataBase:
    @db_session
    def get_tasks(self, status=None):
        if status:
            tasks = select(x for x in Tasks if x.status == status)
        else:
            tasks = select(x for x in Tasks)    # удалить в продакшене

        arr = []
        for t in tasks:
            arr.append(dict(id=t.id,
                            status=t.status))
        return arr




    @db_session
    def insert_task(self, email=None):
        '''
        функция добавляет в таблицу новую задачу
        :param email: мыло если есть.
        :return:
        '''
        if email:
            user = Users.get(email=email)
            if not user:
                user = Users(email=email)
        else:
            user = None

        task = Tasks(user=user, create_date=int(time.time()))
        commit()
        return task.id

    @db_session
    def get_task_status(self, task_id):
        '''
        функция возвращает задачу по заданному ID
        :param task_id: ID добавляемой задачи
        :return: status
        '''
        t = Tasks.get(id=task_id)
        if t:
            return t.status
        return None

    @db_session
    def update_task_status(self, task_id, status):
        '''
        функция обновляет статус у задачи
        :param task_id: ID задачи (str)
        :param status: устанавливаемое значение (int)
        :return: True|False
        '''
        t = Tasks.get(id=task_id)
        if t:
            t.status = status
            return True
        else:
            return False

    @db_session
    def insert_reaction(self, task_id, reaction_structure, solvent=None, temperature=None, structurekey=None):
        '''
        функция добавляет в таблицу новую реакцию с заданными параметрами
        :param task_id(str): ID задачи
        :param reaction_structure(str): Структура реакции в формате mrv
        :param solvent(str): Растворитель
        :param temperature(str): Температура
        :return: reaction id or False
        '''
        print('insert_reaction->task_id='+str(task_id))
        t = Tasks.get(id=task_id)
        if t:
            structure = Structures(structure=reaction_structure)
            commit()
            chem = Chemicals(task=t, structure=structure, temperature=temperature)
            commit()
            if solvent:
                for k, v in solvent.items():
                    db_solvent = Solvents.get(id=k)
                    if db_solvent:
                        Solventsets(amount=v, solvent=db_solvent, chemical=chem)

            return chem.id
        else:
            print('TASK NOT FOUND!!!')
            return False

    @db_session
    def get_reaction_structure(self, reaction_id):
        '''
        функция возвращает структуру реакции по заданному ID
        :param id(str): ID реакции
        :return: структура реакции
        '''
        c = Chemicals.get(id=reaction_id)
        if c:
            return c.structure.structure
        else:
            return None

    @db_session
    def get_reaction(self, reaction_id):
        '''
        функция возвращает структуру реакции по заданному ID
        :param id(str): ID реакции
        :return: поля реакции
        '''
        c = Chemicals.get(id=reaction_id)
        if c:
            return dict(structure=c.structure.structure,
                        temperature=c.temperature,
                        models={y.id: y.name for y in c.models},
                        solvents=[dict(id=y.solvent.id, name=y.solvent.name, amount=y.amount) for y in c.solvents])
        else:
            return None

    @db_session
    def get_reactions(self):
        '''
        функция возвращает структуру реакции по заданному ID
        :param id(str): ID реакции
        :return: поля реакции
        '''
        arr = []
        for r in select(x for x in Chemicals):
            arr.append(dict(reaction_id=r.id,
                            task_id=r.task.id,
                            structure=r.structure.structure,
                            temperature=r.temperature,
                            models={m.id: m.name for m in r.models},
                            solvents={s.solvent.id: s.amount for s in r.solvents}))
        return arr


    @db_session
    def update_reaction_structure(self, reaction_id, structure, status=None):
        '''
        функция возвращает структуру реакции по заданному ID
        :param id(str): ID реакции
        :param structure(str): структура реакции
        :return: true, false
        '''
        c = Chemicals.get(id=reaction_id)
        if c:
            c.structure.structure = structure
            if status:
                c.status = status
            return True
        else:
            return False

    @db_session
    def update_reaction_conditions(self, reaction_id, temperature=None, solvent=None, models=None):
        '''
        функция записывает в базу ввведенные пользователем данные для моделирования
        :return:
        '''
        try:
            c = Chemicals.get(id=reaction_id)
            if c:
                if temperature:
                    c.temperature = temperature
                if solvent:
                    for x in c.solvents:  # очистка старых растворителей.
                        x.delete()
                    for s in solvent:  # новые данные по растворителям
                        db_solvent = Solvents.get(id=int(s))
                        if db_solvent:
                            Solventsets(solvent=db_solvent, chemical=c)
                if models:
                    c.models.clear()
                    for k in models:
                        m = Models.get(id=int(k))
                        if m:
                            c.models.add(m)
                            print(' добавили модель ')
                        else:
                            print(' не нашли модель '+str(k))
                return True
        except:
            print('update_reaction_conditions->', sys.exc_info()[0])
        return False


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
    def get_reactions_by_task(self, task_id):
        '''
        функция возвращает список реакций для заданной задачи
        :param task_id: ID задачи
        :return: список реакций (ID, solvent, temperature, models)
        '''
        arr = []
        t = Tasks.get(id=task_id)
        if t:
            for x in t.chemicals.order_by(Chemicals.id):
                arr.append(dict(reaction_id=x.id,
                                temperature=x.temperature,
                                models=[dict(id=x.id, name=x.name) for x in x.models],
                                solvents=[dict(id=x.id, name=x.name) for x in x.solvents.solvent],
                                errors={}))
            return arr
        else:
            return None


    @db_session
    def get_results_by_task(self, task_id):
        '''
        функция возвращает результаты моделирования для заданной задачи
        :param task_id(str): ID задачи
        :return: Результаты моделирования
        .order_by(Results.id)
        '''

        out = []
        t = Tasks.get(id=task_id)
        if t:
            for r in t.chemicals.order_by(Chemicals.id):
                result_arr = []
                for res in r.results.order_by(Results.id):
                    result_arr.append(dict(reaction_id=r.id,
                                           model=res.model.name,
                                           param=res.attrib,
                                           value=res.value,
                                           type=res.type))
                out.append(dict(reaction_id=r.id, results=result_arr))
        return out

    @db_session
    def get_reaction_results(self, reaction_id):
        '''
        функция возвращает результаты моделирования для заданной реакции
        :param reaction_id(str): ID реакции
        :return: Результаты моделирования
        '''

        result_arr = []
        r = Chemicals.get(id=reaction_id)
        if r:
            for res in r.results:
                result_arr.append(dict(reaction_id=r.id,
                                       model=res.model.name,
                                       param=res.attrib,
                                       value=res.value))
        return result_arr


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
                models = [(x.id, x.name, x.is_reaction, x.description) for x in models]
            else:
                models = select((x.id, x.name, x.is_reaction, x.description) for x in Models)

            return [{'id': x, 'name': y, 'is_reaction': z, 'description': w} for x, y, z, w in models]
        except:
            print('get_models->', sys.exc_info()[0])
        return None

    @db_session
    def get_model(self, model_id):
        '''
        функция возвращает список доступных моделей
        :return: список моделей
        '''
        return Models.get(id=model_id)

    @staticmethod
    def insert_model(name, desc, is_reaction, reaction_hashes):
        with db_session:
            model = Models(name=name, description=desc, is_reaction=is_reaction)
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

basedir = os.path.abspath(os.path.dirname(__file__))


# загрузим данные
@db_session
def import_solvents():
    file = open(os.path.join(os.path.dirname(__file__), "import_data/solvents.txt"), "r")
    for _line in file.readlines():
        try:
            solvent_name = _line.strip(' \t\n\r')
            s = Solvents.get(name=solvent_name)
            if not s:
                  Solvents(name=solvent_name)
        except:
            print('import_solvents->', sys.exc_info()[0])
            pass
    file.close()


import_solvents()



