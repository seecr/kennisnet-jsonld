## begin license ##
#
# "Kennisnet Json-LD" provides tools for handling tools
#
# Copyright (C) 2023 Seecr (Seek You Too B.V.) https://seecr.nl
# Copyright (C) 2023 Stichting Kennisnet https://www.kennisnet.nl
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


# Testdata is added from examples found in real life data.
# Data is changed so it is not related to a real life example
__all__ = []

import autotest
test = autotest.get_tester(__name__)

from .enrich import example, MockLookup, prepare_enrich

@test.fixture
def enrich_and_lookup(nr_invalid=0, nr_not_found=0):
    lookup = MockLookup()
    yield prepare_enrich(lookup)[0], lookup
    test.eq(nr_invalid, len(lookup.invalid))
    test.eq(nr_not_found, len(lookup.not_found))

@test
def was_lookuperror_with_educationalAlignment(enrich_and_lookup:1):
    rec = example({
        'schema:educationalAlignment': [{
            '@id': 'urn:keyword:Niet_gespecificeerd',
            '@type': ['schema:AlignmentObject', 'schema:DefinedTerm'],
            'schema:educationalFramework': [{'@value': 'urn:keyword'}],
            'schema:inDefinedTermSet': [{'@value': 'urn:keyword'}],
            'schema:name': [{'@value': 'Niet gespecificeerd'}],
            'schema:targetName': [{'@value': 'Niet gespecificeerd'}],
            'schema:termCode': [{'@value': 'Niet gespecificeerd'}],
        }],
        'schema:educationalLevel': [{
            '@id': 'urn:keyword:VO',
            '@type': ['schema:DefinedTerm'],
            'schema:inDefinedTermSet': [{'@value': 'urn:keyword'}],
            'schema:name': [{'@value': 'VO'}],
            'schema:termCode': [{'@value': 'VO'}]
            }, {
            '@id': 'urn:keyword:MBO',
            '@type': ['schema:DefinedTerm'],
            'schema:inDefinedTermSet': [{'@value': 'urn:keyword'}],
            'schema:name': [{'@value': 'MBO'}],
            'schema:termCode': [{'@value': 'MBO'}]
            }, {
            '@id': 'urn:keyword:Niet_gespecificeerd'
        }],
        '@type': ['schema:Product', 'schema:LearningResource', 'schema:CreativeWork'],
        'schema:audience': [{
            '@id': 'https://purl.edustandaard.nl/vdex_intendedenduserrole_lomv1p0_20060628.xml#learner',
            '@type': ['schema:Audience'],
            'schema:audienceType': [{'@value': 'learner'}]}],
    })
    enrich, lookup = enrich_and_lookup
    r = enrich(rec[0])
    # print(r)
    # No more errors (see tests in defined_term.py)
