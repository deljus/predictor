#Путь к директории, выделенной под хранение входных файлов
BASEDIR = '/home/sergey/verysecure'

#Импортируем служебные библиотеки
import argparse
import os
import json

#Импортируем только что установленные компоненты нашего сервиса
from flask import Flask
app = Flask(__name__)
from redis import Redis
from rq import Queue

#Импортируем функцию, реализующую наш вычислительный процесс, который будет выполняться асинхронно
#classify.py - модуль, поставляемый с библиотекой машинного обучения caffe
#Естественно, вместо него можно импортировать собственные разработки
from classify import main

#Подключаемся к базе данных Redis
q = Queue(connection=Redis(), default_timeout=3600)

#Реализуем первый вызов нашего API

@app.route('/process/<path:file_path>')
def process(file_path):
    full_path = os.path.join(BASEDIR, file_path)    #входной файл лежит в директории BASEDIR
    argv = {'input_file': full_path,
                'gpu': True}
    args = argparse.Namespace(**argv)
    r = q.enqueue_call(main, args=(args,), result_ttl=86400)
    return r.id

#В порядке обмена опытом: ограничим 4-мя цифрами после запятой вещественные числа,
#при сериализации в JSON из массива numpy
def decimal_default(obj):
    if isinstance(obj, float32):
        return round(float(obj), 4)
    else:
        raise TypeError()

#Реализуем второй вызов нашего API

@app.route('/result/<id>')
def result(id):
    try:
        job = q.fetch_job(id)
        if job.is_finished:
            return json.dumps(job.result, ensure_ascii=False, default=decimal_default)
        else:
            return 'Not ready', 202
    except:
        return "Not found", 404

if __name__ == '__main__':
    app.run()
    #app.run(debug=False, host='0.0.0.0')