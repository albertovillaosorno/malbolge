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
#   - Paired timing protocol for the registered three-word heuristic runner.
# - Must-Not:
#   - Write evidence, discover provenance, filter samples, or alter schedules.
# - Allows:
#   - Inputs: frozen plan, trusted verifier, and monotonic nanosecond clock.
#   - Outputs: five retain-all baseline/heuristic pairs and canonical raw CSV.
#   - Side effects: invokes only the two registered runner strategy functions.
# - Split-When:
#   - Evidence persistence or a second heuristic timing policy gains ownership.
# - Merge-When:
#   - A shared harness owns this exact holdout timing protocol.
# - Summary:
#   - Time schedule construction plus full 50,000-evaluation verification.
# - Description:
#   - Fixed baseline-then-heuristic order retains every paired repetition.
# - Usage:
#   - Execute on real holdout only after this protocol is committed.
# - Defaults:
#   - Plan, clock, wall-bound, schedule, or evaluation-count drift fails closed.
#

"""Paired measurement harness for the three-word static heuristic."""

from __future__ import annotations

from collections.abc import Callable
import csv
from dataclasses import dataclass
from io import StringIO
import tomllib
from typing import Never
from typing import Protocol
from typing import cast

from algorithms.superoptimization import (
    initial_decode_heuristic_runner as runner,
)

MEASUREMENT_FORMAT_ID = "initial-decode-heuristic-five-paired-measurement-v1"
_EXPECTED_PROTOCOL_ID = "initial-decode-heuristic-five-paired-protocol-v1"
_EXPECTED_REPETITIONS = 5
_EXPECTED_WARMUPS = 0
_EXPECTED_ORDERING = "fixed-enumeration-then-heuristic"
_EXPECTED_OUTLIER_POLICY = "retain-all"
_EXPECTED_CENTER = "median"
_EXPECTED_DISPERSION = "observed-range"
_EXPECTED_UNCERTAINTY = "observed-range"
_EXPECTED_CLOCK = "time-perf-counter-ns"
_EXPECTED_TIMING_SCOPE = "schedule-construction-plus-full-budget-verification"
_EXPECTED_WALL_SECONDS = 60
_NANOSECONDS_PER_SECOND = 1_000_000_000

type _Strategy = Callable[
    [runner.CandidateVerifier],
    runner.HeuristicStrategyRun,
]


class _Clock(Protocol):
    def __call__(self) -> int: ...


class InvalidInitialDecodeHeuristicMeasurementPlanError(ValueError):
    """The heuristic plan no longer matches its registered timing protocol."""


class InvalidInitialDecodeHeuristicMeasurementError(RuntimeError):
    """One heuristic measurement violated the paired execution contract."""


@dataclass(frozen=True, slots=True)
class TimedHeuristicStrategy:
    """One full-budget strategy summary plus elapsed nanoseconds."""

    summary: runner.HeuristicStrategyRun
    elapsed_nanoseconds: int


@dataclass(frozen=True, slots=True)
class InitialDecodeHeuristicMeasurementPair:
    """One fixed-order natural-enumeration/static-heuristic pair."""

    baseline: TimedHeuristicStrategy
    heuristic: TimedHeuristicStrategy


@dataclass(frozen=True, slots=True)
class InitialDecodeHeuristicMeasurementSeries:
    """Every retained pair from the frozen measurement protocol."""

    format_id: str
    repetitions: tuple[InitialDecodeHeuristicMeasurementPair, ...]


def _plan_fail(message: str) -> Never:
    raise InvalidInitialDecodeHeuristicMeasurementPlanError(message)


def _measurement_fail(message: str) -> Never:
    raise InvalidInitialDecodeHeuristicMeasurementError(message)


def _measurement_table(plan_text: str) -> dict[str, object]:
    if type(plan_text) is not str:
        _plan_fail("initial-decode heuristic plan must use exact string text")
    try:
        parsed = cast("object", tomllib.loads(plan_text))
    except tomllib.TOMLDecodeError as error:
        _plan_fail(f"invalid initial-decode heuristic plan TOML: {error}")
    if not isinstance(parsed, dict):
        _plan_fail("initial-decode heuristic plan root must be a table")
    document = cast("dict[str, object]", parsed)
    value = document.get("measurement")
    if not isinstance(value, dict):
        _plan_fail("initial-decode heuristic measurement table is required")
    return cast("dict[str, object]", value)


def _require_protocol(plan_text: str) -> None:
    table = _measurement_table(plan_text)
    checks = (
        (table.get("id"), _EXPECTED_PROTOCOL_ID, "identity"),
        (table.get("repetitions"), _EXPECTED_REPETITIONS, "repetitions"),
        (table.get("warmup_iterations"), _EXPECTED_WARMUPS, "warmups"),
        (table.get("ordering"), _EXPECTED_ORDERING, "ordering"),
        (table.get("outlier_policy"), _EXPECTED_OUTLIER_POLICY, "outliers"),
        (table.get("center"), _EXPECTED_CENTER, "center"),
        (table.get("dispersion"), _EXPECTED_DISPERSION, "dispersion"),
        (table.get("uncertainty"), _EXPECTED_UNCERTAINTY, "uncertainty"),
        (table.get("clock"), _EXPECTED_CLOCK, "clock"),
        (table.get("timing_scope"), _EXPECTED_TIMING_SCOPE, "timing scope"),
        (
            table.get("per_strategy_wall_clock_seconds"),
            _EXPECTED_WALL_SECONDS,
            "wall bound",
        ),
    )
    for observed, expected, label in checks:
        if observed != expected:
            _plan_fail(
                f"initial-decode heuristic plan {label} differs from protocol"
            )


def _timed_strategy(
    strategy: _Strategy,
    verifier: runner.CandidateVerifier,
    clock_ns: _Clock,
) -> TimedHeuristicStrategy:
    start = clock_ns()
    summary = strategy(verifier)
    end = clock_ns()
    if type(start) is not int or type(end) is not int or end < start:
        _measurement_fail(
            "initial-decode heuristic clock must be monotonic exact integers"
        )
    elapsed = end - start
    if elapsed > _EXPECTED_WALL_SECONDS * _NANOSECONDS_PER_SECOND:
        _measurement_fail(
            "initial-decode heuristic exceeded preregistered wall bound"
        )
    if summary.evaluations != runner.EVALUATION_BUDGET:
        _measurement_fail(
            "initial-decode heuristic strategy lost fixed evaluation budget"
        )
    return TimedHeuristicStrategy(summary, elapsed)


def _require_pair(pair: InitialDecodeHeuristicMeasurementPair) -> None:
    if pair.baseline.summary.schedule_id != runner.BASELINE_ID:
        _measurement_fail("initial-decode heuristic baseline identity drifted")
    if pair.heuristic.summary.schedule_id != runner.HEURISTIC_ID:
        _measurement_fail("initial-decode heuristic schedule identity drifted")
    if pair.baseline.summary.evaluations != pair.heuristic.summary.evaluations:
        _measurement_fail("initial-decode heuristic paired budgets differ")


def run_preregistered_measurement(
    plan_text: str,
    *,
    verifier: runner.CandidateVerifier,
    clock_ns: _Clock,
) -> InitialDecodeHeuristicMeasurementSeries:
    """Run every fixed-order pair from the registered heuristic protocol.

    Returns:
        Five retain-all baseline-then-heuristic measurement pairs.

    """
    _require_protocol(plan_text)
    repetitions: list[InitialDecodeHeuristicMeasurementPair] = []
    for _ in range(_EXPECTED_REPETITIONS):
        baseline = _timed_strategy(
            runner.run_baseline_strategy,
            verifier,
            clock_ns,
        )
        heuristic = _timed_strategy(
            runner.run_heuristic_strategy,
            verifier,
            clock_ns,
        )
        pair = InitialDecodeHeuristicMeasurementPair(baseline, heuristic)
        _require_pair(pair)
        repetitions.append(pair)
    return InitialDecodeHeuristicMeasurementSeries(
        MEASUREMENT_FORMAT_ID,
        tuple(repetitions),
    )


def _optional(value: int | None) -> str:
    return "" if value is None else str(value)


def _row(
    repetition: int,
    timed: TimedHeuristicStrategy,
) -> tuple[str, ...]:
    summary = timed.summary
    return (
        str(repetition),
        summary.schedule_id,
        str(summary.evaluations),
        str(summary.verified_candidate_count),
        _optional(summary.first_verified_evaluation),
        _optional(summary.first_verified_candidate),
        _optional(summary.best_verified_candidate),
        _optional(summary.best_verified_quality),
        str(timed.elapsed_nanoseconds),
    )


def render_raw_csv(series: InitialDecodeHeuristicMeasurementSeries) -> str:
    """Render every retained heuristic pair as canonical CSV.

    Returns:
        Header plus two fixed-order rows for every repetition.

    """
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow((
        "repetition",
        "schedule_id",
        "evaluations",
        "verified_candidate_count",
        "first_verified_evaluation",
        "first_verified_candidate",
        "best_verified_candidate",
        "best_verified_quality",
        "elapsed_nanoseconds",
    ))
    for repetition, pair in enumerate(series.repetitions):
        writer.writerow(_row(repetition, pair.baseline))
        writer.writerow(_row(repetition, pair.heuristic))
    return output.getvalue()
