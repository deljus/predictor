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
from flask_login import UserMixin
from pony.orm import db_session
from .models import User


def load_user(token):
    with db_session:
        user = User.get(token=token)

    if user:
        return UserLogin(user)

    return None


class UserLogin(UserMixin):
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
    def full_name(self):
        return self.__user.full_name

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
            user = User.get(email=email)
            if user and user.verify_password(password):
                return UserLogin(user)
            elif user and user.verify_restore(password):
                user.gen_restore()
                user.change_token()
                user.change_password(password)
                return UserLogin(user)
        return None
