# -*- coding: utf-8 -*-
#
# Copyright 2015 Ramil Nugmanov <stsouko@live.ru>
# This file is part of PREDICTOR.
#
# PREDICTOR is free software; you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
import threading
import time
import schedule
from utils.config import INTERVAL, THREAD_LIMIT, REQ_MAPPING
from utils.utils import gettask, getfiletask
from utils.mappercore import Mapper


TASKS = []


def run():
    TASKS.extend(gettask(REQ_MAPPING))
    ft = getfiletask()
    if ft:
        TASKS.append(ft)

    if TASKS and threading.active_count() < THREAD_LIMIT:
        i = TASKS.pop(0)
        print("map task", i)
        taskthread = Mapper().parsefile if "file" in i else Mapper().mapper
        t = threading.Thread(target=taskthread, args=([i]))
        t.start()


def main():
    schedule.every(INTERVAL).seconds.do(run)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    main()
