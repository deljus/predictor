import pkgutil
import modelset as models
__author__ = 'stsouko'
MODELS = {}


def register_model(name, model):
    MODELS[name] = model

for mloader, pname, ispkg in pkgutil.iter_modules(models.__path__):
    print(pname)
    __import__('modelset.%s' % pname)