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
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Scalable ternary-memory profile correspondence tests.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Scalable ternary-memory profile correspondence tests."""

from __future__ import annotations

from pathlib import Path

from scripts.validate import target_profile as validator

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "malbolge.json"
EVIDENCE_PATH = (
    ROOT
    / "src/interoperability/profile-compatibility/contract"
    / "scalable-memory-evidence.json"
)
METRICS_PATH = (
    ROOT
    / "src/research/algorithms/domain/algorithms/doom/quality/comparison"
    / "metrics.json"
)
CURRENT_PROFILE = "malbolge-2026.3"
EVIDENCE_SELECTED_PROFILE = "malbolge-2026.2"
CLASSIC_TRITS = 10
SCALED_TRITS = 14
THIRTEEN_TRITS = 13
TERNARY_RADIX = 3
SCALED_WORDS = TERNARY_RADIX**SCALED_TRITS
SCALED_MAX = SCALED_WORDS - 1
SCALED_ROTATE_ONE = TERNARY_RADIX ** (SCALED_TRITS - 1)
CLASSIC_ZERO_CRAZY_ZERO = 29_524
CLASSIC_MAX = TERNARY_RADIX**CLASSIC_TRITS - 1
CRAZY_TRIT_TABLE = (
    (1, 0, 0),
    (1, 0, 2),
    (2, 2, 1),
)


def _array(value: validator.JsonValue) -> list[validator.JsonValue]:
    assert isinstance(value, list)
    return value


def _integer(value: validator.JsonValue) -> int:
    assert type(value) is int
    return value


def _object(value: validator.JsonValue) -> validator.JsonObject:
    assert isinstance(value, dict)
    return value


def _profile(profile_id: str) -> validator.JsonObject:
    document = validator.load_document(PROFILE_PATH)
    profiles = _object(document["profiles"])
    return _object(profiles[profile_id])


def _crazy_trit(data: int, accumulator: int) -> int:
    return CRAZY_TRIT_TABLE[data][accumulator]


def _crazy(data: int, accumulator: int, trits: int) -> int:
    result = 0
    place = 1
    for _ in range(trits):
        result += (
            _crazy_trit(data % TERNARY_RADIX, accumulator % TERNARY_RADIX)
            * place
        )
        place *= TERNARY_RADIX
        data //= TERNARY_RADIX
        accumulator //= TERNARY_RADIX
    return result


def _rotate(value: int, trits: int) -> int:
    high_weight = 1
    for _ in range(trits - 1):
        high_weight *= TERNARY_RADIX
    return value // TERNARY_RADIX + (value % TERNARY_RADIX) * high_weight


def test_scaled_profile_matches_tracked_capacity_evidence() -> None:
    """The selected 14-trit profile is tied to the tracked DOOM snapshot."""
    evidence = validator.load_document(EVIDENCE_PATH)
    metrics = validator.load_document(METRICS_PATH)
    workload = _object(evidence["workload_proxy"])
    after = _object(metrics["after"])
    corpus = _object(after["corpus"])
    candidates = _array(evidence["candidate_widths"])
    by_trits = {
        _integer(_object(candidate)["trits"]): _object(candidate)
        for candidate in candidates
    }

    assert evidence["selected_profile"] == EVIDENCE_SELECTED_PROFILE
    assert workload["source_sha256"] == corpus["source_sha256"]
    assert workload["source_bytes"] == corpus["source_bytes"]
    source_bytes = _integer(workload["source_bytes"])
    thirteen = by_trits[THIRTEEN_TRITS]
    fourteen = by_trits[SCALED_TRITS]
    assert _integer(thirteen["words"]) == TERNARY_RADIX**THIRTEEN_TRITS
    assert _integer(fourteen["words"]) == SCALED_WORDS
    assert _integer(thirteen["headroom_over_proxy_words"]) == (
        TERNARY_RADIX**THIRTEEN_TRITS - source_bytes
    )
    assert _integer(fourteen["headroom_over_proxy_words"]) == (
        SCALED_WORDS - source_bytes
    )


def test_scaled_profile_uses_one_word_for_every_address() -> None:
    """Word modulus and memory size remain the same ternary geometry."""
    profile = _profile(CURRENT_PROFILE)
    word = _object(profile["word"])
    memory = _object(profile["memory"])
    semantics = _object(profile["semantics"])
    assert _integer(word["trits"]) == SCALED_TRITS
    assert _integer(word["modulus"]) == SCALED_WORDS
    assert _integer(memory["words"]) == SCALED_WORDS
    assert _integer(semantics["eof_word"]) == SCALED_MAX
    assert SCALED_MAX > CLASSIC_MAX


def test_rotate_generalizes_by_one_ternary_digit() -> None:
    """Rotation stays circular over exactly the profile's N trits."""
    assert _rotate(1, SCALED_TRITS) == SCALED_ROTATE_ONE
    assert _rotate(TERNARY_RADIX, SCALED_TRITS) == 1
    assert _rotate(SCALED_MAX, SCALED_TRITS) == SCALED_MAX


def test_crazy_generalizes_digitwise_without_new_truth_table() -> None:
    """The original crazy truth table applies independently to all N trits."""
    assert _crazy(0, 0, CLASSIC_TRITS) == CLASSIC_ZERO_CRAZY_ZERO
    assert _crazy(CLASSIC_MAX, 0, CLASSIC_TRITS) == CLASSIC_MAX
    assert _crazy(0, CLASSIC_MAX, CLASSIC_TRITS) == 0
    assert _crazy(0, 0, SCALED_TRITS) == SCALED_MAX // 2
    assert _crazy(SCALED_MAX, 0, SCALED_TRITS) == SCALED_MAX
    assert _crazy(0, SCALED_MAX, SCALED_TRITS) == 0


def test_address_successor_wraps_at_scaled_word_modulus() -> None:
    """C and D wrap at 3^N rather than a host pointer width."""
    successor = (SCALED_MAX + 1) % SCALED_WORDS
    assert successor == 0
