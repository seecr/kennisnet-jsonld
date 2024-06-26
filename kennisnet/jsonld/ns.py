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

schema = "https://schema.org/"
dcterms = "http://purl.org/dc/terms/"
lom = "http://ltsc.ieee.org/xsd/LOM#"
prov = "http://www.w3.org/ns/prov#"
edurep_terms = "https://purl.edurep.nl/terms/"


def to_curie(full):
    return (
        full.replace(schema, "schema:")
        .replace(dcterms, "dcterms:")
        .replace(lom, "lom:")
    )


__all__ = ["schema", "dcterms", "lom", "prov", "edurep_terms", "to_curie"]
