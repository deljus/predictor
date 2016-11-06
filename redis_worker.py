from modelset import ModelSet


def cycle_file(structures):
    if len(structures) == 1:
        while True:
            yield structures[0].copy()
    else:
        for s in structures:
            yield s.copy()


def run(structures=None, model=None):
    mod = ModelSet().load_model(model['name'])
    if mod is not None:
        results = mod.get_results(structures)
        if results:
            for s, r in zip(cycle_file(structures), results):
                _res = dict(results=r.pop('results'))
                _res.update(model)
                r['models'] = [_res]
                s.update(r)
        else:  # if failed return empty models list
            for s in structures:
                s['models'] = []
    return structures


def combiner(structures):
    """ simple ad_hoc for saving task metadata and unused structures.
    :param structures: Task structures
    """
    for s in structures:
        s['models'] = []
    return structures
