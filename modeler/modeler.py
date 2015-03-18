# -*- coding: utf-8 -*-
import sched
import time

__author__ = 'stsouko'


def run():
    pass


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