from flask import render_template
from app import app
from flask.ext.restful import reqparse, abort, Api, Resource
import time
import hashlib

@app.route('/')
@app.route('/index')
def index():
    user = { 'nickname': 'Miguel' } # выдуманный пользователь
    return render_template("index.html",
        title = 'Home',
        user = user)

api = Api(app)
REACTIONS = {
    '111': {'task_id': '111',
            'reaction_status': 0,
            'reaction_data': '<cml></cml>',
            'reaction_condition': {'temperature': '290C'},
            'solvent': ' вода', 'model': ' SN2'},
    '222': {'task_id': '111',
            'reaction_status': 0,
            'reaction_data': '<cml></cml>',
            'reaction_condition': {'temperature': '290C'},
            'solvent': ' вода', 'model': ' SN1'},
    '333': {'task_id': '111',
            'reaction_status': 0,
            'reaction_data': '<cml></cml>',
            'reaction_condition': {'temperature': '290C'},
            'solvent': ' вода', 'model': ' SN3'}
}

TASKS = {
    '111': {'task_status': 0}
}


TASK_CREATED    = 0
REQ_MAPPING     = 1
MAPPING_DONE    = 2
REQ_MODELLING   = 3
MODELLING_DONE  = 4

def abort_if_task_doesnt_exist(task_id):
   if task_id not in TASKS:
       print (' задача не найдена '+task_id)
       abort(404, message="Task {} doesn't exist".format(task_id))


def get_new_id():
    x = "qwertyuiopasdfghjklzxcvbnm1234567890"+str(time.time())
    return hashlib.md5( x.encode("utf-8") ).hexdigest()


def find_reaction(reaction_id):
    return REACTIONS.get(reaction_id)


parser = reqparse.RequestParser()
parser.add_argument('reaction_data', type=str)
parser.add_argument('temperature', type=str)
parser.add_argument('solvent', type=str)
parser.add_argument('task_status', type=int)
parser.add_argument('reaction_condition', type=str)


class ReactionListAPI(Resource):
    def get(self):
        return REACTIONS


class ReactionAPI(Resource):
    def get(self, reaction_id):
        #abort_if_todo_doesnt_exist(reaction_id)
        return REACTIONS[reaction_id]

    def post(self):
        args = parser.parse_args()
        reaction_id = get_new_id()
        REACTIONS[reaction_id] = {'reaction_data': args['reaction_data'], 'reaction_condition': args['reaction_condition'], 'temperature': args['temperature'] }
        return reaction_id, 201

    # def delete(self, reaction_id):
    #     abort_if_todo_doesnt_exist(reaction_id)
    #     del REACTIONS[reaction_id]
    #     return '', 204


def create_new_task():
    task_id = get_new_id()
    TASKS[task_id] = {'task_status': 0}
    return task_id


def find_task(task_id):
    return TASKS.get(task_id)


def update_task_status(task_id, task_status):
    task = TASKS.get(task_id)
    if task is not None:
        task['task_status'] = task_status


def insert_reaction(task_id, mol_data):
    reaction_id = get_new_id()
    REACTIONS[reaction_id] = {'task_id':task_id, 'reaction_data': mol_data}


def find_task_reactions(task_id):
    print('task_id='+task_id)
    reactions = []
    for key, val in REACTIONS.items():
        if val['task_id'] == task_id:
            val['reaction_id'] = key
            reactions.append(val)
        else:
            print(key)
    print(str(len(reactions)))
    return reactions


class TaskListAPI(Resource):
    def get(self):
        return TASKS

    def post(self):
        task_id = create_new_task()
        args = parser.parse_args()
        insert_reaction(task_id, args['reaction_data'])
        return task_id


class TaskAPI (Resource):
    def get(self, task_id):
        return find_task(task_id)


    def post(self):
        task_id = create_new_task()
        args = parser.parse_args()
        insert_reaction(task_id, args['reaction_data'])
        return task_id


    def put(self,task_id):
        abort_if_task_doesnt_exist(task_id)
        args = parser.parse_args()
        task_status = args['task_status']
        print('task_id='+task_id)
        print('args[ task_status ]=' + str(task_status))
        update_task_status(task_id,task_status)
        return task_id


class TaskReactionsAPI (Resource):
    def get(self, task_id):
        return find_task_reactions(task_id)



##
## Actually setup the Api resource routing here
##
api.add_resource(ReactionListAPI, '/reactions')
api.add_resource(ReactionAPI, '/reaction/<reaction_id>')

api.add_resource(TaskAPI, '/task/<task_id>')
api.add_resource(TaskListAPI, '/tasks')

api.add_resource(TaskReactionsAPI, '/task_reactions/<task_id>')
