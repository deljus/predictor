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
    mod = ModelSet().load_model(model['name'])
    if mod is not None:
        results = mod.get_results(structures)

        if results:
            out = []
            for s, r in zip(cycle2(structures), results):
                _res = dict(results=r.pop('results'))
                _res.update(model)
                r['models'] = [_res]
                s.update(r)
                out.append(s)
            return out

    # if failed return empty models list
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
