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
#   - Run-record rendering evidence for the superoptimization pilot.
# - Must-Not:
#   - Claim a run occurred or replace shared experiment-manifest validation.
# - Allows:
#   - Inputs: the checked-in plan, synthetic bounded results, fake provenance.
#   - Outputs: deterministic rendering, shared-validation, and drift assertions.
#   - Side effects: dynamic import and repository-local plan reads only.
# - Split-When:
#   - Recorded raw output gains independently governed persistence tests.
# - Merge-When:
#   - Shared experiment tooling owns this exact extension rendering contract.
# - Summary:
#   - Prove bounded results can become provenance-bound candidate run records.
# - Description:
#   - Uses shared schema-v1 validation without fabricating measured evidence.
# - Usage:
#   - Collected by the research algorithm Python test surface.
# - Defaults:
#   - Synthetic fixtures are never retained as research results.
#

"""Run-record rendering evidence for the superoptimization pilot."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
import importlib.util
from pathlib import Path
import sys
import tomllib
from typing import Protocol
from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from collections.abc import Callable

import pytest
from scripts.validate import experiment_manifest as manifest_validator

_ROOT = Path(__file__).resolve().parents[5]
_RUN_RECORD = _ROOT / (
    "src/research/algorithms/composition/algorithms/"
    "superoptimization/run_record.py"
)
_PLAN = _ROOT / (
    "src/research/algorithms/domain/algorithms/"
    "superoptimization-research-program/experiment.toml"
)
_EXPERIMENT_ID = "superoptimization-research-program"
_COMPARISON_ID = "finite-verifier-gated-dual-bound-comparison-v1"
_FORMAT_ID = "superoptimization-run-record-v1"
_EVALUATIONS = 10_000
_WALL_NANOSECONDS = 60_000_000_000
_CANDIDATE_COUNT = 20_000
_COMMIT = "a" * 40
_WORKLOAD = "b" * 64
_RAW_OUTPUT = "algorithms/superoptimization-research-program/out/run.json"
_ENUMERATION_ID = "deterministic-enumeration-v1"
_SEEDED_ID = "splitmix64-sparse-partial-fisher-yates-v1"
_STOP_EVALUATION = "evaluation-budget"
_FOUND = "verified-candidate-found"
_NOT_FOUND = "no-verified-candidate"
_FIRST_EVALUATION = 7
_FIRST_CANDIDATE = 42
_BEST_QUALITY = 3
_FIRST_ELAPSED = 5
_ENUM_ELAPSED = 12
_SEEDED_ELAPSED = 13
_RECORD_KIND_RUN = "run"
_FIRST_CANDIDATE_KEY = "first_verified_candidate"
_BEST_QUALITY_KEY = "best_quality"


@dataclass(frozen=True, slots=True)
class _ScheduleResult:
    schedule_id: str
    evaluations: int
    verified_count: int
    first_verified_evaluation: int | None
    first_verified_candidate: int | None
    best_candidate: int | None
    best_quality: int | None
    outcome: str


@dataclass(frozen=True, slots=True)
class _BoundedRun:
    result: _ScheduleResult
    elapsed_nanoseconds: int
    first_verified_elapsed_nanoseconds: int | None
    stop_reason: str


@dataclass(frozen=True, slots=True)
class _Comparison:
    comparison_id: str
    candidate_count: int
    evaluation_budget: int
    wall_clock_budget_nanoseconds: int
    seed: int
    enumeration: _BoundedRun
    seeded: _BoundedRun


class _Provenance(Protocol):
    commit: str
    workload_sha256: str
    host: str
    accelerator: str
    toolchain: str
    outcome: str
    raw_output: str


class _RunRecordModule(Protocol):
    RunProvenance: object
    RunRecordError: type[ValueError]
    RUN_RECORD_FORMAT_ID: str

    def render_run_manifest(
        self,
        plan_text: str,
        provenance: _Provenance,
        result: _Comparison,
    ) -> str:
        """Render one candidate run manifest."""
        ...


def _load_run_record() -> _RunRecordModule:
    spec = importlib.util.spec_from_file_location(
        "superoptimization_run_record_test",
        _RUN_RECORD,
    )
    if spec is None or spec.loader is None:
        message = "superoptimization run-record module cannot be loaded"
        raise RuntimeError(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return cast("_RunRecordModule", cast("object", module))


_RUN_RECORD_MODULE = _load_run_record()


def _result() -> _Comparison:
    enumeration = _ScheduleResult(
        _ENUMERATION_ID,
        _EVALUATIONS,
        1,
        _FIRST_EVALUATION,
        _FIRST_CANDIDATE,
        _FIRST_CANDIDATE,
        _BEST_QUALITY,
        _FOUND,
    )
    seeded = _ScheduleResult(
        _SEEDED_ID,
        _EVALUATIONS,
        0,
        None,
        None,
        None,
        None,
        _NOT_FOUND,
    )
    return _Comparison(
        _COMPARISON_ID,
        _CANDIDATE_COUNT,
        _EVALUATIONS,
        _WALL_NANOSECONDS,
        0,
        _BoundedRun(
            enumeration,
            _ENUM_ELAPSED,
            _FIRST_ELAPSED,
            _STOP_EVALUATION,
        ),
        _BoundedRun(seeded, _SEEDED_ELAPSED, None, _STOP_EVALUATION),
    )


def _provenance(*, commit: str = _COMMIT) -> _Provenance:
    factory = cast(
        "Callable[..., _Provenance]",
        _RUN_RECORD_MODULE.RunProvenance,
    )
    return factory(
        commit=commit,
        workload_sha256=_WORKLOAD,
        host="windows-x86_64-test",
        accelerator="none",
        toolchain="python-3.14.6",
        outcome="no-solution",
        raw_output=_RAW_OUTPUT,
    )


def _render(result: _Comparison | None = None) -> str:
    return _RUN_RECORD_MODULE.render_run_manifest(
        _PLAN.read_text(encoding="utf-8"),
        _provenance(),
        _result() if result is None else result,
    )


def test_rendered_run_uses_shared_manifest_authority() -> None:
    """Candidate run text satisfies the shared schema-v1 core contract."""
    first = _render()
    second = _render()
    assert first == second
    manifest = manifest_validator.parse_manifest(first)
    assert manifest.identifier == _EXPERIMENT_ID
    assert manifest.record_kind == _RECORD_KIND_RUN
    assert manifest.run is not None
    assert manifest.run.commit == _COMMIT
    assert manifest.run.workload_sha256 == _WORKLOAD
    assert manifest.run.raw_output == _RAW_OUTPUT


def test_run_extension_retains_verified_and_null_schedule_metrics() -> None:
    """Algorithm extension keeps positive and null outcomes distinguishable."""
    document = tomllib.loads(_render())
    extension = cast("dict[str, object]", document["superoptimization"])
    enumeration = cast("dict[str, object]", extension["enumeration"])
    seeded = cast("dict[str, object]", extension["seeded"])
    assert extension["format_id"] == _FORMAT_ID
    assert extension["comparison_id"] == _COMPARISON_ID
    assert enumeration["first_verified_candidate"] == _FIRST_CANDIDATE
    assert enumeration["best_quality"] == _BEST_QUALITY
    assert enumeration["first_verified_elapsed_nanoseconds"] == _FIRST_ELAPSED
    assert seeded["outcome"] == _NOT_FOUND
    assert _FIRST_CANDIDATE_KEY not in seeded
    assert _BEST_QUALITY_KEY not in seeded


def test_run_renderer_rejects_preregistered_bound_drift() -> None:
    """A result cannot silently change frozen evaluation or wall-time bounds."""
    drifted = replace(_result(), evaluation_budget=_EVALUATIONS - 1)
    with pytest.raises(
        _RUN_RECORD_MODULE.RunRecordError,
        match="evaluation budget differs from plan",
    ):
        _ = _render(drifted)


def test_shared_validator_still_owns_commit_shape() -> None:
    """Renderer quoting never replaces the shared run-identity authority."""
    text = _RUN_RECORD_MODULE.render_run_manifest(
        _PLAN.read_text(encoding="utf-8"),
        _provenance(commit="short"),
        _result(),
    )
    with pytest.raises(
        manifest_validator.ExperimentManifestError,
        match="lowercase 40-hex Git commit",
    ):
        _ = manifest_validator.parse_manifest(text)
