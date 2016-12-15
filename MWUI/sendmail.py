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
from smtplib import SMTP
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask_misaka import markdown
from flask import render_template
from .config import LAB_NAME, SMTP_MAIL, SMPT_HOST, SMTP_LOGIN, SMTP_PASSWORD, SMTP_PORT


def send_mail(message, to_mail, to_name=None, from_name=None, subject=None, banner=None, title=None,
              reply_name=None, reply_mail=None):
    html = render_template('email.html', body=markdown(message), banner=banner, title=title)

    part1 = MIMEText(message, 'plain')
    part2 = MIMEText(html, 'html')

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject or ""
    msg['From'] = '%s <%s>' % (from_name or LAB_NAME, SMTP_MAIL)
    msg['To'] = '%s <%s>' % (to_name, to_mail) if to_name else to_mail
    if reply_mail:
        msg['Reply-To'] = '%s <%s>' % (reply_name, reply_mail) if reply_name else reply_mail

    msg.attach(part1)
    msg.attach(part2)

    try:
        with SMTP(SMPT_HOST, SMTP_PORT) as smtp:
            smtp.login(SMTP_LOGIN, SMTP_PASSWORD)
            smtp.sendmail(SMTP_MAIL, to_mail, msg.as_string())
    except:
        pass
