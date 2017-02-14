# -*- coding: utf-8 -*-
#
#  Copyright 2016, 2017 Ramil Nugmanov <stsouko@live.ru>
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
import imghdr
from json import loads
from collections import OrderedDict
from pycountry import countries
from .models import User, Meeting
from .config import (BlogPostType, UserRole, ThesisPostType, ProfileDegree, ProfileStatus, MeetingPostType,
                     EmailPostType, TeamPostType, MeetingPartType)
from .redirect import get_redirect_target, is_safe_url
from flask import url_for, redirect
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from pony.orm import db_session
from werkzeug.datastructures import FileStorage
from wtforms import (StringField, validators, BooleanField, SubmitField, PasswordField, ValidationError,
                     TextAreaField, SelectField, HiddenField, IntegerField, DateTimeField, SelectMultipleField)


class JsonValidator(object):
    def __call__(self, form, field):
        try:
            loads(field.data)
        except Exception:
            raise ValidationError('Bad Json')


class CheckMeetingExist(object):
    def __call__(self, form, field):
        with db_session:
            if not Meeting.exists(id=field.data, post_type=MeetingPostType.MEETING.value):
                raise ValidationError('Bad meeting post id')


class CheckUserFree(object):
    def __call__(self, form, field):
        with db_session:
            if User.exists(email=field.data.lower()):
                raise ValidationError('User exist. Please Log in or if you forgot password use restore procedure')


class CheckUserExist(object):
    def __call__(self, form, field):
        with db_session:
            if not User.exists(email=field.data.lower()):
                raise ValidationError('User not found')


class VerifyPassword(object):
    def __call__(self, form, field):
        with db_session:
            user = User.get(id=current_user.id)
            if not user or not user.verify_password(field.data):
                raise ValidationError('Bad password')


class VerifyImage(object):
    def __init__(self, types):
        self.__types = types

    def __call__(self, form, field):
        if isinstance(field.data, FileStorage) and field.data and imghdr.what(field.data.stream) not in self.__types:
            raise ValidationError('Invalid image')


class SelectValidator(object):
    def __init__(self, types):
        self.__types = types

    def __call__(self, form, field):
        if field.data not in self.__types:
            raise ValidationError('Invalid Data')


class MultiSelectValidator(object):
    def __init__(self, types):
        self.__types = types

    def __call__(self, form, field):
        if set(field.data).difference(self.__types):
            raise ValidationError('Invalid data')


class CustomForm(FlaskForm):
    next = HiddenField()
    _order = None

    @staticmethod
    def reorder(order, prefix=None):
        return ['%s-%s' % (prefix, x) for x in order] if prefix else order

    def __iter__(self):
        collect = OrderedDict((x.name, x) for x in super(CustomForm, self).__iter__())
        for name in self._order or collect:
            yield collect[name]

    def __init__(self, *args, **kwargs):
        super(CustomForm, self).__init__(*args, **kwargs)
        if not self.next.data:
            self.next.data = get_redirect_target()

    def redirect(self, endpoint='.index', **values):
        if self.next.data and is_safe_url(self.next.data):
            return redirect(self.next.data)

        return redirect(url_for(endpoint, **values))


class DeleteButtonForm(CustomForm):
    submit_btn = SubmitField('Delete')


class ProfileForm(CustomForm):
    name = StringField('Name *', [validators.DataRequired()])
    surname = StringField('Surname *', [validators.DataRequired()])
    degree = SelectField('Degree *', [validators.DataRequired()], choices=[(x.value, x.fancy) for x in ProfileDegree],
                         coerce=int)
    status = SelectField('Status *', [validators.DataRequired()], choices=[(x.value, x.fancy) for x in ProfileStatus],
                         coerce=int)

    country = SelectField('Country *', [validators.DataRequired()], choices=[(x.alpha_3, x.name) for x in countries])
    town = StringField('Town')
    affiliation = StringField('Affiliation')
    position = StringField('Position')

    submit_btn = SubmitField('Update Profile')


class Email(CustomForm):
    email = StringField('Email', [validators.DataRequired(), validators.Email(), CheckUserExist()])


class Password(CustomForm):
    password = PasswordField('Password *', [validators.DataRequired(),
                                            validators.EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Repeat Password *', [validators.DataRequired()])


class RegistrationForm(ProfileForm, Password):
    email = StringField('Email *', [validators.DataRequired(), validators.Email(), CheckUserFree()])
    submit_btn = SubmitField('Register')

    __order = ('csrf_token', 'next', 'email', 'password', 'confirm', 'name', 'surname', 'degree',
               'status', 'country', 'town', 'affiliation', 'position', 'submit_btn')

    def __init__(self, *args, **kwargs):
        self._order = self.reorder(self.__order, kwargs.get('prefix'))
        super(RegistrationForm, self).__init__(*args, **kwargs)


class LoginForm(Email):
    password = PasswordField('Password', [validators.DataRequired()])
    remember = BooleanField('Remember me')
    submit_btn = SubmitField('Log in')


class ReLoginForm(CustomForm):
    password = PasswordField('Password', [validators.DataRequired(), VerifyPassword()])
    submit_btn = SubmitField('Log out')


class ChangePasswordForm(Password):
    old_password = PasswordField('Old Password *', [validators.DataRequired(), VerifyPassword()])
    submit_btn = SubmitField('Change Password')


class ForgotPasswordForm(CustomForm):
    email = StringField('Email', [validators.DataRequired(), validators.Email()])
    submit_btn = SubmitField('Restore')


class LogoutForm(CustomForm):
    submit_btn = SubmitField('Log out')


class ChangeRoleForm(Email):
    role_type = SelectField('Role Type', [validators.DataRequired()],
                            choices=[(x.value, x.name) for x in UserRole], coerce=int)
    submit_btn = SubmitField('Change Role')

    @property
    def type(self):
        return UserRole(self.role_type.data)


class BanUserForm(Email):
    submit_btn = SubmitField('Ban User')


class MeetForm(CustomForm):
    part_type = SelectField('Participation Type',
                            [validators.DataRequired(), SelectValidator([x.value for x in MeetingPartType])],
                            choices=[(x.value, x.fancy) for x in MeetingPartType], coerce=int)
    submit_btn = SubmitField('Confirm')

    @property
    def type(self):
        return MeetingPartType(self.part_type.data)


class CommonPost(CustomForm):
    title = StringField('Title *', [validators.DataRequired()])
    body = TextAreaField('Message *', [validators.DataRequired()])
    banner_field = FileField('Graphical Abstract',
                             validators=[FileAllowed('jpg jpe jpeg png'.split(), 'JPEG or PNG images only'),
                                         VerifyImage('jpeg png'.split())])
    attachment = FileField('Abstract File', validators=[FileAllowed('doc docx odt pdf'.split(), 'Documents only')])


class ThesisForm(CommonPost):
    post_type = SelectField('Presentation Type *',
                            [validators.DataRequired(), SelectValidator([x.value for x in ThesisPostType])],
                            choices=[(x.value, x.fancy) for x in ThesisPostType], coerce=int)
    submit_btn = SubmitField('Confirm')

    __order = ('csrf_token', 'next', 'title', 'body', 'banner_field', 'attachment', 'post_type', 'submit_btn')

    def __init__(self, *args, body_name=None, part_type=None, **kwargs):
        self._order = self.reorder(self.__order, kwargs.get('prefix'))
        super(ThesisForm, self).__init__(*args, **kwargs)
        if part_type is not None:
            self.post_type.choices = [(x.value, x.fancy) for x in ThesisPostType.thesis_post_type(part_type)]
        self.body.label.text = body_name and '%s *' % body_name or 'Short Abstract'

    @property
    def type(self):
        return ThesisPostType(self.post_type.data)


class Post(CommonPost):
    slug = StringField('Slug')
    submit_btn = SubmitField('Post')


class PostForm(Post):
    post_type = SelectField('Post Type', [validators.DataRequired(), SelectValidator([x.value for x in BlogPostType])],
                            choices=[(x.value, x.name) for x in BlogPostType], coerce=int)

    __order = ('csrf_token', 'next', 'title', 'body', 'slug', 'banner_field', 'attachment', 'post_type', 'submit_btn')

    def __init__(self, *args, **kwargs):
        self._order = self.reorder(self.__order, kwargs.get('prefix'))
        super(PostForm, self).__init__(*args, **kwargs)

    @property
    def type(self):
        return BlogPostType(self.post_type.data)


class MeetingForm(Post):
    post_type = SelectField('Post Type', [validators.DataRequired(),
                                          SelectValidator([x.value for x in MeetingPostType])],
                            choices=[(x.value, x.name) for x in MeetingPostType], coerce=int)
    deadline = DateTimeField('Deadline', [validators.Optional()], format='%d/%m/%Y %H:%M')
    poster_deadline = DateTimeField('Poster Deadline', [validators.Optional()], format='%d/%m/%Y %H:%M')
    meeting_id = IntegerField('Meeting page', [validators.Optional(), CheckMeetingExist()])
    order = IntegerField('Order', [validators.Optional()])
    body_name = StringField('Body Name')
    participation_types_id = SelectMultipleField('Participation Types',
                                                 [validators.Optional(),
                                                  MultiSelectValidator([x.value for x in MeetingPartType])],
                                                 choices=[(x.value, x.name) for x in MeetingPartType], coerce=int)
    thesis_types_id = SelectMultipleField('Presentation Types',
                                          [validators.Optional(),
                                           MultiSelectValidator([x.value for x in ThesisPostType])],
                                          choices=[(x.value, x.name) for x in ThesisPostType], coerce=int)

    __order = ('csrf_token', 'next', 'title', 'body', 'slug', 'banner_field', 'attachment', 'post_type', 'deadline',
               'poster_deadline', 'meeting_id', 'order', 'body_name', 'participation_types_id', 'thesis_types_id',
               'submit_btn')

    def __init__(self, *args, **kwargs):
        self._order = self.reorder(self.__order, kwargs.get('prefix'))
        super(MeetingForm, self).__init__(*args, **kwargs)

    @property
    def type(self):
        return MeetingPostType(self.post_type.data)

    @property
    def participation_types(self):
        return [MeetingPartType(x) for x in self.participation_types_id.data]

    @property
    def thesis_types(self):
        return [ThesisPostType(x) for x in self.thesis_types_id.data]


class EmailForm(Post):
    post_type = SelectField('Post Type', [validators.DataRequired(), SelectValidator([x.value for x in EmailPostType])],
                            choices=[(x.value, x.name) for x in EmailPostType], coerce=int)
    from_name = StringField('From Name')
    reply_name = StringField('Reply Name')
    reply_mail = StringField('Reply email', [validators.Optional(), validators.Email()])
    meeting_id = IntegerField('Meeting page', [validators.Optional(), CheckMeetingExist()])

    __order = ('csrf_token', 'next', 'title', 'body', 'slug', 'banner_field', 'attachment', 'post_type', 'from_name',
               'reply_mail', 'reply_name', 'meeting_id', 'submit_btn')

    def __init__(self, *args, **kwargs):
        self._order = self.reorder(self.__order, kwargs.get('prefix'))
        super(EmailForm, self).__init__(*args, **kwargs)

    @property
    def type(self):
        return EmailPostType(self.post_type.data)


class TeamForm(Post):
    post_type = SelectField('Member Type', [validators.DataRequired(),
                                            SelectValidator([x.value for x in TeamPostType])],
                            choices=[(x.value, x.name) for x in TeamPostType], coerce=int)
    role = StringField('Role', [validators.DataRequired()])
    order = IntegerField('Order', [validators.Optional()])
    scopus = StringField('Scopus')

    __order = ('csrf_token', 'next', 'title', 'body', 'slug', 'banner_field', 'attachment', 'post_type', 'role',
               'order', 'scopus', 'submit_btn')

    def __init__(self, *args, **kwargs):
        self._order = self.reorder(self.__order, kwargs.get('prefix'))
        super(TeamForm, self).__init__(*args, **kwargs)

    @property
    def type(self):
        return TeamPostType(self.post_type.data)
