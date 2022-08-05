## begin license ##
#
# "Kennisnet Json-LD" provides tools for handling tools
#
# Copyright (C) 2022 Seecr (Seek You Too B.V.) https://seecr.nl
# Copyright (C) 2022 Stichting Kennisnet https://www.kennisnet.nl
#
# This file is part of "Kennisnet Json-LD"
#
# "Kennisnet Json-LD" is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# "Kennisnet Json-LD" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with "Kennisnet Json-LD"; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
## end license ##

from metastreams.jsonld import walk, identity


schema = 'https://schema.org/'

def getp_first_value(d, p):
    for i in d.get(p, []):
        return i.get('@value')
    return None

def copy(rules):
    r = walk(rules)
    def copy_fn(a,s,p,os):
        a[p] = [r(o) for o in os]
        return a
    return copy_fn

def first(l):
    try:
        return next(iter(l))
    except StopIteration:
        return None

def as_value(v,l):
    if l:
        return {'@value':v, '@language':l}
    return {'@value':v}

def definition(lookup, type, scheme, value_p, source_p=None, identifier_p=None):
    def check_fn(a,s,p,os):
        result = a.get(p, [])
        for o in os:
            new_o = {}
            value = getp_first_value(o, value_p)
            if not value:
                continue
            l = lookup(scheme, value)
            new_value = first(l.labels)
            if not new_value is None:
                v,lang = new_value
                new_o[value_p] = [{'@value':v} | ({'@language':lang} if lang else {})]
            if not l.id is None:
                new_o['@id'] = l.id
            if new_o:
                new_o['@type'] = [type]
                result.append(new_o)
        if result:
            return a | {p:result}
        return a
    return check_fn

def prepare_enrich(lookup=None):
    rules = {
        schema+'audience': definition(lookup, schema+'Audience',
                scheme='urn:lms:intendedenduserrole',
                value_p=schema+'audienceType',),
        '*': identity,
    }
    return walk(rules)

__all__ = ['prepare_enrich']

from pyld import jsonld
from autotest import test
from pprint import pprint
from collections import namedtuple

_l = namedtuple('LookupResult', ['id', 'identifier', 'source', 'labels'], defaults=[None, None, None, list()])


# will differ from current kennisnet.edurep.schemalookup
def lookup_for_test(scheme, value):
    return {
        'urn:lms:intendedenduserrole': {
            'learnerrr': _l(
                    id='http://purl.edustandaard.nl/vdex_intendedenduserrole_lomv1p0_20060628.xml#learner',
                    identifier='learner',
                    source='http://purl.edustandaard.nl/vdex_intendedenduserrole_lomv1p0_20060628.xml',
                    labels=[('leerling', 'nl')])
        },
    }.get(scheme, {}).get(value, _l())

enrich = prepare_enrich(lookup_for_test)

@test
def test_setup():
    test.eq(None, lookup_for_test('scheme', 'value').source)
    test.eq('http://purl.edustandaard.nl/vdex_intendedenduserrole_lomv1p0_20060628.xml',
            lookup_for_test('urn:lms:intendedenduserrole', 'learnerrr').source)

@test
def test_audience():
    i = jsonld.expand({
        '@context':{'schema':schema},
        '@id': 'some:id',
        'schema:name': 'Name',
        'schema:audience':{
            'schema:audienceType': 'learnerrr',
            '@type': 'schema:Audience',
        }})
    r = enrich(i[0])
    x = jsonld.expand({
        '@context':{'schema':schema},
        '@id': 'some:id',
        'schema:name': 'Name',
        'schema:audience':{
            'schema:audienceType': {'@value': 'leerling', '@language':'nl'},
            '@type': 'schema:Audience',
            '@id': 'http://purl.edustandaard.nl/vdex_intendedenduserrole_lomv1p0_20060628.xml#learner',
        }})
    test.eq(x,[r], msg=test.diff)


