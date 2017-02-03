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
from collections import OrderedDict
from datetime import datetime
from pony.orm import PrimaryKey, Required, Optional, Set, Json
from networkx import relabel_nodes
from bitstring import BitArray
from itertools import count
from networkx.readwrite.json_graph import node_link_graph, node_link_data
from CGRtools.FEAR import FEAR
from CGRtools.CGRreactor import CGRreactor
from CGRtools.CGRcore import CGRcore
from CGRtools.files import MoleculeContainer, ReactionContainer
from hashlib import md5
from MODtools.descriptors.fragmentor import Fragmentor
from ..config import (FP_SIZE, FP_ACTIVE_BITS, FRAGMENTOR_VERSION, DEBUG,
                      FRAGMENT_TYPE_CGR, FRAGMENT_MIN_CGR, FRAGMENT_MAX_CGR, FRAGMENT_DYNBOND_CGR,
                      FRAGMENT_TYPE_MOL, FRAGMENT_MIN_MOL, FRAGMENT_MAX_MOL, DATA_ISOTOPE, DATA_STEREO)


fear = FEAR(isotope=DATA_ISOTOPE, stereo=DATA_STEREO)
cgr_core = CGRcore()
cgr_reactor = CGRreactor(isotope=DATA_ISOTOPE, stereo=DATA_STEREO)


def get_fingerprints(df):
    bits_map = {}
    for fragment in df.columns:
        b = BitArray(md5(fragment.encode()).digest())
        bits_map[fragment] = [b[r * FP_SIZE: (r + 1) * FP_SIZE].uint for r in range(FP_ACTIVE_BITS)]

    result = []
    for _, s in df.iterrows():
        active_bits = set()
        for k, v in s.items():
            if v:
                active_bits.update(bits_map[k])

        fp = BitArray(2 ** FP_SIZE)
        fp.set(True, active_bits)
        result.append(fp)

    return result


def load_tables(db, schema):
    class Molecule(db.Entity):
        _table_ = '%s_molecule' % schema if DEBUG else (schema, 'molecule')
        id = PrimaryKey(int, auto=True)
        date = Required(datetime, default=datetime.utcnow())
        user = Required('User')
        data = Required(Json)
        fear = Required(str, unique=True)
        fingerprint = Required(str) if DEBUG else Required(str, sql_type='bit(%s)' % (2 ** FP_SIZE))

        children = Set('Molecule', reverse='parent', cascade_delete=True)
        parent = Optional('Molecule', reverse='children')
        last = Required(bool, default=True)

        merge_source = Set('MoleculeMerge', reverse='target')  # molecules where self is more correct
        merge_target = Set('MoleculeMerge', reverse='source')  # links to correct molecules

        reactions = Set('MoleculeReaction')

        def __init__(self, molecule, user, fingerprint=None, fear_string=None):
            data = node_link_data(molecule)

            if fear_string is None:
                fear_string = self.get_fear(molecule)
            if fingerprint is None:
                fingerprint = self.get_fingerprints([molecule])[0]

            self.__cached_structure_raw = molecule
            self.__cached_bitstring = fingerprint
            super(Molecule, self).__init__(data=data, user=db.User[user], fear=fear_string, fingerprint=fingerprint.bin)

        def update(self, molecule, user):
            new_hash = {k: v['element'] for k, v in molecule.nodes(data=True)}
            old_hash = {k: v['element'] for k, v in self.structure_raw.nodes(data=True)}
            if new_hash != old_hash:
                return False

            fear_string = self.get_fear(molecule)
            exists = Molecule.get(fear=fear_string)
            if not exists:
                m = Molecule(molecule, user, fear_string=fear_string)
                for mr in self.last_edition.reactions:
                    ''' replace current last molecule edition in all reactions.
                    '''
                    mr.molecule = m
                    mr.reaction.refresh_fear_fingerprint()

                self.last_edition.last = False
                m.parent = self.parent or self
                self.__last_edition = m
                return True

            ex_parent = exists.parent or exists
            if ex_parent != (self.parent or self):
                if not any((x.target.parent or x.target) == ex_parent for x in self.merge_target):
                    iso = cgr_reactor.get_cgr_matcher(molecule, exists.structure_raw).isomorphisms_iter()
                    MoleculeMerge(target=exists, source=self,
                                  mapping=[(k, v) for k, v in next(iso).items() if k != v] or None)

            return False

        def merge_molecule(self, molecule):
            m = Molecule[molecule]
            mm = MoleculeMerge.get(target=m, source=self)
            if not mm:
                return False
            ''' replace self in reactions to last edition of mergable molecule.
            '''
            mmap = dict(mm.mapping or [])
            mapping = [(n, mmap.get(n, n)) for n in self.structure_raw.nodes()]
            for mr in self.last_edition.reactions:
                rmap = dict(mr.mapping or [])
                mr.mapping = [(k, v) for k, v in ((v, rmap.get(k, k)) for k, v in mapping) if k != v] or None
                mr.molecule = m.last_edition
                mr.reaction.refresh_fear_fingerprint()

            ''' remap self'''
            if self.parent:
                tmp = [self.parent] + list(self.parent.children)
            else:
                tmp = [self] + list(self.children)

            for x in tmp:
                x.data = node_link_data(relabel_nodes(x.structure_raw, mmap))

            ''' set self.parent to molecule chain
            '''
            if m.parent:
                tmp = [m.parent] + list(m.parent.children)
            else:
                tmp = [m] + list(m.children)

            for x in tmp:
                x.parent = self.parent or self

            self.last_edition.last = False
            self.__last_edition = m.last_edition
            mm.delete()
            return True

        @staticmethod
        def get_fear(molecule):
            return fear.get_cgr_string(molecule)

        @staticmethod
        def get_fingerprints(structures):
            f = Fragmentor(workpath='.', version=FRAGMENTOR_VERSION, fragment_type=FRAGMENT_TYPE_MOL,
                           min_length=FRAGMENT_MIN_MOL, max_length=FRAGMENT_MAX_MOL,
                           useformalcharge=True).get(structures)['X']
            return get_fingerprints(f)

        @property
        def structure_raw(self):
            if self.__cached_structure_raw is None:
                g = node_link_graph(self.data)
                g.__class__ = MoleculeContainer
                self.__cached_structure_raw = g
            return self.__cached_structure_raw

        @property
        def structure_parent(self):
            if self.parent:
                return self.parent.structure_raw
            return None

        @property
        def structure(self):
            return self.last_edition.structure_raw

        @property
        def last_edition(self):
            if self.__last_edition is None:
                if self.last:
                    tmp = self
                elif self.parent and self.parent.last:
                    tmp = self.parent
                else:
                    tmp = (self.parent or self).children.filter(lambda x: x.last).first()
                self.__last_edition = tmp
            return self.__last_edition

        @property
        def bitstring_fingerprint(self):
            if self.__cached_bitstring is None:
                self.__cached_bitstring = BitArray(bin=self.fingerprint)
            return self.__cached_bitstring

        __cached_structure_raw = None
        __last_edition = None
        __cached_bitstring = None

    class Reaction(db.Entity):
        _table_ = '%s_reaction' % schema if DEBUG else (schema, 'reaction')
        id = PrimaryKey(int, auto=True)
        date = Required(datetime, default=datetime.utcnow())
        user = Required('User')
        fear = Required(str, unique=True)
        mapless_fear = Required(str)
        fingerprint = Required(str) if DEBUG else Required(str, sql_type='bit(%s)' % (2 ** FP_SIZE))

        children = Set('Reaction', cascade_delete=True)
        parent = Optional('Reaction')

        molecules = Set('MoleculeReaction')
        conditions = Set('Conditions')
        special = Optional(Json)

        def __init__(self, reaction, user, conditions=None, special=None, fingerprint=None, fear_string=None, cgr=None,
                     substrats_fears=None, products_fears=None):
            db_user = db.User[user]
            new_mols, batch = OrderedDict(), {}
            fears = dict(substrats=iter(substrats_fears if substrats_fears and
                                        len(substrats_fears) == len(reaction.substrats) else []),
                         products=iter(products_fears if products_fears and
                                       len(products_fears) == len(reaction.products) else []))

            refreshed = ReactionContainer()
            m_count = count()
            for i, is_p in (('substrats', False), ('products', True)):
                for x in reaction[i]:
                    m_fear_string = next(fears[i], fear.get_cgr_string(x))
                    m = Molecule.get(fear=m_fear_string)
                    if m:
                        mapping = next(cgr_reactor.get_cgr_matcher(m.structure_raw, x).isomorphisms_iter())
                        batch[next(m_count)] = (m.last_edition, is_p,
                                                [(k, v) for k, v in mapping.items() if k != v] or None)
                        refreshed[i].append(relabel_nodes(m.structure, mapping))
                    else:
                        new_mols[next(m_count)] = (x, is_p, m_fear_string)
                        refreshed[i].append(x)

            if new_mols:
                for_fp, for_x = [], []
                for x, _, m_fp in new_mols.values():
                    if m_fp not in for_fp:
                        for_fp.append(m_fp)
                        for_x.append(x)
                    
                fp_dict = dict(zip(for_fp, Molecule.get_fingerprints(for_x)))
                dups = {}
                for n, (x, is_p, m_fear_string) in new_mols.items():
                    if m_fear_string not in dups:
                        m = Molecule(x, user, fear_string=m_fear_string, fingerprint=fp_dict[m_fear_string])
                        dups[m_fear_string] = m
                        mapping = None
                    else:
                        m = dups[m_fear_string]
                        iso = next(cgr_reactor.get_cgr_matcher(m.structure_raw, x).isomorphisms_iter())
                        mapping = [(k, v) for k, v in iso.items() if k != v] or None
                    batch[n] = (m, is_p, mapping)

            if fear_string is None:
                fear_string, cgr = self.get_fear(reaction, get_cgr=True)
            elif cgr is None:
                cgr = cgr_core.getCGR(reaction)

            if fingerprint is None:
                fingerprint = self.get_fingerprints([cgr], is_cgr=True)[0]

            merged = cgr_core.merge_mols(refreshed)
            super(Reaction, self).__init__(user=db_user, fear=fear_string, fingerprint=fingerprint.bin,
                                           mapless_fear='%s>>%s' % (Molecule.get_fear(merged['substrats']),
                                                                    Molecule.get_fear(merged['products'])))

            for m, is_p, mapping in (batch[x] for x in sorted(batch)):
                MoleculeReaction(reaction=self, molecule=m, product=is_p, mapping=mapping)

            if conditions:
                Conditions(data=conditions, reaction=self, user=db_user)

            if special:
                self.special = special

            self.__cached_cgr = cgr
            self.__cached_structure = reaction
            self.__cached_bitstring = fingerprint

        @staticmethod
        def refresh_reaction(reaction):
            fresh = dict(substrats=[], products=[])
            for i, is_p in (('substrats', False), ('products', True)):
                for x in reaction[i]:
                    m_fear_string = fear.get_cgr_string(x)
                    m = Molecule.get(fear=m_fear_string)
                    if m:
                        fresh[i].append(m)
                    else:
                        return False

            return ReactionContainer(substrats=[relabel_nodes(x.structure,
                                                              next(cgr_reactor.get_cgr_matcher(x.structure_raw,
                                                                                               y).isomorphisms_iter()))
                                                for x, y in zip(fresh['substrats'], reaction.substrats)],
                                     products=[relabel_nodes(x.structure,
                                                             next(cgr_reactor.get_cgr_matcher(x.structure_raw,
                                                                                              y).isomorphisms_iter()))
                                               for x, y in zip(fresh['products'], reaction.products)])

        @staticmethod
        def mapless_exists(reaction):
            fresh = Reaction.refresh_reaction(reaction)
            if fresh:
                merged = cgr_core.merge_mols(fresh)
                ml_fear = '%s>>%s' % (Molecule.get_fear(merged['substrats']), Molecule.get_fear(merged['products']))
                return Reaction.exists(mapless_fear=ml_fear)
            return False

        @staticmethod
        def cgr_exists(reaction):
            fresh = Reaction.refresh_reaction(reaction)
            if fresh:
                fear_string = fear.get_cgr_string(cgr_core.getCGR(fresh))
                return Reaction.exists(fear=fear_string)
            return False

        @staticmethod
        def get_fingerprints(reactions, is_cgr=False):
            cgrs = reactions if is_cgr else [cgr_core.getCGR(x) for x in reactions]
            f = Fragmentor(workpath='.', version=FRAGMENTOR_VERSION, fragment_type=FRAGMENT_TYPE_CGR,
                           min_length=FRAGMENT_MIN_CGR, max_length=FRAGMENT_MAX_CGR,
                           cgr_dynbonds=FRAGMENT_DYNBOND_CGR, useformalcharge=True).get(cgrs)['X']
            return get_fingerprints(f)

        @staticmethod
        def get_fear(reaction, get_cgr=False):
            cgr = cgr_core.getCGR(reaction)
            cgr_string = fear.get_cgr_string(cgr)
            return (cgr_string, cgr) if get_cgr else cgr_string

        @property
        def cgr(self):
            if self.__cached_cgr is None:
                self.__cached_cgr = cgr_core.getCGR(self.structure)
            return self.__cached_cgr

        @property
        def structure(self):
            if self.__cached_structure is None:
                r = ReactionContainer()
                for m in self.molecules.order_by(lambda x: x.id):
                    r['products' if m.product else 'substrats'].append(
                        relabel_nodes(m.molecule.structure_raw, dict(m.mapping)) if m.mapping else m.molecule.structure)
                self.__cached_structure = r
            return self.__cached_structure

        @property
        def bitstring_fingerprint(self):
            if self.__cached_bitstring is None:
                self.__cached_bitstring = BitArray(bin=self.fingerprint)
            return self.__cached_bitstring

        def refresh_fear_fingerprint(self):
            fear_string, cgr = Reaction.get_fear(self.structure, get_cgr=True)
            fingerprint = Reaction.get_fingerprints([cgr], is_cgr=True)[0]
            print(self.date)  # Pony BUG. AD-HOC!
            self.fear = fear_string
            self.fingerprint = fingerprint.bin
            self.__cached_bitstring = fingerprint

        __cached_structure = None
        __cached_cgr = None
        __cached_conditions = None
        __cached_bitstring = None

    class MoleculeReaction(db.Entity):
        _table_ = '%s_molecule_reaction' % schema if DEBUG else (schema, 'molecule_reaction')
        id = PrimaryKey(int, auto=True)
        reaction = Required('Reaction')
        molecule = Required('Molecule')
        product = Required(bool, default=False)
        mapping = Optional(Json)

    class MoleculeMerge(db.Entity):
        _table_ = '%s_molecule_merge' % schema if DEBUG else (schema, 'molecule_merge')
        id = PrimaryKey(int, auto=True)
        source = Required('Molecule', reverse='merge_target')
        target = Required('Molecule', reverse='merge_source')
        mapping = Optional(Json)

    class Conditions(db.Entity):
        _table_ = '%s_conditions' % schema if DEBUG else (schema, 'conditions')
        id = PrimaryKey(int, auto=True)
        date = Required(datetime, default=datetime.utcnow())
        user = Required('User')
        data = Required(Json)
        reaction = Required('Reaction')

    return Molecule, Reaction, Conditions
