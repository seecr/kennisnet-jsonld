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

from .utils import pretty_print_uuid, normalize_datetime


def test_uuid_pretty_print():
    assert pretty_print_uuid("http://uri/no_uuid") == "http://uri/no_uuid"
    assert (
        pretty_print_uuid("http://uri/B79AA975CFC24FBB90939B4A2E7B05A6")
        == "http://uri/b79aa975-cfc2-4fbb-9093-9b4a2e7b05a6"
    )
    assert (
        pretty_print_uuid("http://uri/b79aa975cfc24fbb90939b4a2e7b05a6")
        == "http://uri/b79aa975-cfc2-4fbb-9093-9b4a2e7b05a6"
    )
    assert (
        pretty_print_uuid("http://uri/b79aa975cfc24fbb90939b4a2e7b05a6?ARST")
        == "http://uri/b79aa975-cfc2-4fbb-9093-9b4a2e7b05a6?ARST"
    )
    for same in [
        "http://purl.edustandaard.nl/begrippenkader//0a715024-bacd-41ed-9ac8-134be6c03f7",
        "/0a715024-bacd-41ed-9ac8-134be6c03f7",
    ]:
        assert pretty_print_uuid(same) == same


def test_normalize_datetime():
    assert normalize_datetime("2023-01-11T12:34:56Z") == "2023-01-11T12:34:56Z"
    assert normalize_datetime("2023-01-11T12:34:56+00:00") == "2023-01-11T12:34:56Z"
    assert normalize_datetime("2023-01-11T13:34:56+01:00") == "2023-01-11T12:34:56Z"
    assert normalize_datetime("2023-01-11") == "2023-01-11T00:00:00Z"
    assert normalize_datetime("last year") == None
    assert normalize_datetime(None) == None
