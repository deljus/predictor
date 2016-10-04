from app.config import StructureStatus


def run(structures=None, model=None, structuresfile=None):
    for s in structures:
        s['models'] = [model]
        s['is_reaction'] = False
        s['status'] = StructureStatus.CLEAR
    return structures


def combiner(x):
    """ simple ad_hoc for saving task metadata and unused structures.
    :param x: Task data structure
    """
    return x
