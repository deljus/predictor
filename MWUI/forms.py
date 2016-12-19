#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-
#
#  Copyright 2016 Ramil Nugmanov <stsouko@live.ru>
#  This file is part of predictor.
#
#  predictor
#  is free software; you can redistribute it and/or modify
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
from .models import Users, Meetings
from .config import (BlogPostType, UserRole, ThesisPostType, ProfileDegree, ProfileStatus, MeetingPostType,
                     EmailPostType, TeamPostType)
from .redirect import get_redirect_target, is_safe_url
from flask import url_for, redirect
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from pony.orm import db_session
from wtforms import (StringField, validators, BooleanField, SubmitField, PasswordField, ValidationError,
                     TextAreaField, SelectField, HiddenField, IntegerField, DateTimeField)


class JsonValidator(object):
    message = 'Bad Json'

    def __call__(self, form, field):
        try:
            loads(field.data)
        except Exception:
            raise ValidationError(self.message)


class CheckMeetingExist(object):
    message = 'Bad meeting post id'

    def __call__(self, form, field):
        with db_session:
            if not Meetings.exists(id=field.data, post_type=MeetingPostType.MEETING.value):
                raise ValidationError(self.message)


class CheckUserFree(object):
    message = 'User exist. Please Log in or if you forgot password use restore procedure'

    def __call__(self, form, field):
        with db_session:
            if Users.exists(email=field.data.lower()):
                raise ValidationError(self.message)


class CheckUserExist(object):
    message = 'User not found'

    def __call__(self, form, field):
        with db_session:
            if not Users.exists(email=field.data.lower()):
                raise ValidationError(self.message)


class VerifyPassword(object):
    message = 'Bad password'

    def __call__(self, form, field):
        with db_session:
            user = Users.get(id=current_user.id)
            if not user or not user.verify_password(field.data):
                raise ValidationError(self.message)


class VerifyImage(object):
    message = 'Invalid image'

    def __init__(self, types):
        self.__types = types

    def __call__(self, form, field):
        if field.has_file() and imghdr.what(field.data.stream) not in self.__types:
            raise ValidationError(self.message)


class PostValidator(object):
    message = 'Invalid Post Type'

    def __init__(self, types):
        self.__types = types

    def __call__(self, form, field):
        if field.data not in self.__types:
            raise ValidationError(self.message)


class CustomForm(FlaskForm):
    next = HiddenField()
    _order = None

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
        self._order = ['%s%s' % ('prefix' in kwargs and '%s-' % kwargs['prefix'] or '', x) for x in self.__order]
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


class CommonPost(CustomForm):
    title = StringField('Title *', [validators.DataRequired()])
    body = TextAreaField('Message *', [validators.DataRequired()])
    banner = FileField('Graphical Abstract',
                       validators=[FileAllowed('jpg jpe jpeg png'.split(), 'JPEG or PNG images only'),
                                   VerifyImage('jpeg png'.split())])
    attachment = FileField('Abstract File', validators=[FileAllowed('doc docx odt'.split(), 'Documents only')])


class ThesisForm(CommonPost):
    post_type = SelectField('Presentation Type *',
                            [validators.DataRequired(), PostValidator([x.value for x in ThesisPostType])],
                            choices=[(x.value, x.fancy) for x in ThesisPostType], coerce=int)
    submit_btn = SubmitField('Confirm')

    def __init__(self, *args, body_name=None, **kwargs):
        super(ThesisForm, self).__init__(*args, **kwargs)
        self.body.label.text = body_name and '%s *' % body_name or 'Short Abstract'

    @property
    def type(self):
        return ThesisPostType(self.post_type.data)


class Post(CommonPost):
    slug = StringField('Slug')
    submit_btn = SubmitField('Post')


class PostForm(Post):
    post_type = SelectField('Post Type', [validators.DataRequired(), PostValidator([x.value for x in BlogPostType])],
                            choices=[(x.value, x.name) for x in BlogPostType], coerce=int)

    @property
    def type(self):
        return BlogPostType(self.post_type.data)


class MeetingForm(Post):
    post_type = SelectField('Post Type', [validators.DataRequired(), PostValidator([x.value for x in MeetingPostType])],
                            choices=[(x.value, x.name) for x in MeetingPostType], coerce=int)
    deadline = DateTimeField('Deadline', [validators.Optional()], format='%d/%m/%Y %H:%M')
    meeting_id = IntegerField('Meeting page', [validators.Optional(), CheckMeetingExist()])
    order = IntegerField('Order', [validators.Optional()])
    body_name = StringField('Body Name')

    @property
    def type(self):
        return MeetingPostType(self.post_type.data)


class EmailForm(Post):
    post_type = SelectField('Post Type', [validators.DataRequired(), PostValidator([x.value for x in EmailPostType])],
                            choices=[(x.value, x.name) for x in EmailPostType], coerce=int)
    from_name = StringField('From Name')
    reply_name = StringField('Reply Name')
    reply_mail = StringField('Reply email', [validators.Optional(), validators.Email()])
    meeting_id = IntegerField('Meeting page', [validators.Optional(), CheckMeetingExist()])

    @property
    def type(self):
        return EmailPostType(self.post_type.data)


class TeamForm(Post):
    post_type = SelectField('Member Type', [validators.DataRequired(), PostValidator([x.value for x in TeamPostType])],
                            choices=[(x.value, x.name) for x in TeamPostType], coerce=int)
    role = StringField('Role', [validators.DataRequired()])
    order = IntegerField('Order', [validators.Optional()])
    scopus = StringField('Scopus')

    @property
    def type(self):
        return TeamPostType(self.post_type.data)
