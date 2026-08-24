# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Independent exhaustive evidence for exact classic decode sum classes.
# - Must-Not:
#   - Import runtime decode helpers or canonicalize whole machine state.
# - Allows:
#   - Inputs: preserved historical xlat1 and all graphical cell/phase pairs.
#   - Outputs: exact permutation, class-size, and decode-equivalence assertions.
#   - Side effects: repository reads only.
# - Split-When:
#   - Another decode canonicalization needs independent historical evidence.
# - Merge-When:
#   - A shared decode proof owns this exact 94-class quotient.
# - Summary:
#   - Prove graphical decode pairs quotient exactly by their modulo-94 sum.
# - Description:
#   - Checks historical xlat1 injectivity and all 8,836 cell/phase pairs.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Applies only where downstream semantics need the decoded opcode alone.
#

"""Independent evidence for exact classic decode sum classes."""

from __future__ import annotations

import ast
from pathlib import Path


def _repository_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "Cargo.toml").is_file():
            return parent
    raise AssertionError


_REPOSITORY_ROOT = _repository_root()
_HISTORICAL = (
    _REPOSITORY_ROOT
    / "src/interoperability/historical-malbolge/adapter-outbound/main.c"
)
_DECLARATION = "const char xlat1[] ="
_GRAPHICAL_START = 33
_GRAPHICAL_STOP = 127
_PHASES = 94
_EXPECTED_PAIRS = _PHASES * _PHASES


def _xlat1() -> bytes:
    source = _HISTORICAL.read_text(encoding="utf-8")
    _, declaration, tail = source.partition(_DECLARATION)
    if not declaration:
        raise AssertionError
    literals: list[str] = []
    for line in tail.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        literals.append(stripped.removesuffix(";"))
        if stripped.endswith(";"):
            break
    return "".join(ast.literal_eval(item) for item in literals).encode("ascii")


def _sum_class(cell: int, phase: int) -> int:
    return ((cell - _GRAPHICAL_START) + phase) % _PHASES


def test_historical_xlat1_is_exact_graphical_permutation() -> None:
    """The historical decode table is injective over all 94 phase indices."""
    table = _xlat1()
    assert len(table) == _PHASES
    assert len(set(table)) == _PHASES
    assert set(table) == set(range(_GRAPHICAL_START, _GRAPHICAL_STOP))


def test_decode_pairs_partition_into_exact_sum_classes() -> None:
    """All 8,836 graphical cell/phase pairs form 94 equal quotient classes."""
    table = _xlat1()
    classes: dict[int, list[tuple[int, int]]] = {
        phase: [] for phase in range(_PHASES)
    }
    observed_outputs: set[int] = set()
    pair_count = 0
    for cell in range(_GRAPHICAL_START, _GRAPHICAL_STOP):
        for phase in range(_PHASES):
            canonical = _sum_class(cell, phase)
            classes[canonical].append((cell, phase))
            observed_outputs.add(table[canonical])
            pair_count += 1
    assert pair_count == _EXPECTED_PAIRS
    assert set(classes) == set(range(_PHASES))
    assert all(len(pairs) == _PHASES for pairs in classes.values())
    assert observed_outputs == set(table)


def test_decode_equality_is_exactly_sum_class_equality() -> None:
    """xlat1 injectivity makes the sum class a complete decode key."""
    table = _xlat1()
    representatives = {
        canonical: (_GRAPHICAL_START, canonical)
        for canonical in range(_PHASES)
    }
    for cell in range(_GRAPHICAL_START, _GRAPHICAL_STOP):
        for phase in range(_PHASES):
            canonical = _sum_class(cell, phase)
            rep_cell, rep_phase = representatives[canonical]
            assert _sum_class(rep_cell, rep_phase) == canonical
            assert table[_sum_class(cell, phase)] == table[canonical]
    assert len({table[canonical] for canonical in representatives}) == _PHASES
