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
from .defined_term import defined_term, improve_keywords, result_to_defined_term
from .ns import schema, lom, dcterms, edurep_terms, to_curie
import kennisnet.jsonld.utils as utils


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
                new_o.setdefault(value_p, []).append(utils.as_value(v,lang))
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

def definition(target_p, lookup, **kwargs):
    value_fn, build_fn = _definition_fns(**kwargs)

    def check_fn(a,s,p,os):
        result = a.get(target_p, [])
        for o in os:
            target = target_p
            value = value_fn(o)
            if not value:
                continue
            l = lookup(value)

            new = build_fn(l)
            if new:
                result.append(new)

        addition = {}
        if result:
            addition[target_p] = result
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

    def license_fn(a, s, p, os):
        '''Op basis van lom:copyrightAndOtherRestrictions wordt een lookup gedaan.
        Bij succesvolle lookup worden de velden lom:copyrightAndOtherRestrictions, schema:license en schema:copyrightNotice gevuld.
        In andere gevallen wordt de huidige data overgenomen'''
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
                    r_notice.append(utils.as_value(v,lang))
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

keyword_definition = dict(
        target_p=schema+'keywords',
        type=schema+'DefinedTerm',
        value_p=schema+'name',
        identifier_p=schema+'termCode',
        source_p=schema+'inDefinedTermSet',
    )

def prepare_enrich(lookupObject=None):
    info = {}
    # def target_and_lookup(target_p, scheme):
    #     key = _key(target_p)
    #     lookup_key = key + key_suffix
    #     # Key is used in Edurep for reporting, see kennisnet/edurep/ld/lom10toldgraph.py
    #     info.setdefault(key, {}).setdefault('lookups', {})[scheme] = {'invalid': lookup_key}
    #     def lookup_fn(value):
    #         return lookup(key=lookup_key, scheme=scheme, value=value)
    #     return dict(target_p=target_p, lookup=lookup_fn)


    license_fn = license(schema+'license', lookupObject, scheme='urn:lms:license')

    rules = {
        schema+'keywords': improve_keywords(lookupByTermCode),
        schema+'creativeWorkStatus': text(schema+'creativeWorkStatus', lookup=lookupObject, scheme='urn:lms:status'),
        schema+'interactivityType': text(schema+'interactivityType', lookup=lookupObject, scheme='urn:lms:interactivitytype'),
        schema+'encodingFormat': text(schema+'encodingFormat', lookup=lookupObject, scheme='urn:lms:mimetype'),
        dcterms+'accessRights': text(dcterms+'accessRights', lookup=lookupObject, scheme='urn:lms:accessrights'),
        lom+'aggregationLevel': text(lom+'aggregationLevel', lookup=lookupObject, scheme='urn:lms:aggregationlevel'),
        lom+'cost': cost(schema+'isAccessibleForFree', lookup=lookupObject, scheme='urn:lms:cost'),
        schema+'isAccessibleForFree': is_boolean,
        schema+'audience': definition(
                type=schema+'Audience',
                identifier_p=schema+'audienceType',
                target_p=schema+'audience',
                lookup=lookupObject,
                scheme='urn:lms:intendedenduserrole'),
        schema+'educationalAlignment': defined_term(schema+'educationalAlignment', lookupObject),
        schema+'educationalLevel': defined_term(schema+'educationalLevel', lookupObject),
        schema+'teaches': defined_term(schema+'teaches', lookupObject),
        schema+'license': license_fn,
        schema+'copyrightNotice': license_fn,
        lom+'copyrightAndOtherRestrictions': license_fn,
        '*': identity,
    }
    for k, v in rules.items():
        doc = None
        if callable(v):
            doc = v.__doc__
        elif isinstance(v, dict):
            doc = v.get('documentation')
        if doc is None:
            continue
        info.setdefault(to_curie(k), {})['documentation'] = doc


    w = walk(rules)
    def enrich(data):
        result = w(data)
        for target, matches_id in result.pop('exactMatch', []):
            terms = result.get(target, ())
            if any(matches_id == item.get('@id') for item in terms):
                continue
            term = result_to_defined_term(lookupById(matches_id), target)
            result[target] = terms + (term,)
        return result
    return enrich, info


__all__ = ['prepare_enrich']

from pyld import jsonld
from autotest import test
from pprint import pprint
from collections import namedtuple
import json

_l = namedtuple('LookupResult', ['id', 'identifier', 'source', 'labels', 'uri', 'exactMatch', 'type'],
                       defaults=[None, None,         None,     list(),   None,  None,         None])


testlookupdata = {
    'byValue': {
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
            'VO': _l(
                id='http://purl.edustandaard.nl/begrippenkader/2a1401e9-c223-493b-9b86-78f6993b1a8d',
                identifier="2a1401e9-c223-493b-9b86-78f6993b1a8d",
                source="http://purl.edustandaard.nl/begrippenkader",
                labels=[('VO', 'nl')],
                # definition=[('Voortgezet Onderwijs', 'nl')])
                type=edurep_terms+'EducationalLevel',
                ),
        }
    },
    'byId': {
        'urn:edurep:conceptset': {
            'http://purl.edustandaard.nl/begrippenkader/2a1401e9-c223-493b-9b86-78f6993b1a8d': _l(
                id='http://purl.edustandaard.nl/begrippenkader/2a1401e9-c223-493b-9b86-78f6993b1a8d',
                identifier="2a1401e9-c223-493b-9b86-78f6993b1a8d",
                source="http://purl.edustandaard.nl/begrippenkader",
                labels=[('VO', 'nl')],
                # definition=[('Voortgezet Onderwijs', 'nl')])
                type=edurep_terms+'EducationalLevel',
                ),
            'http://purl.edustandaard.nl/begrippenkader/my_nl': _l(
                id='http://purl.edustandaard.nl/begrippenkader/my_nl',
                labels=[("Nederlandse tekst", 'nl')],
            ),
            'http://purl.edustandaard.nl/begrippenkader/b79aa975-cfc2-4fbb-9093-9b4a2e7b05a6': _l(
                id='http://purl.edustandaard.nl/begrippenkader/b79aa975-cfc2-4fbb-9093-9b4a2e7b05a6',
                labels=[('Improved', 'en')]),
            'uri:has_match': _l(
                id='uri:has_match',
                source='http://purl.edustandaard.nl/concept',
                labels=[("Heeft overeenkomst", 'nl')], exactMatch='uri:matches'),
            'uri:matches': _l(
                id='uri:matches',
                source='http://purl.edustandaard.nl/concept',
                labels=[("Hetzelfde", 'nl')]),
        },
    }
}

class MockLookup:
    def __init__(self):
        self.not_found = []
        self.invalid = []
    def report_invalid(self, key, value):
        self.invalid.append((key, value))
    def report_not_found(self, key, value):
        self.not_found.append((key, value))
    def lookupById(self, scheme, value):
        return testlookupdata['byId'].get(scheme, {}).get(value, _l())
    def lookupByValue(self, scheme, value):
        return testlookupdata['byValue'].get(scheme, {}).get(value, _l())

def example(d):
    return jsonld.expand({
        '@context':{'schema':schema, 'lom': lom,},
        '@id': 'some:id',
        'schema:name': 'Name'}|d)

@test.fixture
def enrich_and_lookup():
    lookup = MockLookup()
    yield prepare_enrich(lookup)[0], lookup

@test
def test_setup(enrich_and_lookup):
    enricher, lookup = enrich_and_lookup
    test.eq(None, lookup.lookupByValue('scheme', 'value').source)
    test.eq('http://purl.edustandaard.nl/vdex_intendedenduserrole_lomv1p0_20060628.xml',
            lookup.lookupByValue('urn:lms:intendedenduserrole', 'learnerrr').source)
    lookup.report_invalid('schema:name', 'No name')
    test.eq([('schema:name', 'No name')], lookup.invalid)

@test
def test_audience(enrich_and_lookup):
    enricher, lookup = enrich_and_lookup
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
def test_audience_from_value(enrich_and_lookup):
    enricher, lookup = enrich_and_lookup
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
def test_invalid(enrich_and_lookup):
    enricher, lookup = enrich_and_lookup
    i = example({
        'schema:audience':{
            'schema:audienceType': 'no such thing',
            '@type': 'schema:Audience',
        }})
    r = enricher(i[0])
    x = example({})
    test.eq(x,[r], msg=test.diff)

tuple2list = lambda x:json.loads(json.dumps(x))

@test
def test_educationallevel(enrich_and_lookup):
    enricher, lookup = enrich_and_lookup
    i = example({
        'schema:educationalLevel': {
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://download.edustandaard.nl/vdex/vdex_context_czp_20060628.xml',
            'schema:termCode': 'VO'},
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
    test.eq(x[0],tuple2list(r), msg=test.diff2)

@test
def test_educationallevel_by_id(enrich_and_lookup):
    enricher, lookup = enrich_and_lookup
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
    test.eq(x[0],tuple2list(r), msg=test.diff)

@test
def test_educationallevel_copy(enrich_and_lookup):
    enricher, lookup = enrich_and_lookup
    i = example({
        'schema:educationalLevel': {
            '@type': 'schema:DefinedTerm',
            '@id': 'http://purl.edustandaard.nl/begrippenkader/some:unknown:uuid',
            'schema:inDefinedTermSet': 'http://purl.edustandaard.nl/begrippenkader',
            'schema:name': {'@language': 'nl',
                            '@value': 'Copy'},
            }
        })
    r = enricher(i[0])
    x = example({
        'schema:educationalLevel': {
            '@type': 'schema:DefinedTerm',
            '@id': 'http://purl.edustandaard.nl/begrippenkader/some:unknown:uuid',
            'schema:inDefinedTermSet': 'http://purl.edustandaard.nl/begrippenkader',
            'schema:name': {'@language': 'nl',
                            '@value': 'Copy'},
            }
        })
    # TODO id is onbekend, maar dat is prima
    test.eq(x[0],tuple2list(r), msg=test.diff)

@test
def test_educationallevel_copy_with_lookup(enrich_and_lookup):
    enricher, lookup = enrich_and_lookup
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
    test.eq(x[0],tuple2list(r), msg=test.diff)

@test
def test_educationallevel_copy_with_lookup_not_found(enrich_and_lookup):
    enricher, lookup = enrich_and_lookup
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
    test.eq(x[0], tuple2list(r), msg=test.diff)

@test
def test_educationallevel_copy_with_lookup(enrich_and_lookup):
    enricher, lookup = enrich_and_lookup
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
    test.eq(x[0], tuple2list(r), msg=test.diff)

@test
def test_educationallevel_copy_multi(enrich_and_lookup):
    enricher, lookup = enrich_and_lookup
    i = example({
        'schema:educationalLevel': [{
            '@id': 'http://purl.edustandaard.nl/begrippenkader/2a1401e9-c223-493b-9b86-78f6993b1a8d',
            },{
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://purl.edustandaard.nl/begrippenkader',
            '@id': 'http://purl.edustandaard.nl/begrippenkader/some:unknown:id',
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
            '@id': 'http://purl.edustandaard.nl/begrippenkader/some:unknown:id',
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
    test.eq(x[0], tuple2list(r), msg=test.diff)

@test
def test_educationallevel_copy_with_lookup_and_match(enrich_and_lookup):
    enricher, lookup = enrich_and_lookup
    i = example({
        'schema:educationalLevel': {
            '@id': 'uri:has_match',
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://purl.edustandaard.nl/begrippenkader',
            'schema:termCode': 'some code'},
        })
    r = enricher(i[0])
    x = example({
        'schema:educationalLevel': [{
            '@id': 'uri:has_match',
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://purl.edustandaard.nl/begrippenkader',
            'schema:name': {'@language': 'nl',
                            '@value': 'Heeft overeenkomst'},
            'schema:termCode': 'some code'
            },{
            '@id': 'uri:matches',
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://purl.edustandaard.nl/concept',
            'schema:name': {'@language': 'nl',
                            '@value': 'Hetzelfde'},
            },
        ]})
    test.eq(x[0], tuple2list(r), msg=test.diff)

@test
def test_educationallevel_copy_with_lookup_and_match_already_present(enrich_and_lookup):
    enricher, lookup = enrich_and_lookup
    i = example({
        'schema:educationalLevel': [{
            '@id': 'uri:matches',
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://purl.edustandaard.nl/begrippenkader',
            'schema:termCode': 'some code',
         },{
            '@id': 'uri:has_match',
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://purl.edustandaard.nl/begrippenkader',
            'schema:termCode': 'some code'
        }],
        })
    r = enricher(i[0])
    x = example({
        'schema:educationalLevel': [{
            '@id': 'uri:matches',
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://purl.edustandaard.nl/begrippenkader',
            'schema:name': {'@language': 'nl',
                            '@value': 'Hetzelfde'},
            'schema:termCode': 'some code',
         },{
            '@id': 'uri:has_match',
            '@type': 'schema:DefinedTerm',
            'schema:inDefinedTermSet': 'http://purl.edustandaard.nl/begrippenkader',
            'schema:name': {'@language': 'nl',
                            '@value': 'Heeft overeenkomst'},
            'schema:termCode': 'some code'
        }],
        })
    test.eq(x[0], tuple2list(r), msg=test.diff2)

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
def test_text(enrich_and_lookup):
    enricher, lookup = enrich_and_lookup
    i = example({'schema:creativeWorkStatus': 'definitief'})
    r = enricher(i[0])
    x = example({'schema:creativeWorkStatus': 'final'})
    test.eq(x[0],r, msg=test.diff)

@test
def test_cost(enrich_and_lookup):
    enricher, lookup = enrich_and_lookup
    i = example({'lom:cost': 'ja'})
    r = enricher(i[0])
    x = example({'schema:isAccessibleForFree': False})
    test.eq(x[0],r, msg=test.diff)

@test
def test_isAccessibleForFree(enrich_and_lookup):
    enricher, lookup = enrich_and_lookup
    i = example({'schema:isAccessibleForFree': False})
    r = enricher(i[0])
    x = example({'schema:isAccessibleForFree': False})
    test.eq(x[0],r, msg=test.diff)

    i = example({'schema:isAccessibleForFree': 'false'})
    r = enricher(i[0])
    x = example({'schema:isAccessibleForFree': False})
    test.eq(x[0],r, msg=test.diff)

@test
def test_license(enrich_and_lookup):
    enricher, lookup = enrich_and_lookup
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


# @test TODO Documentation
def test_enrich_info():
    enrich_lookup_info = prepare_enrich(MockLookup())[1]
    test.eq({
        'dcterms:accessRights': {
            'lookups': {
                'urn:lms:accessrights': {'invalid': 'dcterms:accessRights'}}},
        'lom:aggregationLevel': {
            'lookups': {
                'urn:lms:aggregationlevel': {'invalid': 'lom:aggregationLevel'}}},
        'lom:copyrightAndOtherRestrictions': {
            'documentation': test.any,},
        'schema:audience': {
            'lookups': {
                'urn:lms:intendedenduserrole': {'invalid': 'schema:audience'}}},
        'schema:copyrightNotice': {
            'documentation': test.any,},
        'schema:creativeWorkStatus': {
            'lookups': {
                'urn:lms:status': {'invalid': 'schema:creativeWorkStatus'}}},
        'schema:educationalAlignment': {
            'documentation': test.any,
            'lookups': {
                'urn:edurep:conceptset': {'invalid': 'schema:educationalAlignment.id_for_label'},
                'urn:lms:disciplinemapping': {'invalid': 'schema:educationalAlignment'}}},
        'schema:educationalLevel': {
            'documentation': test.any,
            'lookups': {
                'urn:edurep:conceptset': {'invalid': 'schema:educationalLevel.id_for_label'},
                'urn:lms:educationallevel': {'invalid': 'schema:educationalLevel'}}},
        'schema:encodingFormat': {
            'lookups': {
                'urn:lms:mimetype': {'invalid': 'schema:encodingFormat'}}},
        'schema:interactivityType': {
            'lookups': {
                'urn:lms:interactivitytype': {'invalid': 'schema:interactivityType'}}},
        'schema:isAccessibleForFree': {
            'lookups': {'urn:lms:cost': {'invalid': 'schema:isAccessibleForFree'}}},
        'schema:license': {
            'documentation': test.any,
            'lookups': {
                'urn:lms:license': {'invalid': 'schema:license'}}},
        'schema:teaches': {
            'documentation': test.any,
            'lookups': {
                'urn:edurep:conceptset': {'invalid': 'schema:teaches.id_for_label'},
                'urn:lms:po_kerndoel': {'invalid': 'schema:teaches'}}}
        }, enrich_lookup_info, msg=test.diff)
