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
from redis import Redis, ConnectionError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from subprocess import Popen, PIPE
from rq import Queue
from flask_misaka import markdown
from flask import render_template
from .config import (LAB_NAME, SMTP_MAIL, REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_MAIL, DEBUG,
                     MAIL_INKEY, MAIL_SIGNER)


def send_mail(message, to_mail, to_name=None, from_name=None, subject=None, banner=None, title=None,
              reply_name=None, reply_mail=None):

    if reply_name and not reply_mail:
        reply_name = None

    r = Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD)

    try:
        r.ping()
        sender = Queue(connection=r, name=REDIS_MAIL, default_timeout=3600)
    except ConnectionError:
        return DEBUG or False

    out = ['Subject: %s' % subject or '',
           'To: %s' % ('%s <%s>' % (to_name, to_mail) if to_name else to_mail),
           'From: %s <%s>' % (from_name or LAB_NAME, SMTP_MAIL)]

    if reply_mail:
        out.append('Reply-To: %s' % ('%s <%s>' % (reply_name, reply_mail) if reply_name else reply_mail))

    msg = MIMEMultipart('alternative')
    msg.attach(MIMEText(message, 'plain'))
    msg.attach(MIMEText(render_template('email.html', body=markdown(message), banner=banner, title=title), 'html'))

    p = Popen(['openssl', 'smime', '-sign', '-inkey', MAIL_INKEY, '-signer', MAIL_SIGNER], stdin=PIPE, stdout=PIPE)
    out.append(p.communicate(input=msg.as_bytes())[0].decode())

    try:
        return sender.enqueue_call('redis_mail.run', args=(to_mail, '\n'.join(out)), result_ttl=60).id
    except:
        return False
