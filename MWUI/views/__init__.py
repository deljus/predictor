# -*- coding: utf-8 -*-
#
#  Copyright 2016, 2017 Ramil Nugmanov <stsouko@live.ru>
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
from flask import redirect, url_for, render_template, Blueprint, abort, make_response
from flask_login import login_required, current_user
from pony.orm import db_session, left_join
from datetime import datetime
from pycountry import countries
from ..forms import DeleteButtonForm
from ..models import User, Meeting, Post, Attachment, Subscription
from ..constants import UserRole, MeetingPostType, ProfileStatus
from .auth import LoginView, LogoutView
from .profile import ProfileView
from .post import PostView
from .visitcard import IndexView, AboutView, StudentsView, LessonsView
from .blog import BlogView, AbstractsView, EmailsView, ThesesView, EventsView


view_bp = Blueprint('view', __name__)

login_view = LoginView.as_view('login')
view_bp.add_url_rule('/login', view_func=login_view)
view_bp.add_url_rule('/login/<int:action>', view_func=login_view)

view_bp.add_url_rule('/logout', view_func=LogoutView.as_view('logout'))

profile_view = ProfileView.as_view('profile')
view_bp.add_url_rule('/profile', view_func=profile_view)
view_bp.add_url_rule('/profile/<int:action>', view_func=profile_view)

view_bp.add_url_rule('/page/<int:post>', view_func=PostView.as_view('blog_post'))

index_view = IndexView.as_view('index')
view_bp.add_url_rule('/', view_func=index_view)
view_bp.add_url_rule('/index', view_func=index_view)

view_bp.add_url_rule('/about', view_func=AboutView.as_view('about'))
view_bp.add_url_rule('/students', view_func=StudentsView.as_view('students'))
view_bp.add_url_rule('/lessons', view_func=LessonsView.as_view('lessons'))

blog_view = BlogView.as_view('blog')
view_bp.add_url_rule('/news', view_func=blog_view)
view_bp.add_url_rule('/news/<int:page>', view_func=blog_view)

theses_view = ThesesView.as_view('theses')
view_bp.add_url_rule('/theses', view_func=theses_view)
view_bp.add_url_rule('/theses/<int:page>', view_func=theses_view)

events_view = EventsView.as_view('events')
view_bp.add_url_rule('/events', view_func=events_view)
view_bp.add_url_rule('/events/<int:page>', view_func=events_view)

abstracts_view = AbstractsView.as_view('abstracts')
view_bp.add_url_rule('/abstracts/<int:event>', view_func=abstracts_view)
view_bp.add_url_rule('/abstracts/<int:event>/<int:page>', view_func=abstracts_view)

emails_view = EmailsView.as_view('emails')
view_bp.add_url_rule('/emails', view_func=emails_view)
view_bp.add_url_rule('/emails/<int:page>', view_func=emails_view)


@view_bp.errorhandler(404)
def page_not_found(*args, **kwargs):
    return render_template('layout.html', title='404', subtitle='Page not found'), 404


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
    return render_template("predictor.html", title='Predictor', subtitle='UI')


@view_bp.route('/<string:_slug>/')
def slug(_slug):
    with db_session:
        p = Post.get(slug=_slug)
        if not p:
            abort(404)
        resp = make_response(redirect(url_for('.blog_post', post=p.id)))
        if p.classtype == 'Meeting' and p.type == MeetingPostType.MEETING:
            resp.set_cookie('meeting', str(p.id))
    return resp


@view_bp.route('/download/<file>/<name>', methods=['GET'])
@db_session
@login_required
def download(file, name):
    a = Attachment.get(file=file)
    if current_user.role_is(UserRole.ADMIN) or a.post.classtype != 'Thesis' or a.post.author.id == current_user.id:
        resp = make_response()
        resp.headers['X-Accel-Redirect'] = '/file/%s' % file
        resp.headers['Content-Description'] = 'File Transfer'
        resp.headers['Content-Transfer-Encoding'] = 'binary'
        resp.headers['Content-Disposition'] = 'attachment; filename=%s' % name
        resp.headers['Content-Type'] = 'application/octet-stream'
        return resp
    abort(404)


@view_bp.route('/remove/<file>/<name>', methods=['GET', 'POST'])
@db_session
@login_required
def remove(file, name):
    form = DeleteButtonForm()
    if form.validate_on_submit():
        a = Attachment.get(file=file)
        if a and (current_user.role_is(UserRole.ADMIN)
                  or a.post.classtype == 'Thesis' and a.post.author.id == current_user.id
                  and a.post.meeting.poster_deadline > datetime.utcnow()):
            a.delete()
        return form.redirect()

    return render_template('button.html', form=form, title='Delete', subtitle=name)


@view_bp.route('/participants/<int:event>', methods=['GET'])
@db_session
def participants(event):
    m = Meeting.get(id=event, post_type=MeetingPostType.MEETING.value)
    if not m:
        return redirect(url_for('.blog'))

    subs = Subscription.select(lambda x: x.meeting == m).order_by(Subscription.id.desc())
    users = {x.id: x for x in left_join(x for x in User for s in x.subscriptions if s.meeting == m)}

    data = [dict(type=x.type.fancy, status=ProfileStatus(users[x.user.id].status).fancy,
                 country=countries.get(alpha_3=users[x.user.id].country).name,
                 user=users[x.user.id].full_name, useid=x.user.id) for x in subs]
    return render_template('participants.html', data=data, title=m.title, subtitle='Participants',
                           crumb=dict(url=url_for('.blog_post', post=event), title='Participants',
                                      parent='Event main page'))


@view_bp.route('/user/<int:_user>', methods=['GET'])
@db_session
def user(_user):
    u = User.get(id=_user)
    if not u:
        return redirect(url_for('.index'))
    return render_template('user.html', data=u, title=u.full_name, subtitle='Profile')
