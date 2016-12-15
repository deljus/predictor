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
                    Meeting, Profile, DeleteButton, Logout)
from .redirect import get_redirect_target
from .logins import User
from .models import Users, Blog
from .config import UserRole, BLOG_POSTS, Glyph, UPLOAD_PATH, IMAGES_ROOT, BlogPost, LAB_NAME, MeetingPost, FormRoute
from .bootstrap import Pagination
from .sendmail import send_mail
from .scopus import get_articles
from flask import redirect, url_for, render_template, Blueprint, flash, abort
from flask_login import login_user, logout_user, login_required, current_user
from pony.orm import db_session, select, commit
from datetime import datetime
from os import path


conf_pages = (BlogPost.THESIS, BlogPost.SERVICE, BlogPost.MEETING)
view_bp = Blueprint('view', __name__)


def save_upload(field, images=False):
    file_name = '%s%s' % (uuid.uuid4(), path.splitext(field.data.filename)[-1])
    field.data.save(path.join(IMAGES_ROOT if images else UPLOAD_PATH, file_name))
    return file_name


def blog_viewer(page, selector):
    if page < 1:
        return None
    with db_session:
        q = select(x for x in Blog).filter(selector)
        count = q.count()
        pag = Pagination(page, count, pagesize=BLOG_POSTS)
        if page != pag.page:
            return None

        data = []
        for p in q.order_by(Blog.date.desc()).page(page, pagesize=BLOG_POSTS):
            tmp = dict(date=p.date.strftime('%B %d, %Y'), glyph=Glyph[p.type.name].value, title=p.title,
                       banner=p.banner, body=p.body, url=url_for('.blog_post', post=p.id),
                       author='%s %s' % (p.author.name, p.author.surname))
            data.append(tmp)

    return data, pag


@view_bp.errorhandler(404)
def page_not_found(*args, **kwargs):
    return render_template('layout.html', title='404', subtitle='Page not found'), 404


@view_bp.route('/login/', methods=['GET', 'POST'])
@view_bp.route('/login/<int:action>', methods=['GET', 'POST'])
def login(action=1):
    if current_user.is_authenticated:
        return redirect(get_redirect_target() or url_for('.index'))

    if not 1 <= action <= 3:
        return redirect(url_for('.login'))

    form = FormRoute(action)

    tabs = [dict(title='Welcome Back!', glyph='', active=False,
                 url=url_for('.login', action=FormRoute.LOGIN.value, next=get_redirect_target())),
            dict(title='Not Registered?', glyph='', active=False,
                 url=url_for('.login', action=FormRoute.REGISTER.value, next=get_redirect_target())),
            dict(title='Forgot Password?', glyph='', active=False,
                 url=url_for('.login', action=FormRoute.FORGOT.value, next=get_redirect_target()))]

    if form == FormRoute.LOGIN:
        message = 'Log in'
        tabs[0]['active'] = True
        active_form = Login()
        if active_form.validate_on_submit():
            user = User.get(active_form.email.data, active_form.password.data)
            if user:
                login_user(user, remember=active_form.remember.data)
                return active_form.redirect()
            flash('Invalid Credentials', 'warning')

    elif form == FormRoute.REGISTER:
        message = 'Registration'
        tabs[1]['active'] = True
        active_form = Registration()
        if active_form.validate_on_submit():
            with db_session:
                m = active_form.welcome and \
                    select(x for x in Blog if x.post_type == BlogPost.EMAIL.value
                           and x.special['welcome'] == active_form.welcome).first() or \
                    select(x for x in Blog
                           if x.post_type == BlogPost.EMAIL.value and x.special['type'] == 'reg').first()

                u = Users(email=active_form.email.data, password=active_form.password.data,
                          name=active_form.name.data, surname=active_form.surname.data,
                          affiliation=active_form.affiliation.data, position=active_form.position.data,
                          town=active_form.town.data, country=active_form.country.data,
                          status=active_form.status.data, degree=active_form.degree.data)

                send_mail((m and m.body or 'Welcome! %s.') % ('%s %s' % (u.name, u.surname)), u.email,
                          to_name='%s %s' % (u.name, u.surname), subject=m and m.title or 'Welcome',
                          banner=m and m.banner or None, title=m and m.title or None,
                          from_name=m.special.get('from'), reply_mail=m.special.get('mail'),
                          reply_name=m.special.get('name'))

            login_user(User(u), remember=False)
            return active_form.redirect()

    elif form == FormRoute.FORGOT:
        message = 'Restore password'
        tabs[2]['active'] = True
        active_form = ForgotPassword()
        if active_form.validate_on_submit():
            with db_session:
                u = Users.get(email=active_form.email.data)
                if u:
                    m = select(x for x in Blog if x.post_type == BlogPost.EMAIL.value and
                               x.special['type'] == 'rep').first()
                    u.gen_restore()
                    send_mail((m and m.body or '%s\n\nNew password: %s') % ('%s %s' % (u.name, u.surname), u.restore),
                              u.email, to_name='%s %s' % (u.name, u.surname),
                              subject=m and m.title or 'Forgot password?',
                              banner=m and m.banner or None, title=m and m.title or None)
            flash('Check your email box', 'warning')
            return redirect(url_for('.login', next=get_redirect_target()))

    else:
        return redirect(url_for('.login'))

    return render_template('forms.html', form=active_form, title='Authorization', tabs=tabs, message=message)


@view_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    form = Logout()
    if form.validate_on_submit():
        logout_user()
        return redirect(url_for('.login'))

    return render_template('logout.html', form=form, title='Logout')


@view_bp.route('/profile/', methods=['GET', 'POST'])
@view_bp.route('/profile/<int:action>', methods=['GET', 'POST'])
@login_required
def profile(action=4):
    if not 4 <= action <= 9:
        return redirect(url_for('.profile'))

    form = FormRoute(action)
    tabs = [dict(title='Edit Profile', glyph='', active=False,
                 url=url_for('.profile', action=FormRoute.EDIT_PROFILE.value)),
            dict(title='Log out on all devices', glyph='', active=False,
                 url=url_for('.profile', action=FormRoute.LOGOUT_ALL.value)),
            dict(title='Change Password', glyph='', active=False,
                 url=url_for('.profile', action=FormRoute.CHANGE_PASSWORD.value))]

    admin = current_user.role_is(UserRole.ADMIN)
    if admin:
        tabs.extend([dict(title='New Blog Post', glyph='', active=False,
                          url=url_for('.profile', action=FormRoute.NEW_POST.value)),
                     dict(title='Ban User', glyph='', active=False,
                          url=url_for('.profile', action=FormRoute.BAN_USER.value)),
                     dict(title='Change Role', glyph='', active=False,
                          url=url_for('.profile', action=FormRoute.CHANGE_USER_ROLE.value))])

    with db_session:
        if form == FormRoute.EDIT_PROFILE:
            message = 'Edit Profile'
            tabs[0]['active'] = True
            active_form = Profile(obj=current_user.get_user())
            if active_form.validate_on_submit():
                u = Users.get(id=current_user.id)
                u.name = active_form.name.data
                u.surname = active_form.surname.data
                u.country = active_form.country.data
                u.degree = active_form.degree.data
                u.status = active_form.status.data

                if active_form.affiliation.data:
                    u.affiliation = active_form.affiliation.data
                elif u.affiliation:
                    u.affiliation = ''

                if active_form.position.data:
                    u.position = active_form.position.data
                elif u.position:
                    u.position = ''

                if active_form.town.data:
                    u.town = active_form.town.data
                elif u.town:
                    u.town = ''

                flash('Profile updated')

        elif form == FormRoute.LOGOUT_ALL:
            message = 'Log out on all devices'
            tabs[1]['active'] = True
            active_form = ReLogin()
            if active_form.validate_on_submit():
                u = Users.get(id=current_user.id)
                u.change_token()
                logout_user()
                flash('Successfully logged out from all devices')
                return redirect(url_for('.login'))

        elif form == FormRoute.CHANGE_PASSWORD:
            message = 'Change Password'
            tabs[2]['active'] = True
            active_form = ChangePassword()
            if active_form.validate_on_submit():
                u = Users.get(id=current_user.id)
                u.change_password(active_form.password.data)
                logout_user()
                flash('Successfully changed password')
                return redirect(url_for('.login'))

        elif admin and form == FormRoute.NEW_POST:
            message = 'New Blog Post'
            tabs[3]['active'] = True
            active_form = NewPost()
            if active_form.validate_on_submit():
                def add_post(parent=None):
                    banner_name = save_upload(active_form.banner, images=True) if active_form.banner.data else None
                    file_name = save_upload(active_form.attachment) if active_form.attachment.data else None
                    p = Blog(type=active_form.type, title=active_form.title.data, slug=active_form.slug.data,
                             body=active_form.body.data, banner=banner_name, special=active_form.special,
                             attachment=file_name, author=Users.get(id=current_user.id), parent=parent)
                    commit()
                    return redirect(url_for('.blog_post', post=p.id))

                if active_form.type == BlogPost.SERVICE:
                    if active_form.parent_field.data:
                        r = Blog.get(id=active_form.parent_field.data)
                        if r and r.type == BlogPost.MEETING:
                            return add_post(r)

                    active_form.parent_field.errors = ['Need parent']
                elif active_form.type != BlogPost.THESIS:
                    return add_post()
                else:
                    active_form.parent_field.errors = ["DON'T post Thesis!"]

        elif admin and form == FormRoute.BAN_USER:
            message = 'Ban User'
            tabs[4]['active'] = True
            active_form = BanUser()
            if active_form.validate_on_submit():
                pass

        elif admin and form == FormRoute.CHANGE_USER_ROLE:
            message = 'Change Role'
            tabs[5]['active'] = True
            active_form = ChangeRole()
            if active_form.validate_on_submit():
                u = Users.get(email=active_form.email.data)
                u.user_role = active_form.type.value
                flash('Successfully changed %s %s (%s) role' % (u.name, u.surname, u.email))

        else:  # admin or GTFO
            return redirect(url_for('.profile'))

    return render_template("forms.html", title='Profile', subtitle=current_user.name,
                           tabs=tabs, form=active_form, message=message)


@view_bp.route('/', methods=['GET'])
@view_bp.route('/index', methods=['GET'])
def index():
    with db_session:
        c = select(x for x in Blog if x.post_type == BlogPost.CAROUSEL.value
                   and x.banner is not None).order_by(Blog.id.desc()).limit(BLOG_POSTS)
        carousel = [dict(banner=x.banner, url=url_for('.blog_post', post=x.id), title=x.title, body=x.body) for x in c]

        ip = select(x for x in Blog if x.post_type in (BlogPost.IMPORTANT.value, BlogPost.MEETING.value))
        info = [dict(url=url_for('.blog_post', post=x.id), title=x.title, body=x.body, glyph=Glyph[x.type.name].value)
                for x in ip.order_by(Blog.id.desc()).limit(3)]

        pl = select(x for x in Blog if x.post_type == BlogPost.PROJECTS.value)

        projects = []
        for x in pl.order_by(Blog.date.desc()):
            projects.append(dict(url=url_for('.blog_post', post=x.id), body=x.body, title=x.title, banner=x.banner))

    return render_template("home.html", carousel=carousel, projects=dict(list=projects, title='Our Projects'),
                           info=info, title='Welcome to', subtitle=LAB_NAME)


@view_bp.route('/about', methods=['GET'])
def about():
    with db_session:
        a = select(x for x in Blog if x.post_type == BlogPost.ABOUT.value).first()
        if a:
            about_us = dict(body=a.body, title=a.title, url=url_for('.blog_post', post=a.id), banner=a.banner)
        else:
            about_us = None

        p = select(x for x in Blog if x.post_type == BlogPost.CHIEF.value)
        chief = []
        for x in p:
            chief.append(dict(title=x.title, url=url_for('.blog_post', post=x.id), body=x.body, banner=x.banner,
                              role=x.special and x.special.get('role') or 'Researcher',
                              order=x.special and x.special.get('order') or 0))

        p = select(x for x in Blog if x.post_type == BlogPost.TEAM.value).order_by(Blog.id.desc())
        team = []
        for x in p:
            team.append(dict(title=x.title, url=url_for('.blog_post', post=x.id), body=x.body, banner=x.banner))

    return render_template("about.html", title='About', subtitle='Laboratory', about=about_us,
                           data=dict(chief=sorted(chief, key=lambda x: x['order'], reverse=True),
                                     team=team, title='Our Team'))


@view_bp.route('/blog/post/<int:post>', methods=['GET', 'POST'])
def blog_post(post):
    admin = current_user.is_authenticated and current_user.role_is(UserRole.ADMIN)
    edit_post = None
    remove_post_form = None
    special_form = None
    special_field = None
    children = []
    title = None
    info = None

    with db_session:
        p = Blog.get(id=post)
        if not p:
            return redirect(url_for('.blog'))

        """ admin page
        """
        if admin:
            remove_post_form = DeleteButton(prefix='Delete')
            edit_post = NewPost(prefix='Edit', obj=p)
            if remove_post_form.validate_on_submit():
                p.delete()
                remove_post_form.redirect('.blog')
                return redirect(url_for('.blog'))
            elif edit_post.validate_on_submit():
                p.body = edit_post.body.data
                p.title = edit_post.title.data
                p.date = datetime.utcnow()

                if p.type not in conf_pages and edit_post.type not in conf_pages:
                    p.post_type = edit_post.type.value
                if edit_post.parent_field.data and p.type == BlogPost.SERVICE and edit_post.parent_field.data != post:
                    parent = Blog.get(id=edit_post.parent_field.data)
                    if parent and parent.type == BlogPost.MEETING:
                        p.parent = parent
                if edit_post.slug.data:
                    p.slug = edit_post.slug.data

                if edit_post.special:
                    p.special = edit_post.special
                elif p.special:
                    p.special = None

                if edit_post.banner.data:
                    p.banner = save_upload(edit_post.banner, images=True)
                if edit_post.attachment.data:
                    p.attachment = save_upload(edit_post.attachment)

        """ sidebar for nested posts
        """
        if p.type in (BlogPost.MEETING, BlogPost.THESIS, BlogPost.SERVICE):
            _parent = p.parent or p
            for i in _parent.children or []:  # need order
                if i.post_type == BlogPost.SERVICE.value and i.id != post:
                    children.append(dict(title=i.title, url=url_for('.blog_post', post=i.id),
                                         order=i.special and i.special.get('order') or 0))
            children.append(dict(title='Participants', url=url_for('.participants', event=_parent.id), order=20))

        """ SERVICE POST
        """
        if p.type == BlogPost.SERVICE:
            crumb = dict(url=url_for('.blog_post', post=p.parent.id), title=p.title, parent='Event')
            title = p.parent.title
            _type = p.special and p.special.get('type')
            if _type == 'reg':
                if datetime.fromtimestamp(p.parent.special and p.parent.special.get('deadline') or 0) > \
                        datetime.utcnow():
                    if current_user.is_authenticated and not select(x for x in Blog
                                                                    if x.author.id == current_user.id
                                                                    and x.post_type == BlogPost.THESIS.value
                                                                    and x.parent == p.parent).exists():
                        special_form = Meeting(prefix='Meeting')
                        if special_form.validate_on_submit():
                            banner_name = save_upload(special_form.banner,
                                                      images=True) if special_form.banner.data else None
                            file_name = save_upload(special_form.attachment) if special_form.attachment.data else None
                            w = Blog(type=BlogPost.THESIS, title=special_form.title.data, body=special_form.body.data,
                                     banner=banner_name, special=special_form.special, attachment=file_name,
                                     author=Users.get(id=current_user.id), parent=p.parent)
                            commit()

                            m = select(x for x in Blog if x.post_type == BlogPost.EMAIL.value and
                                       x.special['meeting'] == p.parent.id).first()
                            send_mail((m and m.body or '%s\n\nYou registered to meeting') % current_user.name,
                                      current_user.email, to_name=current_user.name,
                                      subject=m and m.title or 'Welcome to meeting',
                                      banner=m and m.banner or None, title=m and m.title or None,
                                      from_name=m.special.get('from'), reply_mail=m.special.get('mail'),
                                      reply_name=m.special.get('name'))
                            flash('Welcome to meeting!')
                            return redirect(url_for('.blog_post', post=w.id))

        elif p.type == BlogPost.THESIS:
            if current_user.is_authenticated and p.author.id == current_user.id and \
                    datetime.fromtimestamp(p.parent.special and p.parent.special.get('deadline') or 0) > \
                    datetime.utcnow():
                p.participation = p.special.get('participation')
                special_form = Meeting(prefix='Meeting', obj=p)
                if special_form.validate_on_submit():
                    p.title = special_form.title.data
                    p.body = special_form.body.data
                    p.special.update(special_form.special)

                    if special_form.banner.data:
                        p.banner = save_upload(special_form.banner, images=True)
                    if special_form.attachment.data:
                        p.attachment = save_upload(special_form.attachment)

            crumb = dict(url=url_for('.blog_post', post=p.parent.id), title='Abstract', parent='Event')
            special_field = '**Presentation Type**: *%s*' % MeetingPost(p.special.get('participation')).fancy
        elif p.type in (BlogPost.CHIEF, BlogPost.TEAM):
            crumb = dict(url=url_for('.about'), title='Member', parent='Laboratory')
            scopus = p.special and p.special.get('scopus')
            if scopus:
                special_field = get_articles(scopus)

        elif p.type == BlogPost.ABOUT:
            crumb = dict(url=url_for('.about'), title='Description', parent='Laboratory')
        else:
            crumb = dict(url=url_for('.blog'), title='Post', parent='News')
            """ collect sidebar
            """
            if p.type != BlogPost.MEETING:
                ip = select(x for x in Blog if x.id != post and x.post_type in (BlogPost.IMPORTANT.value,
                                                                                BlogPost.MEETING.value))
                info = [dict(url=url_for('.blog_post', post=x.id), title=x.title, body=x.body,
                             glyph=Glyph[x.type.name].value) for x in ip.order_by(Blog.date.desc()).limit(3)]

        """ final data preparation
        """
        data = dict(date=p.date.strftime('%B %d, %Y at %H:%M'), title=p.title, body=p.body, banner=p.banner,
                    author='%s %s' % (p.author.name, p.author.surname))
        if p.attachment:
            data['attachment'] = url_for('static', filename='docs/%s' % p.attachment)

    return render_template("post.html", title=title or p.title, post=data, info=info,
                           children=sorted(children, key=lambda x: x['order']),
                           edit_form=edit_post, remove_form=remove_post_form, crumb=crumb,
                           special_form=special_form, special_field=special_field)


@view_bp.route('/search', methods=['GET'])
@login_required
def search():
    return render_template("search.html")


@view_bp.route('/queries', methods=['GET'])
@login_required
def queries():
    return render_template("layout.html")


@view_bp.route('/results', methods=['GET'])
@login_required
def results():
    return render_template("layout.html")


@view_bp.route('/predictor', methods=['GET'])
@login_required
def predictor():
    return render_template("predictor.html")


@view_bp.route('/blog/', methods=['GET'])
@view_bp.route('/blog/<int:page>', methods=['GET'])
def blog(page=1):
    res = blog_viewer(page, lambda x: x.post_type not in (BlogPost.THESIS.value, BlogPost.EMAIL.value,
                                                          BlogPost.SERVICE.value))
    if not res:
        return redirect(url_for('.blog'))

    return render_template("blog.html", paginator=res[1], posts=res[0], title='News', subtitle='chart')


@view_bp.route('/events', methods=['GET'])
@view_bp.route('/events/<int:page>', methods=['GET'])
@login_required
def events(page=1):
    res = blog_viewer(page, lambda x: x.post_type == BlogPost.THESIS.value and x.author.id == current_user.id)
    if not res:
        return redirect(url_for('.events'))

    return render_template("blog.html", paginator=res[1], posts=res[0], title='Events', subtitle='Presentations')


@view_bp.route('/participants/<int:event>', methods=['GET'])
@view_bp.route('/participants/<int:event>/<int:page>', methods=['GET'])
@login_required
def participants(event, page=1):
    with db_session:
        b = Blog.get(id=event, post_type=BlogPost.MEETING.value)
    if not b:
        return redirect(url_for('.blog'))

    res = blog_viewer(page, lambda x: x.post_type == BlogPost.THESIS.value and x.parent.id == event)
    if not res:
        return redirect(url_for('.participants', event=event))

    return render_template("blog.html", paginator=res[1], posts=res[0], title=b.title, subtitle='Participants',
                           crumb=dict(url=url_for('.blog_post', post=event), title='Presentations', parent='Event'))


@view_bp.route('/emails', methods=['GET'])
@view_bp.route('/emails/<int:page>', methods=['GET'])
@login_required
def emails(page=1):
    if not current_user.role_is(UserRole.ADMIN):
        return redirect(url_for('.index'))

    res = blog_viewer(page, lambda x: x.post_type == BlogPost.EMAIL.value)
    if not res:
        return redirect(url_for('.emails'))

    return render_template("blog.html", paginator=res[1], posts=res[0], title='E-mail templates', subtitle='list')


@view_bp.route('/<string:slug>/')
def slug(slug):
    with db_session:
        p = Blog.get(slug=slug)
        if not p:
            abort(404)
    return redirect(url_for('.blog_post', post=p.id))
