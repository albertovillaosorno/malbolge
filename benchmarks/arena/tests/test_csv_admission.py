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
#   - Independent CSV delimiter- and quote-boundary admission regressions.
# - Must-Not:
#   - Treat delimiter admission as proof of valid full CSV or authenticity.
# - Allows:
#   - Inputs: bounded synthetic CSV sequences including quoted comma content.
#   - Outputs: assertions on constant-memory CSV column-count admission.
#   - Side effects: none.
# - Split-When:
#   - A second CSV dialect needs a distinct reference parser.
# - Merge-When:
#   - One CSV resource-admission test suite owns both importers' preflight.
# - Summary:
#   - Protects quoted comma content while rejecting true field explosions.
# - Description:
#   - Checks escaped quotes, multiline quotes, and excess separators.
# - Usage:
#   - `pytest benchmarks/arena/tests/test_csv_admission.py`.
# - Defaults:
#   - Empty and invalid column capacities are not admitted.
#

"""Test logical CSV record delimiters without materializing CSV fields."""

# ruff: file-ignore[assert]

from __future__ import annotations

import pytest

from benchmarks.arena import csv_admission


@pytest.mark.parametrize(
    ("text", "maximum", "admitted"),
    [
        ("a,b\nc,d\n", 2, True),
        ("a,b\nc,d,e\n", 2, False),
        ("a,b\n" + "," * 10_000, 2, False),
        ('a,b\n"x,y",z\n', 2, True),
        ('a,b\n"x""y,z",w\n', 2, True),
        ('a,b\n"x\ny,z",w\n', 2, True),
        ('a,b\n"x,y",z,w\n', 2, False),
        ("a,b\nc,d\r\ne,f\r", 2, True),
        ("", 0, False),
    ],
    ids=[
        "paired-fields",
        "three-fields",
        "field-explosion",
        "quoted-comma",
        "escaped-quote",
        "multiline-quoted-value",
        "unquoted-excess",
        "mixed-newlines",
        "invalid-limit",
    ],
)
def test_csv_record_field_admission_matches_registered_limit(
    text: str, maximum: int, *, admitted: bool
) -> None:
    """Quoted separators must not count as CSV column separators."""
    assert csv_admission.within_column_limit(text, maximum) is admitted
