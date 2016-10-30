from modelset import ModelSet


def run(structures=None, model=None):
    mod = ModelSet().load_model(model['name'])
    if mod is not None:
        results = mod.get_results(structures)
        if results:
            for s in results:
                s['models'][0].update(model)
            return results

    # if failed
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
