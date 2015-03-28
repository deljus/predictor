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
        parser.add_argument('file.path', type=str)
        self.parser = parser

    def post(self):
        print(self.parser.parse_args())
        print(request.form)

api.add_resource(ModelListAPI, '/upload')

if __name__ == '__main__':
    app.run(debug=True)