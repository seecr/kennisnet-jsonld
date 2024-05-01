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

from .defined_term import is_curriculum_waarde_in_term


from .ns import schema, edurep_terms
from collections import namedtuple

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
