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
import uuid
from .forms import (Login, Registration, ReLogin, ChangePassword, NewPost, ChangeRole, BanUser, ForgotPassword,
                    Meeting)
from .logins import User
from .models import Users, Blog
from .config import UserRole, BLOG_POSTS, Glyph, UPLOAD_PATH, BlogPost
from .bootstrap import Pagination
from flask import redirect, url_for, render_template, Blueprint, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from pony.orm import db_session, select
from datetime import datetime
from os import path
from io import StringIO


view_bp = Blueprint('view', __name__)


@view_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('.index'))

    registration_form = Registration(prefix='Registration')
    login_form = Login(prefix='Login')
    forgot_form = ForgotPassword(prefix='ForgotPassword')

    forms = [('Welcome Back!', login_form), ('Not Registered?', registration_form), ('Forgot Password?', forgot_form)]

    if login_form.validate_on_submit():
        user = User.get(login_form.email.data, login_form.password.data)
        login_user(user, remember=login_form.remember.data)
        return redirect(url_for('.index'))

    elif registration_form.validate_on_submit():
        with db_session:
            Users(email=registration_form.email.data, password=registration_form.password.data,
                  name=registration_form.name.data, job=registration_form.job.data,
                  town=registration_form.town.data, country=registration_form.country.data,
                  status=registration_form.status.data)
        return redirect(url_for('.login'))

    elif forgot_form.validate_on_submit():
        with db_session:
            if Users.exists(email=forgot_form.email.data):
                pass
            flash('Check your email box', 'warning')
        return redirect(url_for('.login'))

    return render_template('forms.html', forms=forms, title='Login')


@view_bp.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('.login'))


@view_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    re_login_form = ReLogin(prefix='ReLogin')
    change_passwd_form = ChangePassword(prefix='ChangePassword')
    forms = [('Log out on all devices', re_login_form), ('Change Password', change_passwd_form)]

    if re_login_form.validate_on_submit():
        with db_session:
            user = Users.get(id=current_user.id)
            user.change_token()
        logout_user()
        return redirect(url_for('.login'))
    elif change_passwd_form.validate_on_submit():
        with db_session:
            user = Users.get(id=current_user.id)
            user.change_password(change_passwd_form.new_password.data)
        logout_user()
        return redirect(url_for('.login'))

    if current_user.role_is(UserRole.ADMIN):
        new_post_form = NewPost(prefix='NewPost')
        change_role_form = ChangeRole(prefix='ChangeRole')
        ban_form = BanUser(prefix='BanUser')

        forms.extend([('Change User Role', change_role_form), ('Ban User', ban_form)])
        forms.insert(0, ('New Blog Post', new_post_form))

        if new_post_form.validate_on_submit():
            if new_post_form.banner.data:
                banner_name = str(uuid.uuid4())
                new_post_form.banner.data.save(path.join(UPLOAD_PATH, banner_name))
            else:
                banner_name = None

            if new_post_form.attachment.data:
                file_name = str(uuid.uuid4())
                new_post_form.banner.data.save(path.join(UPLOAD_PATH, file_name))
            else:
                file_name = None

            if new_post_form.type == BlogPost.THESIS and new_post_form.part_type.data:
                special = new_post_form.participation.name
            else:
                special = new_post_form.special.data

            with db_session:
                p = Blog(type=new_post_form.type, title=new_post_form.title.data, slug=new_post_form.slug.data,
                         body=new_post_form.body.data, banner=banner_name, special=special,
                         attachment=file_name, author=current_user.get_user())

            return redirect(url_for('.blog_post', post=p.id))

        elif change_role_form.validate_on_submit():
            pass
        elif ban_form.validate_on_submit():
            pass

    return render_template("forms.html", title='Profile', subtitle=current_user.name, forms=forms)


@view_bp.route('/', methods=['GET'])
@view_bp.route('/index', methods=['GET'])
def index():
    with db_session:
        c = select(x for x in Blog if x.post_type == BlogPost.CAROUSEL.value).order_by(Blog.id.desc()).limit(BLOG_POSTS)
        carousel = [dict(banner=url_for('static', filename='uploads/%s' % x.banner),
                         title=x.title, body=x.body[:200]) for x in c]

        ip = select(x for x in Blog if x.post_type == BlogPost.IMPORTANT.value)
        info = [dict(url=url_for('.blog_post', post=x.id), title=x.title, body=x.body[:200])
                for x in ip.order_by(Blog.id.desc()).limit(3)]

        pl = select(x for x in Blog if x.post_type == BlogPost.PROJECTS.value)
        projects = [dict(url=url_for('.blog_post', post=x.id), body=x.body[:100],
                         title=x.title, banner=url_for('static', filename='uploads/%s' % x.banner))
                    for x in pl.order_by(Blog.id.desc())]

    return render_template("home.html", carousel=carousel, projects=projects, info=info, title='Welcome')


@view_bp.route('/blog/', methods=['GET'])
@view_bp.route('/blog/<int:page>', methods=['GET'])
def blog(page=1):
    if page < 1:
        return redirect(url_for('.blog'))

    with db_session:
        q = select(x for x in Blog if x.post_type != BlogPost.THESIS.value)
        count = q.count()
        pag = Pagination(page, count, pagesize=BLOG_POSTS)
        if page != pag.page:
            return redirect(url_for('.blog', page=pag.page))

        msg = [dict(date=x.date.strftime('%B %d, %Y'), glyph=Glyph[x.type.name].value, title=x.title, body=x.body[:500],
                    banner=url_for('static', filename='uploads/%s' % x.banner), url=url_for('.blog_post', post=x.id))
               for x in q.order_by(Blog.id.desc()).page(page,
                                                        pagesize=BLOG_POSTS)] if count > (page - 1) * BLOG_POSTS else []

    return render_template("blog.html", paginator=pag, posts=msg, title='News', subtitle='chart')


@view_bp.route('/blog/post/<int:post>', methods=['GET', 'POST'])
def blog_post(post):
    with db_session:
        p = Blog.get(id=post)
        if not p:
            return redirect(url_for('.blog'))

        if request.args.get('edit') == 'delete' and current_user.role_is(UserRole.ADMIN):
            p.delete()
            return redirect(url_for('.blog'))

        elif request.args.get('edit') == 'edit' and current_user.role_is(UserRole.ADMIN):
            form = NewPost(prefix='Edit', obj=p)
            if form.validate_on_submit():
                p.body = form.body.data
                p.title = form.title.data
                p.slug = form.slug.data
                p.post_type = form.type.value
                p.date = datetime.utcnow()

                if form.special.data:
                    p.special = form.special.data

                if form.banner.data:
                    file_name = str(uuid.uuid4())
                    form.banner.data.save(path.join(UPLOAD_PATH, file_name))
                    p.banner = file_name
        else:
            form = None

        ip = select(x for x in Blog if x.post_type == BlogPost.IMPORTANT.value and x.id != post)
        info = [dict(url=url_for('.blog_post', post=x.id), title=x.title, body=x.body[:200])
                for x in ip.order_by(Blog.id.desc()).limit(3)]

        if p.type == BlogPost.MEETING:
            if current_user.is_authenticated:
                widget = Meeting(prefix='Meeting')
                if widget.validate_on_submit():
                    pass
            else:
                widget = None
        else:
            widget = None

    data = dict(date=p.date.strftime('%B %d, %Y at %H:%M'), title=p.title, widget=widget,
                body=StringIO(p.body), banner=url_for('static', filename='uploads/%s' % p.banner),
                info=info)

    return render_template("post.html", title=p.title, data=data, form=form,
                           editable=current_user.role_is(UserRole.ADMIN))


@view_bp.route('/search', methods=['GET'])
@login_required
def search():
    return render_template("layout.html")


@view_bp.route('/modeling', methods=['GET'])
@login_required
def modeling():
    return render_template("layout.html")


@view_bp.route('/about', methods=['GET'])
def about():
    return render_template("layout.html")


@view_bp.route('/queries', methods=['GET'])
@login_required
def queries():
    return render_template("layout.html")


@view_bp.route('/results', methods=['GET'])
@login_required
def results():
    return render_template("layout.html")


@view_bp.route('/predictor', methods=['GET'])
def predictor():
    return render_template("predictor.html")
