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

from .ns import schema, edurep_terms
from metastreams.jsonld import identity, walk, ignore_silently
import seecr.functools as sfc
import kennisnet.jsonld.utils as utils


def with_predicate(target_p):
    def fn(a,s,p,os):
        return a | {target_p:a.get(target_p, ()) + os}
    return fn

definition_rules = {
    '@type': identity,
    '@id': identity,
    schema+'inDefinedTermSet': identity,
    schema+'termCode': identity,
    schema+'name': identity,
}
definition_walk = walk(definition_rules)
definition_alignment_rules = {
    '@type': identity,
    '@id': identity,
    schema+'educationalFramework': identity,
    schema+'targetName': identity,
    schema+'name': identity,
}
definition_alignment_walk = walk(definition_alignment_rules)

definition_alignment_to_keywords_rules = {
    '@type': lambda a,s,p,os: a|{'@type':(schema+'DefinedTerm',)},
    '@id': identity,
    schema+'educationalFramework': with_predicate(schema+'inDefinedTermSet'),
    schema+'targetName': with_predicate(schema+'termCode'),
    schema+'name': identity,
}
definition_alignment_keywords_walk = walk(definition_alignment_to_keywords_rules)


keywords_target_p = schema+'keywords'


curriculum_uris = {
     'http://purl.edustandaard.nl/begrippenkader',
     'https://opendata.slo.nl/curriculum/uuid',
     'http://purl.edustandaard.nl/concept',
}
def _startswith_uri(termId, uri):
    a,b,c = termId.partition(uri)
    return b == uri and len(c) > 1
def is_curriculum_waarde_in_term(term, inDefinedTermSet=schema+'inDefinedTermSet'):
    termSet = sfc.get_in(term, (inDefinedTermSet, 0, '@value'))
    if termSet and termSet in curriculum_uris:
        return bool(term.get('@id')), termSet
    termId = term.get('@id')
    if termId:
        for uri in curriculum_uris:
            if _startswith_uri(termId, uri):
                return True, uri
    return False, None


def result_to_defined_term(lookup_result, target_p):
    type, termCodeKey, inDefinedTermSetKey = schema+'DefinedTerm', schema+'termCode', schema+'inDefinedTermSet'
    if target_p == schema+'educationalAlignment':
        type, termCodeKey, inDefinedTermSetKey = schema+'AlignmentObject', schema+'targetName', schema+'educationalFramework'

    result = {'@type': (type,),}
    if lookup_result.id:
        result["@id"] = lookup_result.id
    if lookup_result.identifier:
        result[termCodeKey] = ({'@value': lookup_result.identifier},)
    if lookup_result.source:
        result[inDefinedTermSetKey] = ({'@value': lookup_result.source},)
    if lookup_result.labels:
        result[schema+'name'] = tuple(utils.as_value(v,l) for v,l in lookup_result.labels)
    return result


type_to_target = {
    edurep_terms+'EducationalLevel': schema+'educationalLevel',
    edurep_terms+'EducationalObjective': schema+'teaches',
    edurep_terms+'Discipline': schema+'educationalAlignment',
}

def prep_improve_keyword(lookup):
    def improve_keyword(d):
        assert d['@type'] == (schema+'DefinedTerm',) or d['@type'] == [schema+'DefinedTerm',]
        termCode = sfc.get_in(d, (schema+'termCode', 0, '@value'))
        l_result = lookup(termCode)
        if not l_result or not l_result.type:
            return schema+'keywords', d
        target_p = type_to_target[l_result.type]
        return target_p, result_to_defined_term(l_result, target_p)
    return improve_keyword

def improve_keywords(lookup):
    improve_keyword = prep_improve_keyword(lookup)
    def keywords_fn(a,s,p,os):
        newdata = {p:list(a.get(p, ()))}
        for keyword in os:
            if keyword.get('@type') != (schema+'DefinedTerm',):
                newdata[p].append(keyword)
                continue
            target_p, keyword = improve_keyword(keyword)
            if not target_p in newdata:
                newdata[target_p] = a.get(target_p, [])
            newdata[target_p].append(keyword)
        return a|{k:tuple(v) for k,v in newdata.items() if v}
    return keywords_fn


def prep_improve_definedterm(lookup):
    def improve_definedterm(term):
        termId = term.get('@id')
        if not termId:
            return term
        lookup_result = lookup(termId)
        if not lookup_result.id:
            #TODO not_found (welk veld???)
            return term
        termCodeKey = schema+'targetName' if term.get('@type') == (schema+'AlignmentObject',) else schema+'termCode'
        if lookup_result.labels:
            term[schema+'name'] = tuple(utils.as_value(v,l) for v,l in lookup_result.labels)
        if lookup_result.identifier:
            term[termCodeKey] = ({'@value': lookup_result.identifier},)
        return term
    return improve_definedterm


def defined_term(target_p, lookupTermcode, lookupId):
    to_keywords_walk = definition_walk
    copy_walk = definition_walk
    inDefinedTermSet = schema+'inDefinedTermSet'
    if target_p == schema+'educationalAlignment':
        to_keywords_walk = definition_alignment_keywords_walk
        copy_walk = definition_alignment_walk
        inDefinedTermSet = schema+'educationalFramework'
    improve_keyword = prep_improve_keyword(lookupTermcode)
    improve_definedterm = prep_improve_definedterm(lookupId)

    def defined_term_fn(a,s,p,os):
        results = {}
        for term in os:
            is_cur, curriculum_uri = is_curriculum_waarde_in_term(term, inDefinedTermSet)
            if is_cur:
                target = target_p
                result = copy_walk(term)
                result[inDefinedTermSet] = ({'@value': curriculum_uri},)
                result = improve_definedterm(result)
            else:
                target = keywords_target_p
                result = to_keywords_walk(term)
                target, result = improve_keyword(result)
            if not target in results:
                results[target] = a.get(target, ())
            results[target] += (result,)
        return a|{k:v for k,v in results.items() if v}
    return defined_term_fn

__all__ = ['defined_term', 'improve_keywords']


from autotest import test
from collections import namedtuple
_l = namedtuple('LookupResult', ['id', 'identifier', 'source', 'labels', 'uri', 'exactMatch', 'type'], defaults=[None, None, None, list(), None, None, None])


@test
def test_is_curriculum_waarde():
    def term(id, termSet):
        return {'@id':id, schema+'inDefinedTermSet':({'@value': termSet},)}
    test.eq((True, 'http://purl.edustandaard.nl/begrippenkader'),
            is_curriculum_waarde_in_term(term('unknown:id', 'http://purl.edustandaard.nl/begrippenkader')))
    test.eq((False, None),
            is_curriculum_waarde_in_term(term('unknown:id', 'my:begrippenkader')))
    test.eq((True, 'http://purl.edustandaard.nl/begrippenkader'),
            is_curriculum_waarde_in_term(term('http://purl.edustandaard.nl/begrippenkader/unknown:id', 'my:begrippenkader')))
    test.eq((True, 'http://purl.edustandaard.nl/begrippenkader'),
            is_curriculum_waarde_in_term({'@id': 'http://purl.edustandaard.nl/begrippenkader/unknown:id'}))
    test.eq((False, 'http://purl.edustandaard.nl/begrippenkader'),
            is_curriculum_waarde_in_term({schema+'inDefinedTermSet':({'@value': 'http://purl.edustandaard.nl/begrippenkader'},)}))
    test.eq((True, 'http://purl.edustandaard.nl/concept'),
            is_curriculum_waarde_in_term(term('unknown:id', 'http://purl.edustandaard.nl/concept')))
    test.eq((True, 'https://opendata.slo.nl/curriculum/uuid'),
            is_curriculum_waarde_in_term(term('unknown:id', 'https://opendata.slo.nl/curriculum/uuid')))
    test.eq((False, None),
            is_curriculum_waarde_in_term({'@id': 'http://purl.edustandaard.nl/begrippenkader'}))
    test.eq((False, None),
            is_curriculum_waarde_in_term({'@id': 'http://purl.edustandaard.nl/begrippenkader/'}))


class teaches:
    def zoekDefinedTerm(termCode):
        return _l()

    rules = {
        schema+'keywords': ignore_silently,
        schema+'teaches': defined_term(schema+'teaches', zoekDefinedTerm, lambda i:_l()),
    }
    w=walk(rules)

    @test
    def move_data_to_keywords():
        start = {
            schema+'teaches':({
                '@type': (schema+'DefinedTerm',),
                schema+'inDefinedTermSet': ({'@value': 'not:conceptset'},),
                schema+'termCode': ({'@value': 'urn:uuid:onderwijs'},)
            },),
        }

        result = w(start)
        test.eq({
            schema+'keywords':({
                '@type': (schema+'DefinedTerm',),
                schema+'inDefinedTermSet': ({'@value': 'not:conceptset'},),
                schema+'termCode': ({'@value': 'urn:uuid:onderwijs'},)
            },)
        }, result, msg=test.diff2)

    @test
    def keep_data():
        start = {
            schema+'teaches':({
                '@type': (schema+'DefinedTerm',),
                '@id': "urn:uuid:onderwijs",
                schema+'inDefinedTermSet': ({'@value': "http://purl.edustandaard.nl/begrippenkader"},),
                schema+'termCode': ({'@value': 'urn:uuid:onderwijs'},)
            },),
        }
        result = w(start)
        test.eq({
            schema+'teaches':({
                '@type': (schema+'DefinedTerm',),
                '@id': "urn:uuid:onderwijs",
                schema+'inDefinedTermSet': ({'@value': "http://purl.edustandaard.nl/begrippenkader"},),
                schema+'termCode': ({'@value': 'urn:uuid:onderwijs'},)
            },),
        }, result, msg=test.diff2)

class educationalAlignment:
    def zoekDefinedTerm(termCode):
        return _l()
    def lookupById(id):
        return {'http://purl.edustandaard.nl/begrippenkader/12345678-1234-5678-9012-123456123456':_l(
                id='http://purl.edustandaard.nl/begrippenkader/12345678-1234-5678-9012-123456123456',
                identifier='teksten',
                source='http://purl.edustandaard.nl/begrippenkader',
                labels=[('Lezen van zakelijke teksten', 'nl')],
                type=edurep_terms+'Discipline',),
            }.get(id, _l())

    rules = {
        schema+'educationalAlignment': defined_term(schema+'educationalAlignment', zoekDefinedTerm, lookupById),
    }
    w=walk(rules)

    @test
    def move_data_to_keywords():
        start = {schema+'educationalAlignment':({
            '@type': (schema+'AlignmentObject',),
            schema+'educationalFramework': ({'@value': 'not:conceptset'},),
            schema+'targetName': ({'@value': 'urn:uuid:onderwijs'},),
            schema+'name':({'@value':'Ondewijs'},),
        },)}

        result = w(start)
        test.eq({schema+'keywords':({
            '@type': (schema+'DefinedTerm',),
            schema+'inDefinedTermSet': ({'@value': 'not:conceptset'},),
            schema+'termCode': ({'@value': 'urn:uuid:onderwijs'},),
            schema+'name':({'@value':'Ondewijs'},),
        },)}, result, msg=test.diff2)

    @test
    def keep_data():
        start = {schema+'educationalAlignment':({
            '@type': (schema+'AlignmentObject',),
            schema+'educationalFramework': ({'@value': 'https://opendata.slo.nl/curriculum/uuid'},),
            '@id': "urn:uuid:onderwijs",
            schema+'targetName': ({'@value': 'urn:uuid:onderwijs'},),
            schema+'name':({'@value':'Ondewijs'},),
        },)}
        result = w(start)
        test.eq({schema+'educationalAlignment':({
            '@type': (schema+'AlignmentObject',),
            schema+'educationalFramework': ({'@value': 'https://opendata.slo.nl/curriculum/uuid'},),
            '@id': "urn:uuid:onderwijs",
            schema+'targetName': ({'@value': 'urn:uuid:onderwijs'},),
            schema+'name':({'@value':'Ondewijs'},),
        },)}, result, msg=test.diff2)

    @test
    def keep_some():
        start = {
            schema+'educationalAlignment':({
                '@type': (schema+'AlignmentObject',),
                schema+'educationalFramework': ({'@value': 'https://opendata.slo.nl/curriculum/uuid'},),
                '@id': "urn:uuid:onderwijs",
                schema+'targetName': ({'@value': 'urn:uuid:onderwijs'},)
            },{
                '@type': (schema+'AlignmentObject',),
                schema+'educationalFramework': ({'@value': 'unknown:framework'},),
                '@id': "urn:uuid:onderwijs",
                schema+'targetName': ({'@value': 'urn:uuid:onderwijs'},)
            },)
        }
        result = w(start)
        test.eq({
            schema+'educationalAlignment':({
                '@type': (schema+'AlignmentObject',),
                schema+'educationalFramework': ({'@value': 'https://opendata.slo.nl/curriculum/uuid'},),
                '@id': "urn:uuid:onderwijs",
                schema+'targetName': ({'@value': 'urn:uuid:onderwijs'},)
            },),
            schema+'keywords': ({
                '@type': (schema+'DefinedTerm',),
                schema+'inDefinedTermSet': ({'@value': 'unknown:framework'},),
                '@id': "urn:uuid:onderwijs",
                schema+'termCode': ({'@value': 'urn:uuid:onderwijs'},)
            },),
        }, result, msg=test.diff2)

    @test
    def flow2_2_lookup_by_id():
        start = {schema+'educationalAlignment':({
            '@type': (schema+'AlignmentObject',),
            '@id': 'http://purl.edustandaard.nl/begrippenkader/12345678-1234-5678-9012-123456123456',
            schema+'targetName': ({'@value': 'urn:uuid:onderwijs'},),
            schema+'name':({'@value':'Ondewijs'},),
        },)}
        result = w(start)
        test.eq({schema+'educationalAlignment':({
            '@type': (schema+'AlignmentObject',),
            schema+'educationalFramework': ({'@value': 'http://purl.edustandaard.nl/begrippenkader'},),
            '@id': 'http://purl.edustandaard.nl/begrippenkader/12345678-1234-5678-9012-123456123456',
            schema+'targetName': ({'@value': 'teksten'},),
            schema+'name':({'@language': 'nl', '@value':'Lezen van zakelijke teksten'},),
        },)}, result, msg=test.diff2)


class keywords_flow:
    def zoekDefinedTerm(termCode):
        return {
            'urn:uuid:onderwijs': _l(
                id='http://purl.edustandaard.nl/begrippenkader/12345678-0000-1111-2222-123456123456',
                identifier='onderwijs',
                source='http://purl.edustandaard.nl/begrippenkader',
                labels=[('Onderwijs', 'nl')],
                type=edurep_terms+'Discipline',
            ),
            'urn:uuid:rekenen': _l(
                id='http://purl.edustandaard.nl/begrippenkader/12345678-1111-2222-3333-123456123456',
                identifier='rekenen',
                source='http://purl.edustandaard.nl/begrippenkader',
                labels=[('Handig rekenen', 'nl')],
                type=edurep_terms+'EducationalObjective',
            ),
            'urn:uuid:master': _l(
                id='http://purl.edustandaard.nl/begrippenkader/12345678-2222-3333-4444-123456123456',
                identifier='master',
                source='http://purl.edustandaard.nl/begrippenkader',
                labels=[('WO - Master', 'nl'), ('WO Master', 'nl')],
                type=edurep_terms+'EducationalLevel',
            ),
            'zo maar': _l(),
        }[termCode]
    def zoekId(id):
        return {
            'http://purl.edustandaard.nl/begrippenkader/87654321-0000-1111-2222-123456123456': _l(
                id='http://purl.edustandaard.nl/begrippenkader/87654321-0000-1111-2222-123456123456',
                identifier='aanvulling',
                source='http://purl.edustandaard.nl/begrippenkader',
                labels=[('De aanvulling', 'nl')],
                type=edurep_terms+'Discipline',
            ),
        }.get(id, _l())

    rules = {
        schema+'keywords': improve_keywords(zoekDefinedTerm),
        schema+'teaches': defined_term(schema+'teaches', zoekDefinedTerm, zoekId),
        schema+'educationalLevel': defined_term(schema+'educationalLevel', zoekDefinedTerm, zoekId),
        schema+'educationalAlignment': defined_term(schema+'educationalAlignment', zoekDefinedTerm, zoekId),
    }
    w = walk(rules)

    @test
    def keywords_to_teaches():
        improve_keyword = prep_improve_keyword(zoekDefinedTerm)
        keyword = {
            '@type': (schema+'DefinedTerm',),
            schema+'termCode': ({'@value': 'urn:uuid:rekenen'},),
            schema+'name': ({'@value': 'Hello, my name is...'},),
        }

        target, result = improve_keyword(keyword)

        test.eq({
            '@type': (schema+'DefinedTerm',),
            '@id': 'http://purl.edustandaard.nl/begrippenkader/12345678-1111-2222-3333-123456123456',
            schema+'inDefinedTermSet': ({'@value': 'http://purl.edustandaard.nl/begrippenkader'},),
            schema+'termCode': ({'@value': 'rekenen'},),
            schema+'name': ({'@language':'nl', '@value': 'Handig rekenen'},),
        }, result, msg=test.diff2)
        test.eq(schema+'teaches', target)

    @test
    def keywords_to_educational_level():
        improve_keyword = prep_improve_keyword(zoekDefinedTerm)
        keyword = {
            '@type': (schema+'DefinedTerm',),
            schema+'termCode': ({'@value': 'urn:uuid:master'},),
            schema+'name': ({'@value': 'Hello, my name is...'},),
        }

        target, result = improve_keyword(keyword)

        test.eq({
            '@type': (schema+'DefinedTerm',),
            '@id': 'http://purl.edustandaard.nl/begrippenkader/12345678-2222-3333-4444-123456123456',
            schema+'inDefinedTermSet': ({'@value': 'http://purl.edustandaard.nl/begrippenkader'},),
            schema+'termCode': ({'@value': 'master'},),
            schema+'name': ({'@language':'nl', '@value': 'WO - Master'},
                            {'@language':'nl', '@value': 'WO Master'},),
        }, result, msg=test.diff2)
        test.eq(schema+'educationalLevel', target)

    @test
    def keywords_to_educational_alignment():
        improve_keyword = prep_improve_keyword(zoekDefinedTerm)
        keyword = {
            '@type': (schema+'DefinedTerm',),
            schema+'termCode': ({'@value': 'urn:uuid:onderwijs'},),
            schema+'name': ({'@value': 'Hello, my name is...'},),
        }

        target, result = improve_keyword(keyword)

        test.eq(schema+'educationalAlignment', target)
        test.eq({
            '@type': (schema+'AlignmentObject',),
            '@id': 'http://purl.edustandaard.nl/begrippenkader/12345678-0000-1111-2222-123456123456',
            schema+'educationalFramework': ({'@value': 'http://purl.edustandaard.nl/begrippenkader'},),
            schema+'targetName': ({'@value': 'onderwijs'},),
            schema+'name': ({'@language':'nl', '@value': 'Onderwijs'},),
        }, result, msg=test.diff2)

    @test
    def integrate_flow_1_and_flow_2():
        start = {
            schema+'teaches':({
                '@type': (schema+'DefinedTerm',),
                schema+'termCode': ({'@value': 'urn:uuid:rekenen'},),
                schema+'name': ({'@value': 'Hello, my name is...'},),
            },{
                '@type': (schema+'DefinedTerm',),
                schema+'termCode': ({'@value': 'urn:uuid:onderwijs'},),
                schema+'name': ({'@value': 'Eigenlijk schema:educationalAlignment'},),
            },{
                '@type': (schema+'DefinedTerm',),
                schema+'termCode': ({'@value': 'zo maar'},),
                schema+'name': ({'@value': 'Gewoon keyword'},),
            },),
            schema+'keywords':({
                '@type': (schema+'DefinedTerm',),
                schema+'termCode': ({'@value': 'urn:uuid:master'},),
                schema+'name': ({'@value': 'Eigenlijk schema:educationalLevel'},),
            },
            {'@value': 'integratietest'},
            ),
            schema+'educationalAlignment': ({
                '@type': (schema+'AlignmentObject',),
                '@id': 'http://purl.edustandaard.nl/begrippenkader/87654321-0000-1111-2222-123456123456',
                schema+'targetName': ({'@value': 'weet niet'},),
                schema+'name': ({'@value': 'een schema:educationalAlignment'},),
            },)
        }

        result = w(start)

        test.eq({
            schema+'teaches': ({
                '@type': (schema+'DefinedTerm',),
                '@id': 'http://purl.edustandaard.nl/begrippenkader/12345678-1111-2222-3333-123456123456',
                schema+'inDefinedTermSet': ({'@value': 'http://purl.edustandaard.nl/begrippenkader'},),
                schema+'termCode': ({'@value': 'rekenen'},),
                schema+'name': ({'@language':'nl', '@value': 'Handig rekenen'},),
            },),
            schema+'educationalAlignment': ({
                '@type': (schema+'AlignmentObject',),
                '@id': 'http://purl.edustandaard.nl/begrippenkader/12345678-0000-1111-2222-123456123456',
                schema+'educationalFramework': ({'@value': 'http://purl.edustandaard.nl/begrippenkader'},),
                schema+'targetName': ({'@value': 'onderwijs'},),
                schema+'name': ({'@language':'nl', '@value': 'Onderwijs'},),
            },{
                '@type': (schema+'AlignmentObject',),
                '@id': 'http://purl.edustandaard.nl/begrippenkader/87654321-0000-1111-2222-123456123456',
                schema+'educationalFramework': ({'@value': 'http://purl.edustandaard.nl/begrippenkader'},),
                schema+'targetName': ({'@value': 'aanvulling'},),
                schema+'name': ({'@language':'nl', '@value': 'De aanvulling'},),
            },),
            schema+'educationalLevel': ({
                '@type': (schema+'DefinedTerm',),
                '@id': 'http://purl.edustandaard.nl/begrippenkader/12345678-2222-3333-4444-123456123456',
                schema+'inDefinedTermSet': ({'@value': 'http://purl.edustandaard.nl/begrippenkader'},),
                schema+'termCode': ({'@value': 'master'},),
                schema+'name': ({'@language':'nl', '@value': 'WO - Master'},
                                {'@language':'nl', '@value': 'WO Master'},),
            },),
            schema+'keywords':({
                '@type': (schema+'DefinedTerm',),
                schema+'termCode': ({'@value': 'zo maar'},),
                schema+'name': ({'@value': 'Gewoon keyword'},),
            },{
                '@value': 'integratietest',
            },),
        }, result, msg=test.diff2)

