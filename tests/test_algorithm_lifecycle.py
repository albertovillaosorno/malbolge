# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - Apache-2.0
# Confidential:
#   - false
# License-File:
#   - LICENSE
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

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from scripts.validate import algorithm_lifecycle as validator

if TYPE_CHECKING:
    from os import stat_result

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
    "superoptimization-research-program",
    "template",
)
EVIDENCE = "docs/research/methodology/scientific-method.md"
BENEFIT = "benchmarks/research/protocol/examples/deterministic.benchmark.toml"
RESEARCH = "docs/research/algorithms/template/research.md"
EXPERIMENT = "src/research/algorithms/domain/algorithms/template/experiment.toml"


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


def test_lifecycle_nested_array_parser_capacity_is_typed() -> None:
    """Deep but bounded TOML must not leak raw host RecursionError."""
    nested = "[" * 1000 + "1" + "]" * 1000
    text = _base(validator.EXPERIMENTAL) + "\nparser_probe = " + nested + "\n"
    _expect_failure(text, "invalid TOML exceeds host parser capacity")


def test_lifecycle_decimal_digit_limit_fails_typed() -> None:
    """Host parser capacity cannot escape as a raw integer ValueError."""
    limit = sys.get_int_max_str_digits()
    if limit == 0 or limit > 20_000:
        pytest.skip("host decimal token limit unavailable")
    text = _base(validator.EXPERIMENTAL).replace(
        "schema_version = 1", "schema_version = " + "9" * (limit + 1)
    )
    _expect_failure(text, "invalid TOML exceeds host parser capacity")


def test_lifecycle_file_rejects_invalid_utf8(tmp_path: Path) -> None:
    """Lifecycle file encoding failure remains a typed validation error."""
    path = tmp_path / "lifecycle.toml"
    _ = path.write_bytes(bytes((0x5B, 0xFF, 0x5D)))
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


@pytest.mark.parametrize("field", ("research_record", "experiment_manifest"))
def test_lifecycle_paths_reject_toml_escaped_nul(field: str) -> None:
    """NUL cannot reach evidence path admission as an unhandled host error."""
    value = RESEARCH if field == "research_record" else EXPERIMENT
    text = _base(validator.EXPERIMENTAL).replace(
        f'{field} = "{value}"', f'{field} = "docs/\\u0000evidence"'
    )
    _expect_failure(text, "must not contain NUL")


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


@pytest.mark.parametrize("decided_on", ("2026-07-27T12:34:56", "2026-07-27T12:34:56Z"))
def test_lifecycle_decision_requires_exact_local_date(decided_on: str) -> None:
    """A TOML timestamp must not masquerade as the schema's local date."""
    text = (_base(validator.REJECTED) + _decision(negative_results=BENEFIT)).replace(
        f"decided_on = {DECISION_DATE}", f"decided_on = {decided_on}"
    )
    _expect_failure(text, "decided_on must be a TOML local date")


def test_retirement_requires_prior_gate_history_and_successor_identity() -> None:
    """Retired algorithms keep promotion evidence and name their successor."""
    text = _base(validator.RETIRED) + _promotion() + _decision(superseded_by=SUCCESSOR)
    record = validator.parse_lifecycle(text)
    assert record.promotion is not None
    assert record.decision is not None
    assert record.decision.superseded_by == SUCCESSOR

    _expect_failure(
        _base(validator.RETIRED) + _promotion() + _decision(),
        "retired lifecycle state requires superseded_by",
    )


def test_experimental_state_cannot_smuggle_promotion_or_decision_claims() -> None:
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
    text = _base(validator.PROMOTED) + _promotion() + _decision(superseded_by="other")
    _expect_failure(text, "superseded_by is valid only for retired")


def _fixture_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    lifecycle: str,
) -> Path:
    """Create a small complete repository for lifecycle evidence admission.

    Returns:
        The canonical lifecycle manifest location.

    """
    root = tmp_path / "repository"
    experiment = root / EXPERIMENT
    experiment.parent.mkdir(parents=True)
    _ = experiment.write_text("schema_version = 1\n")
    research = root / RESEARCH
    research.parent.mkdir(parents=True)
    _ = research.write_text("# Research\n")
    manifest = experiment.parent / "lifecycle.toml"
    _ = manifest.write_text(lifecycle)
    monkeypatch.setattr(validator, "ROOT", root)
    return manifest


@pytest.mark.parametrize("linked_parent", [False, True])
def test_lifecycle_evidence_cannot_redirect_outside_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    linked_parent: bool,
) -> None:
    """A linked evidence leaf or parent is not repository-owned evidence."""
    decision = _decision(negative_results="evidence/proof.md").replace(
        EVIDENCE, "evidence/proof.md"
    )
    manifest = _fixture_repository(
        tmp_path, monkeypatch, _base(validator.REJECTED) + decision
    )
    root = manifest.parents[6]
    outside = tmp_path / "outside"
    outside.mkdir()
    _ = (outside / "proof.md").write_text("unrelated outside evidence\n")
    if linked_parent:
        (root / "evidence").symlink_to(outside, target_is_directory=True)
    else:
        (root / "evidence").mkdir()
        (root / "evidence/proof.md").symlink_to(outside / "proof.md")
    with pytest.raises(validator.AlgorithmLifecycleError, match="evidence"):
        _ = validator.validate_repository_lifecycle(manifest)


def test_lifecycle_manifest_cannot_redirect_to_another_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The lifecycle file itself must not be a symlink to foreign content."""
    manifest = _fixture_repository(tmp_path, monkeypatch, _base(validator.EXPERIMENTAL))
    source = tmp_path / "other.toml"
    _ = source.write_text(manifest.read_text())
    manifest.unlink()
    manifest.symlink_to(source)
    with pytest.raises(validator.AlgorithmLifecycleError, match="lifecycle"):
        _ = validator.validate_repository_lifecycle(manifest)


def test_lifecycle_rejects_post_status_symlink_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A link switched after lstat cannot substitute equal TOML bytes."""
    manifest = _fixture_repository(tmp_path, monkeypatch, _base(validator.EXPERIMENTAL))
    replacement = tmp_path / "replacement.toml"
    _ = replacement.write_text(manifest.read_text())
    original_lstat = Path.lstat
    changed = False

    def swap_after_status(candidate: Path) -> stat_result:
        nonlocal changed
        status = original_lstat(candidate)
        if candidate == manifest and not changed:
            manifest.unlink()
            manifest.symlink_to(replacement)
            changed = True
        return status

    monkeypatch.setattr(Path, "lstat", swap_after_status)
    with pytest.raises(validator.AlgorithmLifecycleError, match="lifecycle"):
        _ = validator.validate_repository_lifecycle(manifest)
    assert changed


def test_lifecycle_rejects_oversized_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A manifest above its size ceiling must fail before TOML decoding."""
    manifest = _fixture_repository(tmp_path, monkeypatch, _base(validator.EXPERIMENTAL))
    _ = manifest.write_bytes(b"#" * (validator.MAX_LIFECYCLE_BYTES + 1))
    with pytest.raises(validator.AlgorithmLifecycleError, match="size limit"):
        _ = validator.validate_repository_lifecycle(manifest)


def test_lifecycle_parent_link_is_rejected_during_discovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A linked algorithm directory cannot supply a lifecycle identity."""
    manifest = _fixture_repository(tmp_path, monkeypatch, _base(validator.EXPERIMENTAL))
    original = manifest.parent
    outside = tmp_path / "outside-algorithm"
    _ = original.rename(outside)
    original.symlink_to(outside, target_is_directory=True)
    with pytest.raises(OSError, match="research directory must not redirect"):
        _ = validator.validate_repository_lifecycle(manifest)
