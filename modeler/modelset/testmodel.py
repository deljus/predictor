# -*- coding: utf-8 -*-
import random

__author__ = 'stsouko'
from modelset import register_model


class Model():
    def __init__(self):
        print("started")

    def getdesc(self):
        desc = 'this model nothing do, but return something'
        return desc

    def getname(self):
        name = 'tesmodelname'
        return name

    def is_reation(self):
        return 1

    def gethashes(self):
        hashlist = ['1006099,1017020,4007079', '1006099,1007079,1017020']
        return hashlist

    def getresult(self, chemical):
        """do some operations on chemical"""

        result = [dict(type='text', attrib='fictparam', value=random.randrange(0, 100)),
                  dict(type='structure', attrib='fictstruct', value="c1ccc2c(c1)ccc1c3ccccc3ccc21")]
        return result


model = Model()
register_model(model.getname(), model)