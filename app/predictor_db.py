# -*- coding: utf-8 -*-
class PredictorDataBase:

    def insert_task(self, id):
        '''
        функция добавляет в таблицу новую задачу
        :param id: ID добавляемой задачи
        :return:
        '''
        pass


    def get_task(self, id):
        '''
        функция возвращает задачу по заданному ID
        :param id: ID добавляемой задачи
        :return: status
        '''
        pass


    def update_task_status(self, id, status):
        '''
        функция обновляет статус у задачи
        :param id: ID задачи (str)
        :param status: устанавливаемое значение (int)
        :return: True|False
        '''
        pass


    def insert_reaction(self, task_id, reaction_id, reaction_structure, solvent, temperature):
        '''
        функция добавляет в таблицу новую реакцию с заданными параметрами
        :param task_id(str): ID задачи
        :param reaction_id(str): ID реакции
        :param reaction_structure(str): Структура реакции в формате mrv
        :param solvent(str): Растворитель
        :param temperature(str): Температура
        :param conditions(dict): Дополнительные условаия (nah)
        :return:
        '''
        pass


    def get_reaction_structure(self, id):
        '''
        функция возвращает структуру реакции по заданному ID
        :param id(str): ID реакции
        :return: структура реакции
        '''
        pass


    def get_reactions_by_task(self, task_id):
        '''
        функция возвращает список реакций для заданной задачи
        :param task_id: ID задачи
        :return: список реакций (ID, solvent, temperature, models)
        '''
        pass


    def get_results_by_task(self, task_id):
        '''
        функция возвращает результаты моделирования для заданной заданной задачи
        :param task_id(str): ID задачи
        :return: Результаты моделирования
        '''
        return [{'id': '1', 'value1': '123', 'value2': '3321', 'value3': '3989384'},
                {'id': '2', 'value1':'444', 'value2': '33', 'value3': '33343'}]


    def get_solvents(self):
        '''
        функция возвращает список растворителей из базы
        :return: список растворителей
        '''
        return [{'id': '1', 'name': 'вода'},
                {'id': '2', 'name': 'Бензол'}]
        pass

    def get_models(self):
        '''
        функция возвращает список доступных моделей
        :return: список моделей
        '''

        return ['SN1','SN2','E1','E2']

    def update_task_reactions(self):
        '''
        функция записывает в базу ввведенные пользователем данные для моделирования
        :return:
        '''








