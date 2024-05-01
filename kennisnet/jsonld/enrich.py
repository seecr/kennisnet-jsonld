## begin license ##
#
# "Kennisnet Json-LD" provides tools for handling tools
#
# Copyright (C) 2022-2024 Seecr (Seek You Too B.V.) https://seecr.nl
# Copyright (C) 2022-2024 Stichting Kennisnet https://www.kennisnet.nl
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

from metastreams.jsonld import (
    walk,
    identity,
    ignore_silently,
    tuple2list,
    map_predicate2,
)
from .defined_term import (
    defined_term,
    improve_keywords,
    result_to_defined_term,
    add_id_to_defined_term,
)
from .ns import schema, lom, dcterms, edurep_terms, to_curie
import kennisnet.jsonld.utils as utils


def getp_first_value(d, p):
    for i in d.get(p, []):
        return i.get("@value")
    return None


def first(l):
    try:
        return next(iter(l))
    except StopIteration:
        return None


def values(os):
    for o in os:
        yield o["@value"]


def definition(target_p, lookup, scheme, type, identifier_p):
    def value_fn(o):
        return getp_first_value(o, identifier_p) or o.get("@value")

    def build_fn(l):
        new_o = {}
        if l.identifier:
            new_o[identifier_p] = [{"@value": l.identifier}]
        if not l.id is None:
            new_o["@id"] = l.id
        if new_o:
            new_o["@type"] = [type]
            return new_o

    def check_fn(a, s, p, os):
        result = a.get(target_p, [])
        for o in os:
            target = target_p
            value = value_fn(o)
            id = o.get("@id")
            if not (value or id):
                continue
            if value:
                l = lookup.lookupByValue(scheme, value)
            else:
                l = lookup.lookupById(id)
            if l.identifier is None and l.id is None:
                lookup.report_invalid(to_curie(target_p), value or id)
                continue

            new = build_fn(l)
            if new:
                result.append(new)

        addition = {}
        if result:
            addition[target_p] = result
        return a | addition

    check_fn.lookup_info = {scheme: {"invalid": to_curie(target_p)}}
    return check_fn


def text(target_p, lookup, scheme):
    def text_fn(a, s, p, os):
        result = a.get(target_p, [])
        for v in values(os):
            l = lookup.lookupByValue(scheme, v)
            if l.identifier:
                result.append({"@value": l.identifier})
            else:
                lookup.report_invalid(to_curie(target_p), v)
        return a | {target_p: result}

    text_fn.lookup_info = {scheme: {"invalid": to_curie(target_p)}}
    return text_fn


def cost(target_p, lookup, scheme):
    def text_fn(a, s, p, os):
        """Dit is een tijdelijk veld om waarde over te nemen uit het lom/cost veld. Waardes worden omgezet naar True of False voor schema:isAccessibleForFree"""
        for v in values(os):
            l = lookup.lookupByValue(scheme, v)
            if l.identifier:
                return a | {target_p: [{"@value": l.identifier != "yes"}]}
            else:
                lookup.report_invalid(to_curie(target_p), v)
        return a

    text_fn.lookup_info = {scheme: {"invalid": to_curie(target_p)}}
    return text_fn


def license(target_p, lookup, scheme):

    def license_fn(a, s, p, os):
        """Op basis van lom:copyrightAndOtherRestrictions wordt een lookup gedaan.
        Bij succesvolle lookup worden de velden lom:copyrightAndOtherRestrictions, schema:license en schema:copyrightNotice gevuld.
        In andere gevallen wordt de huidige data overgenomen"""
        r_other = a.get(lom + "copyrightAndOtherRestrictions", [])
        r_notice = a.get(schema + "copyrightNotice", [])
        r_license = a.get(schema + "license", [])
        if r_other or r_license or r_notice:
            # Already a result
            return a
        for v in values(s.get(lom + "copyrightAndOtherRestrictions", [])):
            l = lookup.lookupByValue(scheme, v)
            if not l.uri:
                l = lookup.lookupById(scheme, v)
            if l.uri:
                r_license.append({"@value": l.uri})
                r_other.append({"@value": v})
                for v, lang in l.labels:
                    r_notice.append(utils.as_value(v, lang))
            else:
                lookup.report_invalid(to_curie(schema + "license"), v)
        if not r_license:  # nothing new, keep old stuff
            r_other = s.get(lom + "copyrightAndOtherRestrictions", [])
            r_notice = s.get(schema + "copyrightNotice", [])
            r_license = s.get(schema + "license", [])

        new = {
            k: v
            for k, v in [
                (lom + "copyrightAndOtherRestrictions", r_other),
                (schema + "copyrightNotice", r_notice),
                (schema + "license", r_license),
            ]
            if v
        }
        return a | new

    license_fn.lookup_info = {scheme: {"invalid": to_curie(schema + "license")}}
    return license_fn


def is_boolean(a, s, p, os):
    """Valideer dat waardes True of False zijn, waarden als 'yes','no','ja' en 'nee' worden vertaald."""
    result = a.get(p, [])
    for v in values(os):
        if type(v) is bool:
            result.append({"@value": v})
            continue
        b = {
            "true": True,
            "yes": True,
            "ja": True,
            "false": False,
            "no": False,
            "nee": False,
        }.get(str(v).lower())
        if not b is None:
            result.append({"@value": b})
    if result:
        return a | {p: result}
    return a


def normalize_date(os):
    r = (o | {"@value": utils.normalize_datetime(o["@value"])} for o in os)
    return tuple(o for o in r if not o["@value"] is None)


def prepare_enrich(lookupObject=None):
    info = {}

    license_fn = license(schema + "license", lookupObject, scheme="urn:lms:license")

    rules = {
        schema + "keywords": improve_keywords(lookupObject),
        schema
        + "creativeWorkStatus": text(
            schema + "creativeWorkStatus", lookup=lookupObject, scheme="urn:lms:status"
        ),
        schema
        + "interactivityType": text(
            schema + "interactivityType",
            lookup=lookupObject,
            scheme="urn:lms:interactivitytype",
        ),
        schema
        + "encodingFormat": text(
            schema + "encodingFormat", lookup=lookupObject, scheme="urn:lms:mimetype"
        ),
        dcterms
        + "accessRights": text(
            dcterms + "accessRights", lookup=lookupObject, scheme="urn:lms:accessrights"
        ),
        lom
        + "aggregationLevel": text(
            lom + "aggregationLevel",
            lookup=lookupObject,
            scheme="urn:lms:aggregationlevel",
        ),
        lom
        + "cost": cost(
            schema + "isAccessibleForFree", lookup=lookupObject, scheme="urn:lms:cost"
        ),
        schema + "isAccessibleForFree": is_boolean,
        schema
        + "audience": definition(
            type=schema + "Audience",
            identifier_p=schema + "audienceType",
            target_p=schema + "audience",
            lookup=lookupObject,
            scheme="urn:lms:intendedenduserrole",
        ),
        schema
        + "educationalAlignment": defined_term(
            schema + "educationalAlignment", lookupObject
        ),
        schema
        + "educationalLevel": defined_term(schema + "educationalLevel", lookupObject),
        schema + "teaches": defined_term(schema + "teaches", lookupObject),
        schema
        + "learningResourceType": map_predicate2(
            schema + "learningResourceType",
            lambda os: tuple(add_id_to_defined_term(o) for o in os),
        ),
        schema + "license": license_fn,
        schema + "copyrightNotice": license_fn,
        lom + "copyrightAndOtherRestrictions": license_fn,
        schema
        + "dateModified": map_predicate2(schema + "dateModified", normalize_date),
        "*": identity,
    }
    for k, v in rules.items():
        doc = None
        lookup_info = None
        if callable(v):
            doc = v.__doc__
            lookup_info = getattr(v, "lookup_info", None)
        elif isinstance(v, dict):
            doc = v.get("documentation")
        if not doc is None:
            info.setdefault(to_curie(k), {})["documentation"] = doc
        if not lookup_info is None:
            info.setdefault(to_curie(k), {}).setdefault("lookups", {}).update(
                lookup_info
            )

    w = walk(rules)

    def enrich(data, dateModified=None):
        dateModified = utils.normalize_datetime(dateModified)
        result = w(data)
        for target, matches_id in result.pop("exactMatch", []):
            terms = result.get(target, [])
            if any(matches_id == item.get("@id") for item in terms):
                continue
            term = result_to_defined_term(
                lookupObject.lookupById("urn:edurep:conceptset", matches_id), target
            )
            result[target] = terms + [term]
        if dateModified and result.get(schema + "dateModified") is None:
            result[schema + "dateModified"] = [{"@value": dateModified}]
        return tuple2list(result)

    return enrich, info


__all__ = ["prepare_enrich"]
