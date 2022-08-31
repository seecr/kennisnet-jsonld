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
            l = lookup(value)

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
            l = lookup(v)
            if l.identifier:
                result.append({'@value':l.identifier})
        return a | {target_p:result}
    return text_fn

def cost(target_p, lookup):
    def text_fn(a,s,p,os):
        for v in values(os):
            l = lookup(v)
            if l.identifier:
                return a | {target_p:[{'@value': l.identifier != 'yes'}]}
        return a
    return text_fn


def license(target_p, lookup):
    '''Op basis van lom:copyrightAndOtherRestrictions wordt een lookup gedaan.
    Bij succesvolle lookup worden de velden lom:copyrightAndOtherRestrictions, schema:license en schema:copyrightNotice gevuld.
    In andere gevallen wordt de huidige data overgenomen'''

    def license_fn(a, s, p, os):
        r_other = a.get(lom+'copyrightAndOtherRestrictions', [])
        r_notice = a.get(schema+'copyrightNotice', [])
        r_license = a.get(schema+'license', [])
        if r_other or r_license or r_notice:
            # Already a result
            return a
        for v in values(s.get(lom+'copyrightAndOtherRestrictions', [])):
            l = lookup(v)
            if l.uri:
                r_license.append({'@value': l.uri})
                r_other.append({'@value': v})
                for v,lang in l.labels:
                    r_notice.append(as_value(v,lang))
        if not r_license: #nothing new, keep old stuff
            r_other = s.get(lom+'copyrightAndOtherRestrictions', [])
            r_notice = s.get(schema+'copyrightNotice', [])
            r_license = s.get(schema+'license', [])

        new = {k:v for k,v in [
                (lom+'copyrightAndOtherRestrictions', r_other),
                (schema+'copyrightNotice', r_notice),
                (schema+'license', r_license),
            ] if v}
        return a | new
    return license_fn

def copy_if_slo_or_begrippenkader(source):
    '''Als de waardes zijn opgenomen in 'http://purl.edustandaard.nl/begrippenkader', 'https://opendata.slo.nl/curriculum/uuid' of 'http://purl.edustandaard.nl/concept' worden de waardes gekopieerd. Zo niet wordt er een lookup gedaan.'''
    copy_starters = ['http://purl.edustandaard.nl/begrippenkader', 'https://opendata.slo.nl/curriculum/uuid', 'http://purl.edustandaard.nl/concept']
    def switch_fn(a, s):
        termSet = getp_first_value(s, source)
        if not termSet:
            return 'default'
        for starter in copy_starters:
            if termSet.startswith(starter):
                return 'copy'
        return 'default'
    return switch_fn


def copy_data(target_p, rules=None, prepend=False):
    cw = (lambda x:x) if rules is None else walk(rules)
    def copy_fn(a,s,p,os):
        n = a.get(target_p, [])
        result = [cw(o) for o in os]
        c = (result+n) if prepend else (n+result)
        return a | {target_p:c}
    return copy_fn

def is_boolean(a,s,p,os):
    result = a.get(p, [])
    for v in values(os):
        if type(v) is bool:
            result.append({'@value': v})
            continue
        b = {'true':True, 'yes':True, 'ja':True, 'false':False, 'no':False, 'nee':False}.get(str(v).lower())
        if not b is None:
            result.append({'@value': b})
    if result:
        return a | {p:result}
    return a

def _key(full):
    return full.replace(schema, 'schema:').replace(lom, 'lom:').replace(dcterms, 'dcterms:')

keyword_definition = dict(
        target_p=schema+'keywords',
        type=schema+'DefinedTerm',
        value_p=schema+'name',
        identifier_p=schema+'termCode',
        source_p=schema+'inDefinedTermSet',
    )
import re, uuid
uuid_r = re.compile(r'(?i)[a-f0-9\-]{32,36}')
def pretty_print_uuid(s):
    return uuid_r.sub(lambda m:str(uuid.UUID(m.group(0))), s)

def prepare_enrich(lookup=None):
    info = {'lookup':{}, 'translations':{}}
    def target_and_lookup(target_p, scheme):
        key = _key(target_p)
        # Key is used in Edurep for reporting, see kennisnet/edurep/ld/lom10toldgraph.py
        info['lookup'][key] = scheme
        def lookup_fn(value):
            return lookup(key=key, scheme=scheme, value=value)
        return dict(target_p=target_p, lookup=lookup_fn)

    def label_lookup_fn(target_p, scheme):
        key = _key(target_p)+'.id_for_label'
        info['lookup'][key] = scheme

        def fn(a,s,p,os):
            if '@id' in a or scheme+'name' in a:
                return a
            at_id = s.get('@id')
            names = s.get(schema+'name',[])
            r = {}
            if at_id:
                at_id = pretty_print_uuid(at_id)
                r['@id'] = at_id
                lr = lookup(key=key, scheme=scheme, value=at_id)
                if lr.labels:
                    names = [{'@language':lang, '@value': value} for value, lang in lr.labels]
            if names:
                r[schema+'name'] = names
            return a|r
        return fn

    license_fn = license(**target_and_lookup(schema+'license', 'urn:lms:license'))

    _rules = {
        schema+'keywords': copy_data(schema+'keywords', prepend=True),
        schema+'creativeWorkStatus': text(**target_and_lookup(schema+'creativeWorkStatus', 'urn:lms:status')),
        schema+'interactivityType': text(**target_and_lookup(schema+'interactivityType', 'urn:lms:interactivitytype')),
        schema+'encodingFormat': text(**target_and_lookup(schema+'encodingFormat', 'urn:lms:mimetype')),
        dcterms+'accessRights': text(**target_and_lookup(dcterms+'accessRights', 'urn:lms:accessrights')),
        lom+'aggregationLevel': text(**target_and_lookup(lom+'aggregationLevel', 'urn:lms:aggregationlevel')),
        lom+'cost': cost(**target_and_lookup(schema+'isAccessibleForFree', 'urn:lms:cost')),
        schema+'isAccessibleForFree': is_boolean,
        schema+'audience': definition(
                type=schema+'Audience',
                identifier_p=schema+'audienceType',
                **target_and_lookup(schema+'audience', 'urn:lms:intendedenduserrole')),
        schema+'educationalAlignment': ({
            '__switch__': copy_if_slo_or_begrippenkader(schema+'educationalFramework'),
            'default': definition(
                    type=schema+'AlignmentObject',
                    value_p=schema+'name',
                    identifier_p=schema+'targetName',
                    source_p=schema+'educationalFramework',
                    not_found_definition=keyword_definition,
                    **target_and_lookup(schema+'educationalAlignment', 'urn:lms:disciplinemapping'),
                ),
            'copy': copy_data(schema+'educationalAlignment', {
                    '*': identity,
                    '@id': label_lookup_fn(schema+'educationalAlignment', 'urn:edurep:conceptset'),
                    schema+'name': label_lookup_fn(schema+'educationalAlignment', 'urn:edurep:conceptset'),
                }),
            }, 'copy_if_slo_begrippenkader'),
        schema+'educationalLevel': ({
            '__switch__': copy_if_slo_or_begrippenkader(schema+'inDefinedTermSet'),
            'default': definition(
                    type=schema+'DefinedTerm',
                    value_p=schema+'name',
                    identifier_p=schema+'termCode',
                    source_p=schema+'inDefinedTermSet',
                    not_found_definition=keyword_definition,
                    **target_and_lookup(schema+'educationalLevel', 'urn:lms:educationallevel'),
                ),
            'copy': copy_data(schema+'educationalLevel', {
                    '*': identity,
                    '@id': label_lookup_fn(schema+'educationalLevel', 'urn:edurep:conceptset'),
                    schema+'name': label_lookup_fn(schema+'educationalLevel', 'urn:edurep:conceptset'),
                }),
            }, 'copy_if_slo_begrippenkader'),
        schema+'teaches': ({
            '__switch__': copy_if_slo_or_begrippenkader(schema+'inDefinedTermSet'),
            'default': definition(
                    type=schema+'DefinedTerm',
                    value_p=schema+'name',
                    identifier_p=schema+'termCode',
                    source_p=schema+'inDefinedTermSet',
                    not_found_definition=keyword_definition,
                    **target_and_lookup(schema+'teaches', 'urn:lms:po_kerndoel'),
                ),
            'copy': copy_data(schema+'teaches', {
                    '*': identity,
                    '@id': label_lookup_fn(schema+'teaches', 'urn:edurep:conceptset'),
                    schema+'name': label_lookup_fn(schema+'teaches', 'urn:edurep:conceptset'),
                }),
            }, 'copy_if_slo_begrippenkader'),
        schema+'license': (license_fn, 'license'),
        schema+'copyrightNotice': (license_fn, 'license'),
        lom+'copyrightAndOtherRestrictions': (license_fn, 'license'),
        '*': identity,
    }
    rules = {}
    for k, rule in _rules.items():
        if isinstance(rule, tuple):
            rule, rule_info = rule
            info['translations'][_key(k)] = explanations[rule_info]
        rules[k] = rule

    return walk(rules), info

explanations = {
        'license': license.__doc__,
        'copy_if_slo_begrippenkader': copy_if_slo_or_begrippenkader.__doc__ + ''' Als de waardes bij een lookup niet worden gevonden worden ze toegevoegd aan schema:keywords''',
    }

__all__ = ['prepare_enrich', 'explanations']

from pyld import jsonld
from autotest import test
from pprint import pprint
from collections import namedtuple

_l = namedtuple('LookupResult', ['id', 'identifier', 'source', 'labels', 'uri'], defaults=[None, None, None, list(), None])


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
    },
    'urn:lms:cost': {
        'ja': _l(identifier='yes'),
    },
    'urn:lms:license': {
        'cc-by-40': _l(uri='http://creativecommons.org/licenses/by/4.0/', labels=[("CC BY 4.0", 'nl')]),
    },
    'urn:edurep:conceptset': {
        'http://purl.edustandaard.nl/begrippenkader/my_nl': _l(labels=[("Nederlandse tekst", 'nl')]),
        'http://purl.edustandaard.nl/begrippenkader/b79aa975-cfc2-4fbb-9093-9b4a2e7b05a6': _l(labels=[('Improved', 'en')]),
    },
}
testlookupdata['urn:lms:educationallevel']['http://purl.edustandaard.nl/begrippenkader/2a1401e9-c223-493b-9b86-78f6993b1a8d'] = testlookupdata['urn:lms:educationallevel']['VO']

def lookup_for_test(key, scheme, value):
    return testlookupdata.get(scheme, {}).get(value, _l())

def example(d):
    return jsonld.expand({
        '@context':{'schema':schema, 'lom': lom,},
        '@id': 'some:id',
        'schema:name': 'Name'}|d)

@test.fixture
def enricher():
    yield prepare_enrich(lookup_for_test)[0]

@test
def test_setup():
    test.eq(None, lookup_for_test('schema:thing', 'scheme', 'value').source)
    test.eq('http://purl.edustandaard.nl/vdex_intendedenduserrole_lomv1p0_20060628.xml',
            lookup_for_test('schema:audience', 'urn:lms:intendedenduserrole', 'learnerrr').source)

@test
def test_audience(enricher):
    i = example({
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
    x = example({
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
    i = example({'schema:audience': 'learnerrr'})
    r = enricher(i[0])
    x = example({
        'schema:audience':[{
            'schema:audienceType': 'learner',
            '@type': 'schema:Audience',
            '@id': 'http://purl.edustandaard.nl/vdex_intendedenduserrole_lomv1p0_20060628.xml#learner',
        }]})
    test.eq(x,[r], msg=test.diff)

@test
def test_invalid(enricher):
    i = example({
        'schema:audience':{
            'schema:audienceType': 'no such thing',
            '@type': 'schema:Audience',
        }})
    r = enricher(i[0])
    x = example({})
    test.eq(x,[r], msg=test.diff)

@test
def test_educationallevel(enricher):
    i = example({
        'schema:educationalLevel': {
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://download.edustandaard.nl/vdex/vdex_context_czp_20060628.xml',
            'schema:name': 'VO'},
        })
    r = enricher(i[0])
    x = example({
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
    i = example({
        'schema:educationalLevel': {
            '@id': 'http://purl.edustandaard.nl/begrippenkader/2a1401e9-c223-493b-9b86-78f6993b1a8d',
        }})
    r = enricher(i[0])
    x = example({
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
    i = example({
        'schema:educationalLevel': {
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://purl.edustandaard.nl/begrippenkader',
            'schema:name': {'@language': 'nl',
                            '@value': 'Copy'},
            }
        })
    r = enricher(i[0])
    x = example({
        'schema:educationalLevel': {
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://purl.edustandaard.nl/begrippenkader',
            'schema:name': {'@language': 'nl',
                            '@value': 'Copy'},
            }
        })
    test.eq(x[0],r, msg=test.diff)

@test
def test_educationallevel_copy_with_lookup(enricher):
    i = example({
        'schema:educationalLevel': {
            '@id': 'http://purl.edustandaard.nl/begrippenkader/my_nl',
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://purl.edustandaard.nl/begrippenkader',
            'schema:termCode': 'my_nl'},
        })
    r = enricher(i[0])
    x = example({
        'schema:educationalLevel': {
            '@id': 'http://purl.edustandaard.nl/begrippenkader/my_nl',
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://purl.edustandaard.nl/begrippenkader',
            'schema:name': {'@language': 'nl',
                            '@value': 'Nederlandse tekst'},
            'schema:termCode': 'my_nl'},
        })
    test.eq(x[0],r, msg=test.diff)

@test
def test_educationallevel_copy_with_lookup_not_found(enricher):
    i = example({
        'schema:educationalLevel': {
            '@id': 'http://purl.edustandaard.nl/begrippenkader/made_up',
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://purl.edustandaard.nl/begrippenkader',
            'schema:name': {'@language': 'nl',
                            '@value': 'Made Up Tekst'},
            'schema:termCode': 'made_up'},
        })
    r = enricher(i[0])
    x = example({
        'schema:educationalLevel': {
            '@id': 'http://purl.edustandaard.nl/begrippenkader/made_up',
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://purl.edustandaard.nl/begrippenkader',
            'schema:name': {'@language': 'nl',
                            '@value': 'Made Up Tekst'},
            'schema:termCode': 'made_up'},
        })
    test.eq(x[0],r, msg=test.diff)

@test
def test_educationallevel_copy_with_lookup(enricher):
    i = example({
        'schema:educationalLevel': {
            '@id': 'http://purl.edustandaard.nl/begrippenkader/B79AA975CFC24FBB90939B4A2E7B05A6',
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://purl.edustandaard.nl/begrippenkader',
            'schema:termCode': 'b79aa975-cfc2-4fbb-9093-9b4a2e7b05a6'},
        })
    r = enricher(i[0])
    x = example({
        'schema:educationalLevel': {
            '@id': 'http://purl.edustandaard.nl/begrippenkader/b79aa975-cfc2-4fbb-9093-9b4a2e7b05a6',
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://purl.edustandaard.nl/begrippenkader',
            'schema:name': {'@language': 'en',
                            '@value': 'Improved'},
            'schema:termCode': 'b79aa975-cfc2-4fbb-9093-9b4a2e7b05a6'},
        })
    test.eq(x[0],r, msg=test.diff)

@test
def test_educationallevel_copy_multi(enricher):
    i = example({
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
    x = example({
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
    def lookup(v):
        looked.append(v)
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

    test.eq(['value'], looked)
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

    test.eq(['value'], looked)
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

    test.eq(['orig_value'], looked)
    test.eq({'has': 'value',
        'new_target_p':[{
            '@type':['new_type'],
            'new_source_p':[{'@value':'orig_source'}],
            'new_value_p':[{'@value':'orig_value'}],
            'new_identifier_p':[{'@identifier':'orig_identifier'}],
        }]}, r, msg=test.diff)

@test
def test_text(enricher):
    i = example({'schema:creativeWorkStatus': 'definitief'})
    r = enricher(i[0])
    x = example({'schema:creativeWorkStatus': 'final'})
    test.eq(x[0],r, msg=test.diff)

@test
def test_cost(enricher):
    i = example({'lom:cost': 'ja'})
    r = enricher(i[0])
    x = example({'schema:isAccessibleForFree': False})
    test.eq(x[0],r, msg=test.diff)

@test
def test_isAccessibleForFree(enricher):
    i = example({'schema:isAccessibleForFree': False})
    r = enricher(i[0])
    x = example({'schema:isAccessibleForFree': False})
    test.eq(x[0],r, msg=test.diff)

    i = example({'schema:isAccessibleForFree': 'false'})
    r = enricher(i[0])
    x = example({'schema:isAccessibleForFree': False})
    test.eq(x[0],r, msg=test.diff)

@test
def test_license(enricher):
    i = example({
        'lom:copyrightAndOtherRestrictions': 'cc-by-40',
        'schema:copyrightNotice': 'Notice, will be removed'})
    r = enricher(i[0])
    x = example({
        'lom:copyrightAndOtherRestrictions': 'cc-by-40',
        'schema:copyrightNotice': {'@language': 'nl', '@value': 'CC BY 4.0'},
        'schema:license': 'http://creativecommons.org/licenses/by/4.0/'})
    test.eq(x[0],r, msg=test.diff)


    i = example({
        'lom:copyrightAndOtherRestrictions': 'some unresolvable text',
        'schema:copyrightNotice': 'Notice stays'})
    r = enricher(i[0])
    x = example({
        'lom:copyrightAndOtherRestrictions': 'some unresolvable text',
        'schema:copyrightNotice': 'Notice stays'})
    test.eq(x[0],r, msg=test.diff)

    i = example({
        'schema:copyrightNotice': 'Notice stays'})
    # from schema:license

@test
def test_enrich_info():
    enrich_lookup_info = prepare_enrich(lookup_for_test)[1]
    test.eq({
        'lookup': {
            'dcterms:accessRights': 'urn:lms:accessrights',
            'lom:aggregationLevel': 'urn:lms:aggregationlevel',
            'schema:audience': 'urn:lms:intendedenduserrole',
            'schema:creativeWorkStatus': 'urn:lms:status',
            'schema:educationalLevel': 'urn:lms:educationallevel',
            'schema:educationalLevel.id_for_label': 'urn:edurep:conceptset',
            'schema:educationalAlignment': 'urn:lms:disciplinemapping',
            'schema:educationalAlignment.id_for_label': 'urn:edurep:conceptset',
            'schema:teaches': 'urn:lms:po_kerndoel',
            'schema:teaches.id_for_label': 'urn:edurep:conceptset',
            'schema:encodingFormat': 'urn:lms:mimetype',
            'schema:interactivityType': 'urn:lms:interactivitytype',
            'schema:isAccessibleForFree': 'urn:lms:cost',
            'schema:license': 'urn:lms:license',
        },
        'translations':{
            'schema:educationalLevel': explanations['copy_if_slo_begrippenkader'],
            'schema:educationalAlignment': explanations['copy_if_slo_begrippenkader'],
            'schema:teaches': explanations['copy_if_slo_begrippenkader'],
            'schema:license': explanations['license'],
            'lom:copyrightAndOtherRestrictions': explanations['license'],
            'schema:copyrightNotice': explanations['license'],

        }
        }, enrich_lookup_info, msg=test.diff)
