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
from .forms import Login, Registration, ReLogin, ChangePassword, NewPost, ChangeRole, BanUser, ForgotPassword
from .logins import User
from .models import Users
from .config import UserRole
from flask import redirect, url_for, render_template, Blueprint, flash
from flask_login import login_user, logout_user, login_required, current_user
from pony.orm import db_session


view_bp = Blueprint('view', __name__)


def send_restore_email(email):
    with db_session:
        if Users.exists(email=email):
            pass
        flash('Check your email box', 'warning')


@view_bp.route('/registration', methods=['GET', 'POST'])
def registration():
    form = Registration()
    forgot = ForgotPassword()

    if form.validate_on_submit():
        with db_session:
            Users(email=form.email.data, password=form.password.data)
            return redirect(url_for('.login'))

    elif forgot.validate_on_submit():
        send_restore_email(forgot.email.data)
        return redirect(url_for('.login'))

    return render_template('login.html', form=form, forgot=forgot, header='Registration Form', title='Registration')


@view_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = Login(prefix='Login')
    forgot = ForgotPassword(prefix='ForgotPassword')

    if form.validate_on_submit():
        user = User.get(form.email.data, form.password.data)
        login_user(user, remember=form.remember.data)
        return redirect(url_for('.index'))

    elif forgot.validate_on_submit():
        send_restore_email(forgot.email.data)
        return redirect(url_for('.login'))

    return render_template('login.html', form=form, forgot=forgot, header='Login Form', title='Login')


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

    if re_login_form.validate_on_submit():
        with db_session:
            user = Users.get(id=current_user.id)
            user.change_token()
        logout_user()
        redirect(url_for('.login'))
    elif change_passwd_form.validate_on_submit():
        with db_session:
            user = Users.get(id=current_user.id)
            user.change_password()
        logout_user()
        redirect(url_for('.login'))

    if current_user.get_role() == UserRole.ADMIN:
        new_post_form = NewPost(prefix='NewPost')
        change_role_form = ChangeRole(prefix='ChangeRole')
        ban_form = BanUser(prefix='BanUser')

        if new_post_form.validate_on_submit():
            print(new_post_form.type)

        elif change_role_form.validate_on_submit():
            pass
        elif ban_form.validate_on_submit():
            pass

        admin_forms = dict(new_post_form=new_post_form, change_role_form=change_role_form, ban_form=ban_form)
    else:
        admin_forms = {}

    return render_template("profile.html", user=current_user,
                           re_login_form=re_login_form, change_passwd_form=change_passwd_form, **admin_forms)


@view_bp.route('/queries', methods=['GET'])
@login_required
def queries():
    return render_template("layout.html")


@view_bp.route('/results', methods=['GET'])
@login_required
def results():
    return render_template("layout.html")


@view_bp.route('/', methods=['GET'])
@view_bp.route('/index', methods=['GET'])
def index():
    return render_template("home.html", data=dict(info=[dict(url=url_for('.blog'), link='Learn', title='AAA',
                                                             body='BBBB')],
                                                  projects=dict(title='Title',
                                                                list=['CGRtools'],
                                                                foot='Foot',
                                                                img=url_for('static', filename='img/3.png'))))


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


@view_bp.route('/blog', methods=['GET'])
def blog():
    return render_template("layout.html")
