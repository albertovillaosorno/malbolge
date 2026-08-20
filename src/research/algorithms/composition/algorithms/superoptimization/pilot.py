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
#   - Plan-bound orchestration for the preregistered classic pilot.
# - Must-Not:
#   - Write run evidence, discover provenance, or alter challenge semantics.
# - Allows:
#   - Inputs: exact plan TOML and caller-supplied monotonic clock.
#   - Outputs: admitted dual-bound request or in-memory comparison result.
#   - Side effects: invokes only the concrete verifier during explicit
#     execution.
# - Split-When:
#   - Run persistence, environment discovery, or another challenge gains policy.
# - Merge-When:
#   - A shared experiment harness owns this exact plan-to-runner binding.
# - Summary:
#   - Bind the frozen classic pilot plan to its concrete verifier and runner.
# - Description:
#   - Rejects plan drift before constructing or executing a comparison request.
# - Usage:
#   - Research tooling may execute after preregistration and supply its own
#     clock.
# - Defaults:
#   - Importing or parsing the plan does not constitute a measured run.
#

"""Plan-bound orchestration for the preregistered classic superopt pilot."""

from __future__ import annotations

import tomllib
from typing import Never
from typing import cast

from src.research.algorithms.composition.algorithms.superoptimization import (
    challenge,
)
from src.research.algorithms.composition.algorithms.superoptimization import (
    runner,
)

_NANOSECONDS_PER_SECOND = 1_000_000_000
_PLAN_KIND = "plan"
_OBJECTIVE = "halt-without-prior-input-or-output"
_SOURCE_WORDS = 2


class InvalidPilotPlanError(ValueError):
    """The plan no longer matches the concrete preregistered pilot identity."""


def _fail(message: str) -> Never:
    raise InvalidPilotPlanError(message)


def _mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        _fail(f"{context} must be a table")
    return cast("dict[str, object]", value)


def _table(document: dict[str, object], name: str) -> dict[str, object]:
    value = document.get(name)
    if value is None:
        _fail(f"pilot plan {name} table is required")
    return _mapping(value, f"pilot plan {name}")


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


def _parse_plan(plan_text: str) -> dict[str, object]:
    if type(plan_text) is not str:
        _fail("pilot plan must use exact string text")
    try:
        document = cast("object", tomllib.loads(plan_text))
    except tomllib.TOMLDecodeError as error:
        _fail(f"invalid pilot plan TOML: {error}")
    return _mapping(document, "pilot plan root")


def _expect_equal(observed: object, expected: object, label: str) -> None:
    if observed != expected:
        _fail(f"pilot plan {label} differs from concrete challenge")


def _validate_challenge_identity(document: dict[str, object]) -> None:
    core = _table(document, "challenge")
    concrete = _table(document, "classic_block_search")
    verification = _table(document, "verification")
    checks = (
        (
            _exact_string(core, "family", "plan.challenge"),
            challenge.CLASSIC_BLOCK_SEARCH_CHALLENGE_ID,
            "challenge family",
        ),
        (
            _exact_int(
                concrete,
                "candidate_count",
                "plan.classic_block_search",
            ),
            challenge.CLASSIC_BLOCK_SEARCH_CANDIDATE_COUNT,
            "candidate count",
        ),
        (
            _exact_string(
                concrete,
                "candidate_encoding",
                "plan.classic_block_search",
            ),
            challenge.CLASSIC_BLOCK_SEARCH_CANDIDATE_ENCODING_ID,
            "candidate encoding",
        ),
        (
            _exact_string(concrete, "objective", "plan.classic_block_search"),
            _OBJECTIVE,
            "objective",
        ),
        (
            _exact_string(concrete, "quality", "plan.classic_block_search"),
            challenge.CLASSIC_BLOCK_SEARCH_QUALITY_ID,
            "quality identity",
        ),
        (
            _exact_int(concrete, "source_words", "plan.classic_block_search"),
            _SOURCE_WORDS,
            "source-word count",
        ),
        (
            _exact_string(concrete, "verifier", "plan.classic_block_search"),
            challenge.CLASSIC_BLOCK_SEARCH_VERIFIER_ID,
            "verifier identity",
        ),
        (
            _exact_string(verification, "oracle", "plan.verification"),
            challenge.CLASSIC_BLOCK_SEARCH_VERIFIER_ID,
            "verification oracle",
        ),
        (
            _exact_string(
                concrete,
                "workload_sha256",
                "plan.classic_block_search",
            ),
            challenge.workload_sha256(),
            "workload hash",
        ),
    )
    for observed, expected, label in checks:
        _expect_equal(observed, expected, label)


def preregistered_request(plan_text: str) -> runner.BoundedComparisonRequest:
    """Return the exact dual-bound request encoded by the frozen pilot plan.

    Returns:
        Concrete finite corpus, evaluation, wall-clock, and seed bounds.

    """
    document = _parse_plan(plan_text)
    experiment = _table(document, "experiment")
    budget = _table(document, "budget")
    if experiment.get("record_kind") != _PLAN_KIND:
        _fail("pilot orchestration requires an unrun plan record")
    _validate_challenge_identity(document)
    seconds = _exact_int(budget, "seconds", "plan.budget")
    return runner.BoundedComparisonRequest(
        candidate_count=challenge.CLASSIC_BLOCK_SEARCH_CANDIDATE_COUNT,
        evaluation_budget=_exact_int(
            budget,
            "candidate_evaluations",
            "plan.budget",
        ),
        wall_clock_budget_nanoseconds=seconds * _NANOSECONDS_PER_SECOND,
        seed=_exact_int(experiment, "seed", "plan.experiment"),
    )


def run_preregistered_pilot(
    plan_text: str,
    *,
    clock_ns: runner.MonotonicClock,
) -> runner.BoundedComparisonResult:
    """Execute the frozen pilot in memory through its concrete verifier.

    Returns:
        Dual-bound comparison result; no run artifact is written or claimed.

    """
    request = preregistered_request(plan_text)
    return runner.compare_schedules_bounded(
        request,
        verifier=challenge.verified_quality,
        clock_ns=clock_ns,
    )
