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

from .ns import schema, edurep_terms, to_curie
from metastreams.jsonld import identity, walk, ignore_silently
import seecr.functools as sfc
import kennisnet.jsonld.utils as utils
import seecr.functools.core as sfc
import urllib.parse
import rfc3987


def with_predicate(target_p, normalize_os=None):
    if normalize_os is None:
        normalize_os = lambda os: os

    def fn(a, s, p, os):
        return a | {target_p: normalize_os(a.get(target_p, []) + os)}

    return fn


def remove_duplicate_values(os):
    seen = set()
    result = []
    for o in os:
        value = o.get("@value")
        if value in seen:
            continue
        result.append(o)
        seen.add(value)
    return result


def is_uri(s):
    return s is not None and rfc3987.match(s, rule="absolute_IRI")


def add_id_to_defined_term(term):
    if "@id" in term:
        return term
    inDefinedTermSet = sfc.get_in(
        term, (schema + "inDefinedTermSet", 0, "@value"), ""
    ).strip()
    termCode = sfc.get_in(term, (schema + "termCode", 0, "@value"), "").strip()
    if termCode and not is_uri(termCode) and is_uri(inDefinedTermSet):
        h = "" if inDefinedTermSet[-1] in {"#", "/"} else "#"
        termCode = urllib.parse.quote(termCode, safe="")
        term["@id"] = f"{inDefinedTermSet}{h}{termCode}"
    return term


definition_rules = {
    "@type": lambda a, s, p, os: a | {"@type": [schema + "DefinedTerm"]},
    "@id": identity,
    schema + "name": identity,
    schema
    + "inDefinedTermSet": with_predicate(
        schema + "inDefinedTermSet", remove_duplicate_values
    ),
    schema + "termCode": with_predicate(schema + "termCode", remove_duplicate_values),
    # wrong keys
    schema
    + "educationalFramework": with_predicate(
        schema + "inDefinedTermSet", remove_duplicate_values
    ),
    schema + "targetName": with_predicate(schema + "termCode", remove_duplicate_values),
}
definition_walk = walk(definition_rules)
definition_alignment_rules = {
    "@type": identity,
    "@id": identity,
    schema + "educationalFramework": identity,
    schema + "targetName": identity,
    schema + "name": identity,
    schema + "alignmentType": identity,
}
definition_alignment_walk = walk(definition_alignment_rules)

definition_alignment_to_keywords_rules = {
    "@type": lambda a, s, p, os: a | {"@type": [schema + "DefinedTerm"]},
    "@id": identity,
    schema
    + "educationalFramework": with_predicate(
        schema + "inDefinedTermSet", remove_duplicate_values
    ),
    schema + "targetName": with_predicate(schema + "termCode", remove_duplicate_values),
    schema + "name": identity,
    schema + "alignmentType": ignore_silently,
    # wrong values
    schema
    + "inDefinedTermSet": with_predicate(
        schema + "inDefinedTermSet", remove_duplicate_values
    ),
    schema + "termCode": with_predicate(schema + "termCode", remove_duplicate_values),
}
definition_alignment_keywords_walk = walk(definition_alignment_to_keywords_rules)


keywords_target_p = schema + "keywords"


curriculum_uris = {
    "http://purl.edustandaard.nl/begrippenkader",
    "https://opendata.slo.nl/curriculum/uuid",
    "http://purl.edustandaard.nl/concept",
}


def _startswith_uri(termId, uri):
    a, b, c = termId.partition(uri)
    return b == uri and len(c) > 1


def is_curriculum_waarde_in_term(term, inDefinedTermSet=schema + "inDefinedTermSet"):
    termSet = sfc.get_in(term, (inDefinedTermSet, 0, "@value"))
    if termSet and termSet in curriculum_uris:
        return bool(term.get("@id")), termSet
    termId = term.get("@id")
    if termId:
        for uri in curriculum_uris:
            if _startswith_uri(termId, uri):
                return True, uri
    return False, None


def result_to_defined_term(lookup_result, target_p):
    type, termCodeKey, inDefinedTermSetKey = (
        schema + "DefinedTerm",
        schema + "termCode",
        schema + "inDefinedTermSet",
    )
    if target_p == schema + "educationalAlignment":
        type, termCodeKey, inDefinedTermSetKey = (
            schema + "AlignmentObject",
            schema + "targetName",
            schema + "educationalFramework",
        )

    result = {
        "@type": [type],
    }
    if lookup_result.id:
        result["@id"] = lookup_result.id
    if lookup_result.identifier:
        result[termCodeKey] = [{"@value": lookup_result.identifier}]
    if lookup_result.source:
        result[inDefinedTermSetKey] = [{"@value": lookup_result.source}]
    if lookup_result.labels:
        result[schema + "name"] = [
            utils.as_value(v, l) for v, l in lookup_result.labels
        ]
    return result


type_to_target = {
    edurep_terms + "EducationalLevel": schema + "educationalLevel",
    edurep_terms + "EducationalObjective": schema + "teaches",
    edurep_terms + "Discipline": schema + "educationalAlignment",
    None: schema + "keywords",
}


def prep_improve_keyword(lookupObject):
    def improve_keyword(d):
        assert d["@type"] == [schema + "DefinedTerm"]
        termCode = sfc.get_in(d, (schema + "termCode", 0, "@value"))
        search_for = [termCode] + [
            v["@value"] for v in d.get(schema + "name", {}) if "@value" in v
        ]
        l_result = None
        for search in search_for:
            l_result = lookupObject.lookupByValue("urn:edurep:conceptset", search)
            if l_result and l_result.type:
                break
        if not l_result.id or not l_result.type:
            return schema + "keywords", add_id_to_defined_term(d), None
        target_p = type_to_target[l_result.type]
        return target_p, result_to_defined_term(l_result, target_p), l_result.exactMatch

    return improve_keyword


def improve_keywords(lookupObject):
    improve_keyword = prep_improve_keyword(lookupObject)

    def keywords_fn(a, s, p, os):
        """Dit veld wordt gecontroleerd in stap 2.1 van de zogenaamde Flow
        2.1 Op basis van termCode wordt gezocht in prefLabel, altLabel, hiddenLabel op een match. Als in de match een type is opgenomen, dan wordt het keyword verplaatst.
        """
        created_keywords = a.get(p, [])
        newdata = {p: []}
        for keyword in os:
            if keyword.get("@type") != [schema + "DefinedTerm"]:
                newdata[p].append(keyword)
                continue
            target_p, keyword, matches_id = improve_keyword(keyword)
            if matches_id:
                newdata.setdefault("exactMatch", []).append((target_p, matches_id))
            if not target_p in newdata:
                newdata[target_p] = a.get(target_p, [])
            newdata[target_p].append(keyword)
        newdata[p].extend(created_keywords)
        return a | {k: v for k, v in newdata.items() if v}

    keywords_fn.lookup_info = {"urn:edurep:conceptset": {}}
    return keywords_fn


def prep_improve_definedterm(lookupObject):
    def improve_definedterm(term, target_p):
        if not (termId := term.get("@id")):
            return term, None
        termId = utils.pretty_print_uuid(termId)
        lookup_result = lookupObject.lookupById("urn:edurep:conceptset", termId)
        if not lookup_result.id:
            lookupObject.report_not_found(to_curie(target_p), termId)
            return term, None
        term["@id"] = lookup_result.id
        termCodeKey = (
            schema + "targetName"
            if term.get("@type") == [schema + "AlignmentObject"]
            else schema + "termCode"
        )
        if lookup_result.labels:
            term[schema + "name"] = [
                utils.as_value(v, l) for v, l in lookup_result.labels
            ]
        if lookup_result.identifier:
            term[termCodeKey] = [
                {"@value": lookup_result.identifier},
            ]
        return term, lookup_result.exactMatch

    return improve_definedterm


def defined_term(target_p, lookupObject):
    to_keywords_walk = definition_walk
    copy_walk = definition_walk
    inDefinedTermSet = schema + "inDefinedTermSet"
    type_object = schema + "DefinedTerm"
    if target_p == schema + "educationalAlignment":
        to_keywords_walk = definition_alignment_keywords_walk
        copy_walk = definition_alignment_walk
        inDefinedTermSet = schema + "educationalFramework"
        type_object = schema + "AlignmentObject"
    improve_keyword = prep_improve_keyword(lookupObject)
    improve_definedterm = prep_improve_definedterm(lookupObject)

    def defined_term_fn(a, s, p, os):
        """Dit veld wordt gecontroleerd in 3 stappen, de zogenaamde Flow:
        1. Is de term een curriculumwaarde (@id of inDefinedTermSet), zo niet dan verplaatsen naar schema:keywords.
        2.1 Zie schema:keywords
        2.2 vul label en termCode aan op basis van @id
        3 Voeg een DefinedTerm toe op basis van exactMatch
        """
        results = {"exactMatch": a.get("exactMatch", [])}
        for term in os:
            is_cur, curriculum_uri = is_curriculum_waarde_in_term(
                term, inDefinedTermSet
            )
            if is_cur:
                target = target_p
                result = copy_walk(term)
                result[inDefinedTermSet] = [{"@value": curriculum_uri}]
                result["@type"] = [type_object]
                result, matches_id = improve_definedterm(result, target)
            else:
                target = keywords_target_p
                result = to_keywords_walk(term)
                matches_id = None
                if result.get("@type") == [schema + "DefinedTerm"]:
                    target, result, matches_id = improve_keyword(result)
            if not target in results:
                results[target] = a.get(target, [])
            if matches_id:
                results["exactMatch"].append((target, matches_id))
            results[target].append(result)
        return a | {k: v for k, v in results.items() if v}

    defined_term_fn.lookup_info = {
        "urn:edurep:conceptset": {"not_found": to_curie(target_p)}
    }
    return defined_term_fn


__all__ = ["defined_term", "improve_keywords", "result_to_defined_term"]
