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

def definition(lookup, type, value_p=None, source_p=None, identifier_p=None):
    def check_fn(a,s,p,os):
        result = a.get(p, [])
        for o in os:
            new_o = {}
            value = getp_first_value(o, value_p) or getp_first_value(o, identifier_p) or o.get('@value') or o.get('@id')
            if not value:
                continue
            l = lookup(p, value)

            if value_p:
                for v,lang in l.labels:
                    new_o.setdefault(value_p, []).append(as_value(v,lang))
            if identifier_p and l.identifier:
                new_o[identifier_p] = [{'@value': l.identifier}]
            if source_p and l.source:
                new_o[source_p] = [{'@value': l.source}]
            # if
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
    def _lookup(scheme):
        def lookup_fn(predicate, value):
            key = predicate.replace(schema, 'schema:') # Used in Edurep for reporting, see kennisnet/edurep/ld/lom10toldgraph.py
            return lookup(key=key, scheme=scheme, value=value)
        return lookup_fn
    rules = {
        schema+'audience': definition(_lookup('urn:lms:intendedenduserrole'),
                schema+'Audience',
                identifier_p=schema+'audienceType',),
        schema+'educationalLevel': definition(_lookup('urn:lms:educationallevel'),
                schema+'DefinedTerm',
                value_p=schema+'name',
                identifier_p=schema+'termCode',
                source_p=schema+'inDefinedTermSet',
                ),
        '*': identity,
    }
    return walk(rules)

__all__ = ['prepare_enrich']

from pyld import jsonld
from autotest import test
from pprint import pprint
from collections import namedtuple

_l = namedtuple('LookupResult', ['id', 'identifier', 'source', 'labels'], defaults=[None, None, None, list()])


testlookupdata = {
    'urn:lms:intendedenduserrole': {
        'teacher': _l(
                id='http://purl.edustandaard.nl/vdex_intendedenduserrole_lomv1p0_20060628.xml#teacher',
                identifier='teacher',
                source='http://purl.edustandaard.nl/vdex_intendedenduserrole_lomv1p0_20060628.xml',
                labels=[('docent', 'nl')]),
        'learnerrr': _l(
                id='http://purl.edustandaard.nl/vdex_intendedenduserrole_lomv1p0_20060628.xml#learner',
                identifier='learner',
                source='http://purl.edustandaard.nl/vdex_intendedenduserrole_lomv1p0_20060628.xml',
                labels=[('leerling', 'nl')]),
    },
    'urn:lms:educationallevel': {
        'VO': _l(
            id='http://purl.edustandaard.nl/begrippenkader/2a1401e9-c223-493b-9b86-78f6993b1a8d',
            identifier="2a1401e9-c223-493b-9b86-78f6993b1a8d",
            source="http://purl.edustandaard.nl/begrippenkader",
            labels=[('VO', 'nl')],
            # definition=[('Voortgezet Onderwijs', 'nl')])
            ),
    },
}
testlookupdata['urn:lms:educationallevel']['http://purl.edustandaard.nl/begrippenkader/2a1401e9-c223-493b-9b86-78f6993b1a8d'] = testlookupdata['urn:lms:educationallevel']['VO']

def lookup_for_test(key, scheme, value):
    return testlookupdata.get(scheme, {}).get(value, _l())

@test.fixture
def enricher():
    yield prepare_enrich(lookup_for_test)

@test
def test_setup():
    test.eq(None, lookup_for_test('schema:thing', 'scheme', 'value').source)
    test.eq('http://purl.edustandaard.nl/vdex_intendedenduserrole_lomv1p0_20060628.xml',
            lookup_for_test('schema:audience', 'urn:lms:intendedenduserrole', 'learnerrr').source)

@test
def test_audience(enricher):
    i = jsonld.expand({
        '@context':{'schema':schema},
        '@id': 'some:id',
        'schema:name': 'Name',
        'schema:audience':[{
            'schema:audienceType': 'learnerrr',
            '@type': 'schema:Audience',
            },{
            'schema:audienceType': 'wrong',
            '@type': 'schema:Audience',
            },{
            'schema:audienceType': [{'@value':'teacher'}, {'@value':'docent'}],
            '@type': 'schema:Audience',
        }]})
    r = enricher(i[0])
    x = jsonld.expand({
        '@context':{'schema':schema},
        '@id': 'some:id',
        'schema:name': 'Name',
        'schema:audience':[{
            'schema:audienceType': 'learner',
            '@type': 'schema:Audience',
            '@id': 'http://purl.edustandaard.nl/vdex_intendedenduserrole_lomv1p0_20060628.xml#learner',
            },{
            'schema:audienceType': 'teacher',
            '@type': 'schema:Audience',
            '@id': 'http://purl.edustandaard.nl/vdex_intendedenduserrole_lomv1p0_20060628.xml#teacher',
        }]})
    test.eq(x,[r], msg=test.diff)

@test
def test_audience_from_value(enricher):
    i = jsonld.expand({
        '@context':{'schema':schema},
        '@id': 'some:id',
        'schema:name': 'Name',
        'schema:audience': 'learnerrr',
        })
    r = enricher(i[0])
    x = jsonld.expand({
        '@context':{'schema':schema},
        '@id': 'some:id',
        'schema:name': 'Name',
        'schema:audience':[{
            'schema:audienceType': 'learner',
            '@type': 'schema:Audience',
            '@id': 'http://purl.edustandaard.nl/vdex_intendedenduserrole_lomv1p0_20060628.xml#learner',
        }]})
    test.eq(x,[r], msg=test.diff)

@test
def test_invalid(enricher):
    i = jsonld.expand({
        '@context':{'schema':schema},
        '@id': 'some:id',
        'schema:name': 'Name',
        'schema:audience':{
            'schema:audienceType': 'no such thing',
            '@type': 'schema:Audience',
        }})
    r = enricher(i[0])
    x = jsonld.expand({
        '@context':{'schema':schema},
        '@id': 'some:id',
        'schema:name': 'Name',
        })
    test.eq(x,[r], msg=test.diff)

@test
def test_educationallevel(enricher):
    i = jsonld.expand({
        '@context':{'schema':schema},
        '@id': 'some:id',
        'schema:name': 'Name',
        'schema:educationalLevel': {
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://download.edustandaard.nl/vdex/vdex_context_czp_20060628.xml',
            'schema:name': 'VO'},
        })
    r = enricher(i[0])
    x = jsonld.expand({
        '@context':{'schema':schema},
        '@id': 'some:id',
        'schema:name': 'Name',
        'schema:educationalLevel': {
            '@id': 'http://purl.edustandaard.nl/begrippenkader/2a1401e9-c223-493b-9b86-78f6993b1a8d',
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://purl.edustandaard.nl/begrippenkader',
            'schema:name': {'@language': 'nl',
                            '@value': 'VO'},
            'schema:termCode': '2a1401e9-c223-493b-9b86-78f6993b1a8d'},
        })
    # pprint([r])
    # pprint(x)
    test.eq(x[0],r, msg=test.diff)

@test
def test_educationallevel_by_id(enricher):
    i = jsonld.expand({
        '@context':{'schema':schema},
        '@id': 'some:id',
        'schema:name': 'Name',
        'schema:educationalLevel': {
            '@id': 'http://purl.edustandaard.nl/begrippenkader/2a1401e9-c223-493b-9b86-78f6993b1a8d',
        }})
    r = enricher(i[0])
    x = jsonld.expand({
        '@context':{'schema':schema},
        '@id': 'some:id',
        'schema:name': 'Name',
        'schema:educationalLevel': {
            '@id': 'http://purl.edustandaard.nl/begrippenkader/2a1401e9-c223-493b-9b86-78f6993b1a8d',
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://purl.edustandaard.nl/begrippenkader',
            'schema:name': {'@language': 'nl',
                            '@value': 'VO'},
            'schema:termCode': '2a1401e9-c223-493b-9b86-78f6993b1a8d'},
        })
    # pprint([r])
    # pprint(x)
    test.eq(x[0],r, msg=test.diff)

@test
def test_definition():
    looked = []
    def lookup(p, v):
        looked.append((p,v))
        return _l(id='urn:id', identifier='identifier', labels=[('aap', 'nl'), ('ape', 'en')], source='source')

    df = definition(lookup, 'type', value_p='value_p', source_p='source_p', identifier_p='identifier_p')
    acc = {'has':'value'}
    os = [{'@value':'value'}]
    s = {'value_p':os}
    p = 'pred'
    r = df(acc,s,p,os)

    test.eq([('pred', 'value')], looked)
    test.eq({'has': 'value',
        'pred': [{
            'value_p': [{'@value': 'aap', '@language': 'nl'},
                        {'@value': 'ape', '@language': 'en'}],
            'identifier_p': [{'@value': 'identifier'}],
            'source_p': [{'@value': 'source'}],
            '@id': 'urn:id',
            '@type': ['type']
            }]
        }, r)

