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
from os.path import splitext, join
from uuid import uuid4
from werkzeug.utils import secure_filename
from .config import UPLOAD_PATH, IMAGES_ROOT


def save_upload(field, images=False):
    ext = splitext(field.filename)[-1].lower()
    file_name = '%s%s' % (uuid4(), ext)
    field.save(join(IMAGES_ROOT if images else UPLOAD_PATH, file_name))
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
