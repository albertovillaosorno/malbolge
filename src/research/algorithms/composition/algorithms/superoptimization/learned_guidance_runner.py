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
#   - Equal-budget stop-on-first static-versus-learned comparison runner.
# - Must-Not:
#   - Define verifier semantics, alter orders from outcomes, or write evidence.
# - Allows:
#   - Inputs: one trusted holdout verifier callback and monotonic clock.
#   - Outputs: first-hit work plus separated training/search/end-to-end timing.
#   - Side effects: invokes training fit and the caller-supplied verifier.
# - Split-When:
#   - Another learned stopping/timing policy gains independent identity.
# - Merge-When:
#   - A shared learned-search runner owns this exact protocol.
# - Summary:
#   - Compare static and training-only learned schedules through one verifier.
# - Description:
#   - Learned end-to-end time includes fit from scratch on every repetition.
# - Usage:
#   - Execute only after plan/model/baseline/runner registration.
# - Defaults:
#   - Malformed quality, clock, or schedule cardinality fails closed.
#

"""Verifier-gated runner for training-only learned guidance."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from algorithms.superoptimization import learned_guidance as guidance

COMPARISON_ID: Final = "classic-four-word-training-only-guidance-comparison-v1"
_MAX_QUALITY: Final = 4

type CandidateVerifier = Callable[[int], int | None]
type MonotonicClock = Callable[[], int]


class LearnedGuidanceComparisonError(ValueError):
    """The learned-guidance comparison violated its frozen contract."""


@dataclass(frozen=True, slots=True)
class _SearchConfig:
    order: tuple[int, ...]
    strategy_id: str
    start_nanoseconds: int
    phase_start_nanoseconds: int
    training_nanoseconds: int


@dataclass(frozen=True, slots=True)
class FirstHitRun:
    """One deterministic stop-on-first strategy result."""

    strategy_id: str
    evaluations: int
    candidate: int | None
    quality: int | None
    training_nanoseconds: int
    schedule_and_search_nanoseconds: int
    end_to_end_nanoseconds: int


def _clock(clock_ns: MonotonicClock) -> int:
    value = clock_ns()
    if type(value) is not int or value < 0:
        message = "learned-guidance clock must return a non-negative integer"
        raise LearnedGuidanceComparisonError(message)
    return value


def _quality(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int or not 1 <= value <= _MAX_QUALITY:
        message = "learned-guidance verifier quality is malformed"
        raise LearnedGuidanceComparisonError(message)
    return value


def _require_order(order: tuple[int, ...]) -> None:
    if (
        len(order) != guidance.EVALUATION_BUDGET
        or len(set(order)) != len(order)
    ):
        message = "learned-guidance schedule lost fixed-budget uniqueness"
        raise LearnedGuidanceComparisonError(message)


def _search(
    config: _SearchConfig,
    verifier: CandidateVerifier,
    clock_ns: MonotonicClock,
) -> FirstHitRun:
    _require_order(config.order)
    candidate_hit: int | None = None
    quality_hit: int | None = None
    evaluations = 0
    for candidate in config.order:
        evaluations += 1
        quality = _quality(verifier(candidate))
        if quality is not None:
            candidate_hit = candidate
            quality_hit = quality
            break
    end = _clock(clock_ns)
    if end < config.phase_start_nanoseconds:
        message = "learned-guidance clock moved backwards"
        raise LearnedGuidanceComparisonError(message)
    return FirstHitRun(
        config.strategy_id,
        evaluations,
        candidate_hit,
        quality_hit,
        config.training_nanoseconds,
        end - config.phase_start_nanoseconds,
        end - config.start_nanoseconds,
    )


def run_static(
    verifier: CandidateVerifier,
    clock_ns: MonotonicClock,
) -> FirstHitRun:
    """Run the non-learned static baseline to first hit or budget.

    Returns:
        Verifier-gated first-hit or exhausted baseline result.

    """
    start = _clock(clock_ns)
    order = guidance.static_order()
    config = _SearchConfig(
        order,
        guidance.STATIC_ORDER_ID,
        start,
        start,
        0,
    )
    return _search(config, verifier, clock_ns)


def run_learned(
    verifier: CandidateVerifier,
    clock_ns: MonotonicClock,
) -> FirstHitRun:
    """Fit from scratch, then run learned guidance to first hit or budget.

    Returns:
        Verifier-gated first-hit or exhausted learned result with fit timing.

    Raises:
        LearnedGuidanceComparisonError: If the monotonic clock regresses.

    """
    start = _clock(clock_ns)
    model = guidance.fit_model()
    fit_end = _clock(clock_ns)
    if fit_end < start:
        message = "learned-guidance clock moved backwards"
        raise LearnedGuidanceComparisonError(message)
    order = guidance.learned_order(model)
    config = _SearchConfig(
        order,
        guidance.LEARNED_ORDER_ID,
        start,
        fit_end,
        fit_end - start,
    )
    return _search(config, verifier, clock_ns)
