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
#       url:  "http://server:port//task_reactions/<task_id>"
#       method: GET
#       parameters: {}
#
# обновление реакции
#       url:  "http://server:port///reaction/<reaction_id>"
#       method: PUT
#       parameters: {'temperature': <TEMPERATURE>, 'solvent': <SOLVENT>}


# Пример
url="http://localhost:8080/tasks"
parameters = {"task_status": 2}
headers = {'content-type': 'application/json'}
resultRaw = requests.get(url, data=json.dumps(parameters), headers=headers)
result=resultRaw.text

