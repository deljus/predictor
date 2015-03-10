# -*- coding: utf-8 -*-
from pony.orm import *
from hashlib import md5
import time

SALT = "bla-bla"


def id_gen(name):
    return md5(''.join([SALT, name, "%.6f" % time.time()])).hexdigest()


db = Database("sqlite", "database.sqlite", create_db=True)


class Users(db.Entity):
    id = PrimaryKey(int, auto=True)
    email = Required(str, 128, unique=True)
    uid = Required(str, 128)
    tasks = Set("Tasks")


class Tasks(db.Entity):
    id = PrimaryKey(int, auto=True)
    user = Optional(Users)
    tid = Required(str, 128)
    chemicals = Set("Chemicals")
    status = Required(int, default=0)


class Chemicals(db.Entity):
    id = PrimaryKey(int, auto=True)
    rid = Required(str, 128)
    status = Required(int, default=0)
    temperature = Optional(float)
    solvents = Set("Solventsets")
    task = Required(Tasks)
    structure = Required("Structures")
    results = Set("Results")
    models = Set("Models")


class Structures(db.Entity):
    id = PrimaryKey(int, auto=True)
    structure = Required(str)
    strID = Optional(str, unique=True)
    chemicals = Set(Chemicals)


class Results(db.Entity):
    id = PrimaryKey(int, auto=True)
    chemical = Required(Chemicals)
    attrib = Required(str)
    value = Required(float)
    model = Required("Models")


class Models(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(unicode)
    chemicals = Set(Chemicals)
    results = Set(Results)


class Solvents(db.Entity):
    id = PrimaryKey(int, auto=True)
    solID = Required(int, unique=True)
    name = Required(str, unique=True)
    solventsets = Set("Solventsets")


class Solventsets(db.Entity):
    id = PrimaryKey(int, auto=True)
    amount = Required(float)
    solvent = Required(Solvents)
    chemical = Required(Chemicals)


sql_debug(True)
db.generate_mapping(create_tables=True)


class PredictorDataBase:
    @db_session
    def insert_task(self, email=None):
        '''
        функция добавляет в таблицу новую задачу
        :param email: мыло если есть.
        :return:
        '''
        tid = id_gen("task")
        if email:
            user = Users.get(email=email)
            if not user:
                user = Users(email=email, uid=id_gen("user"))
        else:
            user = None

        Tasks(user=user, tid=tid)
        return tid

    @db_session
    def get_task_status(self, id):
        '''
        функция возвращает задачу по заданному ID
        :param id: ID добавляемой задачи
        :return: status
        '''
        t = Tasks.get(tid=id)
        if t:
            return t.status
        return None

    @db_session
    def update_task_status(self, id, status):
        '''
        функция обновляет статус у задачи
        :param id: ID задачи (str)
        :param status: устанавливаемое значение (int)
        :return: True|False
        '''
        t = Tasks.get(tid=id)
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
        :param reaction_id(str): ID реакции
        :param reaction_structure(str): Структура реакции в формате mrv
        :param solvent(str): Растворитель
        :param temperature(str): Температура
        :return: reaction id or False
        '''
        t = Tasks.get(tid=task_id)
        if t:
            cid = id_gen("reaction")
            structure = Structures(strID=structurekey, structure=reaction_structure)
            chem = Chemicals(task=t, rid=cid, structure=structure, temperature=temperature)
            if solvent:
                for k, v in solvent.items():
                    solv = Solvents.get(solID=k)
                    if solv:
                        Solventsets(amount=v, solvent=solv, chemical=chem)

            return cid
        else:
            return False

    @db_session
    def get_reaction_structure(self, id):
        '''
        функция возвращает структуру реакции по заданному ID
        :param id(str): ID реакции
        :return: структура реакции
        '''
        c = Chemicals.get(rid=id)
        if c:
            return c.structure.structure
        else:
            return None

    @db_session
    def update_reaction_structure(self, id, structure):
        '''
        функция возвращает структуру реакции по заданному ID
        :param id(str): ID реакции
        :param structure(str): структура реакции
        :return: true, false
        '''
        c = Chemicals.get(rid=id)
        if c:
            c.structure.structure = structure
            return True
        else:
            return False

    @db_session
    def update_reaction_conditions(self, reaction_id, temperature=None, solvent=None):
        '''
        функция записывает в базу ввведенные пользователем данные для моделирования
        :return:
        '''
        c = Chemicals.get(rid=reaction_id)
        if c:
            if temperature:
                c.temperature = temperature
            if solvent:
                for x in c.solvents:  # очистка старых растворителей.
                    x.delete()
                for k, v in solvent.items():  # новые данные по растворителям
                    solv = Solvents.get(solID=k)
                    if solv:
                        Solventsets(amount=v, solvent=solv, chemical=c)
            return True
        else:
            return False

    @db_session
    def get_reactions_by_task(self, task_id):
        '''
        функция возвращает список реакций для заданной задачи
        :param task_id: ID задачи
        :return: список реакций (ID, solvent, temperature, models)
        '''
        t = Tasks.get(tid=task_id)
        if t:
            return {x.rid: dict(temperature=x.temperature,
                                models={y.id: y.name for y in x.models},
                                solvents={y.solID: y.amount for y in x.solvents}) for x in t.chemicals}
        else:
            return None

    @db_session
    def get_results_by_task(self, task_id):
        '''
        функция возвращает результаты моделирования для заданной задачи
        :param task_id(str): ID задачи
        :return: Результаты моделирования
        '''
        t = Tasks.get(tid=task_id)
        if t:
            out = {}
            for x in t.chemicals:
                out[x.rid] = defaultdict(dict)
                for y in x.results:
                    out[x.rid][y.model.name][y.attrib] = y.value
            return out
        else:
            return None

    @db_session
    def get_solvents(self):
        '''
        функция возвращает список растворителей из базы
        :return: список растворителей
        '''
        return select({'id': x.sloID, 'name': x.name} for x in Solvents)[:]

    @db_session
    def get_models(self):
        '''
        функция возвращает список доступных моделей
        :return: список моделей
        '''
        return select({'id': x.id, 'name': x.name} for x in Models)[:]


