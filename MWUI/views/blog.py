# -*- coding: utf-8 -*-
#
#  Copyright 2017 Ramil Nugmanov <stsouko@live.ru>
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
from flask import redirect, url_for, render_template, flash
from flask.views import View
from flask_login import login_required, current_user
from pony.orm import db_session, select
from ..bootstrap import Pagination
from ..config import BLOG_POSTS_PER_PAGE
from ..constants import UserRole, MeetingPostType
from ..models import Email, Meeting, Post, Thesis, Subscription


def blog_viewer(page, query, redirect_url, title, subtitle, crumb=None):
    if page < 1:
        return redirect(url_for(redirect_url))

    pag = Pagination(page, query.count(), pagesize=BLOG_POSTS_PER_PAGE)
    if page != pag.page:
        return redirect(url_for(redirect_url))

    posts = list(query.page(page, pagesize=BLOG_POSTS_PER_PAGE))
    return render_template("blog.html", paginator=pag, posts=posts, title=title, subtitle=subtitle, crumb=crumb)


class BlogView(View):
    methods = ['GET']
    decorators = [db_session]

    def dispatch_request(self, page=1):
        q = select(x for x in Post
                   if x.classtype not in ('Thesis', 'Email')
                   and x.post_type not in (MeetingPostType.COMMON.value, MeetingPostType.SUBMISSION.value,
                                           MeetingPostType.REGISTRATION.value)).order_by(Post.date.desc())
        return blog_viewer(page, q, '.blog', 'News', 'list')


class AbstractsView(View):
    methods = ['GET']
    decorators = [db_session]
    txt = '''Abstract here are the ones submitted by participants. If you want to submit it,
             please log in to the site, confirm your participation in the Conference
             and then follow submission procedure.'''

    def dispatch_request(self, event, page=1):
        m = Meeting.get(id=event, post_type=MeetingPostType.MEETING.value)
        if not m:
            return redirect(url_for('.blog'))

        flash(self.txt, 'warning')

        q = select(x for x in Thesis if x.post_parent == m).order_by(Thesis.id.desc())
        return blog_viewer(page, q, '.participants', m.title, 'Abstracts',
                           crumb=dict(url=url_for('.blog_post', post=event), title='Abstracts',
                                      parent='Event main page'))


class EmailsView(View):
    methods = ['GET']
    decorators = [db_session, login_required]

    def dispatch_request(self, page=1):
        if not current_user.role_is(UserRole.ADMIN):
            return redirect(url_for('.index'))

        q = select(x for x in Email).order_by(Email.id.desc())
        return blog_viewer(page, q, '.emails', 'E-mail templates', 'list')


class ThesesView(View):
    methods = ['GET']
    decorators = [db_session, login_required]

    def dispatch_request(self, page=1):
        q = select(x for x in Thesis if x.author.id == current_user.id).order_by(Thesis.id.desc())
        return blog_viewer(page, q, '.theses', 'Events', 'Abstracts')


class EventsView(View):
    methods = ['GET']
    decorators = [db_session, login_required]

    def dispatch_request(self, page=1):
        q = select(x.meeting for x in Subscription if x.user == current_user.get_user()).order_by(Meeting.id.desc())
        return blog_viewer(page, q, '.events', 'Events', 'Participation')
