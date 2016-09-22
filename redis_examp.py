from datetime import datetime


def prep(x):
    x['date'] = datetime.now()
    return x

def file(x):
    return x

def st(x):
    return x