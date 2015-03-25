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
        parser.add_argument('result', type=str)
        parser.add_argument('params', type=str, action='append')
        parser.add_argument('values', type=str, action='append')
        self.parser = parser

    def post(self, reaction_id):
        args = self.parser.parse_args()
        print(args)

api.add_resource(ModelListAPI, '/reaction_result/<reaction_id>')

if __name__ == '__main__':
    app.run(debug=True)