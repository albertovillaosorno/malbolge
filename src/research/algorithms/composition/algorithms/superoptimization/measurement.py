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
#   - Repeated in-memory measurement for the preregistered classic pilot.
# - Must-Not:
#   - Write evidence, discover provenance, filter samples, or change search
#     order.
# - Allows:
#   - Inputs: frozen plan text and one caller-owned monotonic nanosecond clock.
#   - Outputs: retained comparison repetitions and canonical raw CSV text.
#   - Side effects: invokes the concrete pilot verifier during explicit
#     execution.
# - Split-When:
#   - Evidence persistence or statistical inference gains independent policy.
# - Merge-When:
#   - A shared experiment harness owns this exact retained-sample contract.
# - Summary:
#   - Execute and serialize the frozen five-repetition superoptimization pilot.
# - Description:
#   - Preserves every schedule result without warmup or outlier deletion.
# - Usage:
#   - Run only after the measurement extension has been committed.
# - Defaults:
#   - Rendering is pure and never claims a performance conclusion.
#

"""Retained measurements for the preregistered superoptimization pilot."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
import tomllib
from typing import Never
from typing import Protocol
from typing import cast

from src.research.algorithms.composition.algorithms.superoptimization import (
    pilot,
)

MEASUREMENT_FORMAT_ID = "superoptimization-five-repetition-measurement-v1"
_EXPECTED_REPETITIONS = 5
_EXPECTED_WARMUPS = 0
_EXPECTED_ORDERING = "fixed-enumeration-then-seeded"
_EXPECTED_OUTLIER_POLICY = "retain-all"
_EXPECTED_CENTER = "median"
_EXPECTED_DISPERSION = "observed-range"
_EXPECTED_UNCERTAINTY = "observed-range"


class _Clock(Protocol):
    def __call__(self) -> int: ...


class _ScheduleResult(Protocol):
    schedule_id: str
    evaluations: int
    verified_count: int
    first_verified_evaluation: int | None
    first_verified_candidate: int | None
    best_candidate: int | None
    best_quality: int | None
    outcome: str


class _BoundedSchedule(Protocol):
    result: _ScheduleResult
    elapsed_nanoseconds: int
    first_verified_elapsed_nanoseconds: int | None
    stop_reason: str


class _Comparison(Protocol):
    enumeration: _BoundedSchedule
    seeded: _BoundedSchedule


class InvalidMeasurementPlanError(ValueError):
    """The frozen plan no longer matches the preregistered timing protocol."""


@dataclass(frozen=True, slots=True)
class MeasurementSeries:
    """All retained repetitions from one frozen measurement protocol."""

    format_id: str
    repetitions: tuple[_Comparison, ...]


def _fail(message: str) -> Never:
    raise InvalidMeasurementPlanError(message)


def _measurement_table(plan_text: str) -> dict[str, object]:
    try:
        parsed = cast("object", tomllib.loads(plan_text))
    except tomllib.TOMLDecodeError as error:
        _fail(f"invalid measurement plan TOML: {error}")
    if not isinstance(parsed, dict):
        _fail("measurement plan root must be a table")
    document = cast("dict[str, object]", parsed)
    value = document.get("measurement")
    if not isinstance(value, dict):
        _fail("measurement plan table is required")
    return cast("dict[str, object]", value)


def _require_measurement_protocol(plan_text: str) -> None:
    table = _measurement_table(plan_text)
    checks = (
        (table.get("repetitions"), _EXPECTED_REPETITIONS, "repetitions"),
        (table.get("warmup_iterations"), _EXPECTED_WARMUPS, "warmups"),
        (table.get("ordering"), _EXPECTED_ORDERING, "ordering"),
        (
            table.get("outlier_policy"),
            _EXPECTED_OUTLIER_POLICY,
            "outlier policy",
        ),
        (table.get("center"), _EXPECTED_CENTER, "center statistic"),
        (
            table.get("dispersion"),
            _EXPECTED_DISPERSION,
            "dispersion statistic",
        ),
        (
            table.get("uncertainty"),
            _EXPECTED_UNCERTAINTY,
            "uncertainty statistic",
        ),
    )
    for observed, expected, label in checks:
        if observed != expected:
            _fail(f"measurement plan {label} differs from preregistration")


def run_preregistered_measurement(
    plan_text: str,
    *,
    clock_ns: _Clock,
) -> MeasurementSeries:
    """Run every retained repetition through the frozen concrete pilot.

    Returns:
        Five retained comparison results in preregistered execution order.

    """
    _require_measurement_protocol(plan_text)
    concrete = tuple(
        pilot.run_preregistered_pilot(plan_text, clock_ns=clock_ns)
        for _ in range(_EXPECTED_REPETITIONS)
    )
    repetitions = cast("tuple[_Comparison, ...]", cast("object", concrete))
    return MeasurementSeries(MEASUREMENT_FORMAT_ID, repetitions)


def _optional(value: int | None) -> str:
    return "" if value is None else str(value)


def _schedule_row(
    repetition: int,
    schedule: _BoundedSchedule,
) -> tuple[str, ...]:
    result = schedule.result
    return (
        str(repetition),
        result.schedule_id,
        str(result.evaluations),
        str(result.verified_count),
        _optional(result.first_verified_evaluation),
        _optional(result.first_verified_candidate),
        _optional(result.best_candidate),
        _optional(result.best_quality),
        str(schedule.elapsed_nanoseconds),
        _optional(schedule.first_verified_elapsed_nanoseconds),
        schedule.stop_reason,
        result.outcome,
    )


def render_raw_csv(series: MeasurementSeries) -> str:
    """Render every retained schedule result as canonical CSV.

    Returns:
        Header plus two schedule rows for each retained repetition.

    """
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow((
        "repetition",
        "schedule_id",
        "evaluations",
        "verified_count",
        "first_verified_evaluation",
        "first_verified_candidate",
        "best_candidate",
        "best_quality",
        "elapsed_nanoseconds",
        "first_verified_elapsed_nanoseconds",
        "stop_reason",
        "outcome",
    ))
    for repetition, comparison in enumerate(series.repetitions):
        writer.writerow(_schedule_row(repetition, comparison.enumeration))
        writer.writerow(_schedule_row(repetition, comparison.seeded))
    return output.getvalue()
