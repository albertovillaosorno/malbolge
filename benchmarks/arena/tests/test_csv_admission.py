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

import csv
from io import StringIO
from itertools import product
from random import Random
from typing import cast

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


@pytest.mark.parametrize(
    "invalid_limit",
    [float("nan"), float("inf"), True, 1.0, None, "2", []],
    ids=["nan", "infinity", "boolean", "float", "missing", "text", "list"],
)
def test_noninteger_csv_limit_cannot_bypass_preflight(
    invalid_limit: object,
) -> None:
    """Unregistered capacities cannot disable the column-allocation bound."""
    assert not csv_admission.within_column_limit(
        "a,b,c,d,e", cast("int", invalid_limit)
    )


@pytest.mark.parametrize(
    "invalid_text",
    [None, b"a,b", 123],
    ids=["missing", "raw-bytes", "integer"],
)
def test_nontext_csv_preflight_fails_closed(invalid_text: object) -> None:
    """The preflight only accepts already decoded bounded CSV source text."""
    assert not csv_admission.within_column_limit(cast("str", invalid_text), 2)


def test_seeded_csv_writer_preserves_quoted_delimiter_counts() -> None:
    """Independently generated escaped CSV rows preserve the real field cap."""
    # Seeded pseudo-randomness only synthesizes reproducible test cases.
    random = Random(8675309)  # ruff: ignore[suspicious-non-cryptographic-random-usage]
    alphabet = ("a", "b", "c", ",", '"', "\n", "\r", " ", "")
    for _ in range(300):
        count = random.randint(1, 12)
        fields = [
            "".join(random.choice(alphabet) for _ in range(random.randint(0, 25)))
            for _ in range(count)
        ]
        buffer = StringIO(newline="")
        csv.writer(buffer, lineterminator="\n").writerow(fields)
        text = buffer.getvalue()
        assert csv_admission.within_column_limit(text, count)
        if count > 1:
            assert not csv_admission.within_column_limit(text, count - 1)


def test_short_valid_csv_differential_oracle_matches_exact_field_counts() -> None:
    """Independent parser agrees on every short valid quote/delimiter shape.

    This tests the preflight's field-count decision, not CSV authenticity or
    a substitute for the strict parsing and schema checks that follow it.
    """
    alphabet = ("a", ",", '"', "\r", "\n")
    for length in range(8):
        for tokens in product(alphabet, repeat=length):
            text = "".join(tokens)
            try:
                counts = [
                    len(row)
                    for row in csv.reader(StringIO(text, newline=""), strict=True)
                ]
            except csv.Error:
                # The downstream parser rejects malformed records. The
                # delimiter preflight is not responsible for that judgment.
                continue
            for maximum in (1, 2, 3):
                expected = all(count <= maximum for count in counts)
                assert csv_admission.within_column_limit(text, maximum) is expected


@pytest.mark.parametrize(
    ("token", "replacement"),
    [("CSV_COMMA", ";"), ("CSV_QUOTE", "a"), ("CSV_NEWLINES", "b")],
)
def test_csv_column_preflight_ignores_mutable_dialect_token_swaps(
    monkeypatch: pytest.MonkeyPatch, token: str, replacement: str
) -> None:
    """The downstream canonical CSV parser must retain the original bound."""
    source = "a,b,c\n"
    assert len(next(csv.reader(StringIO(source, newline=""), strict=True))) == 3
    assert not csv_admission.within_column_limit(source, 2)
    with monkeypatch.context() as patched:
        patched.setattr(csv_admission, token, replacement)
        assert not csv_admission.within_column_limit(source, 2)


@pytest.mark.parametrize(
    ("token", "replacement", "source"),
    [
        ("CSV_QUOTE", "!", '"x,y",z\n'),
        ("CSV_NEWLINES", "_", "a,b\nc,d\n"),
    ],
)
def test_mutable_csv_dialect_tokens_cannot_reject_valid_record_limits(
    monkeypatch: pytest.MonkeyPatch, token: str, replacement: str, source: str
) -> None:
    """Source-valid native two-column CSV must keep its admitted status."""
    with monkeypatch.context() as patched:
        patched.setattr(csv_admission, token, replacement)
        assert csv_admission.within_column_limit(source, 2)
