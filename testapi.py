# -*- coding: utf-8 -*-
from functools import wraps
from flask.ext.restful import Resource, abort, reqparse, Api
from flask import Flask

app = Flask(__name__)
api = Api(app)


def authenticate(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not getattr(func.__self__, 'auth', False):
            return func(*args, **kwargs)

        acct = True  # custom account lookup function

        if acct:
            return func(*args, **kwargs)

        abort(401)
    return wrapper


class Resource(Resource):
    method_decorators = [authenticate]

parser = reqparse.RequestParser()
parser.add_argument('inp', type=str)


class ParserAPI(Resource):
    auth = True
    def get(self):
        self.auth = True
        args = parser.parse_args()
        return args['inp'], 201

api.add_resource(ParserAPI, '/')

if __name__ == "__main__":
    app.run()