# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - Apache-2.0
# Confidential:
#   - false
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
    if maximum < 1:
        return False
    columns = 1
    at_start = True
    quoted = False
    index = 0
    while index < len(text):  # ruff: ignore[too-many-nested-blocks]
        char = text[index]
        if quoted:
            if char == CSV_QUOTE:
                if index + 1 < len(text) and text[index + 1] == CSV_QUOTE:
                    index += 1
                else:
                    quoted = False
        elif char == CSV_COMMA:
            columns += 1
            if columns > maximum:
                return False
            at_start = True
        elif char in CSV_NEWLINES:
            columns = 1
            at_start = True
        elif char == CSV_QUOTE and at_start:
            quoted = True
            at_start = False
        else:
            at_start = False
        index += 1
    return True
