# File:
#   - test_experiment_manifest.py
# Path:
#   - tests/test_experiment_manifest.py
#
# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE
# Path-Rule:
#   - All paths in this header are repository-root relative.
#
# Boundary-Contract:
# - Owns:
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Regression tests for reproducible experiment manifest schema v1.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#
# Related documents:
# - None.
#
# Large file:
#   - false
#

"""Regression tests for reproducible experiment manifest schema v1."""

from __future__ import annotations

from scripts.validate import experiment_manifest as validator

EXPECTED_IDS = (
    "adaptive-accelerator-resource-budgeting",
    "compact-guest-bytecode-strategy",
    "malbolge-specific-optimization-mathematics",
    "pytorch-search-orchestration",
    "search-pruning-and-state-canonicalization",
    "self-modification-state-graph-optimizer",
    "stochastic-and-guided-search",
    "template",
)
RESOURCE_EXHAUSTED = "resource-exhausted"
RUN_COMMIT = "a" * 40
RUN_HASH = "b" * 64


def _run_manifest(**overrides: str) -> str:
    values = {
        "accelerator": "none",
        "commit": RUN_COMMIT,
        "host": "windows-x86_64-test",
        "outcome": "success",
        "raw_output": "algorithms/example/out/raw.json",
        "toolchain": "python-3.14.6",
        "workload_sha256": RUN_HASH,
    }
    values.update(overrides)
    return f"""schema_version = 1

[experiment]
id = "example"
record_kind = "run"
method_class = "benchmarking"
seed = 7

[challenge]
family = "fixture"
difficulty = 1
target_profile = "malbolge-2026.2"

[budget]
seconds = 1

[verification]
required = true
oracle = "trusted-fixture"

[provenance]
implementation = "algorithms/example/"
configuration = "algorithms/example/experiment.toml"
output = "algorithms/example/out/"

[run]
commit = "{values["commit"]}"
workload_sha256 = "{values["workload_sha256"]}"
host = "{values["host"]}"
accelerator = "{values["accelerator"]}"
toolchain = "{values["toolchain"]}"
outcome = "{values["outcome"]}"
raw_output = "{values["raw_output"]}"
"""


def _expect_failure(text: str, message: str) -> None:
    try:
        _ = validator.parse_manifest(text)
    except validator.ExperimentManifestError as error:
        if message not in str(error):
            mismatch = f"unexpected manifest error: {error}"
            raise AssertionError(mismatch) from error
        return
    failure = "invalid experiment manifest unexpectedly succeeded"
    raise AssertionError(failure)


def test_repository_experiment_manifests_are_schema_valid() -> None:
    """Every mirrored algorithm carries one valid version-one plan manifest."""
    manifests = validator.validate_repository()
    assert tuple(item.identifier for item in manifests) == EXPECTED_IDS


def test_recorded_run_requires_exact_commit_and_workload_hash() -> None:
    """Recorded evidence cannot omit exact source and workload identity."""
    _expect_failure(
        _run_manifest(commit="short"),
        "lowercase 40-hex Git commit",
    )
    _expect_failure(
        _run_manifest(workload_sha256="short"),
        "lowercase SHA-256 hex",
    )


def test_recorded_run_retains_negative_outcome_identity() -> None:
    """A non-success run remains a valid recorded experiment outcome."""
    manifest = validator.parse_manifest(
        _run_manifest(outcome=RESOURCE_EXHAUSTED)
    )
    assert manifest.run is not None
    assert manifest.run.outcome == RESOURCE_EXHAUSTED


def test_recorded_run_rejects_unknown_outcome() -> None:
    """Unknown run outcomes fail closed."""
    _expect_failure(_run_manifest(outcome="lucky"), "unsupported run outcome")


def test_plan_requires_positive_stopping_bound() -> None:
    """A research plan without a positive budget is not reconstructible."""
    text = _run_manifest().replace("seconds = 1", "seconds = 0")
    _expect_failure(text, "positive integer stopping bound")


def test_verification_cannot_be_disabled_by_manifest() -> None:
    """Research configuration cannot make semantic verification optional."""
    text = _run_manifest().replace("required = true", "required = false")
    _expect_failure(text, "verification.required must be true")


def test_plan_cannot_smuggle_recorded_run_metadata() -> None:
    """A plan does not masquerade as already observed run evidence."""
    text = _run_manifest().replace(
        'record_kind = "run"', 'record_kind = "plan"'
    )
    _expect_failure(
        text, "plan experiment manifest must not contain a run table"
    )
