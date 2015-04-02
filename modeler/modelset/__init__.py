# -*- coding: utf-8 -*-
import pkgutil
import modelset as models
from utils.utils import chemaxpost

__author__ = 'stsouko'
MODELS = {}


def register_model(name, model):
    MODELS[name] = model


for mloader, pname, ispkg in pkgutil.iter_modules(models.__path__):
    __import__('modelset.%s' % pname)