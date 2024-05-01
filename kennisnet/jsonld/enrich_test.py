## begin license ##
#
# "Kennisnet Json-LD" provides tools for handling tools
#
# Copyright (C) 2024 Seecr (Seek You Too B.V.) https://seecr.nl
# Copyright (C) 2024 Stichting Kennisnet https://www.kennisnet.nl
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

from .enrich import prepare_enrich, definition

from collections import namedtuple
from .utils import anything
from .ns import edurep_terms, schema, lom, dcterms
from contextlib import contextmanager
from pyld import jsonld

import pytest

_l = namedtuple(
    "LookupResult",
    ["id", "identifier", "source", "labels", "uri", "exactMatch", "type"],
    defaults=[None, None, None, list(), None, None, None],
)


testlookupdata = {
    "byValue": {
        "urn:lms:intendedenduserrole": {
            "teacher": _l(
                id="http://purl.edustandaard.nl/vdex_intendedenduserrole_lomv1p0_20060628.xml#teacher",
                identifier="teacher",
                source="http://purl.edustandaard.nl/vdex_intendedenduserrole_lomv1p0_20060628.xml",
                labels=[("docent", "nl")],
            ),
            "learnerrr": _l(
                id="http://purl.edustandaard.nl/vdex_intendedenduserrole_lomv1p0_20060628.xml#learner",
                identifier="learner",
                source="http://purl.edustandaard.nl/vdex_intendedenduserrole_lomv1p0_20060628.xml",
                labels=[("leerling", "nl")],
            ),
        },
        "urn:lms:status": {
            "definitief": _l(identifier="final"),
        },
        "urn:lms:cost": {
            "ja": _l(identifier="yes"),
        },
        "urn:lms:license": {
            "cc-by-40": _l(
                uri="http://creativecommons.org/licenses/by/4.0/",
                labels=[("CC BY 4.0", "nl")],
            ),
        },
        "urn:edurep:conceptset": {
            "VO": _l(
                id="http://purl.edustandaard.nl/begrippenkader/2a1401e9-c223-493b-9b86-78f6993b1a8d",
                identifier="2a1401e9-c223-493b-9b86-78f6993b1a8d",
                source="http://purl.edustandaard.nl/begrippenkader",
                labels=[("VO", "nl")],
                # definition=[('Voortgezet Onderwijs', 'nl')])
                type=edurep_terms + "EducationalLevel",
            ),
        },
    },
    "byId": {
        "urn:edurep:conceptset": {
            "http://purl.edustandaard.nl/begrippenkader/2a1401e9-c223-493b-9b86-78f6993b1a8d": _l(
                id="http://purl.edustandaard.nl/begrippenkader/2a1401e9-c223-493b-9b86-78f6993b1a8d",
                identifier="2a1401e9-c223-493b-9b86-78f6993b1a8d",
                source="http://purl.edustandaard.nl/begrippenkader",
                labels=[("VO", "nl")],
                # definition=[('Voortgezet Onderwijs', 'nl')])
                type=edurep_terms + "EducationalLevel",
            ),
            "http://purl.edustandaard.nl/begrippenkader/my_nl": _l(
                id="http://purl.edustandaard.nl/begrippenkader/my_nl",
                labels=[("Nederlandse tekst", "nl")],
            ),
            "http://purl.edustandaard.nl/begrippenkader/b79aa975-cfc2-4fbb-9093-9b4a2e7b05a6": _l(
                id="http://purl.edustandaard.nl/begrippenkader/b79aa975-cfc2-4fbb-9093-9b4a2e7b05a6",
                labels=[("Improved", "en")],
            ),
            "uri:has_match": _l(
                id="uri:has_match",
                source="http://purl.edustandaard.nl/concept",
                labels=[("Heeft overeenkomst", "nl")],
                exactMatch="uri:matches",
            ),
            "uri:matches": _l(
                id="uri:matches",
                source="http://purl.edustandaard.nl/concept",
                labels=[("Hetzelfde", "nl")],
            ),
        },
    },
}


class MockLookup:
    def __init__(self):
        self.not_found = []
        self.invalid = []
        self.by_id = {} | testlookupdata["byId"]
        self.by_value = {} | testlookupdata["byValue"]

    def report_invalid(self, key, value):
        self.invalid.append((key, value))

    def report_not_found(self, key, value):
        self.not_found.append((key, value))

    def lookupById(self, scheme, value):
        return self.by_id.get(scheme, {}).get(value, _l())

    def lookupByValue(self, scheme, value):
        return self.by_value.get(scheme, {}).get(value, _l())


def example(d):
    return jsonld.expand(
        {
            "@context": {"schema": schema, "lom": lom, "dcterms": dcterms},
            "@id": "some:id",
            "schema:name": "Name",
        }
        | d
    )


@contextmanager
def enrich_and_lookup(nr_invalid=0, nr_not_found=0):
    lookup = MockLookup()
    yield prepare_enrich(lookup)[0], lookup
    assert len(lookup.invalid) == nr_invalid
    assert len(lookup.not_found) == nr_not_found


def test_setup():
    with enrich_and_lookup(1) as (enricher, lookup):
        assert lookup.lookupByValue("scheme", "value").source is None
        assert (
            lookup.lookupByValue("urn:lms:intendedenduserrole", "learnerrr").source
            == "http://purl.edustandaard.nl/vdex_intendedenduserrole_lomv1p0_20060628.xml"
        )
        lookup.report_invalid("schema:name", "No name")
        assert lookup.invalid == [("schema:name", "No name")]


def test_audience():
    with enrich_and_lookup(1) as (enricher, lookup):
        i = example(
            {
                "schema:audience": [
                    {
                        "schema:audienceType": "learnerrr",
                        "@type": "schema:Audience",
                    },
                    {
                        "schema:audienceType": "wrong",
                        "@type": "schema:Audience",
                    },
                    {
                        "schema:audienceType": [
                            {"@value": "teacher"},
                            {"@value": "docent"},
                        ],
                        "@type": "schema:Audience",
                    },
                ]
            }
        )
        r = enricher(i[0])
        x = example(
            {
                "schema:audience": [
                    {
                        "schema:audienceType": "learner",
                        "@type": "schema:Audience",
                        "@id": "http://purl.edustandaard.nl/vdex_intendedenduserrole_lomv1p0_20060628.xml#learner",
                    },
                    {
                        "schema:audienceType": "teacher",
                        "@type": "schema:Audience",
                        "@id": "http://purl.edustandaard.nl/vdex_intendedenduserrole_lomv1p0_20060628.xml#teacher",
                    },
                ]
            }
        )
        assert [r] == x
        assert lookup.invalid == [("schema:audience", "wrong")]


def test_audience_from_value():
    with enrich_and_lookup() as (enricher, lookup):
        i = example({"schema:audience": "learnerrr"})
        r = enricher(i[0])
        x = example(
            {
                "schema:audience": [
                    {
                        "schema:audienceType": "learner",
                        "@type": "schema:Audience",
                        "@id": "http://purl.edustandaard.nl/vdex_intendedenduserrole_lomv1p0_20060628.xml#learner",
                    }
                ]
            }
        )
        assert [r] == x


def test_invalid():
    with enrich_and_lookup(1) as (enricher, lookup):
        i = example(
            {
                "schema:audience": {
                    "schema:audienceType": "no such thing",
                    "@type": "schema:Audience",
                }
            }
        )
        assert [enricher(i[0])] == example({})
        assert lookup.invalid == [("schema:audience", "no such thing")]


def test_educationallevel():
    with enrich_and_lookup() as (enricher, lookup):
        i = example(
            {
                "schema:educationalLevel": {
                    "@type": "schema:DefinedTerm",
                    "schema:inDefinedTermSet": "http://download.edustandaard.nl/vdex/vdex_context_czp_20060628.xml",
                    "schema:termCode": "VO",
                },
            }
        )
        assert (
            enricher(i[0])
            == example(
                {
                    "schema:educationalLevel": {
                        "@id": "http://purl.edustandaard.nl/begrippenkader/2a1401e9-c223-493b-9b86-78f6993b1a8d",
                        "@type": "schema:DefinedTerm",
                        "schema:inDefinedTermSet": "http://purl.edustandaard.nl/begrippenkader",
                        "schema:name": {"@language": "nl", "@value": "VO"},
                        "schema:termCode": "2a1401e9-c223-493b-9b86-78f6993b1a8d",
                    },
                }
            )[0]
        )


def test_educationallevel_by_id():
    with enrich_and_lookup() as (enricher, lookup):
        i = example(
            {
                "schema:educationalLevel": {
                    "@id": "http://purl.edustandaard.nl/begrippenkader/2a1401e9-c223-493b-9b86-78f6993b1a8d",
                }
            }
        )
        assert [enricher(i[0])] == example(
            {
                "schema:educationalLevel": {
                    "@id": "http://purl.edustandaard.nl/begrippenkader/2a1401e9-c223-493b-9b86-78f6993b1a8d",
                    "@type": "schema:DefinedTerm",
                    "schema:inDefinedTermSet": "http://purl.edustandaard.nl/begrippenkader",
                    "schema:name": {"@language": "nl", "@value": "VO"},
                    "schema:termCode": "2a1401e9-c223-493b-9b86-78f6993b1a8d",
                },
            }
        )


def test_educationallevel_copy():
    with enrich_and_lookup(0, 1) as (enricher, lookup):
        i = example(
            {
                "schema:educationalLevel": {
                    "@type": "schema:DefinedTerm",
                    "@id": "http://purl.edustandaard.nl/begrippenkader/some:unknown:uuid",
                    "schema:inDefinedTermSet": "http://purl.edustandaard.nl/begrippenkader",
                    "schema:name": {"@language": "nl", "@value": "Copy"},
                }
            }
        )
        assert [enricher(i[0])] == example(
            {
                "schema:educationalLevel": {
                    "@type": "schema:DefinedTerm",
                    "@id": "http://purl.edustandaard.nl/begrippenkader/some:unknown:uuid",
                    "schema:inDefinedTermSet": "http://purl.edustandaard.nl/begrippenkader",
                    "schema:name": {"@language": "nl", "@value": "Copy"},
                }
            }
        )
        assert lookup.not_found == [
            (
                "schema:educationalLevel",
                "http://purl.edustandaard.nl/begrippenkader/some:unknown:uuid",
            )
        ]


def test_educationallevel_copy_with_lookup():
    with enrich_and_lookup() as (enricher, lookup):
        i = example(
            {
                "schema:educationalLevel": {
                    "@id": "http://purl.edustandaard.nl/begrippenkader/my_nl",
                    "@type": "schema:DefinedTerm",
                    "schema:inDefinedTermSet": "http://purl.edustandaard.nl/begrippenkader",
                    "schema:termCode": "my_nl",
                },
            }
        )
        assert [enricher(i[0])] == example(
            {
                "schema:educationalLevel": {
                    "@id": "http://purl.edustandaard.nl/begrippenkader/my_nl",
                    "@type": "schema:DefinedTerm",
                    "schema:inDefinedTermSet": "http://purl.edustandaard.nl/begrippenkader",
                    "schema:name": {"@language": "nl", "@value": "Nederlandse tekst"},
                    "schema:termCode": "my_nl",
                },
            }
        )


def test_educationallevel_copy_multi():
    with enrich_and_lookup(0, 1) as (enricher, lookup):
        i = example(
            {
                "schema:educationalLevel": [
                    {
                        "@id": "http://purl.edustandaard.nl/begrippenkader/2a1401e9-c223-493b-9b86-78f6993b1a8d",
                    },
                    {
                        "@type": "schema:DefinedTerm",
                        "schema:inDefinedTermSet": "http://purl.edustandaard.nl/begrippenkader",
                        "@id": "http://purl.edustandaard.nl/begrippenkader/some:unknown:id",
                        "schema:name": {"@language": "nl", "@value": "Copy"},
                    },
                    {
                        "@type": "schema:DefinedTerm",
                        "schema:inDefinedTermSet": "http://download.edustandaard.nl/vdex/vdex_classification_educationallevel_czp_20060628.xml",
                        "schema:name": {"@language": "nl", "@value": "VWO, studiehuis"},
                        "schema:termCode": "vwo_st",
                    },
                    {
                        "@type": "schema:DefinedTerm",
                        "schema:name": {
                            "@language": "nl",
                            "@value": "Voortgezet Onderwijs",
                        },
                    },
                ],
                "schema:keywords": ["aap", "noot"],
            }
        )
        assert [enricher(i[0])] == example(
            {
                "schema:educationalLevel": [
                    {
                        "@id": "http://purl.edustandaard.nl/begrippenkader/2a1401e9-c223-493b-9b86-78f6993b1a8d",
                        "@type": "schema:DefinedTerm",
                        "schema:inDefinedTermSet": "http://purl.edustandaard.nl/begrippenkader",
                        "schema:name": {"@language": "nl", "@value": "VO"},
                        "schema:termCode": "2a1401e9-c223-493b-9b86-78f6993b1a8d",
                    },
                    {
                        "@type": "schema:DefinedTerm",
                        "@id": "http://purl.edustandaard.nl/begrippenkader/some:unknown:id",
                        "schema:inDefinedTermSet": "http://purl.edustandaard.nl/begrippenkader",
                        "schema:name": {"@language": "nl", "@value": "Copy"},
                    },
                ],
                "schema:keywords": [
                    {"@value": "aap"},
                    {"@value": "noot"},
                    {
                        "@id": "http://download.edustandaard.nl/vdex/vdex_classification_educationallevel_czp_20060628.xml#vwo_st",
                        "@type": "schema:DefinedTerm",
                        "schema:inDefinedTermSet": "http://download.edustandaard.nl/vdex/vdex_classification_educationallevel_czp_20060628.xml",
                        "schema:name": {"@language": "nl", "@value": "VWO, studiehuis"},
                        "schema:termCode": "vwo_st",
                    },
                    {
                        "@type": "schema:DefinedTerm",
                        "schema:name": {
                            "@language": "nl",
                            "@value": "Voortgezet Onderwijs",
                        },
                    },
                ],
            }
        )
        assert lookup.not_found == [
            (
                "schema:educationalLevel",
                "http://purl.edustandaard.nl/begrippenkader/some:unknown:id",
            )
        ]


def test_educationallevel_copy_with_lookup_and_match():
    with enrich_and_lookup() as (enricher, lookup):
        i = example(
            {
                "schema:educationalLevel": {
                    "@id": "uri:has_match",
                    "@type": "schema:DefinedTerm",
                    "schema:inDefinedTermSet": "http://purl.edustandaard.nl/begrippenkader",
                    "schema:termCode": "some code",
                },
            }
        )
        assert [enricher(i[0])] == example(
            {
                "schema:educationalLevel": [
                    {
                        "@id": "uri:has_match",
                        "@type": "schema:DefinedTerm",
                        "schema:inDefinedTermSet": "http://purl.edustandaard.nl/begrippenkader",
                        "schema:name": {
                            "@language": "nl",
                            "@value": "Heeft overeenkomst",
                        },
                        "schema:termCode": "some code",
                    },
                    {
                        "@id": "uri:matches",
                        "@type": "schema:DefinedTerm",
                        "schema:inDefinedTermSet": "http://purl.edustandaard.nl/concept",
                        "schema:name": {"@language": "nl", "@value": "Hetzelfde"},
                    },
                ]
            }
        )


def test_educationallevel_copy_with_lookup_and_match_already_present():
    with enrich_and_lookup() as (enricher, lookup):
        i = example(
            {
                "schema:educationalLevel": [
                    {
                        "@id": "uri:matches",
                        "@type": "schema:DefinedTerm",
                        "schema:inDefinedTermSet": "http://purl.edustandaard.nl/begrippenkader",
                        "schema:termCode": "some code",
                    },
                    {
                        "@id": "uri:has_match",
                        "@type": "schema:DefinedTerm",
                        "schema:inDefinedTermSet": "http://purl.edustandaard.nl/begrippenkader",
                        "schema:termCode": "some code",
                    },
                ],
            }
        )
        assert [enricher(i[0])] == example(
            {
                "schema:educationalLevel": [
                    {
                        "@id": "uri:matches",
                        "@type": "schema:DefinedTerm",
                        "schema:inDefinedTermSet": "http://purl.edustandaard.nl/begrippenkader",
                        "schema:name": {"@language": "nl", "@value": "Hetzelfde"},
                        "schema:termCode": "some code",
                    },
                    {
                        "@id": "uri:has_match",
                        "@type": "schema:DefinedTerm",
                        "schema:inDefinedTermSet": "http://purl.edustandaard.nl/begrippenkader",
                        "schema:name": {
                            "@language": "nl",
                            "@value": "Heeft overeenkomst",
                        },
                        "schema:termCode": "some code",
                    },
                ],
            }
        )


def test_two_matches_in_different_items():
    with enrich_and_lookup() as (enricher, lookup):
        i = example(
            {
                "schema:teaches": [
                    {
                        "@id": "uri:has_match",
                        "@type": "schema:DefinedTerm",
                        "schema:inDefinedTermSet": "http://purl.edustandaard.nl/begrippenkader",
                        "schema:termCode": "some code",
                    }
                ],
                "schema:educationalLevel": [
                    {
                        "@id": "uri:has_match",
                        "@type": "schema:DefinedTerm",
                        "schema:inDefinedTermSet": "http://purl.edustandaard.nl/begrippenkader",
                        "schema:termCode": "some code",
                    }
                ],
            }
        )
        assert [enricher(i[0])] == example(
            {
                "schema:teaches": [
                    {
                        "@id": "uri:has_match",
                        "@type": "schema:DefinedTerm",
                        "schema:inDefinedTermSet": "http://purl.edustandaard.nl/begrippenkader",
                        "schema:name": {
                            "@language": "nl",
                            "@value": "Heeft overeenkomst",
                        },
                        "schema:termCode": "some code",
                    },
                    {
                        "@id": "uri:matches",
                        "@type": "schema:DefinedTerm",
                        "schema:inDefinedTermSet": "http://purl.edustandaard.nl/concept",
                        "schema:name": {"@language": "nl", "@value": "Hetzelfde"},
                    },
                ],
                "schema:educationalLevel": [
                    {
                        "@id": "uri:has_match",
                        "@type": "schema:DefinedTerm",
                        "schema:inDefinedTermSet": "http://purl.edustandaard.nl/begrippenkader",
                        "schema:name": {
                            "@language": "nl",
                            "@value": "Heeft overeenkomst",
                        },
                        "schema:termCode": "some code",
                    },
                    {
                        "@id": "uri:matches",
                        "@type": "schema:DefinedTerm",
                        "schema:inDefinedTermSet": "http://purl.edustandaard.nl/concept",
                        "schema:name": {"@language": "nl", "@value": "Hetzelfde"},
                    },
                ],
            }
        )


def test_definition():
    with enrich_and_lookup() as (enricher, lookup):
        lookup.by_value["test:lookup"] = {
            "value": _l(
                id="urn:id",
                identifier="identifier",
                labels=[("aap", "nl"), ("ape", "en")],
                source="source",
            )
        }

        df = definition(
            target_p="target_p",
            lookup=lookup,
            scheme="test:lookup",
            type="type",
            identifier_p="identifier_p",
        )
        acc = {"has": "value"}
        os = [{"@value": "value"}]
        s = {"value_p": os}
        p = "pred"
        assert df(acc, s, p, os) == {
            "has": "value",
            "target_p": [
                {
                    "identifier_p": [{"@value": "identifier"}],
                    "@id": "urn:id",
                    "@type": ["type"],
                }
            ],
        }


def test_definition_not_found():
    with enrich_and_lookup(1) as (enricher, lookup):

        df = definition(
            target_p="target_p",
            lookup=lookup,
            scheme="test:lookup",
            type="type",
            identifier_p="identifier_p",
        )
        acc = {"has": "value"}
        os = [{"@value": "value"}]
        s = {"value_p": os}
        p = "pred"
        assert df(acc, s, p, os) == {
            "has": "value",
        }
        assert lookup.invalid == [("target_p", "value")]


def test_date_modified():
    with enrich_and_lookup() as (enricher, lookup):
        i = example({})
        r = enricher(i[0], dateModified="2023-01-10T00:11:22Z")
        x = example({"schema:dateModified": "2023-01-10T00:11:22Z"})
        assert [r] == x

        i = example({"schema:dateModified": "2019-01-10T00:11:22Z"})
        r = enricher(i[0], dateModified="2023-01-10T00:11:22Z")
        x = example({"schema:dateModified": "2019-01-10T00:11:22Z"})
        assert [r] == x

        i = example({"schema:dateModified": "2019-01-10T00:11:22+00:00"})
        r = enricher(i[0], dateModified="2023-01-10T00:11:22Z")
        x = example({"schema:dateModified": "2019-01-10T00:11:22Z"})
        assert [r] == x

        i = example({})
        r = enricher(i[0], dateModified="2023-01-10")
        x = example({"schema:dateModified": "2023-01-10T00:00:00Z"})
        assert [r] == x


def test_text():
    with enrich_and_lookup() as (enricher, lookup):
        i = example({"schema:creativeWorkStatus": "definitief"})
        assert [enricher(i[0])] == example({"schema:creativeWorkStatus": "final"})


def test_cost():
    with enrich_and_lookup() as (enricher, lookup):
        i = example({"lom:cost": "ja"})
        assert [enricher(i[0])] == example({"schema:isAccessibleForFree": False})


def test_isAccessibleForFree():
    with enrich_and_lookup() as (enricher, lookup):
        i = example({"schema:isAccessibleForFree": False})
        assert [enricher(i[0])] == example({"schema:isAccessibleForFree": False})

        i = example({"schema:isAccessibleForFree": "false"})
        assert [enricher(i[0])] == example({"schema:isAccessibleForFree": False})


def test_license():
    with enrich_and_lookup(1) as (enricher, lookup):
        i = example(
            {
                "lom:copyrightAndOtherRestrictions": "cc-by-40",
                "schema:copyrightNotice": "Notice, will be removed",
            }
        )
        assert [enricher(i[0])] == example(
            {
                "lom:copyrightAndOtherRestrictions": "cc-by-40",
                "schema:copyrightNotice": {"@language": "nl", "@value": "CC BY 4.0"},
                "schema:license": "http://creativecommons.org/licenses/by/4.0/",
            }
        )

        i = example(
            {
                "lom:copyrightAndOtherRestrictions": "some unresolvable text",
                "schema:copyrightNotice": "Notice stays",
            }
        )
        assert [enricher(i[0])] == example(
            {
                "lom:copyrightAndOtherRestrictions": "some unresolvable text",
                "schema:copyrightNotice": "Notice stays",
            }
        )

        assert lookup.invalid == [("schema:license", "some unresolvable text")]


def test_learningResourceType():
    with enrich_and_lookup() as (enricher, lookup):
        i = example(
            {
                "schema:learningResourceType": [
                    {
                        "@type": "schema:DefinedTerm",
                        "schema:inDefinedTermSet": "http://purl.edustandaard.nl/vdex_learningresourcetype_czp_20060628.xml",
                        "schema:termCode": "open opdracht",
                    },
                    {
                        "@type": "schema:DefinedTerm",
                        "schema:inDefinedTermSet": "http://purl.edustandaard.nl/vdex_learningresourcetype_czp_20060628.xml",
                        "schema:termCode": "open opdracht",
                    },
                    {
                        "@id": "some:id:already",
                        "@type": "schema:DefinedTerm",
                        "schema:inDefinedTermSet": "http://purl.edustandaard.nl/vdex_learningresourcetype_czp_20060628.xml",
                        "schema:termCode": "open opdracht",
                    },
                    {
                        "@type": "schema:DefinedTerm",
                        "schema:inDefinedTermSet": "TPv1.0.2_anders",
                        "schema:termCode": "bron",
                    },
                ]
            }
        )
        assert [enricher(i[0])] == example(
            {
                "schema:learningResourceType": [
                    {
                        "@id": "http://purl.edustandaard.nl/vdex_learningresourcetype_czp_20060628.xml#open%20opdracht",
                        "@type": "schema:DefinedTerm",
                        "schema:inDefinedTermSet": "http://purl.edustandaard.nl/vdex_learningresourcetype_czp_20060628.xml",
                        "schema:termCode": "open opdracht",
                    },
                    {  # double values by id are removed in Edurep by compacting etc.
                        "@id": "http://purl.edustandaard.nl/vdex_learningresourcetype_czp_20060628.xml#open%20opdracht",
                        "@type": "schema:DefinedTerm",
                        "schema:inDefinedTermSet": "http://purl.edustandaard.nl/vdex_learningresourcetype_czp_20060628.xml",
                        "schema:termCode": "open opdracht",
                    },
                    {
                        "@id": "some:id:already",
                        "@type": "schema:DefinedTerm",
                        "schema:inDefinedTermSet": "http://purl.edustandaard.nl/vdex_learningresourcetype_czp_20060628.xml",
                        "schema:termCode": "open opdracht",
                    },
                    {
                        "@type": "schema:DefinedTerm",
                        "schema:inDefinedTermSet": "TPv1.0.2_anders",
                        "schema:termCode": "bron",
                    },
                ]
            }
        )


def test_enrich_info():
    assert prepare_enrich(MockLookup())[1] == {
        "dcterms:accessRights": {
            "lookups": {"urn:lms:accessrights": {"invalid": "dcterms:accessRights"}}
        },
        "lom:aggregationLevel": {
            "lookups": {"urn:lms:aggregationlevel": {"invalid": "lom:aggregationLevel"}}
        },
        "lom:copyrightAndOtherRestrictions": {
            "documentation": anything,
            "lookups": {"urn:lms:license": {"invalid": "schema:license"}},
        },
        "schema:audience": {
            "lookups": {"urn:lms:intendedenduserrole": {"invalid": "schema:audience"}}
        },
        "schema:copyrightNotice": {
            "documentation": anything,
            "lookups": {"urn:lms:license": {"invalid": "schema:license"}},
        },
        "schema:creativeWorkStatus": {
            "lookups": {"urn:lms:status": {"invalid": "schema:creativeWorkStatus"}}
        },
        "schema:educationalAlignment": {
            "documentation": anything,
            "lookups": {
                "urn:edurep:conceptset": {"not_found": "schema:educationalAlignment"}
            },
        },
        "schema:educationalLevel": {
            "documentation": anything,
            "lookups": {
                "urn:edurep:conceptset": {"not_found": "schema:educationalLevel"}
            },
        },
        "schema:encodingFormat": {
            "lookups": {"urn:lms:mimetype": {"invalid": "schema:encodingFormat"}}
        },
        "schema:interactivityType": {
            "lookups": {
                "urn:lms:interactivitytype": {"invalid": "schema:interactivityType"}
            }
        },
        "lom:cost": {
            "documentation": anything,
            "lookups": {"urn:lms:cost": {"invalid": "schema:isAccessibleForFree"}},
        },
        "schema:isAccessibleForFree": {"documentation": anything},
        "schema:license": {
            "documentation": anything,
            "lookups": {"urn:lms:license": {"invalid": "schema:license"}},
        },
        "schema:keywords": {
            "documentation": anything,
            "lookups": {"urn:edurep:conceptset": {}},
        },
        "schema:teaches": {
            "documentation": anything,
            "lookups": {"urn:edurep:conceptset": {"not_found": "schema:teaches"}},
        },
    }


# Testdata is added from examples found in real life data.
# Data is changed so it is not related to a real life example


def test_was_lookuperror_with_educationalAlignment():
    with enrich_and_lookup(1) as (enricher, lookup):
        rec = example(
            {
                "schema:educationalAlignment": [
                    {
                        "@id": "urn:keyword:Niet_gespecificeerd",
                        "@type": ["schema:AlignmentObject", "schema:DefinedTerm"],
                        "schema:educationalFramework": [{"@value": "urn:keyword"}],
                        "schema:inDefinedTermSet": [{"@value": "urn:keyword"}],
                        "schema:name": [{"@value": "Niet gespecificeerd"}],
                        "schema:targetName": [{"@value": "Niet gespecificeerd"}],
                        "schema:termCode": [{"@value": "Niet gespecificeerd"}],
                    }
                ],
                "schema:educationalLevel": [
                    {
                        "@id": "urn:keyword:VO",
                        "@type": ["schema:DefinedTerm"],
                        "schema:inDefinedTermSet": [{"@value": "urn:keyword"}],
                        "schema:name": [{"@value": "VO"}],
                        "schema:termCode": [{"@value": "VO"}],
                    },
                    {
                        "@id": "urn:keyword:MBO",
                        "@type": ["schema:DefinedTerm"],
                        "schema:inDefinedTermSet": [{"@value": "urn:keyword"}],
                        "schema:name": [{"@value": "MBO"}],
                        "schema:termCode": [{"@value": "MBO"}],
                    },
                    {"@id": "urn:keyword:Niet_gespecificeerd"},
                ],
                "@type": [
                    "schema:Product",
                    "schema:LearningResource",
                    "schema:CreativeWork",
                ],
                "schema:audience": [
                    {
                        "@id": "https://purl.edustandaard.nl/vdex_intendedenduserrole_lomv1p0_20060628.xml#learner",
                        "@type": ["schema:Audience"],
                        "schema:audienceType": [{"@value": "learner"}],
                    }
                ],
            }
        )
        r = enricher(rec[0])
