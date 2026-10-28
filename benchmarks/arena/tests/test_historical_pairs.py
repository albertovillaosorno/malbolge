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
#   - Source-backed classic paired experiment adapter regression evidence.
# - Must-Not:
#   - Represent retained host timing as newly measured or semantic proof.
# - Allows:
#   - Inputs: existing research source files and test-local tampered copies.
#   - Outputs: assertions over retained timing, identity and fail-closed input.
#   - Side effects: test-local copies of source evidence only.
# - Split-When:
#   - Other historical measurement formats become independently admissible.
# - Merge-When:
#   - Research source import testing gains a shared governed adapter suite.
# - Summary:
#   - Locks existing five-paired timing evidence and rejects source drift.
# - Description:
#   - Replays existing research files without running any semantic verifier.
# - Usage:
#   - `python -B -m pytest benchmarks/arena/tests/test_historical_pairs.py`.
# - Defaults:
#   - Only the two supported classic measurement schemas can be imported.
#

"""Checks historical source-reported timing pairs without new measurements."""

# Test assertions intentionally use pytest policy.
# ruff: file-ignore[assert]

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys

import pytest

from benchmarks.arena import historical_pairs

REPO = Path(__file__).resolve().parents[3]
PREFIX = "2026-09-04-classic-prefix-decomposition-linux"
REUSE = "2026-09-04-classic-verified-block-reuse-linux"
BASE = "benchmarks/research/evidence/"
TEMP = BASE + "tampered-classic-pairs"
PAIR_COUNT = 5
PREFIX_BASELINE = "full-candidate-independent-verification-v1"
PREFIX_CANDIDATE = "exact-first-step-prefix-decomposition-v1"
REUSE_BASELINE = "per-request-independent-verification-v1"
REUSE_CANDIDATE = "exact-candidate-verified-result-reuse-v1"
NO_NEW_EXECUTION = "no new execution"
SOURCE_REPORTED = "source-reported-not-reverified"


def _result(name: str) -> dict:
    return historical_pairs.build_report(REPO, BASE + name)


def _copy_source(tmp_path: Path, name: str) -> Path:
    directory = tmp_path / TEMP
    directory.mkdir(parents=True)
    for filename in (
        "experiment.toml",
        "benchmark.toml",
        "raw.csv",
        "source-commit.txt",
    ):
        original = REPO / BASE / name / filename
        destination = directory / filename
        contents = original.read_bytes().replace(
            (BASE + name).encode(),
            TEMP.encode(),
        )
        _ = destination.write_bytes(contents)
    return directory


def _alter(directory: Path, filename: str, *, before: str, after: str) -> None:
    path = directory / filename
    source = path.read_text(encoding="utf-8")
    assert before in source
    _ = path.write_text(source.replace(before, after, 1), encoding="utf-8")


def test_prefix_source_is_retained_null_timing_result() -> None:
    """Recorded prefix verification reduction does not imply lower runtime."""
    report = _result(PREFIX)
    source = report["historical_evidence"]
    assert source["reported_verifier_calls"] == {
        PREFIX_BASELINE: [8836],
        PREFIX_CANDIDATE: [8742],
    }
    pairs = report["paired_baseline_comparisons"]
    assert len(pairs) == 1
    assert pairs[0]["paired_trials"] == PAIR_COUNT
    assert pairs[0]["outcomes"]["both_verified"] == PAIR_COUNT
    assert pairs[0]["cost_differences"]["elapsed_ns"] == {
        "candidate_lower": 2,
        "candidate_equal": 0,
        "candidate_higher": 3,
        "median_candidate_minus_baseline": [25205409, 1],
    }
    assert report["pareto_frontiers"][0]["algorithms"] == [PREFIX_BASELINE]
    results = {point["algorithm"]: point for point in report["capacity_curve"]}
    assert results[PREFIX_BASELINE]["medians"]["elapsed_ns"] == [831921051, 1]
    assert results[PREFIX_CANDIDATE]["medians"]["elapsed_ns"] == [835180632, 1]
    assert NO_NEW_EXECUTION in source["scope"]
    assert source["evidence_status"] == SOURCE_REPORTED


def test_verified_result_reuse_source_preserves_paired_speedup() -> None:
    """Existing reported five-pair reuse win stays separated from proof."""
    report = _result(REUSE)
    source = report["historical_evidence"]
    assert source["reported_verifier_calls"] == {
        REUSE_BASELINE: [17672],
        REUSE_CANDIDATE: [8836],
    }
    pair = report["paired_baseline_comparisons"][0]
    assert pair["paired_trials"] == PAIR_COUNT
    assert pair["outcomes"]["both_verified"] == PAIR_COUNT
    assert pair["cost_differences"]["elapsed_ns"] == {
        "candidate_lower": PAIR_COUNT,
        "candidate_equal": 0,
        "candidate_higher": 0,
        "median_candidate_minus_baseline": [-792780699, 1],
    }
    assert report["pareto_frontiers"][0]["algorithms"] == [REUSE_CANDIDATE]
    medians = {
        p["algorithm"]: p["medians"]["elapsed_ns"]
        for p in report["capacity_curve"]
    }
    assert medians[REUSE_BASELINE] == [1617672749, 1]
    assert medians[REUSE_CANDIDATE] == [851323429, 1]


@pytest.mark.parametrize("name", [PREFIX, REUSE])
def test_exact_source_fingerprints_reproduce(name: str) -> None:
    """Inspect the same retained raw and manifest bytes as the report."""
    reported = _result(name)["historical_evidence"]["source_sha256"]
    assert reported == {
        filename: sha256(
            (REPO / BASE / name / filename).read_bytes()
        ).hexdigest()
        for filename in (
            "benchmark.toml",
            "experiment.toml",
            "raw.csv",
            "source-commit.txt",
        )
    }


@pytest.mark.parametrize(
    "case",
    [
        (PREFIX, "raw.csv", "831921051", "9999999999999999999", "budget"),
        (PREFIX, "raw.csv", "33d23f934b", "3333333333", "quality map"),
        (PREFIX, "raw.csv", "0,full-candidate", "0,unregistered", "strategy"),
        (
            PREFIX,
            "raw.csv",
            "1,full-candidate",
            "0,full-candidate",
            "duplicated",
        ),
        (
            PREFIX,
            "benchmark.toml",
            "equivalent = true",
            "equivalent = false",
            "equivalent_workload",
        ),
        (
            PREFIX,
            "benchmark.toml",
            "repetitions = 5",
            "repetitions = 6",
            "repetition",
        ),
        (
            PREFIX,
            "experiment.toml",
            'outcome = "success"',
            'outcome = "no-solution"',
            "success",
        ),
        (
            PREFIX,
            "raw.csv",
            "full_candidate_verifications,",
            "unregistered_verification_field,",
            "columns differ",
        ),
        (
            REUSE,
            "raw.csv",
            "unique_candidate_count,",
            "unknown_candidate_column,",
            "columns differ",
        ),
        (REUSE, "raw.csv", "9dfe349bf", "1111111111", "quality map"),
        (
            PREFIX,
            "source-commit.txt",
            "ed6825af65aa",
            "000000000000",
            "source-commit pin",
        ),
        (
            PREFIX,
            "raw.csv",
            "8836,8836,8836",
            "8836,8835,8836",
            "full verifier accounting",
        ),
        (
            PREFIX,
            "raw.csv",
            "8742,8742,94",
            "8742,8742,93",
            "discharged-candidate",
        ),
        (REUSE, "raw.csv", "8836,8836,20", "8836,8835,20", "reused-request"),
        (
            REUSE,
            "experiment.toml",
            "baseline_verifier_calls = 17672",
            "baseline_verifier_calls = 17673",
            "verifier-call counts",
        ),
        (
            PREFIX,
            "experiment.toml",
            "best_verified_quality = 1",
            "best_verified_quality = true",
            "registered counter",
        ),
        (
            PREFIX,
            "experiment.toml",
            "candidate_count = 8836",
            "candidate_count = 8835",
            "structural identity drift",
        ),
    ],
)
def test_source_drift_rejected(
    tmp_path: Path,
    case: tuple[str, str, str, str, str],
) -> None:
    """An altered raw row or preregistration never becomes trusted evidence."""
    source, filename, before, after, reason = case
    directory = _copy_source(tmp_path, source)
    _alter(directory, filename, before=before, after=after)
    with pytest.raises(historical_pairs.HistoricalEvidenceError, match=reason):
        historical_pairs.build_report(tmp_path, TEMP)


def test_missing_and_linked_historical_source_rejected(tmp_path: Path) -> None:
    """Versioned import never follows an absent or redirected source file."""
    directory = _copy_source(tmp_path, PREFIX)
    raw_path = directory / "raw.csv"
    raw_path.unlink()
    with pytest.raises(FileNotFoundError, match=r"raw\.csv"):
        historical_pairs.build_report(tmp_path, TEMP)
    raw_path.symlink_to(REPO / BASE / PREFIX / "raw.csv")
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="symlink"
    ):
        historical_pairs.build_report(tmp_path, TEMP)


def test_unsupported_source_root_rejected(tmp_path: Path) -> None:
    """Callers cannot import unrelated data paths into a performance claim."""
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="research evidence"
    ):
        historical_pairs.build_report(tmp_path, "untrusted/samples")


def test_incomplete_quality_fingerprint_rejected(tmp_path: Path) -> None:
    """A matching row is insufficient without valid registered SHA-256."""
    directory = _copy_source(tmp_path, PREFIX)
    source = (directory / "experiment.toml").read_text(encoding="utf-8")
    section = source.split("[prefix_decomposition_measurement]", 1)
    original = section[1]
    fingerprint = original.split('quality_map_sha256 = "', 1)[1].split('"', 1)[
        0
    ]
    original = original.replace(
        'quality_map_sha256 = "' + fingerprint + '"',
        'quality_map_sha256 = "not-a-digest"',
    )
    _ = (directory / "experiment.toml").write_text(
        section[0] + "[prefix_decomposition_measurement]" + original,
        encoding="utf-8",
    )
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError,
        match="quality-map fingerprint",
    ):
        historical_pairs.build_report(tmp_path, TEMP)


def test_historical_cli_prints_no_partial_result_on_bad_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Historical replay prints an entire arena report or no JSON at all."""
    directory = _copy_source(tmp_path, PREFIX)
    monkeypatch.setattr(
        sys,
        "argv",
        ["historical-pairs", TEMP, "--root", str(tmp_path)],
    )
    assert historical_pairs.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result["historical_evidence"]["evidence_status"] == SOURCE_REPORTED
    _alter(
        directory,
        "raw.csv",
        before="831921051",
        after="9999999999999999999",
    )
    with pytest.raises(SystemExit, match="2"):
        historical_pairs.main()
    rejected = capsys.readouterr()
    assert not rejected.out
    assert rejected.err.startswith("arena historical evidence:")
