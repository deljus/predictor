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
            return User(user.id, user.email, user.name, user.active, user.token, user.role)

    return None


class User(UserMixin):
    def __init__(self, _id, email, name, active, token, role):
        self.id = _id
        self.__email = email
        self.__name = name
        self.__active = active
        self.__token = token
        self.__role = role

    @property
    def is_active(self):
        return self.__active

    def get_email(self):
        return self.__email

    def get_name(self):
        return self.__name

    def get_id(self):
        return self.__token

    def get_role(self):
        return self.__role

    @staticmethod
    def get(email, password):
        with db_session:
            user = Users.get(email=email)
            if user and user.verify_password(password):
                return User(user.id, user.email, user.name, user.active, user.token, user.role)
        return None
