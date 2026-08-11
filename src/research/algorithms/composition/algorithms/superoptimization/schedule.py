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
#   - Version-stable candidate-index schedules for the preregistered pilot.
# - Must-Not:
#   - Define challenge semantics, execute candidates, or grant verifier
#     authority.
# - Allows:
#   - Inputs: finite candidate count, evaluation budget, and unsigned seed.
#   - Outputs: deterministic enumeration or seeded no-replacement index order.
#   - Side effects: none.
# - Split-When:
#   - Candidate proposal semantics gain their own executable challenge model.
# - Merge-When:
#   - A shared research scheduler owns this exact replay contract.
# - Summary:
#   - Reproducible candidate ordering below the superoptimization verifier gate.
# - Description:
#   - Uses natural enumeration and sparse SplitMix64 partial Fisher-Yates.
# - Usage:
#   - Research harnesses may consume schedules under identical candidate sets.
# - Defaults:
#   - Foreign numeric types and values outside unsigned-64 bounds fail closed.
#

"""Version-stable candidate-index schedules for the superoptimization pilot."""

from __future__ import annotations

_MAX_U64 = (1 << 64) - 1
_SPLITMIX_INCREMENT = 0x9E3779B97F4A7C15
_SPLITMIX_MIX1 = 0xBF58476D1CE4E5B9
_SPLITMIX_MIX2 = 0x94D049BB133111EB

ENUMERATION_SCHEDULE_ID = "deterministic-enumeration-v1"
SEEDED_PROPOSAL_SCHEDULE_ID = "splitmix64-sparse-partial-fisher-yates-v1"


class InvalidCandidateScheduleError(ValueError):
    """One pilot candidate schedule request is malformed."""


class _SplitMix64:
    """Stable local pseudorandom stream used only for proposal ordering."""

    def __init__(self, seed: int) -> None:
        self._state: int = seed

    def next_u64(self) -> int:
        """Return the next deterministic unsigned 64-bit word.

        Returns:
            Next SplitMix64 stream word.

        """
        self._state = (self._state + _SPLITMIX_INCREMENT) & _MAX_U64
        value = self._state
        value = ((value ^ (value >> 30)) * _SPLITMIX_MIX1) & _MAX_U64
        value = ((value ^ (value >> 27)) * _SPLITMIX_MIX2) & _MAX_U64
        return (value ^ (value >> 31)) & _MAX_U64


def _u64(value: object, label: str) -> int:
    if type(value) is not int or not 0 <= value <= _MAX_U64:
        message = f"{label} must be an unsigned 64-bit integer"
        raise InvalidCandidateScheduleError(message)
    return value


def enumeration_order(
    candidate_count: int,
    evaluation_budget: int,
) -> tuple[int, ...]:
    """Return the stable deterministic-enumeration prefix.

    Returns:
        Natural candidate-index prefix bounded by candidate count and budget.

    """
    count = _u64(candidate_count, "candidate count")
    budget = _u64(evaluation_budget, "evaluation budget")
    return tuple(range(min(count, budget)))


def _partial_fisher_yates(
    count: int,
    selected_count: int,
    stream: _SplitMix64,
) -> tuple[int, ...]:
    swaps: dict[int, int] = {}
    result: list[int] = []
    for position in range(selected_count):
        selected = position + (stream.next_u64() % (count - position))
        selected_value = swaps.get(selected, selected)
        if selected != position:
            swaps[selected] = swaps.get(position, position)
        _ = swaps.pop(position, None)
        result.append(selected_value)
    return tuple(result)


def seeded_proposal_order(
    candidate_count: int,
    evaluation_budget: int,
    seed: int,
) -> tuple[int, ...]:
    """Return a stable seeded no-replacement candidate-index prefix.

    Returns:
        SplitMix64 partial Fisher-Yates prefix bounded by count and budget.

    """
    count = _u64(candidate_count, "candidate count")
    budget = _u64(evaluation_budget, "evaluation budget")
    admitted_seed = _u64(seed, "schedule seed")
    selected_count = min(count, budget)
    if selected_count == 0:
        return ()
    return _partial_fisher_yates(
        count,
        selected_count,
        _SplitMix64(admitted_seed),
    )
