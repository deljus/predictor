# -*- coding: utf-8 -*-
#
# Copyright 2015-2017 Ramil Nugmanov <stsouko@live.ru>
# Copyright 2015 Oleg Varlamov <ovarlamo@gmail.com>
# This file is part of PREDICTOR.
#
# PREDICTOR is free software; you can redistribute it and/or modify
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
from .ORM import db, main_tables, save_tables, data_tables

User, Post, Attachment, Model, Destination, Additive, BlogPost, TeamPost, Meeting, Thesis, Email = main_tables
Task, Structure, Result, Additiveset = save_tables
Molecule, Reaction = data_tables
