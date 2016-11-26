import shutil
import tempfile
from modelset import ModelSet


def cycle2(structures):
    while True:
        yield structures[0].copy()


def run(structures=None, model=None):
    workpath = tempfile.mkdtemp(dir='/tmp')
    mod = ModelSet().load_model(model['name'], workpath=workpath)

    results = mod.get_results(structures) if mod is not None else None

    if results:
        out = []
        # AD-HOC for preparing model for uploaded files processing.
        tmp = cycle2(structures) if isinstance(structures[0]['data'], dict) else structures

        for s, r in zip(tmp, results):
            _res = dict(results=r.pop('results', []))
            _res.update(model)
            r['models'] = [_res]
            s.update(r)
            out.append(s)
        structures = out
    else:
        # AD-HOC for preparing model for uploaded files processing.
        if isinstance(structures[0]['data'], dict):
            raise Exception('Preparer model failed on file processing')

        # if failed return empty models list
        for s in structures:
            s['models'] = []

    shutil.rmtree(workpath)
    return structures
