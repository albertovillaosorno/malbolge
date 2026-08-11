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
#   - Deterministic run-manifest rendering for superoptimization comparisons.
# - Must-Not:
#   - Invent run provenance, write evidence, or redefine shared manifest rules.
# - Allows:
#   - Inputs: preregistered plan text, bounded comparison, exact run identity.
#   - Outputs: one candidate schema-v1 run manifest with extension metrics.
#   - Side effects: none.
# - Split-When:
#   - Raw-output persistence or host/toolchain discovery gains ownership.
# - Merge-When:
#   - A shared research renderer owns algorithm-specific extension tables.
# - Summary:
#   - Bind bounded superoptimization results to explicit run provenance.
# - Description:
#   - Reuses the checked-in plan and appends shared run plus result identities.
# - Usage:
#   - Call only after a concrete challenge has truthful run provenance.
# - Defaults:
#   - Plan/result bound drift and malformed provenance fail closed.
#

"""Render provenance-bound superoptimization run manifests without writing."""

from __future__ import annotations

from dataclasses import dataclass
import json
import tomllib
from typing import Never
from typing import Protocol
from typing import cast

_NANOSECONDS_PER_SECOND = 1_000_000_000
_PLAN_KIND = "plan"
_PLAN_RECORD = 'record_kind = "plan"'
_RUN_RECORD = 'record_kind = "run"'
_RUN_TABLE_MARKER = "\n[run]"
_EXPECTED_COMPARISON_ID = "finite-verifier-gated-dual-bound-comparison-v1"
RUN_RECORD_FORMAT_ID = "superoptimization-run-record-v1"
MEASUREMENT_RUN_RECORD_FORMAT_ID = "superoptimization-measurement-run-record-v1"


class RunRecordError(ValueError):
    """Preregistered plan, result, or run identity cannot form one record."""


class _ScheduleRun(Protocol):
    schedule_id: str
    evaluations: int
    verified_count: int
    first_verified_evaluation: int | None
    first_verified_candidate: int | None
    best_candidate: int | None
    best_quality: int | None
    outcome: str


class _BoundedScheduleRun(Protocol):
    result: _ScheduleRun
    elapsed_nanoseconds: int
    first_verified_elapsed_nanoseconds: int | None
    stop_reason: str


class BoundedComparison(Protocol):
    """Structural result required by the run-record boundary."""

    comparison_id: str
    candidate_count: int
    evaluation_budget: int
    wall_clock_budget_nanoseconds: int
    seed: int
    enumeration: _BoundedScheduleRun
    seeded: _BoundedScheduleRun


class MeasurementSeries(Protocol):
    """Structural repeated-measurement result required by this boundary."""

    format_id: str
    repetitions: tuple[BoundedComparison, ...]


@dataclass(frozen=True, slots=True)
class _PreregisteredPlan:
    """Frozen plan identity that every rendered run must preserve."""

    candidate_count: int
    evaluation_budget: int
    seed: int
    wall_clock_budget_nanoseconds: int
    workload_sha256: str


@dataclass(frozen=True, slots=True)
class RunProvenance:
    """Truthful environment/output identity supplied by the concrete runner."""

    commit: str
    workload_sha256: str
    host: str
    accelerator: str
    toolchain: str
    outcome: str
    raw_output: str


def _fail(message: str) -> Never:
    raise RunRecordError(message)


def _table(document: dict[str, object], name: str) -> dict[str, object]:
    value = document.get(name)
    if not isinstance(value, dict):
        _fail(f"superoptimization plan {name} table is required")
    return cast("dict[str, object]", value)


def _exact_int(table: dict[str, object], key: str, context: str) -> int:
    value = table.get(key)
    if type(value) is not int:
        _fail(f"{context}.{key} must be an exact integer")
    return value


def _exact_string(table: dict[str, object], key: str, context: str) -> str:
    value = table.get(key)
    if type(value) is not str or not value:
        _fail(f"{context}.{key} must be a non-empty exact string")
    return value


def _parse_plan(text: str) -> dict[str, object]:
    if type(text) is not str:
        _fail("superoptimization plan must use exact string text")
    try:
        parsed = cast("object", tomllib.loads(text))
    except tomllib.TOMLDecodeError as error:
        _fail(f"invalid superoptimization plan TOML: {error}")
    if not isinstance(parsed, dict):
        _fail("superoptimization plan root must be a table")
    return cast("dict[str, object]", parsed)


def _preregistered_plan(plan: dict[str, object]) -> _PreregisteredPlan:
    experiment = _table(plan, "experiment")
    budget = _table(plan, "budget")
    challenge = _table(plan, "classic_block_search")
    if experiment.get("record_kind") != _PLAN_KIND:
        _fail("superoptimization run renderer requires a plan record")
    seconds = _exact_int(budget, "seconds", "plan.budget")
    return _PreregisteredPlan(
        candidate_count=_exact_int(
            challenge,
            "candidate_count",
            "plan.classic_block_search",
        ),
        evaluation_budget=_exact_int(
            budget,
            "candidate_evaluations",
            "plan.budget",
        ),
        seed=_exact_int(experiment, "seed", "plan.experiment"),
        wall_clock_budget_nanoseconds=seconds * _NANOSECONDS_PER_SECOND,
        workload_sha256=_exact_string(
            challenge,
            "workload_sha256",
            "plan.classic_block_search",
        ),
    )


def _expect_equal(observed: object, expected: object, message: str) -> None:
    if observed != expected:
        _fail(message)


def _require_bound_identity(
    plan: dict[str, object],
    provenance: RunProvenance,
    result: BoundedComparison,
) -> None:
    expected = _preregistered_plan(plan)
    checks = (
        (
            result.comparison_id,
            _EXPECTED_COMPARISON_ID,
            "superoptimization result uses wrong comparison identity",
        ),
        (
            result.candidate_count,
            expected.candidate_count,
            "superoptimization candidate count differs from plan",
        ),
        (
            result.seed,
            expected.seed,
            "superoptimization result seed differs from preregistered plan",
        ),
        (
            result.evaluation_budget,
            expected.evaluation_budget,
            "superoptimization evaluation budget differs from plan",
        ),
        (
            result.wall_clock_budget_nanoseconds,
            expected.wall_clock_budget_nanoseconds,
            "superoptimization wall-clock budget differs from plan",
        ),
        (
            provenance.workload_sha256,
            expected.workload_sha256,
            "superoptimization workload hash differs from plan",
        ),
    )
    for observed, preregistered, message in checks:
        _expect_equal(observed, preregistered, message)


def _require_measurement_identity(
    plan: dict[str, object],
    provenance: RunProvenance,
    series: MeasurementSeries,
) -> None:
    measurement = _table(plan, "measurement")
    repetitions = _exact_int(measurement, "repetitions", "plan.measurement")
    if len(series.repetitions) != repetitions:
        _fail("superoptimization measurement repetitions differ from plan")
    if not series.repetitions:
        _fail("superoptimization measurement series must not be empty")
    for result in series.repetitions:
        _require_bound_identity(plan, provenance, result)


def _quoted(value: object, label: str) -> str:
    if type(value) is not str or not value:
        _fail(f"{label} must be a non-empty exact string")
    return json.dumps(value, ensure_ascii=True)


def _run_lines(provenance: RunProvenance) -> list[str]:
    return [
        "[run]",
        f"commit = {_quoted(provenance.commit, 'run commit')}",
        (
            "workload_sha256 = "
            f"{_quoted(provenance.workload_sha256, 'workload hash')}"
        ),
        f"host = {_quoted(provenance.host, 'run host')}",
        f"accelerator = {_quoted(provenance.accelerator, 'run accelerator')}",
        f"toolchain = {_quoted(provenance.toolchain, 'run toolchain')}",
        f"outcome = {_quoted(provenance.outcome, 'run outcome')}",
        f"raw_output = {_quoted(provenance.raw_output, 'raw output path')}",
    ]


def _optional_int(lines: list[str], key: str, value: int | None) -> None:
    if value is not None:
        lines.append(f"{key} = {value}")


def _schedule_lines(
    table_name: str,
    run: _BoundedScheduleRun,
) -> list[str]:
    result = run.result
    lines = [
        f"[superoptimization.{table_name}]",
        f"schedule_id = {_quoted(result.schedule_id, 'schedule id')}",
        f"evaluations = {result.evaluations}",
        f"verified_count = {result.verified_count}",
        f"elapsed_nanoseconds = {run.elapsed_nanoseconds}",
        f"stop_reason = {_quoted(run.stop_reason, 'stop reason')}",
        f"outcome = {_quoted(result.outcome, 'schedule outcome')}",
    ]
    _optional_int(
        lines,
        "first_verified_evaluation",
        result.first_verified_evaluation,
    )
    _optional_int(
        lines,
        "first_verified_candidate",
        result.first_verified_candidate,
    )
    _optional_int(
        lines,
        "first_verified_elapsed_nanoseconds",
        run.first_verified_elapsed_nanoseconds,
    )
    _optional_int(lines, "best_candidate", result.best_candidate)
    _optional_int(lines, "best_quality", result.best_quality)
    return lines


def _extension_lines(result: BoundedComparison) -> list[str]:
    lines = [
        "[superoptimization]",
        f"format_id = {_quoted(RUN_RECORD_FORMAT_ID, 'run record format')}",
        f"comparison_id = {_quoted(result.comparison_id, 'comparison id')}",
        f"candidate_count = {result.candidate_count}",
        f"evaluation_budget = {result.evaluation_budget}",
        (
            "wall_clock_budget_nanoseconds = "
            f"{result.wall_clock_budget_nanoseconds}"
        ),
        f"seed = {result.seed}",
        "",
    ]
    lines.extend(_schedule_lines("enumeration", result.enumeration))
    lines.append("")
    lines.extend(_schedule_lines("seeded", result.seeded))
    return lines


def _measurement_extension_lines(
    series: MeasurementSeries,
) -> list[str]:
    first = series.repetitions[0]
    return [
        "[superoptimization_measurement]",
        (
            "format_id = "
            f"{_quoted(MEASUREMENT_RUN_RECORD_FORMAT_ID, 'measurement format')}"
        ),
        f"measurement_series_id = {_quoted(series.format_id, 'series format')}",
        f"repetitions = {len(series.repetitions)}",
        f"comparison_id = {_quoted(first.comparison_id, 'comparison id')}",
        f"candidate_count = {first.candidate_count}",
        f"evaluation_budget = {first.evaluation_budget}",
        (
            "wall_clock_budget_nanoseconds = "
            f"{first.wall_clock_budget_nanoseconds}"
        ),
        f"seed = {first.seed}",
    ]


def render_measurement_run_manifest(
    plan_text: str,
    provenance: RunProvenance,
    series: MeasurementSeries,
) -> str:
    """Render one recorded-run manifest for all retained repetitions.

    Returns:
        Deterministic TOML binding the frozen plan to retained raw evidence.

    """
    plan = _parse_plan(plan_text)
    _require_measurement_identity(plan, provenance, series)
    if plan_text.count(_PLAN_RECORD) != 1 or _RUN_TABLE_MARKER in plan_text:
        _fail("superoptimization plan record marker is not canonical")
    prefix = plan_text.replace(_PLAN_RECORD, _RUN_RECORD, 1).rstrip()
    lines = [
        prefix,
        "",
        *_run_lines(provenance),
        "",
        *_measurement_extension_lines(series),
    ]
    return "\n".join(lines) + "\n"


def render_run_manifest(
    plan_text: str,
    provenance: RunProvenance,
    result: BoundedComparison,
) -> str:
    """Render one candidate recorded-run manifest from the frozen plan.

    Returns:
        Deterministic TOML containing shared run identity and extension metrics.

    """
    plan = _parse_plan(plan_text)
    _require_bound_identity(plan, provenance, result)
    if plan_text.count(_PLAN_RECORD) != 1 or _RUN_TABLE_MARKER in plan_text:
        _fail("superoptimization plan record marker is not canonical")
    prefix = plan_text.replace(_PLAN_RECORD, _RUN_RECORD, 1).rstrip()
    lines = [
        prefix,
        "",
        *_run_lines(provenance),
        "",
        *_extension_lines(result),
    ]
    return "\n".join(lines) + "\n"
