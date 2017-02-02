#!/usr/bin/env python3.4
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
from smtplib import SMTP
from MWUI.config import SMPT_HOST, SMTP_PORT, SMTP_LOGIN, SMTP_PASSWORD, SMTP_MAIL


def run(mail, message):
    with SMTP(SMPT_HOST, SMTP_PORT) as smtp:
            smtp.login(SMTP_LOGIN, SMTP_PASSWORD)
            smtp.sendmail(SMTP_MAIL, mail, message)
