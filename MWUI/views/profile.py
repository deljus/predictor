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
from flask_login import logout_user, login_required, current_user
from pony.orm import db_session, commit
from ..config import UserRole, MeetingPostType, FormRoute
from ..forms import (ReLoginForm, ChangePasswordForm, PostForm, ChangeRoleForm, BanUserForm,
                     ProfileForm, MeetingForm, EmailForm, TeamForm)
from ..models import User, BlogPost, Email, Meeting, TeamPost
from ..upload import combo_save


class ProfileView(View):
    methods = ['GET', 'POST']
    decorators = [db_session, login_required]

    def dispatch_request(self, action=4):
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
                u = User.get(id=current_user.id)
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
                u = User.get(id=current_user.id)
                u.change_token()
                logout_user()
                flash('Successfully logged out from all devices')
                return redirect(url_for('.login'))

        elif form == FormRoute.CHANGE_PASSWORD:
            message = 'Change Password'
            tabs[2]['active'] = True
            active_form = ChangePasswordForm()
            if active_form.validate_on_submit():
                u = User.get(id=current_user.id)
                u.change_password(active_form.password.data)
                logout_user()
                flash('Successfully changed password')
                return redirect(url_for('.login'))

        elif admin and form == FormRoute.NEW_BLOG_POST:
            message = 'New Blog Post'
            tabs[3]['active'] = True
            active_form = PostForm()
            if active_form.validate_on_submit():
                banner_name, file_name = combo_save(active_form.banner_field, active_form.attachment)
                p = BlogPost(type=active_form.type, title=active_form.title.data, slug=active_form.slug.data,
                             body=active_form.body.data, banner=banner_name, attachments=file_name,
                             author=current_user.get_user())
                commit()
                return redirect(url_for('.blog_post', post=p.id))

        elif admin and form == FormRoute.NEW_MEETING_PAGE:
            message = 'New Meeting Page'
            tabs[4]['active'] = True
            active_form = MeetingForm()

            def add_post():
                banner_name, file_name = combo_save(active_form.banner_field, active_form.attachment)
                p = Meeting(meeting=active_form.meeting_id.data, deadline=active_form.deadline.data,
                            poster_deadline=active_form.poster_deadline.data,
                            participation_types=active_form.participation_types, thesis_types=active_form.thesis_types,
                            order=active_form.order.data, type=active_form.type, author=current_user.get_user(),
                            title=active_form.title.data, slug=active_form.slug.data,
                            body_name=active_form.body_name.data, body=active_form.body.data, banner=banner_name,
                            attachments=file_name)
                commit()
                return p.id

            if active_form.validate_on_submit():
                if active_form.type != MeetingPostType.MEETING:
                    if active_form.meeting_id.data and Meeting.exists(id=active_form.meeting_id.data,
                                                                      post_type=MeetingPostType.MEETING.value):
                        return redirect(url_for('.blog_post', post=add_post()))
                    active_form.meeting_id.errors = ['Bad parent']
                else:
                    if active_form.deadline.data and active_form.poster_deadline.data:
                        return redirect(url_for('.blog_post', post=add_post()))
                    active_form.deadline.errors = ["Need deadline"]
                    active_form.poster_deadline.errors = ["Need deadline"]

        elif admin and form == FormRoute.NEW_EMAIL_TEMPLATE:
            message = 'New Email Template'
            tabs[5]['active'] = True
            active_form = EmailForm()

            def add_post():
                banner_name, file_name = combo_save(active_form.banner_field, active_form.attachment)
                p = Email(from_name=active_form.from_name.data, reply_name=active_form.reply_name.data,
                          reply_mail=active_form.reply_mail.data, meeting=active_form.meeting_id.data,
                          type=active_form.type, author=current_user.get_user(),
                          title=active_form.title.data, slug=active_form.slug.data,
                          body=active_form.body.data, banner=banner_name, attachments=file_name)
                commit()
                return p.id

            if active_form.validate_on_submit():
                if active_form.type.is_meeting:
                    if active_form.meeting_id.data and Meeting.exists(id=active_form.meeting_id.data,
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
                banner_name, file_name = combo_save(active_form.banner_field, active_form.attachment)
                p = TeamPost(type=active_form.type, title=active_form.title.data, slug=active_form.slug.data,
                             body=active_form.body.data, banner=banner_name, attachments=file_name,
                             author=current_user.get_user(), role=active_form.role.data, scopus=active_form.scopus.data,
                             order=active_form.order.data)
                commit()
                return redirect(url_for('.blog_post', post=p.id))

        elif admin and form == FormRoute.BAN_USER:
            message = 'Ban User'
            tabs[7]['active'] = True
            active_form = BanUserForm()
            if active_form.validate_on_submit():
                u = User.get(email=active_form.email.data.lower())
                u.active = False
                flash('Successfully banned %s %s (%s)' % (u.name, u.surname, u.email))

        elif admin and form == FormRoute.CHANGE_USER_ROLE:
            message = 'Change Role'
            tabs[8]['active'] = True
            active_form = ChangeRoleForm()
            if active_form.validate_on_submit():
                u = User.get(email=active_form.email.data.lower())
                u.user_role = active_form.type.value
                flash('Successfully changed %s %s (%s) role' % (u.name, u.surname, u.email))

        else:  # admin or GTFO
            return redirect(url_for('.profile'))

        return render_template("forms.html", title='Profile', subtitle=current_user.full_name,
                               tabs=tabs, form=active_form, message=message)
