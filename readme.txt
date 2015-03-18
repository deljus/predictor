###         ЗАДАЧИ
#
#   запрос задач с заданным статусом
#       url:  "http://server:port/tasks"
#       method: GET
#       parameters: {'task_status':<STATUS>}
#
#   обновление статуса задачи
#       url:  "http://server:port/task_status/<task_id>"
#       method: PUT
#       parameters: {'task_status':<STATUS>}
#
#       РЕАКЦИИ
#
# получение списка реакция для данной задачи
#       url:  "http://server:port/task_reactions/<task_id>"
#       method: GET
#       parameters: {}
#
# обновление реакции
#       url:  "http://server:port/reaction/<reaction_id>"
#       method: PUT
#       parameters: {'temperature': <FLOAT,OPT>, 'solvent': <SOLVENT,OPT>, 'model':<STR,OPT>}
#!!! model передается в виде строки id моделей через зпт "1,2,3"

# обновление результатов моделирования
#       url:  "http://server:port/reaction_result/<reaction_id>"
#       method: PUT
#       parameters: {'model_id': <INT>, 'param': <STR>, 'value': <FLOAT>}

# обновление структуры   реакции
#       url:  "http://server:port/reaction_structure/<reaction_id>"
#       method: PUT
#       parameters: {'reaction_structure': <STR>}

# получение моделей
#       url:  "http://server:port/models"
#       method: GET
#       parameters: {'hash':'<STR,OPTION>'}






# Пример
url="http://localhost:8080/tasks"
parameters = {"task_status": 2}
headers = {'content-type': 'application/json'}
resultRaw = requests.get(url, data=json.dumps(parameters), headers=headers)
result=resultRaw.text

