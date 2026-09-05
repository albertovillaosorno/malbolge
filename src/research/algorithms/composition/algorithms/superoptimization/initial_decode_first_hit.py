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
#   - Stop-on-first comparison for the bucketed initial-decode follow-up.
# - Must-Not:
#   - Define challenge semantics, alter schedules from outcomes, or persist
#     data.
# - Allows:
#   - Inputs: one trusted verifier callback and a monotonic clock.
#   - Outputs: first-hit work and elapsed time under the fixed ceiling.
#   - Side effects: invokes only the caller verifier and clock.
# - Split-When:
#   - Another stop policy or heuristic feature gains independent ownership.
# - Merge-When:
#   - A shared first-hit harness owns this exact follow-up comparison.
# - Summary:
#   - Measure first-hit runtime after the retained full-budget holdout result.
# - Description:
#   - Includes schedule construction and stops only on verifier success.
# - Usage:
#   - Execute real timing only after the follow-up plan is committed.
# - Defaults:
#   - Malformed verifier quality or clock evidence fails closed.
#

"""Stop-on-first runtime follow-up for the three-word static heuristic."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter_ns
from typing import Final

from algorithms.superoptimization import initial_decode_heuristic as heuristic
from algorithms.superoptimization import schedule

BASELINE_ID: Final = "deterministic-enumeration-first-hit-v1"
HEURISTIC_ID: Final = "bucketed-initial-decode-first-hit-v1"
CANDIDATE_COUNT: Final = heuristic.THREE_WORD_CANDIDATE_COUNT
EVALUATION_BUDGET: Final = 50_000
_MAX_U64: Final = (1 << 64) - 1

type CandidateVerifier = Callable[[int], int | None]
type Clock = Callable[[], int]


class InitialDecodeFirstHitError(ValueError):
    """The first-hit follow-up violated its fixed execution contract."""


@dataclass(frozen=True, slots=True)
class FirstHitRun:
    """One stopped search result including schedule construction time."""

    strategy_id: str
    evaluations: int
    candidate: int | None
    quality: int | None
    elapsed_nanoseconds: int


def _quality(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int or not 0 <= value <= _MAX_U64:
        message = "trusted first-hit quality is malformed"
        raise InitialDecodeFirstHitError(message)
    return value


def _run(
    strategy_id: str,
    *,
    order_factory: Callable[[], tuple[int, ...]],
    verifier: CandidateVerifier,
    clock_ns: Clock,
) -> FirstHitRun:
    start = clock_ns()
    order = order_factory()
    evaluations = 0
    candidate_hit: int | None = None
    quality_hit: int | None = None
    for candidate in order:
        evaluations += 1
        quality = _quality(verifier(candidate))
        if quality is not None:
            candidate_hit = candidate
            quality_hit = quality
            break
    end = clock_ns()
    if type(start) is not int or type(end) is not int or end < start:
        message = "first-hit clock must be monotonic integers"
        raise InitialDecodeFirstHitError(message)
    return FirstHitRun(
        strategy_id,
        evaluations,
        candidate_hit,
        quality_hit,
        end - start,
    )


def run_baseline(
    verifier: CandidateVerifier,
    clock_ns: Clock = perf_counter_ns,
) -> FirstHitRun:
    """Run natural enumeration until verified hit or budget exhaustion.

    Returns:
        First verified candidate or one explicit budget-exhausted result.

    """
    return _run(
        BASELINE_ID,
        order_factory=lambda: schedule.enumeration_order(
            CANDIDATE_COUNT,
            EVALUATION_BUDGET,
        ),
        verifier=verifier,
        clock_ns=clock_ns,
    )


def run_heuristic(
    verifier: CandidateVerifier,
    clock_ns: Clock = perf_counter_ns,
) -> FirstHitRun:
    """Run the exact bucketed heuristic until first verified hit.

    Returns:
        First independently verified candidate or budget exhaustion.

    """
    return _run(
        HEURISTIC_ID,
        order_factory=lambda: heuristic.heuristic_order(
            CANDIDATE_COUNT,
            EVALUATION_BUDGET,
        ),
        verifier=verifier,
        clock_ns=clock_ns,
    )
