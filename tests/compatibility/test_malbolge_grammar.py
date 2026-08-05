# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - TextMate lexical agreement with the canonical source-byte boundary.
# - Must-Not:
#   - Claim position-dependent instruction validation or compile the grammar.
# - Allows:
#   - Inputs: the checked-in strict JSON grammar.
#   - Outputs: exact scope and ASCII character-class assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when upstream Linguist compilation gains independent evidence.
# - Merge-When:
#   - Merge when another suite owns the same grammar lexical contract.
# - Summary:
#   - Keeps source whitespace and invalid controls aligned with the VM.
# - Description:
#   - Proves vertical tab is whitespace and rejected controls remain exact.
# - Usage:
#   - Collected by the repository Python test suite.
# - Defaults:
#   - Unknown or malformed grammar structure fails closed.
#

"""TextMate grammar lexical boundary regression tests."""

from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
GRAMMAR = ROOT / (
    "src/tooling/language-support/contract/grammar/syntaxes/"
    "malbolge.tmLanguage.json"
)
SOURCE_WHITESPACE = (0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x20)
REJECTED_CONTROLS = (0x00, 0x08, 0x0E, 0x1F, 0x7F)


def _grammar() -> dict[str, object]:
    document = json.loads(GRAMMAR.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _pattern(document: dict[str, object], key: str) -> re.Pattern[str]:
    repository = document["repository"]
    assert isinstance(repository, dict)
    entry = repository[key]
    assert isinstance(entry, dict)
    pattern = entry["match"]
    assert isinstance(pattern, str)
    return re.compile(pattern)


def test_grammar_admits_exact_source_whitespace() -> None:
    """The invalid-control class excludes all six source whitespace bytes."""
    document = _grammar()
    assert document["scopeName"] == "source.malbolge"
    invalid = _pattern(document, "invalid-control-character")
    for byte in SOURCE_WHITESPACE:
        assert invalid.fullmatch(chr(byte)) is None
    for byte in REJECTED_CONTROLS:
        assert invalid.fullmatch(chr(byte)) is not None


def test_grammar_scopes_exact_graphical_source_units() -> None:
    """Encoded source units remain precisely graphical ASCII."""
    encoded = _pattern(_grammar(), "encoded-source-unit")
    for byte in range(0x21, 0x7F):
        assert encoded.fullmatch(chr(byte)) is not None
    for byte in (*SOURCE_WHITESPACE, 0x7F):
        assert encoded.fullmatch(chr(byte)) is None
