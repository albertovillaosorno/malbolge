# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - LicenseRef-Proprietary
# Confidential:
#   - true
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - Bounded CSV record-column preflight before Python's CSV row allocation.
# - Must-Not:
#   - Authenticate source bytes or replace the strict CSV schema validator.
# - Allows:
#   - Inputs: decoded bounded CSV text and a registered positive column cap.
#   - Outputs: boolean result of the delimiter-count admission.
#   - Side effects: none.
# - Split-When:
#   - A different CSV dialect requires independently audited parsing semantics.
# - Merge-When:
#   - Registered arena and historical CSV share this standard dialect.
# - Summary:
#   - Rejects excessive columns without counting commas inside quoted fields.
# - Description:
#   - Tracks field starts and doubled quotes through logical CSV records.
# - Usage:
#   - Called before csv.reader or csv.DictReader builds field objects.
# - Defaults:
#   - The importer supplies the exact registered maximum column count.
#

"""Constant-memory preflight of CSV record field counts before parsing."""

from __future__ import annotations

CSV_QUOTE = '"'
CSV_COMMA = ","
CSV_NEWLINES = "\r\n"
# The bounded preflight must keep the original stdlib CSV dialect even when
# a public module token is substituted after import.
_SOURCE_CSV_QUOTE = CSV_QUOTE
_SOURCE_CSV_COMMA = CSV_COMMA
_SOURCE_CSV_NEWLINES = CSV_NEWLINES
# Input shape and full traversal must use native providers, not late aliases.
_NATIVE_TYPE = type
_NATIVE_STR = str
_NATIVE_INT = int
_NATIVE_LEN = len


# A single-pass CSV quote state machine necessarily branches on dialect tokens.
def within_column_limit(  # ruff: ignore[complex-structure,too-many-branches,too-many-statements]
    text: str, maximum: int
) -> bool:
    """Check standard CSV delimiters without building field lists.

    Doubled quotes inside quoted fields are data, and newlines only begin a
    new logical record when outside a quoted field. The strict CSV parser
    remains responsible for rejecting malformed quoting and missing fields.

    Returns:
        Whether each logical record has at most the admitted column count.

    """
    if (
        _NATIVE_TYPE(text) is not _NATIVE_STR
        or _NATIVE_TYPE(maximum) is not _NATIVE_INT
        or maximum < 1
    ):
        return False
    columns = 1
    at_start = True
    quoted = False
    index = 0
    source_length = _NATIVE_LEN(text)
    while index < source_length:  # ruff: ignore[too-many-nested-blocks]
        char = text[index]
        if quoted:
            if char == _SOURCE_CSV_QUOTE:
                if index + 1 < source_length and text[index + 1] == _SOURCE_CSV_QUOTE:
                    index += 1
                else:
                    quoted = False
        elif char == _SOURCE_CSV_COMMA:
            columns += 1
            if columns > maximum:
                return False
            at_start = True
        elif char in _SOURCE_CSV_NEWLINES:
            columns = 1
            at_start = True
        elif char == _SOURCE_CSV_QUOTE and at_start:
            quoted = True
            at_start = False
        else:
            at_start = False
        index += 1
    return True
