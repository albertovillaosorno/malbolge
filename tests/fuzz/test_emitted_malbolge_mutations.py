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
#   - Seeded invalid-decode mutations and deterministic analyzer replay
#     evidence.
# - Must-Not:
#   - Use ambient entropy, import verifier helpers, or execute guest
#     instructions.
# - Allows:
#   - Inputs: fixed ordinal mutations and the public analyzer CLI.
#   - Outputs: byte-exact replay plus precise rejection locations.
#   - Side effects: test-local source files and bounded subprocess execution.
# - Split-When:
#   - Another mutation family needs independent shrinking or replay identity.
# - Merge-When:
#   - Differential evidence owns the same mutation and replay protocol.
# - Summary:
#   - Replays deterministic positional-decode counterexamples through the CLI.
# - Description:
#   - Mutates one loaded cell while preserving surrounding valid source words.
# - Usage:
#   - Collected by repository pytest validation.
# - Defaults:
#   - Fixed ordinals fully determine mutation position and bytes.
#

"""Seeded invalid mutations for emitted-Malbolge static analysis."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from typing import Final
from typing import cast

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_ANALYZER = _ROOT / "verifier" / "emitted_malbolge.py"
_SCHEMA: Final = "malbolge-static-image/v13"
_DECODE_CODE: Final = "MALBOLGE-STATIC-004"
_GRAPHICAL_START: Final = 33
_XLAT1: Final = (
    b'+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA"lI'
    rb".v%{gJh4G\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha"
)
_BASE_DECODE: Final = ord("o")
_FORBIDDEN_DECODE: Final = ord("A")
_WORD_COUNT: Final = 32
_CASE_COUNT: Final = 16


def _source_byte(decoded: int, position: int) -> int:
    index = _XLAT1.index(decoded)
    return ((index - position) % len(_XLAT1)) + _GRAPHICAL_START


def _base_source() -> tuple[bytearray, tuple[int, ...]]:
    source = bytearray()
    offsets: list[int] = []
    for position in range(_WORD_COUNT):
        if position % 4 == 0:
            source.extend(b" \n")
        offsets.append(len(source))
        source.append(_source_byte(_BASE_DECODE, position))
    return source, tuple(offsets)


def _mutation(ordinal: int) -> tuple[bytes, int, int]:
    source, offsets = _base_source()
    position = (ordinal * 7 + 3) % _WORD_COUNT
    offset = offsets[position]
    source[offset] = _source_byte(_FORBIDDEN_DECODE, position)
    return bytes(source), position, offset


def _run(path: Path) -> sp.CompletedProcess[str]:
    return sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [sys.executable, str(_ANALYZER), str(path)],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        shell=False,
        text=True,
        timeout=30,
    )


@pytest.mark.parametrize("ordinal", range(_CASE_COUNT))
def test_seeded_invalid_decode_replays_exactly(
    tmp_path: Path,
    ordinal: int,
) -> None:
    """Replay one deterministic invalid mutation with exact context."""
    source, position, offset = _mutation(ordinal)
    path = tmp_path / "mutated.malbolge"
    _ = path.write_bytes(source)
    first = _run(path)
    second = _run(path)
    assert first.returncode == 1
    assert second.returncode == 1
    assert not first.stderr
    assert not second.stderr
    assert first.stdout == second.stdout
    document = cast("dict[str, object]", json.loads(first.stdout))
    assert document["schema"] == _SCHEMA
    assert document["admitted_initial_image"] is False
    assert document["source_sha256"] == "sha256:" + sha256(source).hexdigest()
    findings = cast("list[dict[str, object]]", document["findings"])
    assert len(findings) == 1
    finding = findings[0]
    assert finding["code"] == _DECODE_CODE
    assert finding["loaded_position"] == position
    assert finding["byte_offset"] == offset
    assert finding["decoded_byte"] == _FORBIDDEN_DECODE
