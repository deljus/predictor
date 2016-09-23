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
from math import ceil
from flask_login import current_user
from flask_nav.elements import *


def top_nav():
    if current_user.is_authenticated:
        navbar = [Subgroup(current_user.get_email(), View('Profile', '.index'), Separator(), View('Logout', '.logout')),
                  View('Search', '.search'), View('Modeling', '.modeling'), View('Results', '.results'),
                  View('Queries', '.queries')]
    else:
        navbar = [View('Login', '.login'), View('Registration', '.registration')]

    return Navbar('Predictor', *navbar)


class Pagination(object):
    def __init__(self, page, total_count, pagesize=50):
        self.per_page = pagesize
        self.total_count = total_count or 1
        self.page = page if total_count >= (page - 1) * pagesize else self.pages

    @property
    def pages(self):
        return int(ceil(self.total_count / self.per_page))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def prev_num(self):
        return self.page - 1

    @property
    def next_num(self):
        return self.page + 1

    @property
    def offset(self):
        return (self.page - 1) * self.per_page

    def iter_pages(self):
        return range(1, self.pages + 1)
