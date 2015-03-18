# -*- coding: utf-8 -*-
import pkgutil
import sched
import time
import modelset as models

__author__ = 'stsouko'


def run():
    # Import tracker handlers on fly.
    # It is an .egg-friendly alternative to os.listdir() walking.
    #for mloader, pname, ispkg in pkgutil.iter_modules(models.__path__):
    #    __import__('modelset.%s' % pname)
    print(models.MODELS)


class PeriodicScheduler(object):
    def __init__(self):
        self.scheduler = sched.scheduler(time.time, time.sleep)

    def setup(self, interval, action, actionargs=()):
        action(*actionargs)
        self.scheduler.enter(interval, 1, self.setup, (interval, action, actionargs))

    def run(self):
        self.scheduler.run()


def main():
    #periodic_scheduler = PeriodicScheduler()
    #periodic_scheduler.setup(INTERVAL, run)
    #periodic_scheduler.run()
    run()

if __name__ == '__main__':
    main()