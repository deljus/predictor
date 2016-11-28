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
from requests import get
from collections import MutableSet
from .config import SCOPUS_API_KEY


class OrderedSet(MutableSet):
    def __init__(self, iterable=None):
        self.end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.map = {}                   # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        if key not in self.map:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.map[key] = [key, curr, end]

    def discard(self, key):
        if key in self.map:
            key, prev, next = self.map.pop(key)
            prev[2] = next
            next[1] = prev

    def __iter__(self):
        end = self.end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def pop(self, last=True):
        if not self:
            raise KeyError('set is empty')
        key = self.end[1][0] if last else self.end[2][0]
        self.discard(key)
        return key

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)


def get_articles(author_id):
    resp = get("https://api.elsevier.com/content/search/scopus?"
               "query=AU-ID(%s)&view=COMPLETE&sort=-coverDate,title&"
               "field=dc:title,prism:publicationName,prism:volume,prism:issueIdentifier,"
               "prism:pageRange,prism:coverDate,prism:doi,dc:description,"
               "citedby-count,affiliation,author" % author_id,
               headers={'Accept': 'application/json', 'X-ELS-APIKey': SCOPUS_API_KEY})

    arts = ['**List of published articles** (*Provided by SCOPUS API*)\n']
    if resp.status_code == 200:
        resp = resp.json()
        for i in resp["search-results"]["entry"]:
            authors = OrderedSet('{initials} {surname}'.format(initials=x['initials'], surname=x['surname'])
                                 for x in i["author"])
            reformatted = dict(title=i["dc:title"],
                               journal=i["prism:publicationName"],
                               volume=(i.get("prism:volume") or 'NA'),
                               issue=(i.get("prism:issueIdentifier") or 'NA'),
                               pages=(i.get("prism:pageRange") or 'NA'),
                               date=(i.get("prism:coverDate") or 'NA'),
                               doi=(i.get("prism:doi") or 'NA'),
                               cited=i["citedby-count"],
                               authors=', '.join(authors))
            arts.append('* **{date}:** *{title}* / {authors} // ***{journal}.*** V.{volume}. Is.{issue}. P.{pages} '
                        '[cited count: {cited}, [doi](//dx.doi.org/{doi})]'.format(**reformatted))
        return '\n'.join(arts)

    return None
