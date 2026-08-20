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
#   - Paired timing for the preregistered crazy-preimage comparison.
# - Must-Not:
#   - Write evidence, discover provenance, filter samples, or alter strategies.
# - Allows:
#   - Inputs: frozen plan, independent crazy oracle, and monotonic clock.
#   - Outputs: all retained paired samples and canonical raw CSV text.
#   - Side effects: executes only registered deterministic comparison
#     strategies.
# - Split-When:
#   - Evidence persistence or statistical inference gains independent policy.
# - Merge-When:
#   - A shared crazy-preimage experiment harness owns this exact protocol.
# - Summary:
#   - Execute the frozen five-pair exact-preimage pruning measurement.
# - Description:
#   - Measures full-domain then exact strategy runs without warmup or filtering.
# - Usage:
#   - Run only after this protocol and harness have been committed.
# - Defaults:
#   - Any protocol, clock, semantic, or wall-bound drift fails closed.
#

"""Paired retained measurement for exact classic crazy preimage pruning."""

from __future__ import annotations

from collections.abc import Callable
import csv
from dataclasses import dataclass
from io import StringIO
import tomllib
from typing import Never
from typing import Protocol
from typing import cast

from algorithms.superoptimization import crazy_preimage_runner

MEASUREMENT_FORMAT_ID = "crazy-preimage-five-paired-measurement-v1"
_EXPECTED_PROTOCOL_ID = "crazy-preimage-five-paired-protocol-v1"
_EXPECTED_REPETITIONS = 5
_EXPECTED_WARMUPS = 0
_EXPECTED_ORDERING = "fixed-full-domain-then-exact"
_EXPECTED_OUTLIER_POLICY = "retain-all"
_EXPECTED_CENTER = "median"
_EXPECTED_DISPERSION = "observed-range"
_EXPECTED_UNCERTAINTY = "observed-range"
_EXPECTED_CLOCK = "time-perf-counter-ns"
_EXPECTED_TIMING_SCOPE = "strategy-run-including-independent-semantic-check"
_EXPECTED_WALL_SECONDS = 60
_NANOSECONDS_PER_SECOND = 1_000_000_000

type _Strategy = Callable[
    [crazy_preimage_runner.CrazySemanticOracle],
    crazy_preimage_runner.CrazyPreimageStrategyRun,
]


class _Clock(Protocol):
    def __call__(self) -> int: ...


class InvalidCrazyPreimageMeasurementPlanError(ValueError):
    """The frozen plan no longer matches the measurement protocol."""


class InvalidCrazyPreimageMeasurementError(RuntimeError):
    """One attempted measurement violated the frozen execution contract."""


@dataclass(frozen=True, slots=True)
class TimedCrazyPreimageStrategy:
    """One retained structural summary plus paired elapsed time."""

    summary: crazy_preimage_runner.CrazyPreimageStrategyRun
    elapsed_nanoseconds: int


@dataclass(frozen=True, slots=True)
class CrazyPreimageMeasurementPair:
    """One fixed-order full-domain/exact repetition pair."""

    baseline: TimedCrazyPreimageStrategy
    exact: TimedCrazyPreimageStrategy


@dataclass(frozen=True, slots=True)
class CrazyPreimageMeasurementSeries:
    """Every retained repetition from the frozen paired protocol."""

    format_id: str
    repetitions: tuple[CrazyPreimageMeasurementPair, ...]


def _plan_fail(message: str) -> Never:
    raise InvalidCrazyPreimageMeasurementPlanError(message)


def _measurement_fail(message: str) -> Never:
    raise InvalidCrazyPreimageMeasurementError(message)


def _measurement_table(plan_text: str) -> dict[str, object]:
    if type(plan_text) is not str:
        _plan_fail("crazy preimage measurement plan must use exact string text")
    try:
        parsed = cast("object", tomllib.loads(plan_text))
    except tomllib.TOMLDecodeError as error:
        _plan_fail(f"invalid crazy preimage measurement plan TOML: {error}")
    if not isinstance(parsed, dict):
        _plan_fail("crazy preimage measurement plan root must be a table")
    document = cast("dict[str, object]", parsed)
    value = document.get("measurement")
    if not isinstance(value, dict):
        _plan_fail("crazy preimage measurement table is required")
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
                f"crazy preimage measurement plan {label} differs from protocol"
            )


def _timed_strategy(
    strategy: _Strategy,
    oracle: crazy_preimage_runner.CrazySemanticOracle,
    clock_ns: _Clock,
) -> TimedCrazyPreimageStrategy:
    start = clock_ns()
    summary = strategy(oracle)
    end = clock_ns()
    if type(start) is not int or type(end) is not int or end < start:
        _measurement_fail(
            "crazy preimage measurement clock must be monotonic exact integers"
        )
    elapsed = end - start
    if elapsed > _EXPECTED_WALL_SECONDS * _NANOSECONDS_PER_SECOND:
        _measurement_fail(
            "crazy preimage measurement exceeded preregistered wall bound"
        )
    return TimedCrazyPreimageStrategy(summary, elapsed)


def run_preregistered_measurement(
    plan_text: str,
    *,
    oracle: crazy_preimage_runner.CrazySemanticOracle,
    clock_ns: _Clock,
) -> CrazyPreimageMeasurementSeries:
    """Run every fixed-order pair from the preregistered protocol.

    Returns:
        Five retained full-domain/exact strategy pairs.

    """
    _require_protocol(plan_text)
    repetitions: list[CrazyPreimageMeasurementPair] = []
    for _ in range(_EXPECTED_REPETITIONS):
        baseline = _timed_strategy(
            crazy_preimage_runner.run_baseline_strategy,
            oracle,
            clock_ns,
        )
        exact = _timed_strategy(
            crazy_preimage_runner.run_exact_strategy,
            oracle,
            clock_ns,
        )
        if baseline.summary.semantic_sha256 != exact.summary.semantic_sha256:
            _measurement_fail(
                "crazy preimage measurement strategies disagree on semantics"
            )
        if baseline.summary.preimage_count != exact.summary.preimage_count:
            _measurement_fail(
                "crazy preimage measurement strategies disagree on cardinality"
            )
        repetitions.append(CrazyPreimageMeasurementPair(baseline, exact))
    return CrazyPreimageMeasurementSeries(
        MEASUREMENT_FORMAT_ID,
        tuple(repetitions),
    )


def _row(
    repetition: int,
    timed: TimedCrazyPreimageStrategy,
) -> tuple[str, ...]:
    summary = timed.summary
    return (
        str(repetition),
        summary.strategy_id,
        str(summary.evaluations),
        str(summary.preimage_count),
        summary.semantic_sha256,
        str(timed.elapsed_nanoseconds),
    )


def render_raw_csv(series: CrazyPreimageMeasurementSeries) -> str:
    """Render all retained paired samples as canonical CSV.

    Returns:
        Header plus two fixed-order rows for every retained repetition.

    """
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow((
        "repetition",
        "strategy_id",
        "evaluations",
        "preimage_count",
        "semantic_sha256",
        "elapsed_nanoseconds",
    ))
    for repetition, pair in enumerate(series.repetitions):
        writer.writerow(_row(repetition, pair.baseline))
        writer.writerow(_row(repetition, pair.exact))
    return output.getvalue()
