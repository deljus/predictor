#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-
#
#  Copyright 2017 Ramil Nugmanov <stsouko@live.ru>
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
from datetime import datetime
from pony.orm import PrimaryKey, Required, Optional, Set, Json, left_join
from networkx import relabel_nodes
from bitstring import BitArray
from networkx.readwrite.json_graph import node_link_graph, node_link_data
from CGRtools.FEAR import FEAR
from CGRtools.CGRreactor import CGRreactor
from CGRtools.CGRcore import CGRcore
from CGRtools.files import MoleculeContainer, ReactionContainer
from hashlib import md5
from MODtools.descriptors.fragmentor import Fragmentor
from ..config import (FP_SIZE, FP_ACTIVE_BITS, FRAGMENTOR_VERSION, DEBUG,
                      FRAGMENT_TYPE_CGR, FRAGMENT_MIN_CGR, FRAGMENT_MAX_CGR, FRAGMENT_DYNBOND_CGR,
                      FRAGMENT_TYPE_MOL, FRAGMENT_MIN_MOL, FRAGMENT_MAX_MOL)


fear = FEAR(isotop=True)
cgr_core = CGRcore()
cgr_reactor = CGRreactor(isotop=True)


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

        merge_source = Set('Molecule', reverse='merge_target')  # molecules where self is more correct
        merge_target = Set('Molecule', reverse='merge_source',
                           table='%s_merge' % schema if DEBUG else (schema, 'merge'))  # links to correct molecules

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
            fear_string = self.get_fear(molecule)
            exists = Molecule.exists(fear=fear_string)
            if not exists:
                m = Molecule(molecule, user, fear_string=fear_string)
                parent = self.parent or self

                # todo: add new reaction record
                q = left_join(rs.reaction for m in Molecule if m == parent or m.parent == parent for rs in m.reactions)
                for x in q:
                    pass

                m.parent = parent
                self.__cached_structure = molecule
                return m

            elif exists not in self.merge_target:
                self.merge_target.add(exists)

            return False

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
            if self.__cached_structure_parent is None and self.parent:
                g = node_link_graph(self.parent.data)
                g.__class__ = MoleculeContainer
                self.__cached_structure_parent = g
            return self.__cached_structure_parent

        @property
        def structure(self):
            if self.__cached_structure is None and self.__has_newest:
                data = self.children.order_by(Molecule.date).desc().first()
                if data:
                    g = node_link_graph(self.parent.data)
                    g.__class__ = MoleculeContainer
                    self.__cached_structure = g
                else:
                    self.__has_newest = False
            return self.__cached_structure

        @property
        def bitstring_fingerprint(self):
            if self.__cached_bitstring is None:
                self.__cached_bitstring = BitArray(bin=self.fingerprint)
            return self.__cached_bitstring

        __cached_structure_parent = None
        __cached_structure_raw = None
        __cached_structure = None
        __cached_bitstring = None
        __has_newest = True

    class Reaction(db.Entity):
        _table_ = '%s_reaction' % schema if DEBUG else (schema, 'reaction')
        id = PrimaryKey(int, auto=True)
        date = Required(datetime, default=datetime.utcnow())
        fear = Required(str, unique=True)
        fingerprint = Required(str) if DEBUG else Required(str, sql_type='bit(%s)' % (2 ** FP_SIZE))

        children = Set('Reaction', cascade_delete=True)
        parent = Optional('Reaction')

        molecules = Set('MoleculeReaction')
        conditions = Set('Conditions')
        special = Optional(Json)

        def __init__(self, reaction, conditions=None, fingerprint=None, fear_string=None, cgr=None,
                     substrats_fears=None, products_fears=None):
            if fear_string is None:
                fear_string, cgr = self.get_fear(reaction, get_cgr=True)
            elif cgr is None:
                cgr = cgr_core.getCGR(reaction)

            if fingerprint is None:
                fingerprint = self.get_fingerprints([cgr], is_cgr=True)[0]

            self.__cached_cgr = cgr
            self.__cached_structure = reaction
            self.__cached_bitstring = fingerprint
            super(Reaction, self).__init__(fear=fear_string, fingerprint=fingerprint.bin)

            new_mols, batch = [], []
            fears = dict(substrats=iter(substrats_fears or []), products=iter(products_fears or []))
            for i, is_p in (('substrats', False), ('products', True)):
                for x in reaction[i]:
                    m_fear_string = next(fears[i], fear.get_cgr_string(x))
                    m = Molecule.get(fear=m_fear_string)
                    if m:
                        iso = cgr_reactor.get_cgr_matcher(m.structure_raw, x).isomorphisms_iter()
                        mapping = list(next(iso).items())
                        batch.append((m, is_p, mapping))
                    else:
                        new_mols.append((x, is_p, m_fear_string))

            if new_mols:
                for fp, (x, is_p, m_fear_string) in zip(Molecule.get_fingerprints([x for x, *_ in new_mols]),
                                                        new_mols):
                    m = Molecule(x, fear_string=m_fear_string, fingerprint=fp)
                    batch.append((m, is_p, None))

            for m, is_p, mapping in batch:
                MoleculeReaction(reaction=self, molecule=m, product=is_p, mapping=mapping)

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
                        relabel_nodes(m.molecule.structure, dict(m.mapping)) if m.mapping else m.molecule.structure)
                self.__cached_structure = r
            return self.__cached_structure

        @property
        def bitstring_fingerprint(self):
            if self.__cached_bitstring is None:
                self.__cached_bitstring = BitArray(bin=self.fingerprint)
            return self.__cached_bitstring

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

    class Conditions(db.Entity):
        _table_ = '%s_conditions' % schema if DEBUG else (schema, 'conditions')
        id = PrimaryKey(int, auto=True)

        children = Set('Conditions', cascade_delete=True)
        parent = Optional('Conditions')

        reaction = Required('Reaction')

    return Molecule, Reaction
