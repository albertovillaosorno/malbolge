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
#   - Paired timing protocol for the registered verified-block-reuse runner.
# - Must-Not:
#   - Write evidence, discover provenance, persist cache state, or open results.
# - Allows:
#   - Inputs: frozen plan, trusted verifier, and monotonic nanosecond clock.
#   - Outputs: retain-all paired samples and canonical raw CSV text.
#   - Side effects: invokes only the two registered deterministic strategies.
# - Split-When:
#   - Evidence persistence or statistical interpretation gains separate policy.
# - Merge-When:
#   - A shared reuse harness owns this exact paired protocol.
# - Summary:
#   - Freeze five baseline-then-reuse repetitions before real timing.
# - Description:
#   - Requires complete request-quality-map equality in every retained pair.
# - Usage:
#   - Execute only after this protocol and harness have been committed.
# - Defaults:
#   - Protocol, clock, map, or wall-bound drift fails closed.
#

"""Paired measurement harness for exact verified-result reuse."""

from __future__ import annotations

from collections.abc import Callable
import csv
from dataclasses import dataclass
from io import StringIO
import tomllib
from typing import Never
from typing import Protocol
from typing import cast

from algorithms.superoptimization import verified_block_reuse_runner as runner

MEASUREMENT_FORMAT_ID = "verified-block-reuse-five-paired-measurement-v1"
_EXPECTED_PROTOCOL_ID = "verified-block-reuse-five-paired-protocol-v1"
_EXPECTED_REPETITIONS = 5
_EXPECTED_WARMUPS = 0
_EXPECTED_ORDERING = "fixed-per-request-then-exact-reuse"
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
    runner.VerifiedBlockReuseStrategyRun,
]


class _Clock(Protocol):
    def __call__(self) -> int: ...


class InvalidVerifiedBlockReuseMeasurementPlanError(ValueError):
    """The frozen reuse plan no longer matches the timing protocol."""


class InvalidVerifiedBlockReuseMeasurementError(RuntimeError):
    """One attempted reuse measurement violated the execution contract."""


@dataclass(frozen=True, slots=True)
class TimedVerifiedBlockReuseStrategy:
    """One retained structural summary plus paired elapsed time."""

    summary: runner.VerifiedBlockReuseStrategyRun
    elapsed_nanoseconds: int


@dataclass(frozen=True, slots=True)
class VerifiedBlockReuseMeasurementPair:
    """One fixed-order per-request/reuse repetition pair."""

    baseline: TimedVerifiedBlockReuseStrategy
    reused: TimedVerifiedBlockReuseStrategy


@dataclass(frozen=True, slots=True)
class VerifiedBlockReuseMeasurementSeries:
    """Every retained repetition from the frozen paired protocol."""

    format_id: str
    repetitions: tuple[VerifiedBlockReuseMeasurementPair, ...]


def _plan_fail(message: str) -> Never:
    raise InvalidVerifiedBlockReuseMeasurementPlanError(message)


def _measurement_fail(message: str) -> Never:
    raise InvalidVerifiedBlockReuseMeasurementError(message)


def _measurement_table(plan_text: str) -> dict[str, object]:
    if type(plan_text) is not str:
        _plan_fail("verified-block-reuse plan must use exact string text")
    try:
        parsed = cast("object", tomllib.loads(plan_text))
    except tomllib.TOMLDecodeError as error:
        _plan_fail(f"invalid verified-block-reuse plan TOML: {error}")
    if not isinstance(parsed, dict):
        _plan_fail("verified-block-reuse plan root must be a table")
    document = cast("dict[str, object]", parsed)
    value = document.get("measurement")
    if not isinstance(value, dict):
        _plan_fail("verified-block-reuse measurement table is required")
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
                f"verified-block-reuse plan {label} differs from protocol"
            )


def _timed_strategy(
    strategy: _Strategy,
    verifier: runner.CandidateVerifier,
    clock_ns: _Clock,
) -> TimedVerifiedBlockReuseStrategy:
    start = clock_ns()
    summary = strategy(verifier)
    end = clock_ns()
    if type(start) is not int or type(end) is not int or end < start:
        _measurement_fail(
            "verified-block-reuse clock must be monotonic exact integers"
        )
    elapsed = end - start
    if elapsed > _EXPECTED_WALL_SECONDS * _NANOSECONDS_PER_SECOND:
        _measurement_fail(
            "verified-block-reuse exceeded preregistered wall bound"
        )
    return TimedVerifiedBlockReuseStrategy(summary, elapsed)


def _require_pair_equality(pair: VerifiedBlockReuseMeasurementPair) -> None:
    baseline = pair.baseline.summary
    reused = pair.reused.summary
    if baseline.quality_map != reused.quality_map:
        _measurement_fail("verified-block-reuse strategies disagree on map")
    if baseline.quality_map_sha256 != reused.quality_map_sha256:
        _measurement_fail("verified-block-reuse strategy map digests disagree")
    if baseline.request_count != reused.request_count:
        _measurement_fail("verified-block-reuse request counts disagree")
    if (
        reused.independent_verifier_calls
        >= baseline.independent_verifier_calls
    ):
        _measurement_fail(
            "verified-block-reuse verifier calls did not decrease"
        )


def run_preregistered_measurement(
    plan_text: str,
    *,
    verifier: runner.CandidateVerifier,
    clock_ns: _Clock,
) -> VerifiedBlockReuseMeasurementSeries:
    """Run every fixed-order pair from the preregistered protocol.

    Returns:
        Five retained per-request/reuse strategy pairs.

    """
    _require_protocol(plan_text)
    repetitions: list[VerifiedBlockReuseMeasurementPair] = []
    for _ in range(_EXPECTED_REPETITIONS):
        baseline = _timed_strategy(
            runner.run_baseline_strategy,
            verifier,
            clock_ns,
        )
        reused = _timed_strategy(
            runner.run_reuse_strategy,
            verifier,
            clock_ns,
        )
        pair = VerifiedBlockReuseMeasurementPair(baseline, reused)
        _require_pair_equality(pair)
        repetitions.append(pair)
    return VerifiedBlockReuseMeasurementSeries(
        MEASUREMENT_FORMAT_ID,
        tuple(repetitions),
    )


def _row(
    repetition: int,
    timed: TimedVerifiedBlockReuseStrategy,
) -> tuple[str, ...]:
    summary = timed.summary
    best_quality = "" if summary.best_verified_quality is None else str(
        summary.best_verified_quality
    )
    return (
        str(repetition),
        summary.strategy_id,
        str(summary.request_count),
        str(summary.unique_candidate_count),
        str(summary.independent_verifier_calls),
        str(summary.reused_request_count),
        str(summary.accepted_request_count),
        best_quality,
        summary.quality_map_sha256,
        str(timed.elapsed_nanoseconds),
    )


def render_raw_csv(series: VerifiedBlockReuseMeasurementSeries) -> str:
    """Render every retained paired sample as canonical CSV.

    Returns:
        Header plus two fixed-order rows for every retained repetition.

    """
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow((
        "repetition",
        "strategy_id",
        "request_count",
        "unique_candidate_count",
        "independent_verifier_calls",
        "reused_request_count",
        "accepted_request_count",
        "best_verified_quality",
        "quality_map_sha256",
        "elapsed_nanoseconds",
    ))
    for repetition, pair in enumerate(series.repetitions):
        writer.writerow(_row(repetition, pair.baseline))
        writer.writerow(_row(repetition, pair.reused))
    return output.getvalue()
