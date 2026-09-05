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
#   - Paired timing protocol for the registered prefix-decomposition runner.
# - Must-Not:
#   - Write evidence, discover provenance, alter proof classes, or open results.
# - Allows:
#   - Inputs: frozen plan, trusted verifier, and monotonic nanosecond clock.
#   - Outputs: retain-all paired samples and canonical raw CSV text.
#   - Side effects: invokes only the two registered deterministic strategies.
# - Split-When:
#   - Evidence persistence or statistical interpretation gains separate policy.
# - Merge-When:
#   - A shared decomposition harness owns this exact paired protocol.
# - Summary:
#   - Freeze five baseline-then-decomposed repetitions before real timing.
# - Description:
#   - Requires complete quality-map equality in every retained pair.
# - Usage:
#   - Execute only after this protocol and harness have been committed.
# - Defaults:
#   - Protocol, clock, map, or wall-bound drift fails closed.
#

"""Paired measurement harness for exact classic prefix decomposition."""

from __future__ import annotations

from collections.abc import Callable
import csv
from dataclasses import dataclass
from io import StringIO
import tomllib
from typing import Never
from typing import Protocol
from typing import cast

from algorithms.superoptimization import prefix_decomposition_runner as runner

MEASUREMENT_FORMAT_ID = "prefix-decomposition-five-paired-measurement-v1"
_EXPECTED_PROTOCOL_ID = "prefix-decomposition-five-paired-protocol-v1"
_EXPECTED_REPETITIONS = 5
_EXPECTED_WARMUPS = 0
_EXPECTED_ORDERING = "fixed-full-verification-then-decomposed"
_EXPECTED_OUTLIER_POLICY = "retain-all"
_EXPECTED_CENTER = "median"
_EXPECTED_DISPERSION = "observed-range"
_EXPECTED_UNCERTAINTY = "observed-range"
_EXPECTED_CLOCK = "time-perf-counter-ns"
_EXPECTED_TIMING_SCOPE = "strategy-run-only"
_EXPECTED_WALL_SECONDS = 60
_NANOSECONDS_PER_SECOND = 1_000_000_000

type _Strategy = Callable[
    [runner.CandidateVerifier],
    runner.PrefixDecompositionStrategyRun,
]


class _Clock(Protocol):
    def __call__(self) -> int: ...


class InvalidPrefixDecompositionMeasurementPlanError(ValueError):
    """The frozen plan no longer matches the registered timing protocol."""


class InvalidPrefixDecompositionMeasurementError(RuntimeError):
    """One attempted measurement violated the frozen execution contract."""


@dataclass(frozen=True, slots=True)
class TimedPrefixDecompositionStrategy:
    """One structural strategy summary plus paired elapsed time."""

    summary: runner.PrefixDecompositionStrategyRun
    elapsed_nanoseconds: int


@dataclass(frozen=True, slots=True)
class PrefixDecompositionMeasurementPair:
    """One fixed-order full-verification/decomposed repetition pair."""

    baseline: TimedPrefixDecompositionStrategy
    decomposed: TimedPrefixDecompositionStrategy


@dataclass(frozen=True, slots=True)
class PrefixDecompositionMeasurementSeries:
    """Every retained repetition from the frozen paired protocol."""

    format_id: str
    repetitions: tuple[PrefixDecompositionMeasurementPair, ...]


def _plan_fail(message: str) -> Never:
    raise InvalidPrefixDecompositionMeasurementPlanError(message)


def _measurement_fail(message: str) -> Never:
    raise InvalidPrefixDecompositionMeasurementError(message)


def _measurement_table(plan_text: str) -> dict[str, object]:
    if type(plan_text) is not str:
        _plan_fail("prefix decomposition plan must use exact string text")
    try:
        parsed = cast("object", tomllib.loads(plan_text))
    except tomllib.TOMLDecodeError as error:
        _plan_fail(f"invalid prefix decomposition plan TOML: {error}")
    if not isinstance(parsed, dict):
        _plan_fail("prefix decomposition plan root must be a table")
    document = cast("dict[str, object]", parsed)
    value = document.get("measurement")
    if not isinstance(value, dict):
        _plan_fail("prefix decomposition measurement table is required")
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
                f"prefix decomposition plan {label} differs from protocol"
            )


def _timed_strategy(
    strategy: _Strategy,
    verifier: runner.CandidateVerifier,
    clock_ns: _Clock,
) -> TimedPrefixDecompositionStrategy:
    start = clock_ns()
    summary = strategy(verifier)
    end = clock_ns()
    if type(start) is not int or type(end) is not int or end < start:
        _measurement_fail(
            "prefix decomposition clock must be monotonic exact integers"
        )
    elapsed = end - start
    wall_limit = _EXPECTED_WALL_SECONDS * _NANOSECONDS_PER_SECOND
    if elapsed > wall_limit:
        _measurement_fail(
            "prefix decomposition exceeded preregistered wall bound"
        )
    return TimedPrefixDecompositionStrategy(summary, elapsed)


def _require_pair_equality(pair: PrefixDecompositionMeasurementPair) -> None:
    baseline = pair.baseline.summary
    decomposed = pair.decomposed.summary
    if baseline.quality_map != decomposed.quality_map:
        _measurement_fail(
            "prefix decomposition strategies disagree on quality map"
        )
    if baseline.quality_map_sha256 != decomposed.quality_map_sha256:
        _measurement_fail("prefix decomposition strategy map digests disagree")
    if baseline.candidate_count != decomposed.candidate_count:
        _measurement_fail("prefix decomposition candidate counts disagree")
    if (
        decomposed.independent_verifier_calls
        >= baseline.independent_verifier_calls
    ):
        _measurement_fail(
            "prefix decomposition verifier calls did not decrease"
        )


def run_preregistered_measurement(
    plan_text: str,
    *,
    verifier: runner.CandidateVerifier,
    clock_ns: _Clock,
) -> PrefixDecompositionMeasurementSeries:
    """Run every fixed-order pair from the preregistered protocol.

    Returns:
        Five retained full-verification/decomposed strategy pairs.

    """
    _require_protocol(plan_text)
    repetitions: list[PrefixDecompositionMeasurementPair] = []
    for _ in range(_EXPECTED_REPETITIONS):
        baseline = _timed_strategy(
            runner.run_baseline_strategy,
            verifier,
            clock_ns,
        )
        decomposed = _timed_strategy(
            runner.run_decomposed_strategy,
            verifier,
            clock_ns,
        )
        pair = PrefixDecompositionMeasurementPair(baseline, decomposed)
        _require_pair_equality(pair)
        repetitions.append(pair)
    return PrefixDecompositionMeasurementSeries(
        MEASUREMENT_FORMAT_ID,
        tuple(repetitions),
    )


def _row(
    repetition: int,
    timed: TimedPrefixDecompositionStrategy,
) -> tuple[str, ...]:
    summary = timed.summary
    best_quality = "" if summary.best_verified_quality is None else str(
        summary.best_verified_quality
    )
    return (
        str(repetition),
        summary.strategy_id,
        str(summary.candidate_count),
        str(summary.independent_verifier_calls),
        str(summary.full_candidate_verifications),
        str(summary.structurally_discharged_candidates),
        str(summary.accepted_candidate_count),
        best_quality,
        summary.quality_map_sha256,
        str(timed.elapsed_nanoseconds),
    )


def render_raw_csv(series: PrefixDecompositionMeasurementSeries) -> str:
    """Render every retained paired sample as canonical CSV.

    Returns:
        Header plus two fixed-order rows for every retained repetition.

    """
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow((
        "repetition",
        "strategy_id",
        "candidate_count",
        "independent_verifier_calls",
        "full_candidate_verifications",
        "structurally_discharged_candidates",
        "accepted_candidate_count",
        "best_verified_quality",
        "quality_map_sha256",
        "elapsed_nanoseconds",
    ))
    for repetition, pair in enumerate(series.repetitions):
        writer.writerow(_row(repetition, pair.baseline))
        writer.writerow(_row(repetition, pair.decomposed))
    return output.getvalue()
