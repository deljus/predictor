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
from flask import redirect, url_for, render_template, flash, request
from flask.views import View
from flask_login import login_user, logout_user, login_required, current_user
from pony.orm import db_session, select
from ..constants import FormRoute, EmailPostType
from ..forms import LoginForm, RegistrationForm, ForgotPasswordForm, LogoutForm
from ..logins import UserLogin
from ..models import User, Email, Meeting
from ..redirect import get_redirect_target
from ..sendmail import send_mail


class LoginView(View):
    methods = ['GET', 'POST']

    def dispatch_request(self, action=1):
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
                user = UserLogin.get(active_form.email.data.lower(), active_form.password.data)
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
                    meeting = mid and mid.isdigit() and Meeting.get(id=int(mid))
                    m = meeting and Email.get(post_parent=meeting.meeting,
                                              post_type=EmailPostType.MEETING_REGISTRATION.value) or \
                        Email.select(lambda x: x.post_type == EmailPostType.REGISTRATION.value
                                     and not x.post_parent).first()

                    u = User(email=active_form.email.data.lower(), password=active_form.password.data,
                             name=active_form.name.data, surname=active_form.surname.data,
                             affiliation=active_form.affiliation.data, position=active_form.position.data,
                             town=active_form.town.data, country=active_form.country.data,
                             status=active_form.status.data, degree=active_form.degree.data)

                    send_mail((m and m.body or 'Welcome! %s.') % u.full_name, u.email,
                              to_name=u.full_name, subject=m and m.title or 'Welcome',
                              banner=m and m.banner, title=m and m.title,
                              from_name=m and m.from_name, reply_mail=m and m.reply_mail, reply_name=m and m.reply_name)

                login_user(UserLogin(u), remember=False)
                return active_form.redirect()

        elif form == FormRoute.FORGOT:
            message = 'Restore password'
            tabs[2]['active'] = True
            active_form = ForgotPasswordForm()
            if active_form.validate_on_submit():
                with db_session:
                    u = User.get(email=active_form.email.data.lower())
                    if u:
                        m = select(x for x in Email if x.post_type == EmailPostType.FORGOT.value).first()
                        restore = u.gen_restore()
                        send_mail((m and m.body or '%s\n\nNew password: %s') % (u.full_name, restore),
                                  u.email, to_name=u.full_name,
                                  subject=m and m.title or 'Forgot password?',
                                  banner=m and m.banner, title=m and m.title,
                                  from_name=m and m.from_name, reply_mail=m and m.reply_mail,
                                  reply_name=m and m.reply_name)
                flash('Check your email box', 'warning')
                return redirect(url_for('.login', next=get_redirect_target()))

        else:
            return redirect(url_for('.login'))

        return render_template('forms.html', form=active_form, title='Authorization', tabs=tabs, message=message)


class LogoutView(View):
    methods = ['GET', 'POST']
    decorators = [login_required]

    def dispatch_request(self):
        form = LogoutForm()
        if form.validate_on_submit():
            logout_user()
            return redirect(url_for('.login'))

        return render_template('button.html', form=form, title='Logout')
