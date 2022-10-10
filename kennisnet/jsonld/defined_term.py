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

from .ns import *
from metastreams.jsonld import identity, walk
import seecr.functools as sfc


def with_predicate(target_p):
    def fn(a,s,p,os):
        return a | {target_p:a.get(target_p, ()) + os}
    return fn


definition_rules = {
    '@type': identity,
    '@id': identity,
    schema+'inDefinedTermSet': identity,
    schema+'termCode': identity,
}
definition_walk = walk(definition_rules)
definition_alignment_rules = {
    '@type': identity,
    '@id': identity,
    schema+'educationalFramework': identity,
    schema+'targetName': identity,
}
definition_alignment_walk = walk(definition_alignment_rules)

definition_alignment_to_keywords_rules = {
    '@type': lambda a,s,p,os: a|{'@type':(schema+'DefinedTerm',)},
    '@id': identity,
    schema+'educationalFramework': with_predicate(schema+'inDefinedTermSet'),
    schema+'targetName': with_predicate(schema+'termCode'),
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
        return bool(term.get('@id'))
    termId = term.get('@id')
    if termId and any(_startswith_uri(termId, uri) for uri in curriculum_uris):
        return True
    return False

def defined_term(target_p):
    to_keywords_walk = definition_walk
    copy_walk = definition_walk
    inDefinedTermSet = schema+'inDefinedTermSet'
    if target_p == schema+'educationalAlignment':
        to_keywords_walk = definition_alignment_keywords_walk
        copy_walk = definition_alignment_walk
        inDefinedTermSet = schema+'educationalFramework'

    def defined_term_fn(a,s,p,os):
        results = {
            keywords_target_p: a.get(keywords_target_p, ()),
            target_p: a.get(target_p, ()),
        }
        for term in os:
            target = target_p
            w = copy_walk
            if not is_curriculum_waarde_in_term(term, inDefinedTermSet):
                target = keywords_target_p
                w = to_keywords_walk
            results[target] += (w(term),)
        return a|{k:v for k,v in results.items() if v}
    return defined_term_fn

__all__ = ['defined_term']


from autotest import test

class teaches:
    rules = {
        schema+'teaches': defined_term(schema+'teaches'),
    }
    w=walk(rules)

    @test
    def move_data_to_keywords():
        start = {schema+'teaches':({
            '@type': (schema+'DefinedTerm',),
            schema+'inDefinedTermSet': ({'@value': 'not:conceptset'},),
            schema+'termCode': ({'@value': 'urn:uuid:onderwijs'},)
        },)}

        result = w(start)
        test.eq({schema+'keywords':({
            '@type': (schema+'DefinedTerm',),
            schema+'inDefinedTermSet': ({'@value': 'not:conceptset'},),
            schema+'termCode': ({'@value': 'urn:uuid:onderwijs'},)
        },)}, result, msg=test.diff2)

    @test
    def keep_data():
        start = {schema+'teaches':({
            '@type': (schema+'DefinedTerm',),
            '@id': "urn:uuid:onderwijs",
            schema+'inDefinedTermSet': ({'@value': "http://purl.edustandaard.nl/begrippenkader"},),
            schema+'termCode': ({'@value': 'urn:uuid:onderwijs'},)
        },)}
        result = w(start)
        test.eq({schema+'teaches':({
            '@type': (schema+'DefinedTerm',),
            '@id': "urn:uuid:onderwijs",
            schema+'inDefinedTermSet': ({'@value': "http://purl.edustandaard.nl/begrippenkader"},),
            schema+'termCode': ({'@value': 'urn:uuid:onderwijs'},)
        },)}, result, msg=test.diff2)

class educationalAlignment:
    rules = {
        schema+'educationalAlignment': defined_term(schema+'educationalAlignment'),
    }
    w=walk(rules)

    @test
    def move_data_to_keywords():
        start = {schema+'educationalAlignment':({
            '@type': (schema+'AlignmentObject',),
            schema+'educationalFramework': ({'@value': 'not:conceptset'},),
            schema+'targetName': ({'@value': 'urn:uuid:onderwijs'},)
        },)}

        result = w(start)
        test.eq({schema+'keywords':({
            '@type': (schema+'DefinedTerm',),
            schema+'inDefinedTermSet': ({'@value': 'not:conceptset'},),
            schema+'termCode': ({'@value': 'urn:uuid:onderwijs'},)
        },)}, result, msg=test.diff2)

    @test
    def keep_data():
        start = {schema+'educationalAlignment':({
            '@type': (schema+'AlignmentObject',),
            schema+'educationalFramework': ({'@value': 'https://opendata.slo.nl/curriculum/uuid'},),
            '@id': "urn:uuid:onderwijs",
            schema+'targetName': ({'@value': 'urn:uuid:onderwijs'},)
        },)}
        result = w(start)
        test.eq({schema+'educationalAlignment':({
            '@type': (schema+'AlignmentObject',),
            schema+'educationalFramework': ({'@value': 'https://opendata.slo.nl/curriculum/uuid'},),
            '@id': "urn:uuid:onderwijs",
            schema+'targetName': ({'@value': 'urn:uuid:onderwijs'},)
        },)}, result, msg=test.diff2)

@test
def test_is_curriculum_waarde():
    def term(id, termSet):
        return {'@id':id, schema+'inDefinedTermSet':({'@value': termSet},)}
    test.truth(is_curriculum_waarde_in_term(term('unknown:id', 'http://purl.edustandaard.nl/begrippenkader')))
    test.not_(is_curriculum_waarde_in_term(term('unknown:id', 'my:begrippenkader')))
    test.truth(is_curriculum_waarde_in_term(term('http://purl.edustandaard.nl/begrippenkader/unknown:id', 'my:begrippenkader')))
    test.truth(is_curriculum_waarde_in_term({'@id': 'http://purl.edustandaard.nl/begrippenkader/unknown:id'}))
    test.not_(is_curriculum_waarde_in_term({schema+'inDefinedTermSet':({'@value': 'http://purl.edustandaard.nl/begrippenkader'},)}))
    test.truth(is_curriculum_waarde_in_term(term('unknown:id', 'http://purl.edustandaard.nl/concept')))
    test.truth(is_curriculum_waarde_in_term(term('unknown:id', 'https://opendata.slo.nl/curriculum/uuid')))
    test.not_(is_curriculum_waarde_in_term({'@id': 'http://purl.edustandaard.nl/begrippenkader'}))
    test.not_(is_curriculum_waarde_in_term({'@id': 'http://purl.edustandaard.nl/begrippenkader/'}))
