import shutil
import tempfile
from modelset import ModelSet


def cycle2(structures):  # AD-HOC for preparing model for uploaded files processing.
    saved = []
    for s in structures:
        saved.append(s)
        yield s.copy()

    while True:
        for s in saved:
            yield s.copy()


def run(structures=None, model=None):
    workpath = tempfile.mkdtemp(dir='/tmp')
    mod = ModelSet().load_model(model['name'], workpath=workpath)

    results = mod.get_results(structures) if mod is not None else None

    if results:
        out = []
        for s, r in zip(cycle2(structures), results):
            _res = dict(results=r.pop('results'))
            _res.update(model)
            r['models'] = [_res]
            s.update(r)
            out.append(s)
        structures = out
    else:
        # if failed return empty models list
        for s in structures:
            s['models'] = []

    shutil.rmtree(workpath)
    return structures


def combiner(structures):
    """ simple ad_hoc for saving task metadata and unused structures.
    :param structures: Task structures
    """
    for s in structures:
        s['models'] = []
    return structures
