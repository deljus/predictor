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
from .models import Users
from .config import BlogPost, UserRole
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from flask_login import current_user
from pony.orm import db_session
from wtforms import (StringField, validators, BooleanField, SubmitField, PasswordField, ValidationError, TextAreaField,
                     SelectField)


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


class VerifyPassword(object):
    def __init__(self):
        self.message = 'Bad password'

    def __call__(self, form, field):
        with db_session:
            user = Users.get(id=current_user.id)
            if not user or not user.verify_password(field.data):
                raise ValidationError(self.message)


class Registration(FlaskForm):
    email = StringField('Email', [validators.DataRequired(), validators.Email(), CheckUserFree()])
    password = PasswordField('Password', [validators.DataRequired(),
                                          validators.EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Repeat Password', [validators.DataRequired()])
    submit_btn = SubmitField('Register')


class Login(FlaskForm):
    email = StringField('Email', [validators.DataRequired(), validators.Email(), CheckUserExist()])
    password = PasswordField('Password', [validators.DataRequired()])
    remember = BooleanField('Remember me')
    submit_btn = SubmitField('Log in')


class ReLogin(FlaskForm):
    password = PasswordField('Password', [validators.DataRequired(), VerifyPassword()])
    submit_btn = SubmitField('Log out')


class ChangePassword(FlaskForm):
    password = PasswordField('Old Password', [validators.DataRequired(), VerifyPassword()])
    new_password = PasswordField('Password', [validators.DataRequired(),
                                              validators.EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Repeat Password', [validators.DataRequired()])
    submit_btn = SubmitField('Change Password')


class ForgotPassword(FlaskForm):
    email = StringField('Email', [validators.DataRequired(), validators.Email()])
    submit_btn = SubmitField('Restore')


class ChangeRole(FlaskForm):
    email = StringField('User Email', validators=[validators.DataRequired(), CheckUserExist()])
    role_type = SelectField('Post Type', [validators.DataRequired()],
                            choices=[(x.name, x.name) for x in UserRole])
    submit_btn = SubmitField('Change Role')

    @property
    def type(self):
        return UserRole(self.role_type.data)


class BanUser(FlaskForm):
    email = StringField('User Email', [validators.DataRequired(), CheckUserExist()])
    submit_btn = SubmitField('Ban User')


class NewPost(FlaskForm):
    title = StringField('Title', [validators.DataRequired()])
    slug = StringField('Slug', [validators.DataRequired()])
    body = TextAreaField('Message', [validators.DataRequired()])
    banner = FileField('Image', validators=[FileAllowed('jpg jpe jpeg png gif svg bmp'.split(), 'Images only')])
    special = StringField('Special')
    post_type = SelectField('Post Type', [validators.DataRequired()],
                            choices=[(x.name, x.name) for x in BlogPost])
    submit_btn = SubmitField('Post')

    @property
    def type(self):
        return BlogPost[self.post_type.data]
