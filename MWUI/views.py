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
from .forms import Login, Registration
from .logins import User
from .models import Users
from flask import redirect, url_for, render_template, Blueprint
from flask_login import login_user, logout_user, login_required
from pony.orm import db_session


view_bp = Blueprint('view', __name__)


@view_bp.route('/registration', methods=['GET', 'POST'])
def registration():
    form = Registration()
    if form.validate_on_submit():
        with db_session:
            Users(email=form.email.data, password=form.password.data)
            return redirect(url_for('.login'))
    return render_template('formpage.html', form=form, header='Registration', title='Registration')


@view_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = Login()
    if form.validate_on_submit():
        user = User.get(form.email.data, form.password.data)
        if user:
            login_user(user, remember=form.remember.data)
            return redirect(url_for('.index'))
    return render_template('formpage.html', form=form, header='Login', title='Login')


@view_bp.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('.login'))


@view_bp.route('/', methods=['GET'])
@view_bp.route('/index', methods=['GET'])
@login_required
def index():
    return render_template("home.html", home=dict(info=[1], welcome='Hello!'))


@view_bp.route('/search', methods=['GET'])
@login_required
def search():
    return render_template("home.html")


@view_bp.route('/modeling', methods=['GET'])
@login_required
def modeling():
    return render_template("home.html")


@view_bp.route('/queries', methods=['GET'])
@login_required
def queries():
    return render_template("home.html")


@view_bp.route('/results', methods=['GET'])
@login_required
def results():
    return render_template("home.html")


@view_bp.route('/profile', methods=['GET'])
@login_required
def profile():
    return render_template("home.html")


@view_bp.route('/about', methods=['GET'])
def about():
    return render_template("home.html")


@view_bp.route('/blog', methods=['GET'])
def blog():
    return render_template("home.html")
