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
from flask_login import UserMixin
from pony.orm import db_session


def load_user(token):
    with db_session:
        user = Users.get(token=token)

    if user:
        return User(user)

    return None


class User(UserMixin):
    def __init__(self, user):
        self.__user = user

    def get_user(self):
        return self.__user

    @property
    def id(self):
        return self.__user.id

    @property
    def is_active(self):
        return self.__user.active

    @property
    def email(self):
        return self.__user.email

    @property
    def name(self):
        return '%s %s' % (self.__user.name, self.__user.surname)

    def get_id(self):
        return self.__user.token

    @property
    def role(self):
        return self.__user.role

    def role_is(self, role):
        return self.__user.role == role

    @staticmethod
    def get(email, password):
        with db_session:
            user = Users.get(email=email)
            if user and user.verify_password(password):
                return User(user)
            elif user and user.verify_restore(password):
                user.gen_restore()
                user.change_token()
                user.change_password(password)
                return User(user)
        return None
