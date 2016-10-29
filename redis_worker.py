from app.config import StructureStatus
from modelset import ModelSet


def run(structures=None, model=None, structuresfile=None):
    models = ModelSet()
    mod = models.load_model(model['name'])
    results = mod.get_results(structures)
    for s in structures: # todo: implement
        s['models'] = [model]
        s['status'] = StructureStatus.CLEAR
    return structures


def combiner(x):
    """ simple ad_hoc for saving task metadata and unused structures.
    :param x: Task data structure
    """
    return x
