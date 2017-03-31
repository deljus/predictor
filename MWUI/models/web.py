# -*- coding: utf-8 -*-
#
#  Copyright 2017 Ramil Nugmanov <stsouko@live.ru>
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
from bcrypt import hashpw, gensalt
from datetime import datetime
from hashlib import md5
from pony.orm import PrimaryKey, Required, Optional, Set, Json
from pycountry import countries
from ..config import DEBUG
from ..constants import (ModelType, AdditiveType, UserRole, ProfileDegree, ProfileStatus, Glyph, BlogPostType,
                         MeetingPostType, ThesisPostType, EmailPostType, TeamPostType, MeetingPartType)


def filter_kwargs(kwargs):
    return {x: y for x, y in kwargs.items() if y}


def load_tables(db, schema):
    class MeetingMixin(object):
        @property
        def meeting_id(self):
            return self.meeting.id

        @staticmethod
        def _get_parent(_parent):
            parent = Meeting[_parent]
            if parent.type != MeetingPostType.MEETING:
                raise Exception('Only MEETING type can be parent')
            return parent

    class User(db.Entity):
        _table_ = '%s_user' % schema if DEBUG else (schema, 'user')
        id = PrimaryKey(int, auto=True)
        active = Required(bool, default=True)
        email = Required(str, unique=True)
        password = Required(str)
        user_role = Required(int)
        tasks = Set('Task')
        token = Required(str)
        restore = Optional(str)

        name = Required(str)
        surname = Required(str)
        banner = Optional(str)
        degree = Required(int, default=ProfileDegree.NO_DEGREE.value)
        status = Required(int, default=ProfileStatus.COMMON.value)

        country = Required(str)
        town = Optional(str)
        affiliation = Optional(str)
        position = Optional(str)

        posts = Set('Post')
        subscriptions = Set('Subscription')

        def __init__(self, email, password, role=UserRole.COMMON, **kwargs):
            password = self.__hash_password(password)
            token = self.__gen_token(email, str(datetime.utcnow()))
            super(User, self).__init__(email=email, password=password, token=token, user_role=role.value,
                                       **filter_kwargs(kwargs))

        @property
        def full_name(self):
            return '{0.name} {0.surname}'.format(self)

        @property
        def sci_degree(self):
            return ProfileDegree(self.degree)

        @property
        def sci_status(self):
            return ProfileStatus(self.status)

        @property
        def country_name(self):
            return countries.get(alpha_3=self.country).name

        @staticmethod
        def __hash_password(password):
            return hashpw(password.encode(), gensalt()).decode()

        def verify_password(self, password):
            return hashpw(password.encode(), self.password.encode()) == self.password.encode()

        def verify_restore(self, restore):
            return self.restore and hashpw(restore.encode(), self.restore.encode()) == self.restore.encode()

        def gen_restore(self):
            restore = self.__gen_token(self.email, str(datetime.utcnow()))[:8]
            self.restore = self.__hash_password(restore)
            return restore

        def change_password(self, password):
            self.password = self.__hash_password(password)

        @staticmethod
        def __gen_token(email, password):
            return md5((email + password).encode()).hexdigest()

        def change_token(self):
            self.token = self.__gen_token(self.email, str(datetime.utcnow()))

        @property
        def role(self):
            return UserRole(self.user_role)

    class Subscription(db.Entity):
        _table_ = '%s_subscription' % schema if DEBUG else (schema, 'subscription')
        id = PrimaryKey(int, auto=True)
        user = Required('User')
        meeting = Required('Meeting')
        part_type = Required(int)

        def __init__(self, user, meeting, part_type):
            super(Subscription, self).__init__(user=user, meeting=meeting, part_type=part_type.value)

        @property
        def type(self):
            return MeetingPartType(self.part_type)

        def update_type(self, _type):
            self.part_type = _type.value

    class Attachment(db.Entity):
        _table_ = '%s_attachment' % schema if DEBUG else (schema, 'attachment')
        id = PrimaryKey(int, auto=True)
        file = Required(str)
        name = Required(str)
        post = Required('Post')

    class Post(db.Entity):
        _table_ = '%s_post' % schema if DEBUG else (schema, 'post')
        id = PrimaryKey(int, auto=True)
        post_type = Required(int)
        author = Required('User')
        title = Required(str)
        body = Required(str)
        date = Required(datetime)
        banner = Optional(str)
        attachments = Set('Attachment')
        slug = Optional(str, unique=True)

        children = Set('Post', cascade_delete=True)
        post_parent = Optional('Post')
        special = Optional(Json)

        def __init__(self, **kwargs):
            attachments = kwargs.pop('attachments', None) or []
            date = kwargs.pop('date', datetime.utcnow())
            super(Post, self).__init__(date=date, **filter_kwargs(kwargs))

            for file, name in attachments:
                self.add_attachment(file, name)

        def add_attachment(self, file, name):
            Attachment(file=file, name=name, post=self)

        def remove_attachment(self, attachment):
            self.attachments.remove(Attachment[attachment])

        @property
        def glyph(self):
            return Glyph[self.type.name].value

        @property
        def author_name(self):
            return self.author.full_name

    class BlogPost(Post):
        def __init__(self, **kwargs):
            _type = kwargs.pop('type', BlogPostType.COMMON).value
            super(BlogPost, self).__init__(post_type=_type, **kwargs)

        @property
        def type(self):
            return BlogPostType(self.post_type)

        def update_type(self, _type):
            self.post_type = _type.value

    class TeamPost(Post):
        def __init__(self, role='Researcher', scopus=None, order=0, **kwargs):
            _type = kwargs.pop('type', TeamPostType.TEAM).value
            special = dict(scopus=scopus, order=order, role=role)
            super(TeamPost, self).__init__(post_type=_type, special=special, **kwargs)

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

    class Meeting(Post, MeetingMixin):
        subscribers = Set('Subscription')

        def __init__(self, meeting=None, deadline=None, poster_deadline=None, order=0, body_name=None,
                     participation_types=None, thesis_types=None, **kwargs):
            _type = kwargs.pop('type', MeetingPostType.MEETING)
            special = dict(order=order)

            if _type != MeetingPostType.MEETING:
                if meeting:
                    parent = self._get_parent(meeting)
                else:
                    raise Exception('Need parent meeting post')
            else:
                parent = None
                special['body_name'] = body_name or None
                if deadline and poster_deadline:
                    special['deadline'] = deadline.timestamp()
                    special['poster_deadline'] = poster_deadline.timestamp()
                else:
                    raise Exception('Need deadlines information')

                if participation_types is not None:
                    special['participation_types'] = [x.value for x in participation_types]

                if thesis_types is not None:
                    special['thesis_types'] = [x.value for x in thesis_types]

            super(Meeting, self).__init__(post_type=_type.value, post_parent=parent, special=special, **kwargs)

        @property
        def participation_types(self):
            return [MeetingPartType(x) for x in self.meeting.special.get('participation_types', [])]

        @property
        def participation_types_id(self):
            return self.meeting.special.get('participation_types', [])

        def update_participation_types(self, types):
            self.meeting.special['participation_types'] = [x.value for x in types]

        @property
        def thesis_types(self):
            return [ThesisPostType(x) for x in self.meeting.special.get('thesis_types', [])]

        @property
        def thesis_types_id(self):
            return self.meeting.special.get('thesis_types', [])

        def update_thesis_types(self, types):
            self.meeting.special['thesis_types'] = [x.value for x in types]

        @property
        def body_name(self):
            return self.meeting.special['body_name']

        def update_body_name(self, name):
            self.meeting.special['body_name'] = name or None

        @property
        def type(self):
            return MeetingPostType(self.post_type)

        def update_type(self, _type):
            if self.type == MeetingPostType.MEETING:
                if _type == MeetingPostType.MEETING:
                    return None
                raise Exception('Meeting page can not be changed')
            elif _type == MeetingPostType.MEETING:
                raise Exception('Page can not be changed to Meeting page')

            self.post_type = _type.value

        @property
        def deadline(self):
            return datetime.fromtimestamp(self.meeting.special['deadline'])

        def update_deadline(self, deadline):
            self.meeting.special['deadline'] = deadline.timestamp()

        @property
        def poster_deadline(self):
            return datetime.fromtimestamp(self.meeting.special['poster_deadline'])

        def update_poster_deadline(self, deadline):
            self.meeting.special['poster_deadline'] = deadline.timestamp()

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

    class Thesis(Post, MeetingMixin):
        def __init__(self, meeting, **kwargs):
            _type = kwargs.pop('type', ThesisPostType.POSTER).value
            parent = Meeting[meeting]

            if parent.type != MeetingPostType.MEETING:
                raise Exception('Invalid Meeting id')
            if parent.deadline < datetime.utcnow():
                raise Exception('Deadline left')

            super(Thesis, self).__init__(post_type=_type, post_parent=parent, **filter_kwargs(kwargs))

        @property
        def body_name(self):
            return self.meeting.special['body_name']

        @property
        def type(self):
            return ThesisPostType(self.post_type)

        def update_type(self, _type):
            self.post_type = _type.value

        @property
        def meeting(self):
            return self.post_parent

    class Email(Post, MeetingMixin):
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

            super(Email, self).__init__(post_type=_type.value, post_parent=parent, special=special,
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

    class Model(db.Entity):
        _table_ = '%s_model' % schema if DEBUG else (schema, 'model')
        id = PrimaryKey(int, auto=True)
        description = Optional(str)
        destinations = Set('Destination')
        example = Optional(str)
        model_type = Required(int)
        name = Required(str, unique=True)
        results = Set('Result')

        def __init__(self, **kwargs):
            _type = kwargs.pop('type', ModelType.MOLECULE_MODELING).value
            super(Model, self).__init__(model_type=_type, **filter_kwargs(kwargs))

        @property
        def type(self):
            return ModelType(self.model_type)

    class Destination(db.Entity):
        _table_ = '%s_destination' % schema if DEBUG else (schema, 'destination')
        id = PrimaryKey(int, auto=True)
        host = Required(str)
        model = Required('Model')
        name = Required(str)
        password = Optional(str)
        port = Required(int, default=6379)

        def __init__(self, **kwargs):
            super(Destination, self).__init__(**filter_kwargs(kwargs))

    class Additive(db.Entity):
        _table_ = '%s_additive' % schema if DEBUG else (schema, 'additive')
        id = PrimaryKey(int, auto=True)
        additive_type = Required(int)
        additiveset = Set('Additiveset')
        name = Required(str, unique=True)
        structure = Optional(str)

        def __init__(self, **kwargs):
            _type = kwargs.pop('type', AdditiveType.SOLVENT).value
            super(Additive, self).__init__(additive_type=_type, **kwargs)

        @property
        def type(self):
            return AdditiveType(self.additive_type)

    return (User, Subscription, Model, Destination, Additive,
            Post, BlogPost, TeamPost, Meeting, Thesis, Email, Attachment)
