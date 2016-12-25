# -*- coding: utf-8 -*-
#
# Copyright 2015 Ramil Nugmanov <stsouko@live.ru>
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
import bcrypt
import hashlib
from .config import (DEBUG, DB_PASS, DB_HOST, DB_NAME, DB_USER,
                     TaskType, ModelType, AdditiveType, ResultType, StructureType,
                     StructureStatus, UserRole, ProfileDegree, ProfileStatus,
                     BlogPostType, MeetingPostType, ThesisPostType, EmailPostType, Glyph, TeamPostType)
from datetime import datetime
from pony.orm import Database, sql_debug, PrimaryKey, Required, Optional, Set, Json


if DEBUG:
    db = Database("sqlite", "database.sqlite", create_db=True)
    sql_debug(True)
else:
    db = Database('postgres', user=DB_USER, password=DB_PASS, host=DB_HOST, database=DB_NAME)


def filter_kwargs(kwargs):
    return {x: y for x, y in kwargs.items() if y}


class Users(db.Entity):
    id = PrimaryKey(int, auto=True)
    active = Required(bool, default=True)
    email = Required(str, unique=True)
    password = Required(str)
    user_role = Required(int)
    tasks = Set("Tasks")
    token = Required(str)
    restore = Optional(str)

    name = Required(str)
    surname = Required(str)
    degree = Required(int, default=ProfileDegree.NO_DEGREE.value)
    status = Required(int, default=ProfileStatus.COMMON.value)

    country = Required(str)
    town = Optional(str)
    affiliation = Optional(str)
    position = Optional(str)

    posts = Set("Posts")

    def __init__(self, email, password, role=UserRole.COMMON, **kwargs):
        password = self.__hash_password(password)
        token = self.__gen_token(email, str(datetime.utcnow()))
        super(Users, self).__init__(email=email, password=password, token=token, user_role=role.value,
                                    **filter_kwargs(kwargs))

    @staticmethod
    def __hash_password(password):
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(self, password):
        return bcrypt.hashpw(password.encode(), self.password.encode()) == self.password.encode()

    def verify_restore(self, restore):
        return self.restore and bcrypt.hashpw(restore.encode(), self.restore.encode()) == self.restore.encode()

    def gen_restore(self):
        restore = self.__gen_token(self.email, str(datetime.utcnow()))[:8]
        self.restore = self.__hash_password(restore)
        return restore

    def change_password(self, password):
        self.password = self.__hash_password(password)

    @staticmethod
    def __gen_token(email, password):
        return hashlib.md5((email + password).encode()).hexdigest()

    def change_token(self):
        self.token = self.__gen_token(self.email, str(datetime.utcnow()))

    @property
    def role(self):
        return UserRole(self.user_role)


class Tasks(db.Entity):
    id = PrimaryKey(int, auto=True)
    date = Required(datetime, default=datetime.utcnow())
    structures = Set("Structures")
    task_type = Required(int)
    user = Optional(Users)

    def __init__(self, **kwargs):
        _type = kwargs.pop('type', TaskType.MODELING).value
        super(Tasks, self).__init__(task_type=_type, **kwargs)

    @property
    def type(self):
        return TaskType(self.task_type)


class Structures(db.Entity):
    id = PrimaryKey(int, auto=True)
    additives = Set("Additivesets")
    pressure = Optional(float)
    results = Set("Results")
    structure = Optional(str)
    structure_type = Required(int)
    structure_status = Required(int)
    task = Required(Tasks)
    temperature = Optional(float)

    def __init__(self, **kwargs):
        _type = kwargs.pop('type', StructureType.MOLECULE).value
        status = kwargs.pop('status', StructureStatus.CLEAR).value
        super(Structures, self).__init__(structure_type=_type, structure_status=status, **kwargs)

    @property
    def type(self):
        return StructureType(self.structure_type)

    @property
    def status(self):
        return StructureStatus(self.structure_status)


class Results(db.Entity):
    id = PrimaryKey(int, auto=True)
    key = Required(str)
    model = Required("Models")
    result_type = Required(int)
    structure = Required(Structures)
    value = Required(str)

    def __init__(self, **kwargs):
        _type = kwargs.pop('type', ResultType.TEXT).value
        _model = Models[kwargs.pop('model')]
        super(Results, self).__init__(result_type=_type, model=_model, **kwargs)

    @property
    def type(self):
        return ResultType(self.result_type)


class Models(db.Entity):
    id = PrimaryKey(int, auto=True)
    description = Optional(str)
    destinations = Set("Destinations")
    example = Optional(str)
    model_type = Required(int)
    name = Required(str, unique=True)
    results = Set(Results)

    def __init__(self, **kwargs):
        _type = kwargs.pop('type', ModelType.MOLECULE_MODELING).value
        super(Models, self).__init__(model_type=_type, **filter_kwargs(kwargs))

    @property
    def type(self):
        return ModelType(self.model_type)


class Destinations(db.Entity):
    id = PrimaryKey(int, auto=True)
    host = Required(str)
    model = Required(Models)
    name = Required(str)
    password = Optional(str)
    port = Required(int, default=6379)

    def __init__(self, **kwargs):
        super(Destinations, self).__init__(**filter_kwargs(kwargs))


class Additives(db.Entity):
    id = PrimaryKey(int, auto=True)
    additive_type = Required(int)
    additivesets = Set("Additivesets")
    name = Required(str, unique=True)
    structure = Optional(str)

    def __init__(self, **kwargs):
        _type = kwargs.pop('type', AdditiveType.SOLVENT).value
        super(Additives, self).__init__(additive_type=_type, **kwargs)

    @property
    def type(self):
        return AdditiveType(self.additive_type)


class Additivesets(db.Entity):
    additive = Required(Additives)
    amount = Required(float, default=1)
    structure = Required(Structures)


class Attachments(db.Entity):
    file = Required(str)
    name = Required(str)
    post = Required('Posts')


class Posts(db.Entity):
    post_type = Required(int)
    author = Required(Users)
    title = Required(str)
    body = Required(str)
    date = Required(datetime, default=datetime.utcnow())
    banner = Optional(str)
    attachments = Set(Attachments)
    slug = Optional(str, unique=True)

    children = Set('Posts', cascade_delete=True)
    post_parent = Optional('Posts')
    special = Optional(Json)

    def __init__(self, **kwargs):
        attachments = kwargs.pop('attachments', None) or []
        user = Users[kwargs.pop('author')]
        super(Posts, self).__init__(author=user, **filter_kwargs(kwargs))

        for file, name in attachments:
            self.add_attachment(file, name)

    def add_attachment(self, file, name):
        Attachments(file=file, name=name, post=self)

    def remove_attachment(self, attachment):
        self.attachments.remove(Attachments[attachment])

    @property
    def glyph(self):
        return Glyph[self.type.name].value

    @property
    def author_name(self):
        return '%s %s' % (self.author.name, self.author.surname)


class MeetingMixin(object):
    @property
    def meeting_id(self):
        return self.meeting.id

    @staticmethod
    def _get_parent(_parent):
        parent = Meetings[_parent]
        if parent.type != MeetingPostType.MEETING:
            raise Exception('Only MEETING type can be parent')
        return parent


class BlogPosts(Posts):
    def __init__(self, **kwargs):
        _type = kwargs.pop('type', BlogPostType.COMMON).value
        super(BlogPosts, self).__init__(post_type=_type, **kwargs)

    @property
    def type(self):
        return BlogPostType(self.post_type)

    def update_type(self, _type):
        self.post_type = _type.value


class TeamPosts(Posts):
    def __init__(self, role='Researcher', scopus=None, order=0, **kwargs):
        _type = kwargs.pop('type', TeamPostType.TEAM).value
        special = dict(scopus=scopus, order=order, role=role)
        super(TeamPosts, self).__init__(post_type=_type, special=special, **kwargs)

    @property
    def scopus(self):
        return self.special['scopus']

    def update_scopus(self, scopus):
        self.special['scopus'] = scopus

    @property
    def order(self):
        return self.special['order']

    def update_order(self, order):
        self.special['order'] = order

    @property
    def role(self):
        return self.special['role']

    def update_role(self, role):
        self.special['role'] = role

    @property
    def type(self):
        return TeamPostType(self.post_type)

    def update_type(self, _type):
        self.post_type = _type.value


class Meetings(Posts, MeetingMixin):
    def __init__(self, meeting=None, deadline=None, order=0, **kwargs):
        _type = kwargs.pop('type', MeetingPostType.MEETING)
        special = dict(order=order)

        if _type != MeetingPostType.MEETING:
            if meeting:
                parent = self._get_parent(meeting)
            else:
                raise Exception('Need parent meeting post')
        else:
            parent = None
            if deadline:
                special['deadline'] = deadline.timestamp()
            else:
                raise Exception('Need deadline information')

        super(Meetings, self).__init__(post_type=_type.value, post_parent=parent, special=special, **kwargs)

    @property
    def type(self):
        return MeetingPostType(self.post_type)

    @property
    def deadline(self):
        return datetime.fromtimestamp(self.meeting.special['deadline'])

    def update_deadline(self, deadline):
        self.meeting.special['deadline'] = deadline.timestamp()

    @property
    def order(self):
        return self.special['order']

    def update_order(self, order):
        self.special['order'] = order

    @property
    def meeting(self):
        return self.post_parent or self

    def can_update_meeting(self):
        return self.type != MeetingPostType.MEETING

    def update_meeting(self, meeting):
        if not self.can_update_meeting():
            raise Exception('Parent can not be set to MEETING type post')
        self.post_parent = self._get_parent(meeting)


class Theses(Posts, MeetingMixin):
    def __init__(self, meeting, **kwargs):
        _type = kwargs.pop('type', ThesisPostType.POSTER).value
        parent = Meetings[meeting]

        if parent.type != MeetingPostType.MEETING:
            raise Exception('Invalid Meeting id')
        if parent.deadline < datetime.utcnow():
            raise Exception('Deadline left')

        super(Theses, self).__init__(post_type=_type, post_parent=parent, **filter_kwargs(kwargs))

    @property
    def type(self):
        return ThesisPostType(self.post_type)

    def update_type(self, _type):
        self.post_type = _type.value

    @property
    def meeting(self):
        return self.post_parent


class Emails(Posts, MeetingMixin):
    def __init__(self, from_name=None, reply_name=None, reply_mail=None, meeting=None, **kwargs):
        _type = kwargs.pop('type', EmailPostType.SPAM)
        special = dict(from_name=from_name, reply_name=reply_name, reply_mail=reply_mail)

        if _type.is_meeting:
            if meeting:
                parent = self._get_parent(meeting)
            else:
                raise Exception('Need parent meeting post')
        else:
            parent = None

        super(Emails, self).__init__(post_type=_type.value, post_parent=parent, special=special,
                                     **filter_kwargs(kwargs))

    @property
    def meeting(self):
        return self.post_parent

    def can_update_meeting(self):
        return self.type.is_meeting

    def update_meeting(self, meeting):
        if not self.can_update_meeting():
            raise Exception('Parent can not be set to non MEETING type Email')

        self.post_parent = self._get_parent(meeting)

    @property
    def from_name(self):
        return self.special['from_name']

    def update_from_name(self, name):
        self.special['from_name'] = name

    @property
    def reply_name(self):
        return self.special['reply_name']

    def update_reply_name(self, name):
        self.special['reply_name'] = name

    @property
    def reply_mail(self):
        return self.special['reply_mail']

    def update_reply_mail(self, name):
        self.special['reply_mail'] = name

    @property
    def type(self):
        return EmailPostType(self.post_type)

    def update_type(self, _type):
        if self.type.is_meeting:
            if not _type.is_meeting:
                raise Exception('Meeting Emails can be changed only to meeting Email')
        elif _type.is_meeting:
            raise Exception('Non meeting Emails can be changed only to non meeting Email')

        self.post_type = _type.value


db.generate_mapping(create_tables=True)
