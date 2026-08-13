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
#   - Paired timing for the preregistered finite history comparison.
# - Must-Not:
#   - Write evidence, discover provenance, filter samples, or alter strategies.
# - Allows:
#   - Inputs: frozen history plan and caller-owned monotonic nanosecond clock.
#   - Outputs: all retained paired samples and canonical raw CSV text.
#   - Side effects: executes only registered deterministic history strategies.
# - Split-When:
#   - Evidence persistence or statistical inference gains independent policy.
# - Merge-When:
#   - A shared history experiment harness owns this exact protocol.
# - Summary:
#   - Execute the frozen five-pair history canonicalization measurement.
# - Description:
#   - Measures raw then canonical strategy runs without warmup or filtering.
# - Usage:
#   - Run only after this protocol and harness have been committed.
# - Defaults:
#   - Any protocol, clock, semantic, or wall-bound drift fails closed.
#

"""Paired retained measurement for history-residue canonicalization."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
import tomllib
from typing import Never
from typing import Protocol
from typing import cast

from src.research.algorithms.composition.algorithms.superoptimization import (
    history_runner,
)

MEASUREMENT_FORMAT_ID = "history-residue-five-paired-measurement-v1"
_EXPECTED_PROTOCOL_ID = "history-residue-five-paired-protocol-v1"
_EXPECTED_REPETITIONS = 5
_EXPECTED_WARMUPS = 0
_EXPECTED_ORDERING = "fixed-raw-then-canonicalized"
_EXPECTED_OUTLIER_POLICY = "retain-all"
_EXPECTED_CENTER = "median"
_EXPECTED_DISPERSION = "observed-range"
_EXPECTED_UNCERTAINTY = "observed-range"
_EXPECTED_CLOCK = "time-perf-counter-ns"
_EXPECTED_TIMING_SCOPE = "strategy-run-only"
_EXPECTED_WALL_SECONDS = 60
_NANOSECONDS_PER_SECOND = 1_000_000_000


class _Clock(Protocol):
    def __call__(self) -> int: ...


class InvalidHistoryMeasurementPlanError(ValueError):
    """The frozen plan no longer matches the measurement protocol."""


class InvalidHistoryMeasurementError(RuntimeError):
    """One attempted measurement violated the frozen execution contract."""


@dataclass(frozen=True, slots=True)
class TimedHistoryStrategy:
    """One retained strategy summary plus its paired elapsed time."""

    summary: history_runner.HistoryStrategySummary
    elapsed_nanoseconds: int


@dataclass(frozen=True, slots=True)
class HistoryMeasurementPair:
    """One fixed-order raw/canonicalized repetition pair."""

    baseline: TimedHistoryStrategy
    canonicalized: TimedHistoryStrategy


@dataclass(frozen=True, slots=True)
class HistoryMeasurementSeries:
    """Every retained repetition from the frozen paired protocol."""

    format_id: str
    repetitions: tuple[HistoryMeasurementPair, ...]


def _plan_fail(message: str) -> Never:
    raise InvalidHistoryMeasurementPlanError(message)


def _measurement_fail(message: str) -> Never:
    raise InvalidHistoryMeasurementError(message)


def _measurement_table(plan_text: str) -> dict[str, object]:
    if type(plan_text) is not str:
        _plan_fail("history measurement plan must use exact string text")
    try:
        parsed = cast("object", tomllib.loads(plan_text))
    except tomllib.TOMLDecodeError as error:
        _plan_fail(f"invalid history measurement plan TOML: {error}")
    if not isinstance(parsed, dict):
        _plan_fail("history measurement plan root must be a table")
    document = cast("dict[str, object]", parsed)
    value = document.get("measurement")
    if not isinstance(value, dict):
        _plan_fail("history measurement table is required")
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
            message = (
                f"history measurement plan {label} differs from protocol"
            )
            _plan_fail(message)


def _timed_strategy(strategy_id: str, clock_ns: _Clock) -> TimedHistoryStrategy:
    start = clock_ns()
    summary = history_runner.run_history_strategy(strategy_id)
    end = clock_ns()
    if type(start) is not int or type(end) is not int or end < start:
        message = "history measurement clock must be monotonic exact integers"
        _measurement_fail(message)
    elapsed = end - start
    wall_limit = _EXPECTED_WALL_SECONDS * _NANOSECONDS_PER_SECOND
    if elapsed > wall_limit:
        message = (
            "history measurement exceeded preregistered per-strategy wall bound"
        )
        _measurement_fail(message)
    return TimedHistoryStrategy(summary=summary, elapsed_nanoseconds=elapsed)


def run_preregistered_measurement(
    plan_text: str,
    *,
    clock_ns: _Clock,
) -> HistoryMeasurementSeries:
    """Run every fixed-order pair from the preregistered protocol.

    Returns:
        Five retained raw/canonicalized strategy pairs.

    """
    _require_protocol(plan_text)
    repetitions: list[HistoryMeasurementPair] = []
    for _ in range(_EXPECTED_REPETITIONS):
        baseline = _timed_strategy(
            history_runner.RAW_HISTORY_STATE_ID,
            clock_ns,
        )
        canonicalized = _timed_strategy(
            history_runner.CANONICAL_HISTORY_STATE_ID,
            clock_ns,
        )
        semantic_match = (
            baseline.summary.semantic_sha256
            == canonicalized.summary.semantic_sha256
        )
        if not semantic_match:
            message = (
                "history measurement strategies disagree on exact semantics"
            )
            _measurement_fail(message)
        repetitions.append(HistoryMeasurementPair(baseline, canonicalized))
    return HistoryMeasurementSeries(MEASUREMENT_FORMAT_ID, tuple(repetitions))


def _row(repetition: int, timed: TimedHistoryStrategy) -> tuple[str, ...]:
    summary = timed.summary
    return (
        str(repetition),
        summary.strategy_id,
        str(summary.unique_search_states),
        str(summary.generated_successors),
        str(summary.independent_verifier_calls),
        str(summary.peak_frontier_states),
        summary.semantic_sha256,
        str(timed.elapsed_nanoseconds),
    )


def render_raw_csv(series: HistoryMeasurementSeries) -> str:
    """Render all retained paired samples as canonical CSV.

    Returns:
        Header plus two fixed-order rows for every retained repetition.

    """
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow((
        "repetition",
        "strategy_id",
        "unique_search_states",
        "generated_successors",
        "independent_verifier_calls",
        "peak_frontier_states",
        "semantic_sha256",
        "elapsed_nanoseconds",
    ))
    for repetition, pair in enumerate(series.repetitions):
        writer.writerow(_row(repetition, pair.baseline))
        writer.writerow(_row(repetition, pair.canonicalized))
    return output.getvalue()
