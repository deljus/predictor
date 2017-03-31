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
from datetime import datetime
from flask import redirect, url_for, render_template, flash
from flask.views import View
from flask_login import current_user
from pony.orm import db_session, select, commit
from ..constants import (UserRole, BlogPostType, MeetingPostType, EmailPostType, TeamPostType, MeetingPartType,
                         ThesisPostType)
from ..forms import PostForm, DeleteButtonForm, MeetingForm, EmailForm, ThesisForm, TeamForm, MeetForm
from ..models import Email, Post, Thesis, Subscription
from ..scopus import get_articles
from ..sendmail import send_mail
from ..upload import save_upload, combo_save


class PostView(View):
    methods = ['GET', 'POST']
    decorators = [db_session]

    def dispatch_request(self, post):
        admin = current_user.is_authenticated and current_user.role_is(UserRole.ADMIN)
        edit_post = None
        remove_post_form = None
        special_form = None
        special_field = None
        children = []
        title = None
        info = None

        p = Post.get(id=post)
        if not p:
            return redirect(url_for('.blog'))

        opened_by_author = current_user.is_authenticated and p.author.id == current_user.id
        downloadable = admin or p.classtype != 'Thesis' or opened_by_author
        deletable = admin or p.classtype == 'Thesis' and opened_by_author and p.meeting.deadline > datetime.utcnow()
        """ admin page
        """
        if admin:
            remove_post_form = DeleteButtonForm(prefix='delete')
            if p.classtype == 'BlogPost':
                edit_post = PostForm(obj=p)
            elif p.classtype == 'Meeting':
                edit_post = MeetingForm(obj=p)
            elif p.classtype == 'Thesis':
                edit_post = ThesisForm(obj=p)
            elif p.classtype == 'Email':
                edit_post = EmailForm(obj=p)
            elif p.classtype == 'TeamPost':
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

                if hasattr(edit_post, 'slug') and edit_post.slug.data:
                    p.slug = edit_post.slug.data

                if edit_post.banner_field.data:
                    p.banner = save_upload(edit_post.banner_field.data, images=True)

                if edit_post.attachment.data:
                    p.add_attachment(*save_upload(edit_post.attachment.data))

                if hasattr(p, 'update_type'):
                    try:
                        p.update_type(edit_post.type)
                        if p.classtype == 'Thesis':
                            sub = Subscription.get(user=p.author, meeting=p.meeting)
                            sub.update_type(edit_post.type.participation_type)
                    except Exception as e:
                        edit_post.post_type.errors = [str(e)]

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

                if hasattr(p, 'update_poster_deadline') and edit_post.poster_deadline.data:
                    p.update_poster_deadline(edit_post.poster_deadline.data)

                if hasattr(p, 'update_participation_types') and edit_post.participation_types:
                    p.update_participation_types(edit_post.participation_types)

                if hasattr(p, 'update_thesis_types') and edit_post.thesis_types:
                    p.update_thesis_types(edit_post.thesis_types)

        """ Meetings sidebar and title
        """
        if p.classtype == 'Meeting':
            title = p.meeting.title

            children.append(dict(title='Event main page', url=url_for('.blog_post', post=p.meeting_id)))
            children.extend(dict(title=x.title, url=url_for('.blog_post', post=x.id))
                            for x in p.meeting.children.
                            filter(lambda x: x.classtype == 'Meeting').order_by(lambda x: x.special['order']))

            children.append(dict(title='Participants', url=url_for('.participants', event=p.meeting_id)))
            children.append(dict(title='Abstracts', url=url_for('.abstracts', event=p.meeting_id)))

            if p.type != MeetingPostType.MEETING:
                crumb = dict(url=url_for('.blog_post', post=p.meeting_id), title=p.title, parent='Event main page')

                if current_user.is_authenticated and p.type == MeetingPostType.REGISTRATION \
                        and p.deadline > datetime.utcnow():

                    sub = Subscription.get(user=current_user.get_user(), meeting=p.meeting)
                    special_form = MeetForm(prefix='special', obj=sub, types=p.meeting.participation_types)

                    if special_form.validate_on_submit():
                        thesis = Thesis.get(post_parent=p.meeting, author=current_user.get_user())
                        if sub:
                            if special_form.type == MeetingPartType.LISTENER and thesis:
                                special_form.part_type.errors = ['Listener participation type unavailable. '
                                                                 'You sent thesis earlier.']
                                flash('Participation type change error', 'error')
                            else:
                                sub.update_type(special_form.type)
                                thesis_type = ThesisPostType.thesis_types(special_form.type)[-1]
                                if thesis and thesis.type != thesis_type:
                                    thesis.update_type(thesis_type)
                                    flash('Thesis type changed! Check it.')
                                flash('Participation type changed!')
                        else:
                            Subscription(current_user.get_user(), p.meeting, special_form.type)
                            flash('Welcome to meeting!')

                            m = Email.get(post_parent=p.meeting, post_type=EmailPostType.MEETING_THESIS.value)
                            send_mail((m and m.body or '%s\n\nYou registered to meeting') % current_user.full_name,
                                      current_user.email, to_name=current_user.full_name, title=m and m.title,
                                      subject=m and m.title or 'Welcome to meeting', banner=m and m.banner,
                                      from_name=m and m.from_name, reply_mail=m and m.reply_mail,
                                      reply_name=m and m.reply_name)

                elif current_user.is_authenticated and p.type == MeetingPostType.SUBMISSION \
                        and p.poster_deadline > datetime.utcnow():

                    sub = Subscription.get(user=current_user.get_user(), meeting=p.meeting)
                    if sub and sub.type != MeetingPartType.LISTENER and \
                            not Thesis.exists(post_parent=p.meeting, author=current_user.get_user()):
                        thesis_types = p.meeting.thesis_types
                        special_form = ThesisForm(prefix='special', body_name=p.body_name,
                                                  types=[x for x in ThesisPostType.thesis_types(sub.type)
                                                         if x in thesis_types])
                        if special_form.validate_on_submit():
                            banner_name, file_name = combo_save(special_form.banner_field, special_form.attachment)
                            t = Thesis(p.meeting_id, type=special_form.type,
                                       title=special_form.title.data, body=special_form.body.data,
                                       banner=banner_name, attachments=file_name, author=current_user.get_user())
                            commit()
                            return redirect(url_for('.blog_post', post=t.id))
            else:
                crumb = dict(url=url_for('.blog'), title='Post', parent='News')

        elif p.classtype == 'Thesis':
            if current_user.is_authenticated and opened_by_author and p.meeting.poster_deadline > datetime.utcnow():
                sub = Subscription.get(user=current_user.get_user(), meeting=p.meeting)
                thesis_types = p.meeting.thesis_types
                special_form = ThesisForm(prefix='special', obj=p, body_name=p.body_name,
                                          types=[x for x in ThesisPostType.thesis_types(sub.type) if x in thesis_types])
                if special_form.validate_on_submit():
                    p.title = special_form.title.data
                    p.body = special_form.body.data
                    p.update_type(special_form.type)

                    if special_form.banner_field.data:
                        p.banner = save_upload(special_form.banner_field.data, images=True)
                    if special_form.attachment.data:
                        p.add_attachment(*save_upload(special_form.attachment.data))

            crumb = dict(url=url_for('.abstracts', event=p.meeting_id), title='Abstract', parent='Event participants')
            special_field = '**Presentation Type**: *%s*' % p.type.fancy
        elif p.classtype == 'TeamPost':
            crumb = dict(url=url_for('.students'), title='Student', parent='Laboratory') \
                if p.type == TeamPostType.STUDENT else dict(url=url_for('.about'), title='Member', parent='Laboratory')
            if p.scopus:
                special_field = get_articles(p.scopus)
        elif p.type == BlogPostType.ABOUT:
            crumb = dict(url=url_for('.about'), title='Description', parent='Laboratory')
        else:
            crumb = dict(url=url_for('.blog'), title='Post', parent='News')
            """ collect sidebar news
            """
            info = select(x for x in Post if x.id != post and
                          x.post_type in (BlogPostType.IMPORTANT.value,
                                          MeetingPostType.MEETING.value)).order_by(Post.date.desc()).limit(3)

        return render_template("post.html", title=title or p.title, post=p, info=info, downloadable=downloadable,
                               children=children, deletable=deletable,
                               edit_form=edit_post, remove_form=remove_post_form, crumb=crumb,
                               special_form=special_form, special_field=special_field)
