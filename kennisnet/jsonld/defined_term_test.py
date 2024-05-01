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

from .defined_term import (
    is_curriculum_waarde_in_term,
    add_id_to_defined_term,
    defined_term,
    improve_keywords,
    prep_improve_keyword,
)

from metastreams.jsonld import ignore_silently, walk
from .ns import schema, edurep_terms
from collections import namedtuple
from contextlib import contextmanager

import pytest

_l = namedtuple(
    "LookupResult",
    ["id", "identifier", "source", "labels", "uri", "exactMatch", "type"],
    defaults=[None, None, None, list(), None, None, None],
)


def test_is_curriculum_waarde():
    def term(id, termSet):
        return {"@id": id, schema + "inDefinedTermSet": ({"@value": termSet},)}

    assert is_curriculum_waarde_in_term(
        term("unknown:id", "http://purl.edustandaard.nl/begrippenkader")
    ) == (True, "http://purl.edustandaard.nl/begrippenkader")
    assert is_curriculum_waarde_in_term(term("unknown:id", "my:begrippenkader")) == (
        False,
        None,
    )
    assert is_curriculum_waarde_in_term(
        term(
            "http://purl.edustandaard.nl/begrippenkader/unknown:id", "my:begrippenkader"
        )
    ) == (True, "http://purl.edustandaard.nl/begrippenkader")
    assert is_curriculum_waarde_in_term(
        {"@id": "http://purl.edustandaard.nl/begrippenkader/unknown:id"}
    ) == (True, "http://purl.edustandaard.nl/begrippenkader")
    assert is_curriculum_waarde_in_term(
        {
            schema
            + "inDefinedTermSet": (
                {"@value": "http://purl.edustandaard.nl/begrippenkader"},
            )
        }
    ) == (False, "http://purl.edustandaard.nl/begrippenkader")
    assert is_curriculum_waarde_in_term(
        term("unknown:id", "http://purl.edustandaard.nl/concept")
    ) == (True, "http://purl.edustandaard.nl/concept")
    assert is_curriculum_waarde_in_term(
        term("unknown:id", "https://opendata.slo.nl/curriculum/uuid")
    ) == (True, "https://opendata.slo.nl/curriculum/uuid")
    assert is_curriculum_waarde_in_term(
        {"@id": "http://purl.edustandaard.nl/begrippenkader"}
    ) == (False, None)
    assert is_curriculum_waarde_in_term(
        {"@id": "http://purl.edustandaard.nl/begrippenkader/"}
    ) == (False, None)
    assert is_curriculum_waarde_in_term(
        term(
            "http://purl.edustandaard.nl/vdex_classification_vakaanduidingen_po_2009.xml#natuur",
            "http://purl.edustandaard.nl/vdex_classification_vakaanduidingen_po_2009.xml",
        )
    ) == (False, None)


def test_add_id_to_defined_term():
    assert (
        add_id_to_defined_term(
            {
                schema + "inDefinedTermSet": [{"@value": "uri:like"}],
                schema + "termCode": [{"@value": "termCode"}],
            }
        )["@id"]
        == "uri:like#termCode"
    )
    assert (
        add_id_to_defined_term(
            {
                schema
                + "inDefinedTermSet": [{"@value": "uri:like:with:space:at:end "}],
                schema + "termCode": [{"@value": "termCode"}],
            }
        )["@id"]
        == "uri:like:with:space:at:end#termCode"
    )
    assert (
        add_id_to_defined_term(
            {
                schema + "inDefinedTermSet": [{"@value": "uri:like"}],
                schema + "termCode": [{"@value": "uri:like"}],
            }
        ).get("@id")
        is None
    )

    def test_identity(inp):
        assert add_id_to_defined_term(inp) == inp

    test_identity(
        {
            schema + "inDefinedTermSet": [{"@value": "uri:like"}],
            schema + "termCode": [{"@value": "uri:like"}],
        }
    )
    test_identity(
        {
            schema + "inDefinedTermSet": [{"@value": "uri:like"}],
        }
    )
    test_identity(
        {
            schema + "termCode": [{"@value": "termCode"}],
        }
    )


class LookupObject:
    def __init__(self):
        self.by_id = {}
        self.by_value = {}
        self.not_found = []

    def report_not_found(self, key, value):
        self.not_found.append((key, value))

    def lookupById(self, scheme, value):
        assert scheme == "urn:edurep:conceptset"
        return self.by_id.get(value, _l())

    def lookupByValue(self, scheme, value):
        assert scheme == "urn:edurep:conceptset"
        return self.by_value.get(value, _l())


class TestTeaches:
    @contextmanager
    def convert(self, nr_not_found=0):
        lookup = LookupObject()
        lookup.by_id["urn:uuid:education"] = _l(
            id="urn:uuid:education",
            labels=[("Onderwijs", "nl")],
            identifier="education",
        )
        rules = {
            schema + "keywords": ignore_silently,
            schema + "teaches": defined_term(schema + "teaches", lookup),
        }
        w = walk(rules)
        yield w, lookup
        assert len(lookup.not_found) == nr_not_found

    def test_move_data_to_keywords(self):
        with self.convert(0) as (w, lookup):
            start = {
                schema
                + "teaches": (
                    {
                        "@type": [schema + "DefinedTerm"],
                        schema + "inDefinedTermSet": [{"@value": "not:conceptset"}],
                        schema + "termCode": [{"@value": "onderwijs"}],
                    },
                ),
            }

            assert w(start) == {
                schema
                + "keywords": [
                    {
                        "@id": "not:conceptset#onderwijs",
                        "@type": [schema + "DefinedTerm"],
                        schema + "inDefinedTermSet": [{"@value": "not:conceptset"}],
                        schema + "termCode": [{"@value": "onderwijs"}],
                    }
                ]
            }

    def test_keep_unknown_data(self):
        with self.convert(1) as (w, lookup):
            start = {
                schema
                + "teaches": [
                    {
                        "@type": [schema + "DefinedTerm"],
                        "@id": "urn:uuid:onderwijs",
                        schema
                        + "inDefinedTermSet": [
                            {"@value": "http://purl.edustandaard.nl/begrippenkader"}
                        ],
                        schema + "termCode": [{"@value": "urn:uuid:onderwijs"}],
                    }
                ],
            }
            assert w(start) == {
                schema
                + "teaches": [
                    {
                        "@type": [schema + "DefinedTerm"],
                        "@id": "urn:uuid:onderwijs",
                        schema
                        + "inDefinedTermSet": [
                            {"@value": "http://purl.edustandaard.nl/begrippenkader"}
                        ],
                        schema + "termCode": [{"@value": "urn:uuid:onderwijs"}],
                    }
                ],
            }
            assert lookup.not_found == [("schema:teaches", "urn:uuid:onderwijs")]

    def test_keep_known_data(self):
        with self.convert(0) as (w, lookup):
            start = {
                schema
                + "teaches": [
                    {
                        "@type": [schema + "DefinedTerm"],
                        "@id": "urn:uuid:education",
                        schema
                        + "inDefinedTermSet": [
                            {"@value": "http://purl.edustandaard.nl/begrippenkader"}
                        ],
                        schema + "termCode": [{"@value": "urn:uuid:onderwijs"}],
                    }
                ],
            }
            assert w(start) == {
                schema
                + "teaches": [
                    {
                        "@type": [schema + "DefinedTerm"],
                        "@id": "urn:uuid:education",
                        schema
                        + "inDefinedTermSet": [
                            {"@value": "http://purl.edustandaard.nl/begrippenkader"}
                        ],
                        schema + "termCode": [{"@value": "education"}],
                        schema + "name": [{"@value": "Onderwijs", "@language": "nl"}],
                    }
                ]
            }


class TestEducationalAlignment:
    @contextmanager
    def convert(self, nr_not_found=0):
        lookup = LookupObject()
        lookup.by_id.update(
            {
                "http://purl.edustandaard.nl/begrippenkader/12345678-1234-5678-9012-123456123456": _l(
                    id="http://purl.edustandaard.nl/begrippenkader/12345678-1234-5678-9012-123456123456",
                    identifier="teksten",
                    source="http://purl.edustandaard.nl/begrippenkader",
                    labels=[("Lezen van zakelijke teksten", "nl")],
                    exactMatch="https://opendata.slo.nl/curriculum/uuid/11223344-5566-7788-9900-123456123456",
                    type=edurep_terms + "Discipline",
                ),
            }
        )
        lookup.by_value.update(
            {
                "natuur": _l(
                    id="http://purl.edustandaard.nl/begrippenkader/f97e788f-5aa6-4ab4-9448-9e27b79daa9e",
                    source="http://purl.edustandaard.nl/begrippenkader",
                    labels=[("Natuur", "nl")],
                ),
            }
        )

        rules = {
            schema
            + "educationalAlignment": defined_term(
                schema + "educationalAlignment", lookup
            ),
        }
        w = walk(rules)
        yield w, lookup
        assert len(lookup.not_found) == nr_not_found

    def test_move_data_to_keywords(self):
        with self.convert(0) as (w, lookup):
            start = {
                schema
                + "educationalAlignment": [
                    {
                        "@type": [schema + "AlignmentObject"],
                        schema + "educationalFramework": [{"@value": "not:conceptset"}],
                        schema + "targetName": [{"@value": "urn:uuid:onderwijs"}],
                        schema + "name": [{"@value": "Ondewijs"}],
                        schema + "alignmentType": [{"@value": "discipline"}],
                    }
                ]
            }

            assert w(start) == {
                schema
                + "keywords": [
                    {
                        "@type": [schema + "DefinedTerm"],
                        schema + "inDefinedTermSet": [{"@value": "not:conceptset"}],
                        schema + "termCode": [{"@value": "urn:uuid:onderwijs"}],
                        schema + "name": [{"@value": "Ondewijs"}],
                    }
                ]
            }

    @pytest.mark.skip(
        reason="Duidt een mogelijk probleem aan.  Keywords die geent type krijgen worden niet verbeterd."
    )
    def test_move_data_to_keywords_natuur(self):
        with self.convert(0) as (w, lookup):
            start = {
                schema
                + "educationalAlignment": [
                    {
                        "@id": "http://purl.edustandaard.nl/vdex_classification_vakaanduidingen_po_2009.xml#natuur",
                        "@type": [schema + "AlignmentObject"],
                        schema
                        + "educationalFramework": [
                            {
                                "@value": "http://purl.edustandaard.nl/vdex_classification_vakaanduidingen_po_2009.xml"
                            }
                        ],
                        schema + "targetName": [{"@value": "natuur"}],
                        schema + "name": [{"@value": "natuur"}],
                    }
                ]
            }

            assert w(start) == {
                schema
                + "keywords": [
                    {
                        "@id": "http://purl.edustandaard.nl/begrippenkader/f97e788f-5aa6-4ab4-9448-9e27b79daa9e",
                        "@type": [schema + "DefinedTerm"],
                        schema
                        + "inDefinedTermSet": [
                            {"@value": "http://purl.edustandaard.nl/begrippenkader"}
                        ],
                        schema + "name": [{"@value": "Natuur", "@language": "nl"}],
                    }
                ]
            }

    def test_keep_data(self):
        with self.convert(1) as (w, lookup):
            start = {
                schema
                + "educationalAlignment": [
                    {
                        "@type": [
                            schema + "AlignmentObject",
                        ],
                        schema
                        + "educationalFramework": [
                            {"@value": "https://opendata.slo.nl/curriculum/uuid"},
                        ],
                        "@id": "urn:uuid:onderwijs",
                        schema
                        + "targetName": [
                            {"@value": "urn:uuid:onderwijs"},
                        ],
                        schema
                        + "name": [
                            {"@value": "Ondewijs"},
                        ],
                    },
                ]
            }
            assert w(start) == {
                schema
                + "educationalAlignment": [
                    {
                        "@type": [
                            schema + "AlignmentObject",
                        ],
                        schema
                        + "educationalFramework": [
                            {"@value": "https://opendata.slo.nl/curriculum/uuid"},
                        ],
                        "@id": "urn:uuid:onderwijs",
                        schema
                        + "targetName": [
                            {"@value": "urn:uuid:onderwijs"},
                        ],
                        schema
                        + "name": [
                            {"@value": "Ondewijs"},
                        ],
                    },
                ]
            }
            assert lookup.not_found == [
                ("schema:educationalAlignment", "urn:uuid:onderwijs")
            ]

    def test_keep_some(self):
        with self.convert(1) as (w, lookup):
            start = {
                schema
                + "educationalAlignment": [
                    {
                        "@type": [
                            schema + "AlignmentObject",
                        ],
                        schema
                        + "educationalFramework": [
                            {"@value": "https://opendata.slo.nl/curriculum/uuid"},
                        ],
                        "@id": "urn:uuid:onderwijs",
                        schema
                        + "targetName": [
                            {"@value": "urn:uuid:onderwijs"},
                        ],
                    },
                    {
                        "@type": [
                            schema + "AlignmentObject",
                        ],
                        schema
                        + "educationalFramework": [
                            {"@value": "unknown:framework"},
                        ],
                        "@id": "urn:uuid:onderwijs",
                        schema
                        + "targetName": [
                            {"@value": "urn:uuid:onderwijs"},
                        ],
                    },
                ]
            }
            assert w(start) == {
                schema
                + "educationalAlignment": [
                    {
                        "@type": [
                            schema + "AlignmentObject",
                        ],
                        schema
                        + "educationalFramework": [
                            {"@value": "https://opendata.slo.nl/curriculum/uuid"},
                        ],
                        "@id": "urn:uuid:onderwijs",
                        schema
                        + "targetName": [
                            {"@value": "urn:uuid:onderwijs"},
                        ],
                    },
                ],
                schema
                + "keywords": [
                    {
                        "@type": [
                            schema + "DefinedTerm",
                        ],
                        schema
                        + "inDefinedTermSet": [
                            {"@value": "unknown:framework"},
                        ],
                        "@id": "urn:uuid:onderwijs",
                        schema
                        + "termCode": [
                            {"@value": "urn:uuid:onderwijs"},
                        ],
                    },
                ],
            }
            assert lookup.not_found == [
                ("schema:educationalAlignment", "urn:uuid:onderwijs")
            ]

    def test_flow2_2_lookup_by_id(self):
        with self.convert(0) as (w, lookup):
            start = {
                schema
                + "educationalAlignment": [
                    {
                        "@type": [
                            schema + "AlignmentObject",
                        ],
                        "@id": "http://purl.edustandaard.nl/begrippenkader/12345678-1234-5678-9012-123456123456",
                        schema
                        + "targetName": [
                            {"@value": "urn:uuid:onderwijs"},
                        ],
                        schema
                        + "name": [
                            {"@value": "Ondewijs"},
                        ],
                    },
                ]
            }
            result = w(start)
            assert result.pop("exactMatch") == [
                (
                    schema + "educationalAlignment",
                    "https://opendata.slo.nl/curriculum/uuid/11223344-5566-7788-9900-123456123456",
                )
            ]
            assert result == {
                schema
                + "educationalAlignment": [
                    {
                        "@type": [
                            schema + "AlignmentObject",
                        ],
                        schema
                        + "educationalFramework": [
                            {"@value": "http://purl.edustandaard.nl/begrippenkader"},
                        ],
                        "@id": "http://purl.edustandaard.nl/begrippenkader/12345678-1234-5678-9012-123456123456",
                        schema
                        + "targetName": [
                            {"@value": "teksten"},
                        ],
                        schema
                        + "name": [
                            {
                                "@language": "nl",
                                "@value": "Lezen van zakelijke teksten",
                            },
                        ],
                    }
                ]
            }

    def test_flow2_2_lookup_by_only_id(self):
        with self.convert(0) as (w, lookup):
            start = {
                schema
                + "educationalAlignment": [
                    {
                        "@id": "http://purl.edustandaard.nl/begrippenkader/12345678-1234-5678-9012-123456123456",
                    }
                ]
            }
            result = w(start)
            assert result.pop("exactMatch") == [
                (
                    schema + "educationalAlignment",
                    "https://opendata.slo.nl/curriculum/uuid/11223344-5566-7788-9900-123456123456",
                )
            ]
            assert result == {
                schema
                + "educationalAlignment": [
                    {
                        "@type": [
                            schema + "AlignmentObject",
                        ],
                        schema
                        + "educationalFramework": [
                            {"@value": "http://purl.edustandaard.nl/begrippenkader"},
                        ],
                        "@id": "http://purl.edustandaard.nl/begrippenkader/12345678-1234-5678-9012-123456123456",
                        schema
                        + "targetName": [
                            {"@value": "teksten"},
                        ],
                        schema
                        + "name": [
                            {"@language": "nl", "@value": "Lezen van zakelijke teksten"}
                        ],
                    }
                ]
            }

    def test_wrong_keys_in_educationalAlignment(self):
        with self.convert(0) as (w, lookup):
            start = {
                schema
                + "educationalAlignment": [
                    {
                        "@id": "urn:keyword:Niet_gespecificeerd",
                        "@type": [schema + "AlignmentObject", schema + "DefinedTerm"],
                        schema + "educationalFramework": [{"@value": "urn:keyword"}],
                        schema + "inDefinedTermSet": [{"@value": "urn:keyword"}],
                        schema + "name": [{"@value": "Niet gespecificeerd"}],
                        schema + "targetName": [{"@value": "Niet gespecificeerd"}],
                        schema + "termCode": [{"@value": "Niet gespecificeerd"}],
                    }
                ]
            }
            assert w(start) == {
                schema
                + "keywords": [
                    {
                        "@id": "urn:keyword:Niet_gespecificeerd",
                        "@type": [schema + "DefinedTerm"],
                        schema + "inDefinedTermSet": [{"@value": "urn:keyword"}],
                        schema + "name": [{"@value": "Niet gespecificeerd"}],
                        schema + "termCode": [{"@value": "Niet gespecificeerd"}],
                    }
                ]
            }


class TestKeywords_flow:

    @contextmanager
    def convert(self, nr_not_found=0):
        _lookup = LookupObject()
        _lookup.by_value.update(
            {
                "urn:uuid:onderwijs": _l(
                    id="http://purl.edustandaard.nl/begrippenkader/12345678-0000-1111-2222-123456123456",
                    identifier="onderwijs",
                    source="http://purl.edustandaard.nl/begrippenkader",
                    labels=[("Onderwijs", "nl")],
                    type=edurep_terms + "Discipline",
                ),
                "Handig rekenen": _l(
                    id="http://purl.edustandaard.nl/begrippenkader/12345678-1111-2222-3333-123456123456",
                    identifier="rekenen",
                    source="http://purl.edustandaard.nl/begrippenkader",
                    labels=[("Handig rekenen", "nl")],
                    type=edurep_terms + "EducationalObjective",
                ),
                "urn:uuid:rekenen": _l(
                    id="http://purl.edustandaard.nl/begrippenkader/12345678-1111-2222-3333-123456123456",
                    identifier="rekenen",
                    source="http://purl.edustandaard.nl/begrippenkader",
                    labels=[("Handig rekenen", "nl")],
                    type=edurep_terms + "EducationalObjective",
                ),
                "urn:uuid:master": _l(
                    id="http://purl.edustandaard.nl/begrippenkader/12345678-2222-3333-4444-123456123456",
                    identifier="master",
                    source="http://purl.edustandaard.nl/begrippenkader",
                    labels=[("WO - Master", "nl"), ("WO Master", "nl")],
                    type=edurep_terms + "EducationalLevel",
                ),
                "zo maar": _l(),
            }
        )
        _lookup.by_id.update(
            {
                "http://purl.edustandaard.nl/begrippenkader/87654321-0000-1111-2222-123456123456": _l(
                    id="http://purl.edustandaard.nl/begrippenkader/87654321-0000-1111-2222-123456123456",
                    identifier="aanvulling",
                    source="http://purl.edustandaard.nl/begrippenkader",
                    labels=[("De aanvulling", "nl")],
                    type=edurep_terms + "Discipline",
                ),
            }
        )

        rules = {
            schema + "keywords": improve_keywords(_lookup),
            schema + "teaches": defined_term(schema + "teaches", _lookup),
            schema
            + "educationalLevel": defined_term(schema + "educationalLevel", _lookup),
            schema
            + "educationalAlignment": defined_term(
                schema + "educationalAlignment", _lookup
            ),
        }
        _w = walk(rules)
        _lookup.not_found.clear()
        yield _w, _lookup
        assert len(_lookup.not_found) == nr_not_found

    def test_keywords_to_teaches(self):
        with self.convert(0) as (w, lookup):
            improve_keyword = prep_improve_keyword(lookup)
            keyword = {
                "@type": [
                    schema + "DefinedTerm",
                ],
                schema
                + "termCode": [
                    {"@value": "urn:uuid:rekenen"},
                ],
                schema
                + "name": [
                    {"@value": "Hello, my name is..."},
                ],
            }

            target, result, matches_id = improve_keyword(keyword)

            assert result == {
                "@type": [
                    schema + "DefinedTerm",
                ],
                "@id": "http://purl.edustandaard.nl/begrippenkader/12345678-1111-2222-3333-123456123456",
                schema
                + "inDefinedTermSet": [
                    {"@value": "http://purl.edustandaard.nl/begrippenkader"},
                ],
                schema
                + "termCode": [
                    {"@value": "rekenen"},
                ],
                schema
                + "name": [
                    {"@language": "nl", "@value": "Handig rekenen"},
                ],
            }
            assert target == schema + "teaches"

    def test_keywords_to_teaches_on_name(self):
        with self.convert(0) as (w, lookup):
            improve_keyword = prep_improve_keyword(lookup)
            keyword = {
                "@type": [
                    schema + "DefinedTerm",
                ],
                schema
                + "name": [
                    {"@language": "nl", "@value": "Handig rekenen"},
                ],
            }

            target, result, matches_id = improve_keyword(keyword)

            assert result == {
                "@type": [
                    schema + "DefinedTerm",
                ],
                "@id": "http://purl.edustandaard.nl/begrippenkader/12345678-1111-2222-3333-123456123456",
                schema
                + "inDefinedTermSet": [
                    {"@value": "http://purl.edustandaard.nl/begrippenkader"},
                ],
                schema
                + "termCode": [
                    {"@value": "rekenen"},
                ],
                schema
                + "name": [
                    {"@language": "nl", "@value": "Handig rekenen"},
                ],
            }
            assert target == schema + "teaches"

    def test_keywords_to_educational_level(self):
        with self.convert(0) as (w, lookup):
            improve_keyword = prep_improve_keyword(lookup)
            keyword = {
                "@type": [
                    schema + "DefinedTerm",
                ],
                schema
                + "termCode": [
                    {"@value": "urn:uuid:master"},
                ],
                schema
                + "name": [
                    {"@value": "Hello, my name is..."},
                ],
            }

            target, result, matches_id = improve_keyword(keyword)

            assert result == {
                "@type": [
                    schema + "DefinedTerm",
                ],
                "@id": "http://purl.edustandaard.nl/begrippenkader/12345678-2222-3333-4444-123456123456",
                schema
                + "inDefinedTermSet": [
                    {"@value": "http://purl.edustandaard.nl/begrippenkader"},
                ],
                schema
                + "termCode": [
                    {"@value": "master"},
                ],
                schema
                + "name": [
                    {"@language": "nl", "@value": "WO - Master"},
                    {"@language": "nl", "@value": "WO Master"},
                ],
            }
            assert target == schema + "educationalLevel"

    def test_keywords_to_educational_alignment(self):
        with self.convert(0) as (w, lookup):
            improve_keyword = prep_improve_keyword(lookup)
            keyword = {
                "@type": [
                    schema + "DefinedTerm",
                ],
                schema
                + "termCode": [
                    {"@value": "urn:uuid:onderwijs"},
                ],
                schema
                + "name": [
                    {"@value": "Hello, my name is..."},
                ],
            }

            target, result, matches_id = improve_keyword(keyword)

            assert target == schema + "educationalAlignment"
            assert result == {
                "@type": [
                    schema + "AlignmentObject",
                ],
                "@id": "http://purl.edustandaard.nl/begrippenkader/12345678-0000-1111-2222-123456123456",
                schema
                + "educationalFramework": [
                    {"@value": "http://purl.edustandaard.nl/begrippenkader"},
                ],
                schema
                + "targetName": [
                    {"@value": "onderwijs"},
                ],
                schema
                + "name": [
                    {"@language": "nl", "@value": "Onderwijs"},
                ],
            }

    def test_integrate_flow_1_and_flow_2(self):
        with self.convert(0) as (w, lookup):
            start = {
                schema
                + "teaches": [
                    {
                        "@type": [
                            schema + "DefinedTerm",
                        ],
                        schema
                        + "termCode": [
                            {"@value": "urn:uuid:rekenen"},
                        ],
                        schema
                        + "name": [
                            {"@value": "Hello, my name is..."},
                        ],
                    },
                    {
                        "@type": [
                            schema + "DefinedTerm",
                        ],
                        schema
                        + "termCode": [
                            {"@value": "urn:uuid:onderwijs"},
                        ],
                        schema
                        + "name": [
                            {"@value": "Eigenlijk schema:educationalAlignment"},
                        ],
                    },
                    {
                        "@type": [
                            schema + "DefinedTerm",
                        ],
                        schema
                        + "termCode": [
                            {"@value": "zo maar"},
                        ],
                        schema
                        + "name": [
                            {"@value": "Gewoon keyword"},
                        ],
                    },
                ],
                schema
                + "keywords": [
                    {
                        "@type": [
                            schema + "DefinedTerm",
                        ],
                        schema
                        + "termCode": [
                            {"@value": "urn:uuid:master"},
                        ],
                        schema
                        + "name": [
                            {"@value": "Eigenlijk schema:educationalLevel"},
                        ],
                    },
                    {"@value": "integratietest"},
                ],
                schema
                + "educationalAlignment": [
                    {
                        "@type": [
                            schema + "AlignmentObject",
                        ],
                        "@id": "http://purl.edustandaard.nl/begrippenkader/87654321-0000-1111-2222-123456123456",
                        schema
                        + "targetName": [
                            {"@value": "weet niet"},
                        ],
                        schema
                        + "name": [
                            {"@value": "een schema:educationalAlignment"},
                        ],
                    },
                ],
            }

            assert w(start) == {
                schema
                + "teaches": [
                    {
                        "@type": [
                            schema + "DefinedTerm",
                        ],
                        "@id": "http://purl.edustandaard.nl/begrippenkader/12345678-1111-2222-3333-123456123456",
                        schema
                        + "inDefinedTermSet": [
                            {"@value": "http://purl.edustandaard.nl/begrippenkader"},
                        ],
                        schema
                        + "termCode": [
                            {"@value": "rekenen"},
                        ],
                        schema
                        + "name": [
                            {"@language": "nl", "@value": "Handig rekenen"},
                        ],
                    },
                ],
                schema
                + "educationalAlignment": [
                    {
                        "@type": [
                            schema + "AlignmentObject",
                        ],
                        "@id": "http://purl.edustandaard.nl/begrippenkader/12345678-0000-1111-2222-123456123456",
                        schema
                        + "educationalFramework": [
                            {"@value": "http://purl.edustandaard.nl/begrippenkader"},
                        ],
                        schema
                        + "targetName": [
                            {"@value": "onderwijs"},
                        ],
                        schema
                        + "name": [
                            {"@language": "nl", "@value": "Onderwijs"},
                        ],
                    },
                    {
                        "@type": [
                            schema + "AlignmentObject",
                        ],
                        "@id": "http://purl.edustandaard.nl/begrippenkader/87654321-0000-1111-2222-123456123456",
                        schema
                        + "educationalFramework": [
                            {"@value": "http://purl.edustandaard.nl/begrippenkader"},
                        ],
                        schema
                        + "targetName": [
                            {"@value": "aanvulling"},
                        ],
                        schema
                        + "name": [
                            {"@language": "nl", "@value": "De aanvulling"},
                        ],
                    },
                ],
                schema
                + "educationalLevel": [
                    {
                        "@type": [
                            schema + "DefinedTerm",
                        ],
                        "@id": "http://purl.edustandaard.nl/begrippenkader/12345678-2222-3333-4444-123456123456",
                        schema
                        + "inDefinedTermSet": [
                            {"@value": "http://purl.edustandaard.nl/begrippenkader"},
                        ],
                        schema
                        + "termCode": [
                            {"@value": "master"},
                        ],
                        schema
                        + "name": [
                            {"@language": "nl", "@value": "WO - Master"},
                            {"@language": "nl", "@value": "WO Master"},
                        ],
                    },
                ],
                schema
                + "keywords": [
                    {
                        "@value": "integratietest",
                    },
                    {
                        "@type": [
                            schema + "DefinedTerm",
                        ],
                        schema
                        + "termCode": [
                            {"@value": "zo maar"},
                        ],
                        schema
                        + "name": [
                            {"@value": "Gewoon keyword"},
                        ],
                    },
                ],
            }

    # @test
    def wrong_keys_in_educationalLevel(convert):
        w, lookup = convert
        start = {
            schema
            + "educationalLevel": [
                {
                    "@id": "urn:keyword:Niet_gespecificeerd",
                    "@type": [schema + "AlignmentObject", schema + "DefinedTerm"],
                    schema + "educationalFramework": [{"@value": "urn:keyword"}],
                    schema + "inDefinedTermSet": [{"@value": "urn:keyword"}],
                    schema + "name": [{"@value": "Niet gespecificeerd"}],
                    schema + "targetName": [{"@value": "Niet gespecificeerd"}],
                    schema + "termCode": [{"@value": "Niet gespecificeerd"}],
                }
            ]
        }
        result = w(start)
        test.eq(
            {
                schema
                + "keywords": [
                    {
                        "@id": "urn:keyword:Niet_gespecificeerd",
                        "@type": [schema + "DefinedTerm"],
                        schema + "inDefinedTermSet": [{"@value": "urn:keyword"}],
                        schema + "name": [{"@value": "Niet gespecificeerd"}],
                        schema + "termCode": [{"@value": "Niet gespecificeerd"}],
                    }
                ]
            },
            result,
            diff=test.diff2,
        )

    # @test
    def missing_type(convert):
        w, lookup = convert
        start = {
            schema
            + "educationalLevel": [
                {
                    "@id": "urn:keyword:Niet_gespecificeerd",
                }
            ]
        }
        result = w(start)
        test.eq(
            {
                schema
                + "keywords": [
                    {
                        "@id": "urn:keyword:Niet_gespecificeerd",
                    }
                ]
            },
            result,
            diff=test.diff2,
        )
