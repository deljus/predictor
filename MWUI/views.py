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
from .forms import (LoginForm, RegistrationForm, ReLoginForm, ChangePasswordForm, PostForm, ChangeRoleForm, BanUserForm,
                    ForgotPasswordForm, ProfileForm, DeleteButtonForm, LogoutForm, MeetingForm, EmailForm, ThesisForm,
                    TeamForm)
from .redirect import get_redirect_target
from .logins import User
from .models import Users, BlogPosts, Emails, Meetings, Posts, TeamPosts, Theses, Attachments
from .config import (UserRole, BLOG_POSTS_PER_PAGE, UPLOAD_PATH, IMAGES_ROOT, BlogPostType, LAB_NAME, MeetingPostType,
                     FormRoute, EmailPostType, TeamPostType)
from .bootstrap import Pagination
from .sendmail import send_mail
from .scopus import get_articles
from flask import redirect, url_for, render_template, Blueprint, flash, abort, make_response, request
from flask_login import login_user, logout_user, login_required, current_user
from pony.orm import db_session, select, commit
from datetime import datetime
from os import path
from werkzeug.utils import secure_filename


view_bp = Blueprint('view', __name__)


def save_upload(field, images=False):
    ext = path.splitext(field.filename)[-1].lower()
    file_name = '%s%s' % (uuid.uuid4(), ext)
    field.save(path.join(IMAGES_ROOT if images else UPLOAD_PATH, file_name))
    if images:
        return file_name
    else:
        s_name = secure_filename(field.filename).lower()
        if s_name == ext[1:]:
            s_name = 'document%s' % ext
        return file_name, s_name


def combo_save(banner, attachment):
    banner_name = save_upload(banner.data, images=True) if banner.data else None
    file_name = [save_upload(attachment.data)] if attachment.data else None
    return banner_name, file_name


def blog_viewer(page, query, redirect_url, title, subtitle, crumb=None):
    if page < 1:
        return redirect(url_for(redirect_url))

    pag = Pagination(page, query.count(), pagesize=BLOG_POSTS_PER_PAGE)
    if page != pag.page:
        return redirect(url_for(redirect_url))

    posts = list(query.page(page, pagesize=BLOG_POSTS_PER_PAGE))
    return render_template("blog.html", paginator=pag, posts=posts, title=title, subtitle=subtitle, crumb=crumb)


@view_bp.errorhandler(404)
def page_not_found(*args, **kwargs):
    return render_template('layout.html', title='404', subtitle='Page not found'), 404


@view_bp.route('/login/', methods=['GET', 'POST'])
@view_bp.route('/login/<int:action>', methods=['GET', 'POST'])
def login(action=1):
    if current_user.is_authenticated:
        return redirect(get_redirect_target() or url_for('.index'))

    form = FormRoute.get(action)
    if not form or not form.is_login():
        return redirect(url_for('.login'))

    tabs = [dict(title='Welcome Back!', glyph='', active=False,
                 url=url_for('.login', action=FormRoute.LOGIN.value, next=get_redirect_target())),
            dict(title='Not Registered?', glyph='', active=False,
                 url=url_for('.login', action=FormRoute.REGISTER.value, next=get_redirect_target())),
            dict(title='Forgot Password?', glyph='', active=False,
                 url=url_for('.login', action=FormRoute.FORGOT.value, next=get_redirect_target()))]

    if form == FormRoute.LOGIN:
        message = 'Log in'
        tabs[0]['active'] = True
        active_form = LoginForm()
        if active_form.validate_on_submit():
            user = User.get(active_form.email.data.lower(), active_form.password.data)
            if user:
                login_user(user, remember=active_form.remember.data)
                return active_form.redirect()
            flash('Invalid Credentials', 'warning')

    elif form == FormRoute.REGISTER:
        message = 'Registration'
        tabs[1]['active'] = True
        active_form = RegistrationForm()
        if active_form.validate_on_submit():
            with db_session:
                mid = request.cookies.get('meeting')
                meeting = mid and mid.isdigit() and Meetings.get(id=int(mid))
                m = meeting and Emails.get(post_parent=meeting.meeting,
                                           post_type=EmailPostType.MEETING_REGISTRATION.value) or \
                    select(x for x in Emails if x.post_type == EmailPostType.REGISTRATION.value).first()

                u = Users(email=active_form.email.data.lower(), password=active_form.password.data,
                          name=active_form.name.data, surname=active_form.surname.data,
                          affiliation=active_form.affiliation.data, position=active_form.position.data,
                          town=active_form.town.data, country=active_form.country.data,
                          status=active_form.status.data, degree=active_form.degree.data)

                send_mail((m and m.body or 'Welcome! %s.') % ('%s %s' % (u.name, u.surname)), u.email,
                          to_name='%s %s' % (u.name, u.surname), subject=m and m.title or 'Welcome',
                          banner=m and m.banner, title=m and m.title,
                          from_name=m and m.from_name, reply_mail=m and m.reply_mail, reply_name=m and m.reply_name)

            login_user(User(u), remember=False)
            return active_form.redirect()

    elif form == FormRoute.FORGOT:
        message = 'Restore password'
        tabs[2]['active'] = True
        active_form = ForgotPasswordForm()
        if active_form.validate_on_submit():
            with db_session:
                u = Users.get(email=active_form.email.data.lower())
                if u:
                    m = select(x for x in Emails if x.post_type == EmailPostType.FORGOT.value).first()
                    restore = u.gen_restore()
                    send_mail((m and m.body or '%s\n\nNew password: %s') % ('%s %s' % (u.name, u.surname), restore),
                              u.email, to_name='%s %s' % (u.name, u.surname),
                              subject=m and m.title or 'Forgot password?',
                              banner=m and m.banner, title=m and m.title,
                              from_name=m and m.from_name, reply_mail=m and m.reply_mail, reply_name=m and m.reply_name)
            flash('Check your email box', 'warning')
            return redirect(url_for('.login', next=get_redirect_target()))

    else:
        return redirect(url_for('.login'))

    return render_template('forms.html', form=active_form, title='Authorization', tabs=tabs, message=message)


@view_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    form = LogoutForm()
    if form.validate_on_submit():
        logout_user()
        return redirect(url_for('.login'))

    return render_template('button.html', form=form, title='Logout')


@view_bp.route('/profile/', methods=['GET', 'POST'])
@view_bp.route('/profile/<int:action>', methods=['GET', 'POST'])
@login_required
@db_session
def profile(action=4):
    form = FormRoute.get(action)
    if not form or not form.is_profile():
        return redirect(url_for('.profile'))

    tabs = [dict(title='Edit Profile', glyph='pencil', active=False,
                 url=url_for('.profile', action=FormRoute.EDIT_PROFILE.value)),
            dict(title='Log out on all devices', glyph='remove', active=False,
                 url=url_for('.profile', action=FormRoute.LOGOUT_ALL.value)),
            dict(title='Change Password', glyph='qrcode', active=False,
                 url=url_for('.profile', action=FormRoute.CHANGE_PASSWORD.value))]

    admin = current_user.role_is(UserRole.ADMIN)
    if admin:
        tabs.extend([dict(title='New Blog Post', glyph='font', active=False,
                          url=url_for('.profile', action=FormRoute.NEW_BLOG_POST.value)),
                     dict(title='New Meeting Page', glyph='resize-small', active=False,
                          url=url_for('.profile', action=FormRoute.NEW_MEETING_PAGE.value)),
                     dict(title='New Email Template', glyph='envelope', active=False,
                          url=url_for('.profile', action=FormRoute.NEW_EMAIL_TEMPLATE.value)),
                     dict(title='New Team Member', glyph='knight', active=False,
                          url=url_for('.profile', action=FormRoute.NEW_MEMBER_PAGE.value)),
                     dict(title='Ban User', glyph='remove-circle', active=False,
                          url=url_for('.profile', action=FormRoute.BAN_USER.value)),
                     dict(title='Change Role', glyph='arrow-up', active=False,
                          url=url_for('.profile', action=FormRoute.CHANGE_USER_ROLE.value))])

    if form == FormRoute.EDIT_PROFILE:
        message = 'Edit Profile'
        tabs[0]['active'] = True
        active_form = ProfileForm(obj=current_user.get_user())
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
        active_form = ReLoginForm()
        if active_form.validate_on_submit():
            u = Users.get(id=current_user.id)
            u.change_token()
            logout_user()
            flash('Successfully logged out from all devices')
            return redirect(url_for('.login'))

    elif form == FormRoute.CHANGE_PASSWORD:
        message = 'Change Password'
        tabs[2]['active'] = True
        active_form = ChangePasswordForm()
        if active_form.validate_on_submit():
            u = Users.get(id=current_user.id)
            u.change_password(active_form.password.data)
            logout_user()
            flash('Successfully changed password')
            return redirect(url_for('.login'))

    elif admin and form == FormRoute.NEW_BLOG_POST:
        message = 'New Blog Post'
        tabs[3]['active'] = True
        active_form = PostForm()
        if active_form.validate_on_submit():
            banner_name, file_name = combo_save(active_form.banner, active_form.attachment)
            p = BlogPosts(type=active_form.type, title=active_form.title.data, slug=active_form.slug.data,
                          body=active_form.body.data, banner=banner_name, attachments=file_name,
                          author=current_user.id)
            commit()
            return redirect(url_for('.blog_post', post=p.id))

    elif admin and form == FormRoute.NEW_MEETING_PAGE:
        message = 'New Meeting Page'
        tabs[4]['active'] = True
        active_form = MeetingForm()

        def add_post():
            banner_name, file_name = combo_save(active_form.banner, active_form.attachment)
            p = Meetings(meeting=active_form.meeting_id.data, deadline=active_form.deadline.data,
                         order=active_form.order.data, type=active_form.type, author=current_user.id,
                         title=active_form.title.data, slug=active_form.slug.data, body_name=active_form.body_name.data,
                         body=active_form.body.data, banner=banner_name, attachments=file_name)
            commit()
            return p.id

        if active_form.validate_on_submit():
            if active_form.type in (MeetingPostType.REGISTRATION, MeetingPostType.COMMON):
                if active_form.meeting_id.data and Meetings.exists(id=active_form.meeting_id.data,
                                                                   post_type=MeetingPostType.MEETING.value):
                    return redirect(url_for('.blog_post', post=add_post()))
                active_form.meeting_id.errors = ['Bad parent']
            else:
                if active_form.deadline.data:
                    return redirect(url_for('.blog_post', post=add_post()))
                active_form.deadline.errors = ["Need deadline"]

    elif admin and form == FormRoute.NEW_EMAIL_TEMPLATE:
        message = 'New Email Template'
        tabs[5]['active'] = True
        active_form = EmailForm()

        def add_post():
            banner_name, file_name = combo_save(active_form.banner, active_form.attachment)
            p = Emails(from_name=active_form.from_name.data, reply_name=active_form.reply_name.data,
                       reply_mail=active_form.reply_mail.data, meeting=active_form.meeting_id.data,
                       type=active_form.type, author=current_user.id,
                       title=active_form.title.data, slug=active_form.slug.data,
                       body=active_form.body.data, banner=banner_name, attachments=file_name)
            commit()
            return p.id

        if active_form.validate_on_submit():
            if active_form.type.is_meeting:
                if active_form.meeting_id.data and Meetings.exists(id=active_form.meeting_id.data,
                                                                   post_type=MeetingPostType.MEETING.value):
                    return redirect(url_for('.blog_post', post=add_post()))
                active_form.meeting_id.errors = ['Bad parent']
            else:
                return redirect(url_for('.blog_post', post=add_post()))

    elif admin and form == FormRoute.NEW_MEMBER_PAGE:
        message = 'New Member'
        tabs[6]['active'] = True
        active_form = TeamForm()
        if active_form.validate_on_submit():
            banner_name, file_name = combo_save(active_form.banner, active_form.attachment)
            p = TeamPosts(type=active_form.type, title=active_form.title.data, slug=active_form.slug.data,
                          body=active_form.body.data, banner=banner_name, attachments=file_name,
                          author=current_user.id, role=active_form.role.data, scopus=active_form.scopus.data,
                          order=active_form.order.data)
            commit()
            return redirect(url_for('.blog_post', post=p.id))

    elif admin and form == FormRoute.BAN_USER:
        message = 'Ban User'
        tabs[7]['active'] = True
        active_form = BanUserForm()
        if active_form.validate_on_submit():
            u = Users.get(email=active_form.email.data.lower())
            u.active = False
            flash('Successfully banned %s %s (%s)' % (u.name, u.surname, u.email))

    elif admin and form == FormRoute.CHANGE_USER_ROLE:
        message = 'Change Role'
        tabs[8]['active'] = True
        active_form = ChangeRoleForm()
        if active_form.validate_on_submit():
            u = Users.get(email=active_form.email.data.lower())
            u.user_role = active_form.type.value
            flash('Successfully changed %s %s (%s) role' % (u.name, u.surname, u.email))

    else:  # admin or GTFO
        return redirect(url_for('.profile'))

    return render_template("forms.html", title='Profile', subtitle=current_user.name,
                           tabs=tabs, form=active_form, message=message)


@view_bp.route('/', methods=['GET'])
@view_bp.route('/index', methods=['GET'])
@db_session
def index():
    c = select(x for x in BlogPosts if x.post_type == BlogPostType.CAROUSEL.value
               and x.banner is not None).order_by(BlogPosts.id.desc()).limit(BLOG_POSTS_PER_PAGE)
    ip = select(x for x in Posts if x.post_type in (BlogPostType.IMPORTANT.value,
                                                    MeetingPostType.MEETING.value)).order_by(Posts.id.desc()).limit(3)

    return render_template("home.html", carousel=c, info=ip, title='Welcome to', subtitle=LAB_NAME)


@view_bp.route('/about', methods=['GET'])
@db_session
def about():
    about_us = select(x for x in BlogPosts if x.post_type == BlogPostType.ABOUT.value).first()
    chief = select(x for x in TeamPosts if x.post_type == TeamPostType.CHIEF.value).order_by(lambda x:
                                                                                             x.special['order'])
    team = select(x for x in TeamPosts if x.post_type == TeamPostType.TEAM.value).order_by(TeamPosts.id.desc())
    return render_template("about.html", title='About', subtitle='Laboratory', about=about_us,
                           chief=(chief[x: x + 3] for x in range(0, len(chief), 3)),
                           team=(team[x: x + 3] for x in range(0, len(team), 3)))


@view_bp.route('/students', methods=['GET'])
@db_session
def students():
    studs = select(x for x in TeamPosts if x.post_type == TeamPostType.STUDENT.value).order_by(TeamPosts.id.desc())
    return render_template("students.html", title='Laboratory', subtitle='students',
                           students=(studs[x: x + 4] for x in range(0, len(studs), 4)))


@view_bp.route('/lessons', methods=['GET'])
@db_session
def lessons():
    less = select(x for x in BlogPosts if x.post_type == BlogPostType.LESSON.value).order_by(BlogPosts.id.desc())
    return render_template("lessons.html", title='Master', subtitle='courses',
                           lessons=(less[x: x + 3] for x in range(0, len(less), 3)))


@view_bp.route('/page/<int:post>', methods=['GET', 'POST'])
@db_session
def blog_post(post):
    admin = current_user.is_authenticated and current_user.role_is(UserRole.ADMIN)
    edit_post = None
    remove_post_form = None
    special_form = None
    special_field = None
    children = []
    title = None
    info = None
    theses = None

    p = Posts.get(id=post)
    if not p:
        return redirect(url_for('.blog'))

    opened_by_author = current_user.is_authenticated and p.author.id == current_user.id
    downloadable = admin or p.classtype != 'Theses' or opened_by_author
    deletable = admin or p.classtype == 'Theses' and opened_by_author and p.meeting.deadline > datetime.utcnow()
    """ admin page
    """
    if admin:
        remove_post_form = DeleteButtonForm(prefix='delete')
        if p.classtype == 'BlogPosts':
            edit_post = PostForm(obj=p)
        elif p.classtype == 'Meetings':
            edit_post = MeetingForm(obj=p)
        elif p.classtype == 'Theses':
            edit_post = ThesisForm(obj=p)
        elif p.classtype == 'Emails':
            edit_post = EmailForm(obj=p)
        elif p.classtype == 'TeamPosts':
            edit_post = TeamForm(obj=p)
        else:  # BAD POST
            return redirect(url_for('.blog'))

        if remove_post_form.validate_on_submit():
            p.delete()
            return remove_post_form.redirect('.blog')
        elif edit_post.validate_on_submit():
            p.body = edit_post.body.data
            p.title = edit_post.title.data
            p.date = datetime.utcnow()

            if edit_post.slug.data:
                p.slug = edit_post.slug.data

            if edit_post.banner.data:
                p.banner = save_upload(edit_post.banner.data, images=True)

            if edit_post.attachment.data:
                p.add_attachment(*save_upload(edit_post.attachment.data))

            if hasattr(p, 'update_type'):
                try:
                    p.update_type(edit_post.type)
                except:
                    edit_post.post_type.errors = ['Meeting emails can be changed only to meeting Email']

            if hasattr(p, 'update_meeting') and p.can_update_meeting() and edit_post.meeting_id.data:
                p.update_meeting(edit_post.meeting_id.data)

            if hasattr(p, 'update_order') and edit_post.order.data:
                p.update_order(edit_post.order.data)

            if hasattr(p, 'update_role'):
                p.update_role(edit_post.role.data)

            if hasattr(p, 'update_scopus'):
                p.update_scopus(edit_post.scopus.data)

            if hasattr(p, 'update_from_name'):
                p.update_from_name(edit_post.from_name.data)

            if hasattr(p, 'update_reply_name'):
                p.update_reply_name(edit_post.reply_name.data)

            if hasattr(p, 'update_reply_mail'):
                p.update_reply_mail(edit_post.reply_mail.data)

            if hasattr(p, 'update_body_name'):
                p.update_body_name(edit_post.body_name.data)

            if hasattr(p, 'update_deadline') and edit_post.deadline.data:
                p.update_deadline(edit_post.deadline.data)

    """ Meetings sidebar and title
    """
    if p.classtype == 'Meetings':
        title = p.meeting.title
        theses = dict(title='Participants', url=url_for('.participants', event=p.meeting_id))
        children.append(dict(title='Event main page', id=p.meeting_id))
        children.extend(p.meeting.children.
                        filter(lambda x: x.classtype == 'Meetings').order_by(lambda x: x.special['order']))

        if p.type != MeetingPostType.MEETING:
            crumb = dict(url=url_for('.blog_post', post=p.meeting_id), title=p.title, parent='Event main page')

            if p.type == MeetingPostType.REGISTRATION and p.deadline > datetime.utcnow():
                if current_user.is_authenticated and \
                        not select(x for x in Theses
                                   if x.post_parent == p.meeting and x.author.id == current_user.id).exists():

                    special_form = ThesisForm(prefix='special', body_name=p.body_name)
                    if special_form.validate_on_submit():
                        banner_name, file_name = combo_save(special_form.banner, special_form.attachment)
                        t = Theses(p.meeting_id, type=special_form.type,
                                   title=special_form.title.data, body=special_form.body.data,
                                   banner=banner_name, attachments=file_name, author=current_user.id)
                        commit()

                        m = Emails.get(post_parent=p.meeting, post_type=EmailPostType.MEETING_THESIS.value)
                        send_mail((m and m.body or '%s\n\nYou registered to meeting') % current_user.name,
                                  current_user.email, to_name=current_user.name, title=m and m.title,
                                  subject=m and m.title or 'Welcome to meeting', banner=m and m.banner,
                                  from_name=m and m.from_name, reply_mail=m and m.reply_mail,
                                  reply_name=m and m.reply_name)

                        flash('Welcome to meeting!')
                        return redirect(url_for('.blog_post', post=t.id))
        else:
            crumb = dict(url=url_for('.blog'), title='Post', parent='News')

    elif p.classtype == 'Theses':
        if current_user.is_authenticated and opened_by_author and p.meeting.deadline > datetime.utcnow():
            special_form = ThesisForm(prefix='special', obj=p, body_name=p.body_name)
            if special_form.validate_on_submit():
                p.title = special_form.title.data
                p.body = special_form.body.data
                p.update_type(special_form.type)

                if special_form.banner.data:
                    p.banner = save_upload(special_form.banner.data, images=True)
                if special_form.attachment.data:
                    p.add_attachment(*save_upload(special_form.attachment.data))

        crumb = dict(url=url_for('.participants', event=p.meeting_id), title='Abstract', parent='Event participants')
        special_field = '**Presentation Type**: *%s*' % p.type.fancy
    elif p.classtype == 'TeamPosts':
        crumb = dict(url=url_for('.students'), title='Student', parent='Laboratory') if p.type == TeamPostType.STUDENT \
            else dict(url=url_for('.about'), title='Member', parent='Laboratory')
        if p.scopus:
            special_field = get_articles(p.scopus)
    elif p.type == BlogPostType.ABOUT:
        crumb = dict(url=url_for('.about'), title='Description', parent='Laboratory')
    else:
        crumb = dict(url=url_for('.blog'), title='Post', parent='News')
        """ collect sidebar news
        """
        info = select(x for x in Posts
                      if x.id != post and x.post_type in (BlogPostType.IMPORTANT.value,
                                                          MeetingPostType.MEETING.value)).\
            order_by(Posts.date.desc()).limit(3)

    return render_template("post.html", title=title or p.title, post=p, info=info, downloadable=downloadable,
                           children=children, participants=theses, deletable=deletable,
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


@view_bp.route('/news/', methods=['GET'])
@view_bp.route('/news/<int:page>', methods=['GET'])
@db_session
def blog(page=1):
    q = select(x for x in Posts
               if x.classtype not in ('Theses', 'Emails')
               and x.post_type not in (MeetingPostType.COMMON.value,
                                       MeetingPostType.REGISTRATION.value)).order_by(Posts.date.desc())
    return blog_viewer(page, q, '.blog', 'News', 'list')


@view_bp.route('/events', methods=['GET'])
@view_bp.route('/events/<int:page>', methods=['GET'])
@login_required
@db_session
def events(page=1):
    q = select(x for x in Theses if x.author.id == current_user.id).order_by(Theses.id.desc())
    return blog_viewer(page, q, '.events', 'Events', 'Abstracts')


@view_bp.route('/participants/<int:event>', methods=['GET'])
@view_bp.route('/participants/<int:event>/<int:page>', methods=['GET'])
@db_session
def participants(event, page=1):
    m = Meetings.get(id=event, post_type=MeetingPostType.MEETING.value)
    if not m:
        return redirect(url_for('.blog'))

    q = select(x for x in Theses if x.post_parent == m).order_by(Theses.id.desc())
    return blog_viewer(page, q, '.participants', m.title, 'Participants',
                       crumb=dict(url=url_for('.blog_post', post=event), title='Presentations',
                                  parent='Event main page'))


@view_bp.route('/emails', methods=['GET'])
@view_bp.route('/emails/<int:page>', methods=['GET'])
@login_required
@db_session
def emails(page=1):
    if not current_user.role_is(UserRole.ADMIN):
        return redirect(url_for('.index'))

    q = select(x for x in Emails).order_by(Emails.id.desc())
    return blog_viewer(page, q, '.emails', 'E-mail templates', 'list')


@view_bp.route('/<string:slug>/')
def slug(slug):
    with db_session:
        p = Posts.get(slug=slug)
        if not p:
            abort(404)
        resp = make_response(redirect(url_for('.blog_post', post=p.id)))
        if p.classtype == 'Meetings' and p.type == MeetingPostType.MEETING:
            resp.set_cookie('meeting', str(p.id))
    return resp


@view_bp.route('/download/<file>/<name>', methods=['GET'])
@login_required
def download(file, name):
    with db_session:
        a = Attachments.get(file=file)
        if current_user.role_is(UserRole.ADMIN) or a.post.classtype != 'Theses' or a.post.author.id == current_user.id:
            resp = make_response()
            resp.headers['X-Accel-Redirect'] = '/file/%s' % file
            resp.headers['Content-Description'] = 'File Transfer'
            resp.headers['Content-Transfer-Encoding'] = 'binary'
            resp.headers['Content-Disposition'] = 'attachment; filename=%s' % name
            resp.headers['Content-Type'] = 'application/octet-stream'
            return resp
        abort(404)


@view_bp.route('/remove/<file>/<name>', methods=['GET', 'POST'])
@login_required
def remove(file, name):
    form = DeleteButtonForm()
    if form.validate_on_submit():
        with db_session:
            a = Attachments.get(file=file)
            if a and (current_user.role_is(UserRole.ADMIN)
                      or a.post.classtype == 'Theses' and a.post.author.id == current_user.id
                      and a.post.meeting.deadline > datetime.utcnow()):
                a.delete()
        return form.redirect()

    return render_template('button.html', form=form, title='Delete', subtitle=name)
