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
#   - Independent structural evidence for one suffix-independent prefix class.
# - Must-Not:
#   - Claim verifier-work reduction, timing, or general prefix independence.
# - Allows:
#   - Inputs: frozen two-word corpus and low-level classic decode/entry
#     transfer.
#   - Outputs: exact admitted suffix set and candidate-quality parity for `Q`.
#   - Side effects: none.
# - Split-When:
#   - A registered comparison runner owns all decomposable prefix classes.
# - Merge-When:
#   - Prefix decomposition correctness evidence is centralized elsewhere.
# - Summary:
#   - Prove one exact nontrivial prefix can discharge admitted suffixes.
# - Description:
#   - Entry halt occurs before encryption; suffix only affects load admission.
# - Usage:
#   - Supports runner feasibility without opening the measurement gate.
# - Defaults:
#   - Every other prefix remains unproved and must use full verification.
#

"""Structural basis for the preregistered classic prefix decomposition."""

from src.research.algorithms.composition.algorithms.superoptimization import (
    challenge,
)
from verifier import emitted_malbolge_classic as classic
from verifier import emitted_malbolge_entry as entry_transfer

_GRAPHICAL_START = 33
_GRAPHICAL_VALUES = 94
_PREFIX = ord("Q")
_HALT = ord("v")
_HALTED = "halted"
_ALLOWED_LOAD_INSTRUCTIONS = frozenset(b"ji*p</vo")
_EXPECTED_ADMITTED_SUFFIXES = 8
_EXPECTED_QUALITY = 1


def _candidate_index(suffix: int) -> int:
    prefix_digit = _PREFIX - _GRAPHICAL_START
    suffix_digit = suffix - _GRAPHICAL_START
    return prefix_digit * _GRAPHICAL_VALUES + suffix_digit


def _load_admitted(suffix: int) -> bool:
    first = classic.decode(_PREFIX, 0)
    second = classic.decode(suffix, 1)
    return (
        first in _ALLOWED_LOAD_INSTRUCTIONS
        and second in _ALLOWED_LOAD_INSTRUCTIONS
    )


def test_q_prefix_halts_before_any_suffix_dependent_entry_state() -> None:
    """The admitted `Q` prefix has one exact suffix-independent entry halt."""
    decoded = classic.decode(_PREFIX, 0)
    assert decoded is not None
    assert decoded == _HALT

    suffix_end = _GRAPHICAL_START + _GRAPHICAL_VALUES
    for suffix in range(_GRAPHICAL_START, suffix_end):
        entry = entry_transfer.analyze_entry_transition(
            (_PREFIX, suffix),
            decoded,
        )
        assert entry.accepted is True
        assert entry.status == _HALTED
        assert entry.encryption_address is None
        assert entry.next_fetch_address is None


def test_q_prefix_structural_discharge_matches_complete_challenge_map() -> None:
    """Load admission plus entry halt reproduces all 94 frozen `Q` qualities."""
    admitted = 0
    suffix_end = _GRAPHICAL_START + _GRAPHICAL_VALUES
    for suffix in range(_GRAPHICAL_START, suffix_end):
        candidate = _candidate_index(suffix)
        expected = _EXPECTED_QUALITY if _load_admitted(suffix) else None
        assert challenge.verified_quality(candidate) == expected
        admitted += int(expected is not None)

    assert admitted == _EXPECTED_ADMITTED_SUFFIXES
