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
from app.models import Users
from flask_wtf import Form
from pony.orm import db_session
from wtforms import StringField, validators, BooleanField, SubmitField, PasswordField, ValidationError


class CheckEmailExist(object):
    def __init__(self):
        self.message = 'User exist'

    def __call__(self, form, field):
        with db_session:
            if Users.exists(email=field.data):
                raise ValidationError(self.message)


class Registration(Form):
    email = StringField('Email', [validators.DataRequired(), validators.Email(), CheckEmailExist()])
    password = PasswordField('Password', [validators.DataRequired(),
                                          validators.EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Repeat Password', [validators.DataRequired()])
    submit_btn = SubmitField('Register')


class Login(Form):
    email = StringField('Email', [validators.DataRequired(), validators.Email()])
    password = PasswordField('Password', [validators.DataRequired()])
    remember = BooleanField('Remember me')
    submit_btn = SubmitField('Enter')
