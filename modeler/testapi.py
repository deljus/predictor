import json
import sys

__author__ = 'stsouko'
from flask.ext.restful import Api, Resource
from flask import Flask
from flask import request
from flask.ext.restful import reqparse


app = Flask(__name__)
api = Api(app)

class ModelListAPI(Resource):
    def __init__(self):
        parser = reqparse.RequestParser()
        parser.add_argument('result', type=lambda x: json.loads(x))
        parser.add_argument('modelid', type=int)
        self.parser = parser

    def post(self):
        print(self.parser.parse_args())

api.add_resource(ModelListAPI, '/upload')

if __name__ == '__main__':
    app.run(debug=True)