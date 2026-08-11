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
#   - Equal-budget verifier-gated comparison over opaque finite candidates.
# - Must-Not:
#   - Define candidate semantics, trust schedules as acceptance, or claim
#     timing.
# - Allows:
#   - Inputs: finite dimensions, seed, and one deterministic trusted verifier.
#   - Outputs: evaluation-count, first-hit, best-quality, and null outcomes.
#   - Side effects: invokes only the caller-supplied verifier callback.
# - Split-When:
#   - Candidate-language semantics or measured-run evidence gains ownership.
# - Merge-When:
#   - A shared research execution harness owns this exact comparison contract.
# - Summary:
#   - Deterministic equal-budget superoptimization comparison substrate.
# - Description:
#   - Applies one trusted verifier to enumeration and seeded candidate orders.
# - Usage:
#   - Research pilots may bind concrete candidate semantics above this module.
# - Defaults:
#   - Invalid verifier quality results fail closed and no timing is inferred.
#

"""Verifier-gated equal-budget substrate for superoptimization research."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
from typing import Protocol
from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from collections.abc import Callable


class _ScheduleModule(Protocol):
    ENUMERATION_SCHEDULE_ID: str
    SEEDED_PROPOSAL_SCHEDULE_ID: str

    def enumeration_order(
        self,
        candidate_count: int,
        evaluation_budget: int,
    ) -> tuple[int, ...]: ...

    def seeded_proposal_order(
        self,
        candidate_count: int,
        evaluation_budget: int,
        seed: int,
    ) -> tuple[int, ...]: ...


def _load_schedule() -> _ScheduleModule:
    path = Path(__file__).with_name("schedule.py")
    spec = importlib.util.spec_from_file_location(
        "superoptimization_runner_schedule",
        path,
    )
    if spec is None or spec.loader is None:
        message = "superoptimization schedule module cannot be loaded"
        raise RuntimeError(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return cast("_ScheduleModule", cast("object", module))


_SCHEDULE = _load_schedule()

_MAX_U64 = (1 << 64) - 1
_OUTCOME_FOUND = "verified-candidate-found"
_OUTCOME_NONE = "no-verified-candidate"
VERIFIER_GATED_COMPARISON_ID = "finite-verifier-gated-comparison-v1"
BOUNDED_COMPARISON_ID = "finite-verifier-gated-dual-bound-comparison-v1"
_STOP_EVALUATION = "evaluation-budget"
_STOP_CORPUS = "candidate-corpus-exhausted"
_STOP_WALL_CLOCK = "wall-clock-budget"

type CandidateVerifier = Callable[[int], int | None]
type MonotonicClock = Callable[[], int]


class InvalidVerifierResultError(ValueError):
    """One trusted verifier callback returned a malformed quality result."""


class InvalidComparisonClockError(ValueError):
    """The bounded comparison clock or wall-clock budget is malformed."""


@dataclass(frozen=True, slots=True)
class ScheduleRun:
    """Deterministic result of one complete budget-bounded schedule run."""

    schedule_id: str
    evaluations: int
    verified_count: int
    first_verified_evaluation: int | None
    first_verified_candidate: int | None
    best_candidate: int | None
    best_quality: int | None
    outcome: str


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    """Equal-input enumeration and seeded proposal results."""

    comparison_id: str
    candidate_count: int
    evaluation_budget: int
    seed: int
    enumeration: ScheduleRun
    seeded: ScheduleRun


@dataclass(frozen=True, slots=True)
class BoundedScheduleRun:
    """One schedule result plus exact harness stopping-bound evidence."""

    result: ScheduleRun
    elapsed_nanoseconds: int
    first_verified_elapsed_nanoseconds: int | None
    stop_reason: str


@dataclass(frozen=True, slots=True)
class BoundedComparisonResult:
    """Equal-input dual-bound enumeration and seeded proposal results."""

    comparison_id: str
    candidate_count: int
    evaluation_budget: int
    wall_clock_budget_nanoseconds: int
    seed: int
    enumeration: BoundedScheduleRun
    seeded: BoundedScheduleRun


@dataclass(frozen=True, slots=True)
class BoundedComparisonRequest:
    """Shared finite candidate, evaluation, wall-clock, and seed bounds."""

    candidate_count: int
    evaluation_budget: int
    wall_clock_budget_nanoseconds: int
    seed: int


@dataclass(frozen=True, slots=True)
class _BoundedRunConfig:
    schedule_id: str
    wall_clock_budget_nanoseconds: int
    default_stop_reason: str


@dataclass(slots=True)
class _BoundedRunState:
    start_nanoseconds: int
    previous_nanoseconds: int
    stop_reason: str
    evaluations: int = 0
    verified_count: int = 0
    first_verified_evaluation: int | None = None
    first_verified_candidate: int | None = None
    first_verified_elapsed_nanoseconds: int | None = None
    best_candidate: int | None = None
    best_quality: int | None = None

    def record_verified(
        self,
        candidate: int,
        quality: int | None,
        elapsed_nanoseconds: int,
    ) -> None:
        """Record one verifier result without granting verifier authority."""
        if quality is None:
            return
        self.verified_count += 1
        if self.first_verified_evaluation is None:
            self.first_verified_evaluation = self.evaluations
            self.first_verified_candidate = candidate
            self.first_verified_elapsed_nanoseconds = elapsed_nanoseconds
        if self.best_quality is None or quality < self.best_quality:
            self.best_candidate = candidate
            self.best_quality = quality

    def finish(self, schedule_id: str) -> BoundedScheduleRun:
        """Freeze this bounded state into one schedule result.

        Returns:
            Immutable bounded schedule result.

        """
        result = ScheduleRun(
            schedule_id=schedule_id,
            evaluations=self.evaluations,
            verified_count=self.verified_count,
            first_verified_evaluation=self.first_verified_evaluation,
            first_verified_candidate=self.first_verified_candidate,
            best_candidate=self.best_candidate,
            best_quality=self.best_quality,
            outcome=(
                _OUTCOME_FOUND if self.verified_count else _OUTCOME_NONE
            ),
        )
        return BoundedScheduleRun(
            result=result,
            elapsed_nanoseconds=(
                self.previous_nanoseconds - self.start_nanoseconds
            ),
            first_verified_elapsed_nanoseconds=(
                self.first_verified_elapsed_nanoseconds
            ),
            stop_reason=self.stop_reason,
        )


def _verified_quality(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int or not 0 <= value <= _MAX_U64:
        message = "trusted verifier quality must be an unsigned 64-bit integer"
        raise InvalidVerifierResultError(message)
    return value


def _run_schedule(
    order: tuple[int, ...],
    schedule_id: str,
    verifier: CandidateVerifier,
) -> ScheduleRun:
    verified_count = 0
    first_evaluation: int | None = None
    first_candidate: int | None = None
    best_candidate: int | None = None
    best_quality: int | None = None
    for evaluation, candidate in enumerate(order, start=1):
        quality = _verified_quality(verifier(candidate))
        if quality is None:
            continue
        verified_count += 1
        if first_evaluation is None:
            first_evaluation = evaluation
            first_candidate = candidate
        if best_quality is None or quality < best_quality:
            best_candidate = candidate
            best_quality = quality
    return ScheduleRun(
        schedule_id=schedule_id,
        evaluations=len(order),
        verified_count=verified_count,
        first_verified_evaluation=first_evaluation,
        first_verified_candidate=first_candidate,
        best_candidate=best_candidate,
        best_quality=best_quality,
        outcome=_OUTCOME_FOUND if verified_count else _OUTCOME_NONE,
    )


def compare_schedules(
    candidate_count: int,
    evaluation_budget: int,
    seed: int,
    *,
    verifier: CandidateVerifier,
) -> ComparisonResult:
    """Run both preregistered candidate orders through one trusted verifier.

    Returns:
        Equal-input evaluation-count and verified-quality results for both
        schedules. Every scheduled candidate is evaluated so best-quality and
        null outcomes are retained independently from time-to-first evidence.

    """
    enumeration = _SCHEDULE.enumeration_order(
        candidate_count,
        evaluation_budget,
    )
    seeded = _SCHEDULE.seeded_proposal_order(
        candidate_count,
        evaluation_budget,
        seed,
    )
    return ComparisonResult(
        comparison_id=VERIFIER_GATED_COMPARISON_ID,
        candidate_count=candidate_count,
        evaluation_budget=evaluation_budget,
        seed=seed,
        enumeration=_run_schedule(
            enumeration,
            _SCHEDULE.ENUMERATION_SCHEDULE_ID,
            verifier,
        ),
        seeded=_run_schedule(
            seeded,
            _SCHEDULE.SEEDED_PROPOSAL_SCHEDULE_ID,
            verifier,
        ),
    )


def _clock_value(clock_ns: MonotonicClock) -> int:
    value = clock_ns()
    if type(value) is not int or value < 0:
        message = "comparison clock must return a non-negative exact integer"
        raise InvalidComparisonClockError(message)
    return value


def _elapsed_from_clock(
    state: _BoundedRunState,
    clock_ns: MonotonicClock,
) -> int:
    now = _clock_value(clock_ns)
    if now < state.previous_nanoseconds:
        message = "comparison clock moved backwards"
        raise InvalidComparisonClockError(message)
    state.previous_nanoseconds = now
    return now - state.start_nanoseconds


def _bounded_schedule_run(
    order: tuple[int, ...],
    config: _BoundedRunConfig,
    *,
    verifier: CandidateVerifier,
    clock_ns: MonotonicClock,
) -> BoundedScheduleRun:
    start = _clock_value(clock_ns)
    state = _BoundedRunState(start, start, config.default_stop_reason)
    for candidate in order:
        before = _elapsed_from_clock(state, clock_ns)
        if before >= config.wall_clock_budget_nanoseconds:
            state.stop_reason = _STOP_WALL_CLOCK
            break
        quality = _verified_quality(verifier(candidate))
        state.evaluations += 1
        after = _elapsed_from_clock(state, clock_ns)
        state.record_verified(candidate, quality, after)
        if after >= config.wall_clock_budget_nanoseconds:
            state.stop_reason = _STOP_WALL_CLOCK
            break
    return state.finish(config.schedule_id)


def _positive_wall_clock_budget(value: object) -> int:
    if type(value) is not int or value <= 0 or value > _MAX_U64:
        message = "wall-clock budget must be a positive unsigned 64-bit integer"
        raise InvalidComparisonClockError(message)
    return value


def _bounded_request(
    request: BoundedComparisonRequest,
) -> BoundedComparisonRequest:
    wall_budget = _positive_wall_clock_budget(
        request.wall_clock_budget_nanoseconds
    )
    return BoundedComparisonRequest(
        candidate_count=request.candidate_count,
        evaluation_budget=request.evaluation_budget,
        wall_clock_budget_nanoseconds=wall_budget,
        seed=request.seed,
    )


def _default_stop_reason(request: BoundedComparisonRequest) -> str:
    if request.candidate_count <= request.evaluation_budget:
        return _STOP_CORPUS
    return _STOP_EVALUATION


def compare_schedules_bounded(
    request: BoundedComparisonRequest,
    *,
    verifier: CandidateVerifier,
    clock_ns: MonotonicClock,
) -> BoundedComparisonResult:
    """Run both schedules under equal evaluation and wall-clock bounds.

    Returns:
        Per-schedule verifier evidence, elapsed time, and stopping-bound
        identity. Wall-clock checks occur between synchronous verifier calls;
        this function does not preempt a verifier callback that fails to return.

    """
    admitted = _bounded_request(request)
    enumeration = _SCHEDULE.enumeration_order(
        admitted.candidate_count,
        admitted.evaluation_budget,
    )
    seeded = _SCHEDULE.seeded_proposal_order(
        admitted.candidate_count,
        admitted.evaluation_budget,
        admitted.seed,
    )
    default_stop = _default_stop_reason(admitted)
    enumeration_config = _BoundedRunConfig(
        schedule_id=_SCHEDULE.ENUMERATION_SCHEDULE_ID,
        wall_clock_budget_nanoseconds=(
            admitted.wall_clock_budget_nanoseconds
        ),
        default_stop_reason=default_stop,
    )
    seeded_config = _BoundedRunConfig(
        schedule_id=_SCHEDULE.SEEDED_PROPOSAL_SCHEDULE_ID,
        wall_clock_budget_nanoseconds=(
            admitted.wall_clock_budget_nanoseconds
        ),
        default_stop_reason=default_stop,
    )
    return BoundedComparisonResult(
        comparison_id=BOUNDED_COMPARISON_ID,
        candidate_count=admitted.candidate_count,
        evaluation_budget=admitted.evaluation_budget,
        wall_clock_budget_nanoseconds=admitted.wall_clock_budget_nanoseconds,
        seed=admitted.seed,
        enumeration=_bounded_schedule_run(
            enumeration,
            enumeration_config,
            verifier=verifier,
            clock_ns=clock_ns,
        ),
        seeded=_bounded_schedule_run(
            seeded,
            seeded_config,
            verifier=verifier,
            clock_ns=clock_ns,
        ),
    )
