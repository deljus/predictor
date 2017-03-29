# -*- coding: utf-8 -*-
#
#  Copyright 2015-2017 Ramil Nugmanov <stsouko@live.ru>
#  Copyright 2015 Oleg Varlamov <ovarlamo@gmail.com>
#  This file is part of MWUI.
#
#  MWUI is free software; you can redistribute it and/or modify
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
from os.path import join, exists, expanduser, dirname


UPLOAD_PATH = 'upload'
MAX_UPLOAD_SIZE = 16 * 1024 * 1024
IMAGES_ROOT = join(UPLOAD_PATH, 'images')
RESIZE_URL = '/static/images'
PORTAL_NON_ROOT = ''
SECRET_KEY = 'development key'
YANDEX_METRIKA = None
DEBUG = False

LAB_NAME = 'Kazan Chemoinformatics and Molecular Modeling Laboratory'
LAB_SHORT = 'CIMM'
BLOG_POSTS_PER_PAGE = 10
SCOPUS_API_KEY = None
SCOPUS_TTL = 86400 * 7

SMPT_HOST = None
SMTP_PORT = None
SMTP_LOGIN = None
SMTP_PASSWORD = None
SMTP_MAIL = None

MAIL_INKEY = None
MAIL_SIGNER = None

DB_USER = None
DB_PASS = None
DB_HOST = None
DB_NAME = None
DB_MAIN = None
DB_PRED = None

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_PASSWORD = None
REDIS_TTL = 86400
REDIS_JOB_TIMEOUT = 3600
REDIS_MAIL = 'mail'


config_list = ('UPLOAD_PATH', 'PORTAL_NON_ROOT', 'SECRET_KEY', 'RESIZE_URL', 'MAX_UPLOAD_SIZE', 'IMAGES_ROOT',
               'DB_USER', 'DB_PASS', 'DB_HOST', 'DB_NAME', 'DB_MAIN', 'DB_PRED', 'YANDEX_METRIKA',
               'REDIS_HOST', 'REDIS_PORT', 'REDIS_PASSWORD', 'REDIS_TTL', 'REDIS_JOB_TIMEOUT', 'REDIS_MAIL',
               'LAB_NAME', 'LAB_SHORT', 'BLOG_POSTS_PER_PAGE', 'SCOPUS_API_KEY', 'SCOPUS_TTL',
               'SMPT_HOST', 'SMTP_PORT', 'SMTP_LOGIN', 'SMTP_PASSWORD', 'SMTP_MAIL', 'MAIL_INKEY', 'MAIL_SIGNER')

config_load_list = ['DEBUG']
config_load_list.extend(config_list)

config_dirs = [join(x, '.MWUI.ini') for x in (dirname(__file__), expanduser('~'), '/etc')]

if not any(exists(x) for x in config_dirs):
    with open(config_dirs[1], 'w') as f:
        f.write('\n'.join('%s = %s' % (x, y or '') for x, y in globals().items() if x in config_list))

with open(next(x for x in config_dirs if exists(x))) as f:
    for line in f:
        try:
            k, v = line.split('=')
            k = k.strip()
            v = v.strip()
            if k in config_load_list:
                globals()[k] = int(v) if v.isdigit() else v == 'True' if v in ('True', 'False', '') else v
        except:
            pass
