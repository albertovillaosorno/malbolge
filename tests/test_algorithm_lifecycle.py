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
#   - Regression tests for research algorithm lifecycle policy.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Regression tests for research algorithm lifecycle policy."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from scripts.validate import algorithm_lifecycle as validator

if TYPE_CHECKING:
    from pathlib import Path

DECISION_DATE = "2026-07-27"
SUCCESSOR = "successor-v2"

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
EVIDENCE = "docs/research/methodology/scientific-method.md"
BENEFIT = "benchmarks/research/protocol/examples/deterministic.benchmark.toml"
RESEARCH = "docs/research/algorithms/template/research.md"
EXPERIMENT = (
    "src/research/algorithms/domain/algorithms/template/experiment.toml"
)


def _base(state: str) -> str:
    return f"""schema_version = 1

[algorithm]
id = "template"
state = "{state}"
research_record = "{RESEARCH}"
experiment_manifest = "{EXPERIMENT}"
"""


def _promotion() -> str:
    return f"""
[promotion]
correctness = "{EVIDENCE}"
reproducibility = "docs/research/methodology/experiment-identity.md"
maintainability = "docs/research/methodology/algorithm-lifecycle.md"
portability = "docs/technical/adr/host-cpu-and-accelerator-runtime-baseline.md"
measured_benefit = "{BENEFIT}"
"""


def _decision(**extra: str) -> str:
    lines = [
        "",
        "[decision]",
        f"decided_on = {DECISION_DATE}",
        'reason = "fixture lifecycle decision"',
        f'evidence = "{EVIDENCE}"',
    ]
    lines.extend(f'{key} = "{value}"' for key, value in extra.items())
    return "\n".join(lines) + "\n"


def _expect_failure(text: str, message: str) -> None:
    try:
        _ = validator.parse_lifecycle(text)
    except validator.AlgorithmLifecycleError as error:
        if message not in str(error):
            mismatch = f"unexpected lifecycle validation error: {error}"
            raise AssertionError(mismatch) from error
        return
    failure = "invalid lifecycle unexpectedly succeeded"
    raise AssertionError(failure)


def test_lifecycle_file_rejects_invalid_utf8(tmp_path: Path) -> None:
    """Lifecycle file encoding failure remains a typed validation error."""
    path = tmp_path / "lifecycle.toml"
    _ = path.write_bytes(bytes((0x5b, 0xff, 0x5d)))
    with pytest.raises(
        validator.AlgorithmLifecycleError,
        match="invalid algorithm lifecycle UTF-8",
    ):
        _ = validator.validate_repository_lifecycle(path)


def test_every_research_mirror_has_explicit_experimental_lifecycle() -> None:
    """All current research mirrors declare lifecycle state explicitly."""
    records = validator.validate_repository()
    assert tuple(record.identifier for record in records) == EXPECTED_IDS
    assert {record.state for record in records} == {validator.EXPERIMENTAL}


def test_lifecycle_rejects_windows_drive_relative_path() -> None:
    """Drive-relative Windows syntax cannot redirect lifecycle evidence."""
    text = _base(validator.EXPERIMENTAL).replace(
        f'research_record = "{RESEARCH}"',
        'research_record = "D:escape"',
    )
    _expect_failure(text, "must be repository-relative")


def test_promotion_candidate_requires_all_five_evidence_gates() -> None:
    """Promotion eligibility is evidence-linked rather than boolean asserted."""
    valid = _base(validator.PROMOTION_CANDIDATE) + _promotion()
    record = validator.parse_lifecycle(valid)
    assert record.promotion is not None
    assert record.promotion.measured_benefit == BENEFIT

    missing = valid.replace(f'measured_benefit = "{BENEFIT}"\n', "")
    _expect_failure(missing, "measured_benefit must be a non-empty string")


def test_promoted_state_requires_evidence_and_durable_decision() -> None:
    """Promotion requires both gate evidence and an explicit decision record."""
    text = _base(validator.PROMOTED) + _promotion() + _decision()
    record = validator.parse_lifecycle(text)
    assert record.promotion is not None
    assert record.decision is not None
    assert record.decision.decided_on.isoformat() == DECISION_DATE

    _expect_failure(
        _base(validator.PROMOTED) + _promotion(),
        "promoted requires a decision table",
    )


def test_rejection_requires_retained_negative_results() -> None:
    """Rejected algorithms preserve negative evidence."""
    text = _base(validator.REJECTED) + _decision(negative_results=BENEFIT)
    record = validator.parse_lifecycle(text)
    assert record.decision is not None
    assert record.decision.negative_results == BENEFIT

    _expect_failure(
        _base(validator.REJECTED) + _decision(),
        "rejected lifecycle state requires retained negative_results",
    )


def test_retirement_requires_prior_gate_history_and_successor_identity() -> (
    None
):
    """Retired algorithms keep promotion evidence and name their successor."""
    text = (
        _base(validator.RETIRED)
        + _promotion()
        + _decision(superseded_by=SUCCESSOR)
    )
    record = validator.parse_lifecycle(text)
    assert record.promotion is not None
    assert record.decision is not None
    assert record.decision.superseded_by == SUCCESSOR

    _expect_failure(
        _base(validator.RETIRED) + _promotion() + _decision(),
        "retired lifecycle state requires superseded_by",
    )


def test_experimental_state_cannot_smuggle_promotion_or_decision_claims() -> (
    None
):
    """Experimental records do not masquerade as already promoted work."""
    _expect_failure(
        _base(validator.EXPERIMENTAL) + _promotion(),
        "experimental must not contain promotion evidence",
    )
    _expect_failure(
        _base(validator.EXPERIMENTAL) + _decision(),
        "experimental must not contain a decision table",
    )


def test_superseded_by_is_reserved_for_retired_state() -> None:
    """Promotion and rejection cannot silently encode retirement."""
    text = (
        _base(validator.PROMOTED)
        + _promotion()
        + _decision(superseded_by="other")
    )
    _expect_failure(text, "superseded_by is valid only for retired")
