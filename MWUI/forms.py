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
from json import loads
from collections import OrderedDict
from pycountry import countries
from .models import Users, Blog
from .config import BlogPost, UserRole, MeetingPost
from flask import request, url_for, redirect
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from pony.orm import db_session
from wtforms import (StringField, validators, BooleanField, SubmitField, PasswordField, ValidationError, TextAreaField,
                     SelectField, HiddenField)
from urllib.parse import urlparse, urljoin


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


def get_redirect_target():
    for target in request.args.get('next'), request.referrer:
        if not target:
            continue
        if is_safe_url(target):
            return target


class JsonValidator(object):
    def __init__(self):
        self.message = 'Bad Json'

    def __call__(self, form, field):
        try:
            loads(field.data)
        except Exception:
            raise ValidationError(self.message)


class CheckParentExist(object):
    def __init__(self):
        self.message = 'Bad parent post id'

    def __call__(self, form, field):
        with db_session:
            if not Blog.exists(id=field.data):
                raise ValidationError(self.message)


class CheckUserFree(object):
    def __init__(self):
        self.message = 'User exist'

    def __call__(self, form, field):
        with db_session:
            if Users.exists(email=field.data):
                raise ValidationError(self.message)


class CheckUserExist(object):
    def __init__(self):
        self.message = 'User not found'

    def __call__(self, form, field):
        with db_session:
            if not Users.exists(email=field.data):
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
            self.next.data = get_redirect_target() or ''

    def redirect(self, endpoint='index', **values):
        if is_safe_url(self.next.data):
            return redirect(self.next.data)

        return redirect(get_redirect_target() or url_for(endpoint, **values))


class VerifyPassword(object):
    def __init__(self):
        self.message = 'Bad password'

    def __call__(self, form, field):
        with db_session:
            user = Users.get(id=current_user.id)
            if not user or not user.verify_password(field.data):
                raise ValidationError(self.message)


class Profile(CustomForm):
    name = StringField('Name Surname', [validators.DataRequired()])
    status = StringField('Status')
    job = StringField('Organization')
    town = StringField('Town')
    country = SelectField('Country', [validators.DataRequired()], choices=[(x.alpha_3, x.name) for x in countries])
    submit_btn = SubmitField('Update Profile')


class Email(CustomForm):
    email = StringField('Email', [validators.DataRequired(), validators.Email(), CheckUserExist()])


class Password(CustomForm):
    password = PasswordField('Password', [validators.DataRequired(),
                                          validators.EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Repeat Password', [validators.DataRequired()])


class Registration(Profile, Password):
    email = StringField('Email', [validators.DataRequired(), validators.Email(), CheckUserFree()])
    submit_btn = SubmitField('Register')

    __order = ('csrf_token', 'next', 'email', 'password', 'confirm', 'name',
               'status', 'job', 'town', 'country', 'submit_btn')

    def __init__(self, *args, **kwargs):
        self._order = ['%s%s' % ('prefix' in kwargs and '%s-' % kwargs['prefix'] or '', x) for x in self.__order]
        super(Registration, self).__init__(*args, **kwargs)


class Login(Email):
    password = PasswordField('Password', [validators.DataRequired()])
    remember = BooleanField('Remember me')
    submit_btn = SubmitField('Log in')


class ReLogin(CustomForm):
    password = PasswordField('Password', [validators.DataRequired(), VerifyPassword()])
    submit_btn = SubmitField('Log out')


class ChangePassword(Password):
    old_password = PasswordField('Old Password', [validators.DataRequired(), VerifyPassword()])
    submit_btn = SubmitField('Change Password')


class ForgotPassword(CustomForm):
    email = StringField('Email', [validators.DataRequired(), validators.Email()])
    submit_btn = SubmitField('Restore')


class ChangeRole(Email):
    role_type = SelectField('Role Type', [validators.DataRequired()],
                            choices=[(x.value, x.name) for x in UserRole], coerce=int)
    submit_btn = SubmitField('Change Role')

    @property
    def type(self):
        return UserRole(self.role_type.data)


class BanUser(Email):
    submit_btn = SubmitField('Ban User')


class Post(CustomForm):
    title = StringField('Title', [validators.DataRequired()])
    body = TextAreaField('Message', [validators.DataRequired()])
    banner = FileField('Image', validators=[FileAllowed('jpg jpe jpeg png gif svg bmp'.split(), 'Images only')])
    attachment = FileField('Attachment', validators=[FileAllowed('doc docx odt rtf'.split(), 'Documents only')])


class Meeting(Post):
    participation = SelectField('Participation Type', [validators.DataRequired()],
                                choices=[(x.value, x.name) for x in MeetingPost], coerce=int)
    submit_btn = SubmitField('Meet Up')

    @property
    def special(self):
        return dict(participation=self.participation.data)


class NewPost(Post):
    slug = StringField('Slug')
    special_field = StringField('Special', [validators.Optional(), JsonValidator()])
    post_type = SelectField('Post Type', [validators.DataRequired()],
                            choices=[(x.value, x.name) for x in BlogPost], coerce=int)
    submit_btn = SubmitField('Post')

    @property
    def type(self):
        return BlogPost(self.post_type.data)

    @property
    def special(self):
        if self.special_field.data:
            tmp = loads(self.special_field.data)
            if isinstance(tmp, dict):
                return tmp
        return None
