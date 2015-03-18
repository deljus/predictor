# -*- coding: utf-8 -*-
__author__ = 'stsouko'
from modelset import register_model


class Testmodel():
    def __init__(self):
        print("started")

register_model('tesmodelname', Testmodel)