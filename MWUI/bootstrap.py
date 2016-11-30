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
from flask import request
from flask_login import current_user
from flask_nav.elements import View, NavigationItem, Navbar, Separator, Subgroup
from flask_bootstrap.nav import BootstrapRenderer
from hashlib import sha1
from dominate import tags
from .config import LAB_SHORT, UserRole
from .redirect import get_redirect_target


class LeftSubgroup(NavigationItem):
    """Nested substructure.
    :param items: Any number of :class:`.NavigationItem` instances  that
                  make up the navigation element.
    """
    def __init__(self, *items):
        self.items = items

    @property
    def active(self):
        return any(item.active for item in self.items)


class RightSubgroup(NavigationItem):
    """Nested substructure.
    :param items: Any number of :class:`.NavigationItem` instances  that
                  make up the navigation element.
    """
    def __init__(self, *items):
        self.items = items

    @property
    def active(self):
        return any(item.active for item in self.items)


class CustomBootstrapRenderer(BootstrapRenderer):
    def __init__(self, **kwargs):
        BootstrapRenderer.__init__(self)

    def visit_Navbar(self, node):
        node_id = self.id or sha1(str(id(node)).encode()).hexdigest()

        root = tags.nav() if self.html5 else tags.div(role='navigation')
        root['class'] = 'navbar navbar-inverse navbar-fixed-top'

        cont = root.add(tags.div(_class='container'))

        # collapse button
        header = cont.add(tags.div(_class='navbar-header'))
        btn = header.add(tags.button(**{'type': 'button', 'class': 'navbar-toggle collapsed', 'data-toggle': 'collapse',
                                        'data-target': '#' + node_id, 'aria-expanded': 'false',
                                        'aria-controls': 'navbar'}))

        btn.add(tags.span('Toggle navigation', _class='sr-only'))
        btn.add(tags.span(_class='icon-bar'))
        btn.add(tags.span(_class='icon-bar'))
        btn.add(tags.span(_class='icon-bar'))

        # title may also have a 'get_url()' method, in which case we render
        # a brand-link
        if node.title is not None:
            if hasattr(node.title, 'get_url'):
                header.add(tags.a(node.title.text, _class='navbar-brand', href=node.title.get_url()))
            else:
                header.add(tags.span(node.title, _class='navbar-brand'))

        bar = cont.add(tags.div(_class='navbar-collapse collapse', id=node_id))

        for item in node.items:
            bar.add(self.visit(item))

        return root

    def visit_LeftSubgroup(self, node):
        bar_list = tags.ul(_class='nav navbar-nav')
        for item in node.items:
            bar_list.add(self.visit(item))

        return bar_list

    def visit_RightSubgroup(self, node):
        bar_list = tags.ul(_class='nav navbar-nav navbar-right')
        for item in node.items:
            bar_list.add(self.visit(item))

        return bar_list


class Pagination(object):
    def __init__(self, page, total_count, pagesize=10):
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


def top_nav():
    if current_user.is_authenticated:
        user_menu = [View('Modeling Results', '.results'), View('Queries History', '.queries'), Separator(),
                     View('My Events', '.events'),
                     View('Profile', '.profile'), Separator(), View('Logout', '.logout')]
        if current_user.role_is(UserRole.ADMIN):
            user_menu.insert(4, View('Email Templates', '.emails'))

        navbar = [LeftSubgroup(View('News', '.blog'), View('About Us', '.about')),
                  RightSubgroup(View('Search', '.search'), View('Modeling', '.predictor'),
                                Subgroup(current_user.name, *user_menu))
                  ]
    else:
        navbar = [LeftSubgroup(View('News', '.blog'), View('About Us', '.about')),
                  RightSubgroup(View('Login', '.login', next=get_redirect_target() or request.path),
                                View('Registration', '.registration', next=get_redirect_target() or request.path))]

    return Navbar(View(LAB_SHORT, '.index'), *navbar)
