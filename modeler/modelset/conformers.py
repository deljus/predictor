# -*- coding: utf-8 -*-
import subprocess
import time

__author__ = 'stsouko'
from modelset import register_model


class Model():
    def __init__(self):
        print("started")

    def getdesc(self):
        desc = 'model generate sorted conformers'
        return desc

    def getname(self):
        name = 'best conformers'
        return name

    def is_reation(self):
        return 0

    def gethashes(self):
        hashlist = []
        return hashlist

    def getresult(self, chemical):
        # chemical['structure']
        with open('/home/server/conf/temp.mrv', 'w') as f:
            f.write(chemical['structure'])
        #todo: эта штука может затереть предыдущие файлы
        file_name = int(time.time())
        subprocess.call("ssh timur@130.79.41.90 -t /home/timur/server/start", shell=True)
        subprocess.call("mv /home/server/conf/result.zip /home/server/download/%d.zip" % file_name, shell=True)

        result = [dict(type='link', attrib='file with archive', value='download/%d.zip' % file_name)]
        return result


model = Model()
register_model(model.getname(), model)
