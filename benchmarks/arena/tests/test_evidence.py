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
#   - Cross-record experiment identity and raw-file preflight regressions.
# - Must-Not:
#   - Claim that fixture data were physically measured or verified.
# - Allows:
#   - Inputs: synthetic run manifests and temporary nonempty raw samples.
#   - Outputs: exact checked-link counts and fail-closed diagnostics.
#   - Side effects: test-local files and temporary symlinks.
# - Split-When:
#   - Real hardware evidence acceptance needs separate integration fixtures.
# - Merge-When:
#   - Experiment manifest tests absorb cross-record arena obligations.
# - Summary:
#   - Covers optional arena manifest and reported-trial preflight.
# - Description:
#   - Uses the production experiment parser with synthetic file identities.
# - Usage:
#   - `python -B -m pytest benchmarks/arena/tests/test_evidence.py -q`.
# - Defaults:
#   - Missing, drifted, or unsafe paths reject without published metrics.
#

"""Synthetic-only experiment link checks for the multi-objective arena."""

# Assertions here have the same test-only policy as tests/**/*.py.
# ruff: file-ignore[assert]

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

import pytest

from benchmarks.arena import analyze
from benchmarks.arena import evidence

REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = (
    REPO_ROOT
    / "benchmarks/research/protocol/examples/deterministic.experiment.toml"
).read_text(encoding="utf-8")
EXPECTED_FAMILY = "protocol-fixture-v1"
ALGORITHM_COUNT = 2
CANDIDATE_ALGORITHM = "candidate"
DIGEST_SCOPE = "no content digest verification"
MISSING_FILE = "missing"
EMPTY_FILE = "empty"
LINKED_ERROR = "linked arena evidence invalid"
EXPECTED_DIGEST = "b" * analyze.SHA256_HEX_LENGTH
RAW_TEMPLATE_PATH = (
    'raw_output = "benchmarks/research/protocol/examples/deterministic-raw.csv"'
)


def sample_study(root: Path) -> dict[str, Any]:
    """Construct a synthetic two-algorithm experiment-run comparison.

    Returns:
        An in-memory report with linked temporary manifests and CSV paths.

    """
    directory = root / "evidence"
    directory.mkdir()
    observations = []
    for algorithm in ("baseline", "candidate"):
        manifest_path = f"evidence/{algorithm}.toml"
        sample_path = f"evidence/{algorithm}.csv"
        manifest = TEMPLATE.replace(
            'id = "deterministic-protocol-fixture"',
            f'id = "{algorithm}"',
        ).replace(
            RAW_TEMPLATE_PATH,
            f'raw_output = "{sample_path}"',
        )
        _ = (root / manifest_path).write_text(manifest, encoding="utf-8")
        _ = (root / sample_path).write_text(
            "trial,elapsed_ns\n0,10\n",
            encoding="utf-8",
        )
        observations.append({
            "algorithm": algorithm,
            "case": {
                "family": EXPECTED_FAMILY,
                "version": 1,
                "difficulty": 1,
                "seed": 0,
                "workload_sha256": EXPECTED_DIGEST,
            },
            "trial": 0,
            "outcome": analyze.VERIFIED,
            "verifier": "protocol-fixture-oracle",
            "verifier_verdict": analyze.ACCEPTED,
            "experiment_manifest": manifest_path,
            "raw_sample": sample_path,
            "metrics": {"elapsed_ns": 10, "artifact_bytes": 20},
        })
    return {
        "schema_version": 1,
        "study": {
            "id": "synthetic-links",
            "question": "Do both run reports agree?",
            "hypothesis": "Both link identities remain consistent.",
            "baseline": "baseline",
            "rejection_observation": "Any reported run identity drifts.",
            "stage": "ternary-ir",
            "target_profile": "profile-independent",
            "host": "fixture-host",
            "toolchain": "protocol-fixture-toolchain-v1",
            "budget": {"time_ns": 1000, "memory_bytes": 1024},
            "objectives": ["elapsed_ns", "artifact_bytes"],
        },
        "observations": observations,
    }


def _admit(document: dict[str, Any], root: Path) -> dict[str, Any]:
    parsed = analyze.parse_document(json.dumps(document))
    return evidence.validate_links(parsed, root)


def _modify_manifest(
    root: Path,
    algorithm: str,
    *,
    old: str,
    new: str,
) -> None:
    path = root / "evidence" / f"{algorithm}.toml"
    _ = path.write_text(
        path.read_text(encoding="utf-8").replace(old, new),
        encoding="utf-8",
    )


def test_links_are_checked_without_certification(tmp_path: Path) -> None:
    """Existing manifest parser cross-checks exactly two distinct run links."""
    document = sample_study(tmp_path)
    result = _admit(document, tmp_path)
    assert result["manifest_links_checked"] == ALGORITHM_COUNT
    assert result["raw_sample_paths_checked"] == ALGORITHM_COUNT
    assert result["reported_trials_checked"] == ALGORITHM_COUNT
    assert DIGEST_SCOPE in result["scope"]


@pytest.mark.parametrize(
    ("previous", "replacement", "diagnostic"),
    [
        ('id = "baseline"', 'id = "other"', "experiment ID"),
        (f'family = "{EXPECTED_FAMILY}"', 'family = "wrong"', "family"),
        ("difficulty = 1", "difficulty = 2", "difficulty"),
        ("seed = 0", "seed = 2", "seed"),
        (
            'target_profile = "profile-independent"',
            'target_profile = "multi-profile"',
            "target profile",
        ),
        (
            'oracle = "protocol-fixture-oracle"',
            'oracle = "different-verifier"',
            "oracle",
        ),
        (
            f'workload_sha256 = "{EXPECTED_DIGEST}"',
            f'workload_sha256 = "{"c" * analyze.SHA256_HEX_LENGTH}"',
            "workload digest",
        ),
        ('host = "fixture-host"', 'host = "wrong-host"', "host/toolchain"),
        (
            'toolchain = "protocol-fixture-toolchain-v1"',
            'toolchain = "wrong-toolchain"',
            "host/toolchain",
        ),
        ('outcome = "success"', 'outcome = "no-solution"', "run outcome"),
        (
            'raw_output = "evidence/baseline.csv"',
            'raw_output = "evidence/other.csv"',
            "raw output",
        ),
    ],
)
def test_manifest_identity_drift_rejected(
    tmp_path: Path,
    previous: str,
    replacement: str,
    *,
    diagnostic: str,
) -> None:
    """Every available run identity dimension is bound to its arena claim."""
    document = sample_study(tmp_path)
    _modify_manifest(tmp_path, "baseline", old=previous, new=replacement)
    with pytest.raises(evidence.EvidenceError, match=diagnostic):
        _admit(document, tmp_path)


def test_consistent_rejected_run_keeps_failure_count(tmp_path: Path) -> None:
    """A reported rejection survives cross-check without becoming a success."""
    document = sample_study(tmp_path)
    _modify_manifest(
        tmp_path,
        CANDIDATE_ALGORITHM,
        old='outcome = "success"',
        new='outcome = "candidate-invalid"',
    )
    row = document["observations"][1]
    row["outcome"] = analyze.VERIFIER_REJECTED
    row["verifier_verdict"] = analyze.REJECTED
    del row["metrics"]["artifact_bytes"]
    assert (
        _admit(document, tmp_path)["reported_trials_checked"] == ALGORITHM_COUNT
    )
    report = analyze.analyze(analyze.parse_document(json.dumps(document)))
    candidate = next(
        point
        for point in report["capacity_curve"]
        if point["algorithm"] == CANDIDATE_ALGORITHM
    )
    assert candidate["verified"] == 0
    assert candidate["outcomes"][analyze.VERIFIER_REJECTED] == 1


@pytest.mark.parametrize("path_kind", ["missing", "empty", "symlink"])
def test_missing_empty_or_linked_raw_file_rejected(
    tmp_path: Path,
    path_kind: str,
) -> None:
    """A retained raw path cannot be missing, empty, or a symlink."""
    document = sample_study(tmp_path)
    sample = tmp_path / "evidence/baseline.csv"
    if path_kind == MISSING_FILE:
        sample.unlink()
    elif path_kind == EMPTY_FILE:
        _ = sample.write_bytes(b"")
    else:
        sample.unlink()
        sample.symlink_to(tmp_path / "evidence/candidate.csv")
    with pytest.raises(evidence.EvidenceError, match=r"evidence|symlink"):
        _admit(document, tmp_path)


def test_corrupt_or_oversized_manifest_rejected(tmp_path: Path) -> None:
    """No oversized or malformed run manifest reaches summary admission."""
    document = sample_study(tmp_path)
    manifest = tmp_path / "evidence/baseline.toml"
    _ = manifest.write_text("invalid = {\n", encoding="utf-8")
    with pytest.raises(evidence.EvidenceError, match="invalid"):
        _admit(document, tmp_path)
    with manifest.open("wb") as stream:
        _ = stream.seek(evidence.MAX_MANIFEST_BYTES)
        _ = stream.write(b"a")
    with pytest.raises(evidence.EvidenceError, match="byte limit"):
        _admit(document, tmp_path)


def test_cli_cross_checks_before_reporting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI only reports metrics with all indicated file links intact."""
    document = sample_study(tmp_path)
    input_path = tmp_path / "study.json"
    _ = input_path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["arena-evidence", str(input_path), "--root", str(tmp_path)],
    )
    assert evidence.main() == 0
    output = json.loads(capsys.readouterr().out)
    assert (
        output["evidence_preflight"]["manifest_links_checked"]
        == ALGORITHM_COUNT
    )
    (tmp_path / "evidence/baseline.csv").unlink()
    with pytest.raises(SystemExit, match="2"):
        evidence.main()
    error = capsys.readouterr()
    assert not error.out
    assert LINKED_ERROR in error.err


def test_direct_link_api_rejects_parent_traversal(tmp_path: Path) -> None:
    """Even a caller bypassing schema admission cannot read a parent path."""
    document = sample_study(tmp_path)
    document["observations"][0]["experiment_manifest"] = "../escape.toml"
    with pytest.raises(evidence.EvidenceError, match="canonical relative"):
        evidence.validate_links(document, tmp_path)


BUDGET_SECONDS = 1
BUDGET_MEMORY_MIB = 128
BYTES_PER_MIB = 1_048_576
NANOSECONDS_PER_SECOND = 1_000_000_000
BUDGET_DIAGNOSTIC = "declared budget differs"
NOT_ENFORCED = "no physical budget enforcement"


def _budgeted_study(root: Path) -> dict[str, Any]:
    doc = sample_study(root)
    doc["study"]["budget"] = {
        "time_ns": BUDGET_SECONDS * NANOSECONDS_PER_SECOND,
        "memory_bytes": BUDGET_MEMORY_MIB * BYTES_PER_MIB,
    }
    for row in doc["observations"]:
        path = root / row["experiment_manifest"]
        text = path.read_text(encoding="utf-8")
        _ = path.write_text(
            text.replace(
                "seconds = 1",
                "seconds = 1\nmemory_mib = 128",
            ),
            encoding="utf-8",
        )
    return doc


def _budget_preflight(doc: dict[str, Any], root: Path) -> dict[str, Any]:
    admitted = analyze.parse_document(json.dumps(doc))
    return evidence.validate_links(
        admitted,
        root,
        policy=evidence.EvidencePolicy(require_budget_agreement=True),
    )


def test_opt_in_run_budget_binding_reports_exact_declared_limits(
    tmp_path: Path,
) -> None:
    """Each run must declare the same nanosecond/MiB study resource limits."""
    doc = _budgeted_study(tmp_path)
    checked = _budget_preflight(doc, tmp_path)
    assert checked["run_budget_links_checked"] == ALGORITHM_COUNT
    assert NOT_ENFORCED in checked["scope"]


@pytest.mark.parametrize(
    ("previous", "replacement", "message"),
    [
        ("seconds = 1", "seconds = 2", BUDGET_DIAGNOSTIC),
        ("memory_mib = 128", "memory_mib = 129", BUDGET_DIAGNOSTIC),
        ("memory_mib = 128", "memory_mib = true", "positive integer"),
        ("memory_mib = 128", "memory_mib = -1", "positive integer"),
        ("memory_mib = 128", "memory_mib = 1.5", "positive integer"),
        ("seconds = 1", "seconds = false", "positive integer"),
        ("seconds = 1", "seconds = 0", "positive integer"),
        ("memory_mib = 128", "", "positive integer"),
    ],
)
def test_run_budget_drift_is_rejected_without_performance_claim(
    tmp_path: Path,
    previous: str,
    replacement: str,
    *,
    message: str,
) -> None:
    """Budget values must agree with the registered workload limit exactly."""
    doc = _budgeted_study(tmp_path)
    _modify_manifest(
        tmp_path,
        "baseline",
        old=previous,
        new=replacement,
    )
    with pytest.raises(evidence.EvidenceError, match=message):
        _budget_preflight(doc, tmp_path)


@pytest.mark.parametrize("dimension", ["time_ns", "memory_bytes"])
def test_study_budget_unit_drift_fails_even_by_one_unit(
    tmp_path: Path,
    dimension: str,
) -> None:
    """Whole-second and MiB declarations never round nanosecond/byte drift."""
    doc = _budgeted_study(tmp_path)
    doc["study"]["budget"][dimension] += 1
    with pytest.raises(evidence.EvidenceError, match=BUDGET_DIAGNOSTIC):
        _budget_preflight(doc, tmp_path)


def test_budget_requirement_is_optional_for_old_one_bound_manifests(
    tmp_path: Path,
) -> None:
    """Normal linked-run preflight still admits the governed fixture record."""
    doc = sample_study(tmp_path)
    assert _admit(doc, tmp_path)["reported_trials_checked"] == ALGORITHM_COUNT
    with pytest.raises(evidence.EvidenceError, match="memory_mib"):
        _budget_preflight(doc, tmp_path)


def test_budget_cli_drift_omits_entire_capacity_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """No Pareto JSON escapes after a reported run-budget mismatch."""
    doc = _budgeted_study(tmp_path)
    input_path = tmp_path / "study.json"
    _ = input_path.write_text(json.dumps(doc), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "arena-evidence",
            str(input_path),
            "--root",
            str(tmp_path),
            "--require-budget-agreement",
        ],
    )
    assert evidence.main() == 0
    admitted = json.loads(capsys.readouterr().out)
    assert (
        admitted["evidence_preflight"]["run_budget_links_checked"]
        == ALGORITHM_COUNT
    )
    _modify_manifest(
        tmp_path,
        "candidate",
        old="memory_mib = 128",
        new="memory_mib = 129",
    )
    with pytest.raises(SystemExit, match="2"):
        evidence.main()
    result = capsys.readouterr()
    assert not result.out
    assert BUDGET_DIAGNOSTIC in result.err
