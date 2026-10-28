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
#   - Arena comparison, failure retention, and admission regressions.
# - Must-Not:
#   - Claim synthetic fixture measurements as real performance.
# - Allows:
#   - Inputs: in-memory version-one synthetic study records.
#   - Outputs: assertions about deterministic reported-evidence analysis.
#   - Side effects: temporary CLI input during tests.
# - Split-When:
#   - A dedicated physical benchmark runner needs independent tests.
# - Merge-When:
#   - An owning arena test module replaces the current fixtures.
# - Summary:
#   - Tests exact cohorts, Pareto tradeoffs and fail-closed input.
# - Description:
#   - Covers schema and statistical semantics without a target backend.
# - Usage:
#   - python3.14 -B -m pytest benchmarks/arena/tests/test_analyze.py -q
# - Defaults:
#   - No candidate is considered verified without reported verifier evidence.
#

"""Synthetic, never performance-authoritative arena analysis regressions."""

# Test assertions are intentional (equivalent to tests/**/*.py Ruff policy).
# ruff: file-ignore[assert]

from __future__ import annotations

import copy
import json
import sys
from typing import Any
from typing import TYPE_CHECKING

import pytest

from benchmarks.arena import analyze

if TYPE_CHECKING:
    from pathlib import Path

STAGE = "ternary-ir"
CANDIDATE = "candidate"
BASELINE = "baseline"
FIRST_DIFFICULTY = 1
SECOND_DIFFICULTY = 2
SECOND_SEED = 4
TIME_DIMENSION = "time"
LARGE_INPUT_DIAGNOSTIC = "exceeds 16 MiB"
NON_FILE_DIAGNOSTIC = "regular file"
HASH_A = "a" * analyze.SHA256_HEX_LENGTH
HASH_B = "b" * analyze.SHA256_HEX_LENGTH


def _observation(
    algorithm: str,
    difficulty: int,
    trial: int,
    *,
    outcome: str = analyze.VERIFIED,
) -> dict[str, Any]:
    verdict = {
        analyze.VERIFIED: analyze.ACCEPTED,
        analyze.VERIFIER_REJECTED: analyze.REJECTED,
    }.get(outcome, analyze.NOT_RUN)
    return {
        "algorithm": algorithm,
        "case": {
            "family": "arithmetic-dag",
            "version": 1,
            "difficulty": difficulty,
            "seed": trial + 3,
            "workload_sha256": (
                HASH_A if difficulty == FIRST_DIFFICULTY else HASH_B
            ),
        },
        "trial": 0,
        "outcome": outcome,
        "verifier": "independent-canonical-verifier",
        "verifier_verdict": verdict,
        "experiment_manifest": "algorithms/example/experiment.toml",
        "raw_sample": "algorithms/example/out/samples.csv",
        "metrics": (
            {"elapsed_ns": 10, "artifact_bytes": 40}
            if outcome == analyze.VERIFIED
            else {"elapsed_ns": 10}
        ),
    }


def _document() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "study": {
            "id": "synthetic-scaling-v1",
            "question": "Is candidate faster on identical work?",
            "hypothesis": "Candidate median verified time is lower.",
            "baseline": BASELINE,
            "rejection_observation": "Candidate does not improve the frontier.",
            "stage": STAGE,
            "target_profile": "malbolge-2026",
            "host": "synthetic-host",
            "toolchain": "synthetic-toolchain",
            "budget": {"time_ns": 10000, "memory_bytes": 65536},
            "objectives": ["elapsed_ns", "artifact_bytes"],
        },
        "observations": [
            _observation(BASELINE, FIRST_DIFFICULTY, 0),
            _observation(BASELINE, FIRST_DIFFICULTY, 1),
            _observation(CANDIDATE, FIRST_DIFFICULTY, 0),
            _observation(CANDIDATE, FIRST_DIFFICULTY, 1),
            _observation(BASELINE, SECOND_DIFFICULTY, 0),
            _observation(BASELINE, SECOND_DIFFICULTY, 1),
            _observation(CANDIDATE, SECOND_DIFFICULTY, 0),
            _observation(
                CANDIDATE,
                SECOND_DIFFICULTY,
                1,
                outcome=analyze.VERIFIER_REJECTED,
            ),
        ],
    }


def _run(document: dict[str, Any]) -> dict[str, Any]:
    return analyze.analyze(analyze.parse_document(json.dumps(document)))


def _point(report: dict[str, Any], algorithm: str, difficulty: int) -> dict:
    return next(
        row
        for row in report["capacity_curve"]
        if row["algorithm"] == algorithm and row["difficulty"] == difficulty
    )


def test_capacity_and_frontiers_preserve_success_tradeoff() -> None:
    """Conditional Pareto keeps fast/less-reliable candidate visible."""
    document = _document()
    for row in document["observations"]:
        if row["algorithm"] == BASELINE:
            row["metrics"] = {"elapsed_ns": 50, "artifact_bytes": 60}
        elif row["outcome"] == analyze.VERIFIED:
            row["metrics"] = {"elapsed_ns": 30, "artifact_bytes": 40}
    report = _run(document)
    assert report["stage"] == STAGE
    frontiers = report["pareto_frontiers"]
    assert len(frontiers) == SECOND_DIFFICULTY
    assert frontiers[0]["algorithms"] == [CANDIDATE]
    assert frontiers[1]["algorithms"] == [BASELINE, CANDIDATE]
    point = _point(report, CANDIDATE, SECOND_DIFFICULTY)
    assert point["success_fraction"] == [1, 2]
    assert point["outcomes"][analyze.VERIFIER_REJECTED] == 1
    assert point["medians"] == {
        "elapsed_ns": [30, 1],
        "artifact_bytes": [40, 1],
    }
    capacities = report["highest_observed_verified_difficulty"]
    assert [row["algorithm"] for row in capacities] == [BASELINE, CANDIDATE]
    assert all(
        row["highest_observed_verified_difficulty"] == SECOND_DIFFICULTY
        for row in capacities
    )


def test_failed_attempts_remain_but_do_not_enter_pareto() -> None:
    """Resource-exhausted attempts count against the reported success rate."""
    document = _document()
    for row in document["observations"]:
        if (
            row["algorithm"] == CANDIDATE
            and row["case"]["difficulty"] == SECOND_DIFFICULTY
        ):
            row["outcome"] = "resource_exhausted"
            row["verifier_verdict"] = analyze.NOT_RUN
            row["metrics"] = {"elapsed_ns": 90}
    report = _run(document)
    point = _point(report, CANDIDATE, SECOND_DIFFICULTY)
    assert point["success_fraction"] == [0, 2]
    assert point["medians"] == {
        "elapsed_ns": None,
        "artifact_bytes": None,
    }
    assert report["pareto_frontiers"][1][
        "excluded_without_verified_solution"
    ] == [CANDIDATE]
    capacity = report["highest_observed_verified_difficulty"]
    assert (
        capacity[1]["highest_observed_verified_difficulty"] == FIRST_DIFFICULTY
    )


def test_tradeoffs_are_incomparable() -> None:
    """A smaller artifact need not dominate a faster competitor."""
    document = _document()
    for row in document["observations"]:
        if row["algorithm"] == CANDIDATE:
            row["metrics"]["elapsed_ns"] = 8
            if row["outcome"] == analyze.VERIFIED:
                row["metrics"]["artifact_bytes"] = 90
    report = _run(document)
    assert report["pareto_frontiers"][0]["algorithms"] == [BASELINE, CANDIDATE]


def test_even_median_remains_exact_beyond_float_precision() -> None:
    """Large integer median comparisons cannot collapse into float ties."""
    document = _document()
    huge = 2**64
    for row in document["observations"]:
        if row["algorithm"] == BASELINE:
            row["metrics"]["artifact_bytes"] = huge + 2
        elif row["outcome"] == analyze.VERIFIED:
            row["metrics"]["artifact_bytes"] = huge + 1
    report = _run(document)
    assert report["pareto_frontiers"][0]["algorithms"] == [CANDIDATE]
    assert _point(report, CANDIDATE, FIRST_DIFFICULTY)["medians"][
        "artifact_bytes"
    ] == [huge + 1, 1]
    document["observations"][0]["metrics"]["artifact_bytes"] = huge + 3
    report = _run(document)
    assert _point(report, BASELINE, FIRST_DIFFICULTY)["medians"][
        "artifact_bytes"
    ] == [2 * huge + 5, 2]


def test_observation_order_does_not_affect_report() -> None:
    """Input order is not a hidden scoring dimension."""
    document = _document()
    expected = _run(document)
    document["observations"].reverse()
    assert expected == _run(document)


@pytest.mark.parametrize("field", ["seed", "workload_sha256", "trial"])
def test_unmatched_trial_cohorts_fail_closed(field: str) -> None:
    """Algorithms cannot compare different instances or replicate numbers."""
    document = _document()
    row = document["observations"][2]
    changes = {
        "seed": (row["case"], 91),
        "workload_sha256": (row["case"], "c" * analyze.SHA256_HEX_LENGTH),
        "trial": (row, 7),
    }
    mapping, value = changes[field]
    mapping[field] = value
    with pytest.raises(analyze.ArenaError, match="unmatched trial/workload"):
        _run(document)


def test_missing_declared_baseline_rejected() -> None:
    """No study can silently report a candidate-only comparative frontier."""
    document = _document()
    document["study"]["baseline"] = "omitted-baseline"
    with pytest.raises(analyze.ArenaError, match="missing declared baseline"):
        _run(document)


def test_duplicate_trial_and_boolean_integer_fail_closed() -> None:
    """Duplicate, boolean or zero-valued budget identities are malformed."""
    document = _document()
    document["observations"].append(copy.deepcopy(document["observations"][0]))
    with pytest.raises(analyze.ArenaError, match="duplicate"):
        _run(document)
    document = _document()
    document["observations"][0]["metrics"]["elapsed_ns"] = True
    with pytest.raises(analyze.ArenaError, match="integer"):
        _run(document)
    document = _document()
    document["study"]["budget"]["time_ns"] = 0
    with pytest.raises(analyze.ArenaError, match="positive"):
        _run(document)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("verifier_verdict", analyze.NOT_RUN),
        ("verifier", CANDIDATE),
        ("outcome", "unrecognized"),
        ("outcome", []),
    ],
)
def test_invalid_or_self_certifying_verdict_rejected(
    key: str,
    value: object,
) -> None:
    """A producer cannot self-admit a successful reported candidate."""
    document = _document()
    document["observations"][2][key] = value
    with pytest.raises(analyze.ArenaError, match=r"verifier|outcome"):
        _run(document)


@pytest.mark.parametrize("field", ["missing", "unknown", "relative", "hash"])
def test_missing_cost_unknown_metric_and_invalid_evidence(field: str) -> None:
    """A claimed success must carry exact declared costs and evidence paths."""
    document = _document()
    row = document["observations"][0]
    changes = {
        "missing": lambda: row["metrics"].pop("artifact_bytes"),
        "unknown": lambda: row["metrics"].update({"energy_joules": 3}),
        "relative": lambda: row.update({"raw_sample": "../untrusted.csv"}),
        "hash": lambda: row["case"].update({"workload_sha256": HASH_A.upper()}),
    }
    _ = changes[field]()
    with pytest.raises(
        analyze.ArenaError, match=r"metric|path|SHA-256|objective"
    ):
        _run(document)


@pytest.mark.parametrize(
    "text",
    [
        '{"id": 1, "id": 2}',
        '{"a": NaN}',
        '{"a": Infinity}',
    ],
)
def test_duplicate_keys_and_nonfinite_numbers_fail_closed(text: str) -> None:
    """JSON syntax must not obscure a measurement or study authority."""
    with pytest.raises(analyze.ArenaError, match=r"duplicate|nonfinite"):
        analyze.parse_document(text)


def test_cli_prints_json_and_rejects_invalid_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI output is machine-readable and failures publish no partial JSON."""
    path = tmp_path / "samples.json"
    _ = path.write_text(json.dumps(_document()), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["arena", str(path)])
    assert analyze.main() == 0
    output = capsys.readouterr()
    assert json.loads(output.out) == _run(_document())
    _ = path.write_text('{"schema_version": false}', encoding="utf-8")
    with pytest.raises(SystemExit, match="2"):
        analyze.main()
    failed = capsys.readouterr()
    assert not failed.out
    assert failed.err.startswith("arena:")


@pytest.mark.parametrize("field", ["outcome", "verifier_verdict"])
def test_unhashable_claimed_verdict_is_typed_error(field: str) -> None:
    """Untrusted JSON arrays must not cause an untyped host exception."""
    document = _document()
    document["observations"][0][field] = []
    with pytest.raises(analyze.ArenaError, match=r"verdict|outcome"):
        _run(document)


@pytest.mark.parametrize("dimension", ["time", "memory"])
def test_over_budget_verified_evidence_rejected(dimension: str) -> None:
    """A claimed verified run cannot exceed its stated fixed budget."""
    document = _document()
    metrics = document["observations"][0]["metrics"]
    if dimension == TIME_DIMENSION:
        metrics["elapsed_ns"] = document["study"]["budget"]["time_ns"] + 1
    else:
        metrics["peak_rss_bytes"] = (
            document["study"]["budget"]["memory_bytes"] + 1
        )
    with pytest.raises(analyze.ArenaError, match=r"exceeds study budget"):
        _run(document)


def test_single_algorithm_is_not_a_multi_algorithm_comparison() -> None:
    """A declared baseline cannot create a Pareto frontier by itself."""
    document = _document()
    document["observations"] = [
        item
        for item in document["observations"]
        if item["algorithm"] == BASELINE
    ]
    with pytest.raises(analyze.ArenaError, match="no comparison algorithm"):
        _run(document)


@pytest.mark.parametrize(
    "objectives",
    [
        ["energy_joules"],
        [3],
        [{"name": "elapsed_ns"}],
        ["elapsed_ns", "elapsed_ns"],
        [],
    ],
)
def test_unsupported_objective_fails_closed(objectives: list[object]) -> None:
    """Unregistered and unhashable objectives cannot become Pareto authority."""
    document = _document()
    document["study"]["objectives"] = objectives
    with pytest.raises(analyze.ArenaError, match=r"study\.objectives"):
        _run(document)


def test_cli_rejects_large_and_linked_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """External inputs cannot redirect or force unbounded memory reads."""
    original = tmp_path / "input.json"
    with original.open("wb") as stream:
        _ = stream.seek(analyze.MAX_INPUT_BYTES)
        _ = stream.write(b"a")
    monkeypatch.setattr(sys, "argv", ["arena", str(original)])
    with pytest.raises(SystemExit, match="2"):
        analyze.main()
    first = capsys.readouterr()
    assert LARGE_INPUT_DIAGNOSTIC in first.err
    assert not first.out
    linked = tmp_path / "linked.json"
    try:
        linked.symlink_to(original)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"host has no symlink support: {error}")
    monkeypatch.setattr(sys, "argv", ["arena", str(linked)])
    with pytest.raises(SystemExit, match="2"):
        analyze.main()
    second = capsys.readouterr()
    assert NON_FILE_DIAGNOSTIC in second.err
    assert not second.out


def test_exact_even_sample_dispersion_and_failure_inclusive_elapsed() -> None:
    """All-attempt time exposes failure cost ignored by successful medians."""
    document = _document()
    for row in document["observations"]:
        if row["algorithm"] == BASELINE and row["case"]["difficulty"] == 1:
            row["metrics"]["elapsed_ns"] = 10 + row["case"]["seed"] - 3
    candidate = next(
        row
        for row in document["observations"]
        if row["algorithm"] == CANDIDATE
        and row["case"]["difficulty"] == SECOND_DIFFICULTY
        and row["outcome"] != analyze.VERIFIED
    )
    candidate["metrics"]["elapsed_ns"] = 110
    report = _run(document)
    baseline = _point(report, BASELINE, FIRST_DIFFICULTY)
    assert baseline["medians"]["elapsed_ns"] == [21, 2]
    assert baseline["median_absolute_deviation"]["elapsed_ns"] == [1, 2]
    assert baseline["successful_range"]["elapsed_ns"] == [10, 11]
    point = _point(report, CANDIDATE, SECOND_DIFFICULTY)
    assert point["medians"]["elapsed_ns"] == [10, 1]
    assert point["median_absolute_deviation"]["elapsed_ns"] == [0, 1]
    assert point["successful_range"]["elapsed_ns"] == [10, 10]
    assert point["all_attempt_elapsed_ns"] == {
        "median": [60, 1],
        "median_absolute_deviation": [50, 1],
        "range": [10, 110],
    }


def test_zero_success_still_reports_all_attempt_dispersion() -> None:
    """Null conditional statistics never discard unsuccessful elapsed time."""
    document = _document()
    failures = [
        row
        for row in document["observations"]
        if row["algorithm"] == CANDIDATE
        and row["case"]["difficulty"] == SECOND_DIFFICULTY
    ]
    for index, row in enumerate(failures):
        row["outcome"] = "resource_exhausted"
        row["verifier_verdict"] = analyze.NOT_RUN
        row["metrics"] = {"elapsed_ns": 90 + index * 10}
    point = _point(_run(document), CANDIDATE, SECOND_DIFFICULTY)
    assert point["medians"]["elapsed_ns"] is None
    assert point["median_absolute_deviation"]["elapsed_ns"] is None
    assert point["successful_range"]["elapsed_ns"] is None
    assert point["all_attempt_elapsed_ns"] == {
        "median": [95, 1],
        "median_absolute_deviation": [5, 1],
        "range": [90, 100],
    }


def test_exact_dispersion_does_not_round_large_costs() -> None:
    """A half-unit MAD remains visible above the IEEE-754 integer range."""
    document = _document()
    huge = 2**80
    for row in document["observations"]:
        if row["algorithm"] == BASELINE:
            row["metrics"]["artifact_bytes"] = huge + row["case"]["seed"] - 3
    point = _point(_run(document), BASELINE, FIRST_DIFFICULTY)
    assert point["medians"]["artifact_bytes"] == [2 * huge + 1, 2]
    assert point["median_absolute_deviation"]["artifact_bytes"] == [1, 2]
    assert point["successful_range"]["artifact_bytes"] == [huge, huge + 1]


def test_oracle_identity_drift_rejects_matched_algorithm_comparison() -> None:
    """Matching inputs are not comparable under different verifier versions."""
    document = _document()
    document["observations"][2]["verifier"] = "different-oracle"
    with pytest.raises(analyze.ArenaError, match="verifier cohort"):
        _run(document)


def test_distinct_per_instance_oracles_are_allowed_when_matched() -> None:
    """One verifier per case is required, not one for the whole difficulty."""
    document = _document()
    for row in document["observations"]:
        if row["case"]["seed"] == SECOND_SEED:
            row["verifier"] = "oracle-for-second-instance"
    report = _run(document)
    assert report["pareto_frontiers"][0]["algorithms"] == [BASELINE, CANDIDATE]
