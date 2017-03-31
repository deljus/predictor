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
from CGRdb import Loader
from pony.orm import Database
from .predictions import load_tables as save
from .web import load_tables as main
from ..config import DB_MAIN, DB_PRED

db = Database()

(User, Subscription, Model, Destination, Additive,
 Post, BlogPost, TeamPost, Meeting, Thesis, Email, Attachment) = main(db, DB_MAIN)
Task, Structure, Result, Additiveset = save(db, DB_PRED)

# currently unused
cgr_databases = Loader.list_databases()
