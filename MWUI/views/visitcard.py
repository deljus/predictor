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
from flask import render_template
from flask.views import View
from pony.orm import db_session, select
from ..config import BLOG_POSTS_PER_PAGE, LAB_NAME
from ..constants import BlogPostType, MeetingPostType, TeamPostType
from ..models import BlogPost, Post, TeamPost


class IndexView(View):
    methods = ['GET']
    decorators = [db_session]

    def dispatch_request(self):
        c = select(x for x in BlogPost if x.post_type == BlogPostType.CAROUSEL.value
                   and x.banner is not None).order_by(BlogPost.id.desc()).limit(BLOG_POSTS_PER_PAGE)
        ip = select(x for x in Post if x.post_type in (BlogPostType.IMPORTANT.value,
                                                       MeetingPostType.MEETING.value)).order_by(Post.id.desc()).limit(3)

        return render_template("home.html", carousel=c, info=ip, title='Welcome to', subtitle=LAB_NAME)


class AboutView(View):
    methods = ['GET']
    decorators = [db_session]

    def dispatch_request(self):
        about_us = select(x for x in BlogPost if x.post_type == BlogPostType.ABOUT.value).first()
        chief = select(x for x in TeamPost if x.post_type == TeamPostType.CHIEF.value).order_by(lambda x:
                                                                                                x.special['order'])
        team = select(x for x in TeamPost if x.post_type == TeamPostType.TEAM.value).order_by(TeamPost.id.desc())
        return render_template("about.html", title='About', subtitle='Laboratory', about=about_us,
                               chief=(chief[x: x + 3] for x in range(0, len(chief), 3)),
                               team=(team[x: x + 3] for x in range(0, len(team), 3)))


class StudentsView(View):
    methods = ['GET']
    decorators = [db_session]

    def dispatch_request(self):
        studs = select(x for x in TeamPost if x.post_type == TeamPostType.STUDENT.value).order_by(TeamPost.id.desc())
        return render_template("students.html", title='Laboratory', subtitle='students',
                               students=(studs[x: x + 4] for x in range(0, len(studs), 4)))


class LessonsView(View):
    methods = ['GET']
    decorators = [db_session]

    def dispatch_request(self):
        less = select(x for x in BlogPost if x.post_type == BlogPostType.LESSON.value).order_by(BlogPost.id.desc())
        return render_template("lessons.html", title='Master', subtitle='courses',
                               lessons=(less[x: x + 3] for x in range(0, len(less), 3)))

