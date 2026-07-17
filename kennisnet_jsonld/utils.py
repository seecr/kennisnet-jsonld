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

from seecr.zulutime import ZuluTime


def as_value(v, l):
    if l:
        return {"@value": v, "@language": l}
    return {"@value": v}


import re, uuid

uuid_r = re.compile(r"(?i)[a-f0-9\-]{32,36}")


def pretty_print_uuid(s):
    try:
        return uuid_r.sub(lambda m: str(uuid.UUID(m.group(0))), s)
    except ValueError:
        return s


def normalize_datetime(date):
    if not date:
        return None
    try:
        return ZuluTime(date).zulu()
    except:
        return None


class _Any:
    def __init__(self, f=None):
        self.f = f

    def __call__(self, *args, **kwargs):
        return _Any(*args, **kwargs)

    def __eq__(self, other):
        return self.f is None or self.f(other)

    def __repr__(self):
        return "*" if self.f is None else self.f.__name__ + "(...)"


anything = _Any()
