# -*- coding: utf-8 -*-
#
# Copyright 2015-2017 Ramil Nugmanov <stsouko@live.ru>
# Copyright 2015 Oleg Varlamov <ovarlamo@gmail.com>
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
from enum import Enum
from os import path


UPLOAD_PATH = 'upload'
MAX_UPLOAD_SIZE = 16 * 1024 * 1024
IMAGES_ROOT = path.join(UPLOAD_PATH, 'images')
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
DB_MAIN = None
DB_PRED = None
DB_DATA = None

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_PASSWORD = None
REDIS_TTL = 86400
REDIS_JOB_TIMEOUT = 3600
REDIS_MAIL = 'mail'

FP_SIZE = 12
FP_ACTIVE_BITS = 2
FRAGMENTOR_VERSION = 'last'
FRAGMENT_TYPE_CGR = 3
FRAGMENT_MIN_CGR = 2
FRAGMENT_MAX_CGR = 6
FRAGMENT_DYNBOND_CGR = 1
FRAGMENT_TYPE_MOL = 3
FRAGMENT_MIN_MOL = 2
FRAGMENT_MAX_MOL = 6


class StructureStatus(Enum):
    RAW = 0
    HAS_ERROR = 1
    CLEAR = 2


class StructureType(Enum):
    UNDEFINED = 0
    MOLECULE = 1
    REACTION = 2


class TaskStatus(Enum):
    NEW = 0
    PREPARING = 1
    PREPARED = 2
    MODELING = 3
    DONE = 4


class ModelType(Enum):
    PREPARER = 0
    MOLECULE_MODELING = 1
    REACTION_MODELING = 2
    MOLECULE_SIMILARITY = 3
    REACTION_SIMILARITY = 4
    MOLECULE_SUBSTRUCTURE = 5
    REACTION_SUBSTRUCTURE = 6

    @staticmethod
    def select(structure_type, task_type):
        return ModelType['%s_%s' % (structure_type.name, task_type.name)]

    def compatible(self, structure_type, task_type):
        return self.name == '%s_%s' % (structure_type.name, task_type.name)


class TaskType(Enum):
    MODELING = 0
    SIMILARITY = 1
    SUBSTRUCTURE = 2


class AdditiveType(Enum):
    SOLVENT = 0
    CATALYST = 1


class ResultType(Enum):
    TEXT = 0
    STRUCTURE = 1
    TABLE = 2
    IMAGE = 3
    GRAPH = 4
    GTM = 5


class UserRole(Enum):
    COMMON = 1
    ADMIN = 2
    DATA_MANAGER = 3


class BlogPostType(Enum):
    COMMON = 1
    CAROUSEL = 2
    IMPORTANT = 3
    PROJECTS = 4
    ABOUT = 5
    LESSON = 21


class TeamPostType(Enum):
    TEAM = 6
    CHIEF = 7
    STUDENT = 8


class EmailPostType(Enum):
    REGISTRATION = 9
    FORGOT = 10
    SPAM = 11
    MEETING_REGISTRATION = 12
    MEETING_THESIS = 13
    MEETING_SPAM = 14

    @property
    def is_meeting(self):
        return self.name in ('MEETING_REGISTRATION', 'MEETING_THESIS', 'MEETING_FORGOT', 'MEETING_SPAM')


class MeetingPostType(Enum):
    MEETING = 15
    REGISTRATION = 16
    COMMON = 17


class ThesisPostType(Enum):
    ORAL = 18
    POSTER = 19
    PLENARY = 20

    @property
    def fancy(self):
        names = {18: 'Oral', 19: 'Poster', 20: 'Plenary'}
        return names[self.value]


class Glyph(Enum):
    COMMON = 'file'
    CAROUSEL = 'camera'
    IMPORTANT = 'bullhorn'
    PROJECTS = 'hdd'
    ABOUT = 'eye-open'

    TEAM = 'knight'
    CHIEF = 'queen'
    STUDENT = 'pawn'

    MEETING = 'resize-small'

    REGISTRATION = 'send'
    FORGOT = 'send'
    SPAM = 'send'
    MEETING_REGISTRATION = 'send'
    MEETING_THESIS = 'send'
    MEETING_SPAM = 'send'

    ORAL = 'blackboard'
    POSTER = 'blackboard'
    PLENARY = 'blackboard'

    LESSON = 'education'


class FormRoute(Enum):
    LOGIN = 1
    REGISTER = 2
    FORGOT = 3
    EDIT_PROFILE = 4
    LOGOUT_ALL = 5
    CHANGE_PASSWORD = 6
    NEW_BLOG_POST = 7
    NEW_EMAIL_TEMPLATE = 8
    NEW_MEETING_PAGE = 9
    NEW_MEMBER_PAGE = 10
    BAN_USER = 11
    CHANGE_USER_ROLE = 12

    @staticmethod
    def get(action):
        if 1 <= action <= 12:
            return FormRoute(action)
        return None

    def is_login(self):
        return 1 <= self.value <= 3

    def is_profile(self):
        return 4 <= self.value <= 12


class ProfileDegree(Enum):
    NO_DEGREE = 1
    PHD = 2
    SCID = 3

    @property
    def fancy(self):
        names = {1: 'No Degree', 2: 'Doctor of Philosophy', 3: 'Doctor of Science'}
        return names[self.value]


class ProfileStatus(Enum):
    COMMON = 1
    FOREIGN = 2
    RUS_SCIENTIST = 3
    RUS_YOUNG = 4
    PHD_STUDENT = 5
    STUDENT = 6
    INTERN = 7

    @property
    def fancy(self):
        names = {1: 'Common', 2: 'Foreign participant', 3: 'Russian Scientist (from 40 year old)',
                 4: 'Russian young scientist (up to 39 year old)', 5: 'Ph.D. student', 6: 'Student', 7: 'Intern'}
        return names[self.value]


config_list = ['UPLOAD_PATH', 'PORTAL_NON_ROOT', 'SECRET_KEY', 'RESIZE_URL', 'MAX_UPLOAD_SIZE', 'IMAGES_ROOT',
               'DB_USER', 'DB_PASS', 'DB_HOST', 'DB_MAIN', 'DB_PRED', 'DB_DATA', 'YANDEX_METRIKA',
               'REDIS_HOST', 'REDIS_PORT', 'REDIS_PASSWORD', 'REDIS_TTL', 'REDIS_JOB_TIMEOUT', 'REDIS_MAIL',
               'LAB_NAME', 'LAB_SHORT', 'BLOG_POSTS_PER_PAGE', 'SCOPUS_API_KEY', 'SCOPUS_TTL',
               'SMPT_HOST', 'SMTP_PORT', 'SMTP_LOGIN', 'SMTP_PASSWORD', 'SMTP_MAIL', 'MAIL_INKEY', 'MAIL_SIGNER',
               'FP_SIZE', 'FP_ACTIVE_BITS', 'FRAGMENTOR_VERSION',
               'FRAGMENT_TYPE_CGR', 'FRAGMENT_MIN_CGR', 'FRAGMENT_MAX_CGR', 'FRAGMENT_DYNBOND_CGR',
               'FRAGMENT_TYPE_MOL', 'FRAGMENT_MIN_MOL', 'FRAGMENT_MAX_MOL']

if not path.exists(path.join(path.dirname(__file__), "config.ini")):
    with open(path.join(path.dirname(__file__), "config.ini"), 'w') as f:
        f.write('\n'.join('%s = %s' % (x, y) for x, y in globals().items() if x in config_list))

with open(path.join(path.dirname(__file__), "config.ini")) as f:
    for line in f:
        try:
            k, v = line.split('=')
            k = k.strip()
            v = v.strip()
            if k in ['DEBUG'] + config_list:
                globals()[k] = int(v) if v.isdigit() else v
        except:
            pass
