# -*- coding: utf-8 -*-
import os

import sched
import threading
import time

from .config import INTERVAL, THREAD_LIMIT
from .utils import gettask, getfiletask, mapper, create_task_from_file


TASKS = []


def run():
    TASKS.extend(gettask())
    TASKS.append(getfiletask())

    while TASKS and threading.active_count() < THREAD_LIMIT:
        i = TASKS.pop(0)
        taskthread = create_task_from_file if "file" in i else mapper
        t = threading.Thread(target=taskthread, args=([i]))
        t.start()


class PeriodicScheduler(object):
    def __init__(self):
        self.scheduler = sched.scheduler(time.time, time.sleep)

    def setup(self, interval, action, actionargs=()):
        action(*actionargs)
        self.scheduler.enter(interval, 1, self.setup, (interval, action, actionargs))

    def run(self):
        self.scheduler.run()


def main():
    periodic_scheduler = PeriodicScheduler()
    periodic_scheduler.setup(INTERVAL, run)
    periodic_scheduler.run()

if __name__ == '__main__':
    main()