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

from metastreams.jsonld import walk, identity, ignore_silently


schema = 'https://schema.org/'
dcterms = "http://purl.org/dc/terms/"
lom = "http://ltsc.ieee.org/xsd/LOM#"
prov: "http://www.w3.org/ns/prov#"

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

def values(os):
    for o in os:
        yield o['@value']

def _definition_fns(type, value_p=None, source_p=None, identifier_p=None):
    def value_fn(o):
        return getp_first_value(o, identifier_p) or getp_first_value(o, value_p) or o.get('@value') or o.get('@id')

    def build_fn(l):
        new_o = {}
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
            return new_o
    return value_fn, build_fn

def _not_found(not_found_definition, value_p=None, source_p=None, identifier_p=None, **_):
    if not_found_definition is None:
        return None, lambda o: None
    def build_fn(o):
        new_o = {}
        for old_p, new_p in [
                (value_p, not_found_definition.get('value_p')),
                (source_p, not_found_definition.get('source_p')),
                (identifier_p, not_found_definition.get('identifier_p')),
                ]:
            if old_p is None or new_p is None:
                continue
            v = o.get(old_p)
            if v is None:
                continue
            new_o[new_p] = v
        if new_o and not_found_definition.get('type'):
            new_o['@type'] = [not_found_definition['type']]
        return new_o
    return not_found_definition.get('target_p'), build_fn

def definition(target_p, lookup, not_found_definition=None, **kwargs):
    value_fn, build_fn = _definition_fns(**kwargs)
    new_target_p, copy_fn = _not_found(not_found_definition, **kwargs)

    def check_fn(a,s,p,os):
        result = a.get(target_p, [])
        alt_result = None if new_target_p is None else a.get(new_target_p, [])
        for o in os:
            target = target_p
            value = value_fn(o)
            if not value:
                continue
            l = lookup(target_p, value)

            new = build_fn(l)
            if new:
                result.append(new)
            else:
                new = copy_fn(o)
                if new:
                    alt_result.append(new)

        addition = {}
        if result:
            addition[target_p] = result
        if alt_result:
            addition[new_target_p] = alt_result
        return a | addition
    return check_fn

def text(target_p, lookup):
    def text_fn(a,s,p,os):
        result = a.get(target_p, [])
        for v in values(os):
            l = lookup(target_p, v)
            if l.identifier:
                result.append({'@value':l.identifier})
        return a | {target_p:result}
    return text_fn

def switch_inDefinedTermSet(s):
    # print('switch_inDefinedTermSet', s)
    termSet = getp_first_value(s, schema+'inDefinedTermSet')
    if not termSet:
        return 'default'
    for starter in ['http://purl.edustandaard.nl/begrippenkader', 'https://opendata.slo.nl/curriculum/uuid', 'http://purl.edustandaard.nl/concept']:
        if termSet.startswith(starter):
            return 'copy'
    return 'default'

def copy_data(target_p, prepend=False):
    def copy_fn(a,s,p,os):
        n = a.get(target_p, [])
        c = (list(os)+n) if prepend else (n+list(os))
        return a | {target_p:c}
    return copy_fn


def prepare_enrich(lookup=None):
    def _lookup(scheme):
        def lookup_fn(predicate, value):
            key = predicate.replace(schema, 'schema:') # Used in Edurep for reporting, see kennisnet/edurep/ld/lom10toldgraph.py
            return lookup(key=key, scheme=scheme, value=value)
        return lookup_fn
    keyword_definition = dict(
            target_p=schema+'keywords',
            type=schema+'DefinedTerm',
            value_p=schema+'name',
            identifier_p=schema+'termCode',
            source_p=schema+'inDefinedTermSet',
        )
    rules = {
        schema+'keywords': copy_data(schema+'keywords', prepend=True),
        schema+'creativeWorkStatus': text(
                target_p=schema+'creativeWorkStatus',
                lookup=_lookup('urn:lms:status')
            ),
        schema+'interactivityType': text(
                target_p=schema+'interactivityType',
                lookup=_lookup('urn:lms:interactivitytype')
            ),
        schema+'encodingFormat': text(
                target_p=schema+'encodingFormat',
                lookup=_lookup('urn:lms:mimetype')
            ),
        lom+'aggregationLevel': text(
                target_p=lom+'aggregationLevel',
                lookup=_lookup('urn:lms:aggregationlevel')
            ),
        schema+'audience': definition(
                target_p=schema+'audience',
                lookup=_lookup('urn:lms:intendedenduserrole'),
                type=schema+'Audience',
                identifier_p=schema+'audienceType',),
        schema+'educationalLevel': {
            '__switch__': lambda a,s: switch_inDefinedTermSet(s),
            'default': definition(
                    target_p=schema+'educationalLevel',
                    lookup=_lookup('urn:lms:educationallevel'),
                    type=schema+'DefinedTerm',
                    value_p=schema+'name',
                    identifier_p=schema+'termCode',
                    source_p=schema+'inDefinedTermSet',
                    not_found_definition=keyword_definition,
                ),
            'copy': copy_data(
                    target_p=schema+'educationalLevel',
                ),
            },
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
    'urn:lms:status': {
        'definitief': _l(identifier='final'),
    }
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
    test.eq(x[0],r, msg=test.diff)

@test
def test_educationallevel_copy(enricher):
    i = jsonld.expand({
        '@context':{'schema':schema},
        '@id': 'some:id',
        'schema:name': 'Name',
        'schema:educationalLevel': {
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://purl.edustandaard.nl/begrippenkader',
            'schema:name': {'@language': 'nl',
                            '@value': 'Copy'},
            }
        })
    r = enricher(i[0])
    x = jsonld.expand({
        '@context':{'schema':schema},
        '@id': 'some:id',
        'schema:name': 'Name',
        'schema:educationalLevel': {
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://purl.edustandaard.nl/begrippenkader',
            'schema:name': {'@language': 'nl',
                            '@value': 'Copy'},
            }
        })
    test.eq(x[0],r, msg=test.diff)

@test
def test_educationallevel_copy_multi(enricher):
    i = jsonld.expand({
        '@context':{'schema':schema},
        '@id': 'some:id',
        'schema:name': 'Name',
        'schema:educationalLevel': [{
            '@id': 'http://purl.edustandaard.nl/begrippenkader/2a1401e9-c223-493b-9b86-78f6993b1a8d',
            },{
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://purl.edustandaard.nl/begrippenkader',
            'schema:name': {'@language': 'nl',
                            '@value': 'Copy'},
            }, {
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://download.edustandaard.nl/vdex/vdex_classification_educationallevel_czp_20060628.xml',
            'schema:name': {'@language': 'nl', '@value': 'VWO, studiehuis'},
            'schema:termCode': 'vwo_st'
            }, {
            '@type': 'schema:DefinedTerm',
            'schema:name': {'@language': 'nl',
                            '@value': 'Voortgezet Onderwijs'},
            }],
        'schema:keywords':['aap', 'noot'],
        })
    r = enricher(i[0])
    x = jsonld.expand({
        '@context':{'schema':schema},
        '@id': 'some:id',
        'schema:name': 'Name',
        'schema:educationalLevel': [{
            '@id': 'http://purl.edustandaard.nl/begrippenkader/2a1401e9-c223-493b-9b86-78f6993b1a8d',
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://purl.edustandaard.nl/begrippenkader',
            'schema:name': {'@language': 'nl',
                            '@value': 'VO'},
            'schema:termCode': '2a1401e9-c223-493b-9b86-78f6993b1a8d'
            },{
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://purl.edustandaard.nl/begrippenkader',
            'schema:name': {'@language': 'nl',
                            '@value': 'Copy'},
            }],
        'schema:keywords':[{'@value': 'aap'},{'@value': 'noot'},
            {
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://download.edustandaard.nl/vdex/vdex_classification_educationallevel_czp_20060628.xml',
            'schema:name': {'@language': 'nl', '@value': 'VWO, studiehuis'},
            'schema:termCode': 'vwo_st'
            },{
            '@type': 'schema:DefinedTerm',
            'schema:name': {'@language': 'nl',
                            '@value': 'Voortgezet Onderwijs'},
            }]
        })
    test.eq(x[0],r, msg=test.diff)

def prepare_lookup(no_result_for=None):
    looked = []
    def lookup(p, v):
        looked.append((p,v))
        if v == no_result_for:
            return _l()
        return _l(id='urn:id', identifier='identifier', labels=[('aap', 'nl'), ('ape', 'en')], source='source')
    return looked, lookup

@test
def test_definition():
    looked, lookup = prepare_lookup()

    df = definition(target_p='target_p', lookup=lookup, type='type', value_p='value_p', source_p='source_p', identifier_p='identifier_p')
    acc = {'has':'value'}
    os = [{'@value':'value'}]
    s = {'value_p':os}
    p = 'pred'
    r = df(acc,s,p,os)

    test.eq([('target_p', 'value')], looked)
    test.eq({'has': 'value',
        'target_p': [{
            'value_p': [{'@value': 'aap', '@language': 'nl'},
                        {'@value': 'ape', '@language': 'en'}],
            'identifier_p': [{'@value': 'identifier'}],
            'source_p': [{'@value': 'source'}],
            '@id': 'urn:id',
            '@type': ['type']
            }]
        }, r)

@test
def test_definition_not_found():
    looked, lookup = prepare_lookup(no_result_for='value')

    df = definition(target_p='target_p', lookup=lookup, type='type', value_p='value_p', source_p='source_p', identifier_p='identifier_p')
    acc = {'has':'value'}
    os = [{'@value':'value'}]
    s = {'value_p':os}
    p = 'pred'
    r = df(acc,s,p,os)

    test.eq([('target_p', 'value')], looked)
    test.eq({'has': 'value',
        }, r)

@test
def test_definition_not_found():
    looked, lookup = prepare_lookup(no_result_for='orig_value')

    df = definition(target_p='target_p', lookup=lookup, type='type', value_p='value_p', source_p='source_p', identifier_p='identifier_p',
            not_found_definition=dict(target_p='new_target_p', type='new_type', value_p='new_value_p', source_p='new_source_p', identifier_p='new_identifier_p'),
            )
    acc = {'has':'value'}
    os = [{'@type':['type'],
        'source_p':[{'@value':'orig_source'}],
        'value_p':[{'@value':'orig_value'}],
        'identifier_p':[{'@identifier':'orig_identifier'}],
        '@id':'urn:orig:id',
        }]
    s = {'value_p':os}
    p = 'pred'
    r = df(acc,s,p,os)

    test.eq([('target_p', 'orig_value')], looked)
    test.eq({'has': 'value',
        'new_target_p':[{
            '@type':['new_type'],
            'new_source_p':[{'@value':'orig_source'}],
            'new_value_p':[{'@value':'orig_value'}],
            'new_identifier_p':[{'@identifier':'orig_identifier'}],
        }]}, r, msg=test.diff)

@test
def test_text(enricher):
    i = jsonld.expand({
        '@context':{'schema':schema},
        '@id': 'some:id',
        'schema:name': 'Name',
        'schema:creativeWorkStatus': 'definitief',
        })
    r = enricher(i[0])
    x = jsonld.expand({
        '@context':{'schema':schema},
        '@id': 'some:id',
        'schema:name': 'Name',
        'schema:creativeWorkStatus': 'final',
        })
    # pprint([r])
    # pprint(x)
    test.eq(x[0],r, msg=test.diff)
