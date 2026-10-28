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
#   - Synthetic retained raw CSV admission regressions for arena studies.
# - Must-Not:
#   - Mistake synthetic CSV fixtures for independently verified performance.
# - Allows:
#   - Inputs: synthetic study records and test-local CSV files.
#   - Outputs: assertions about source-byte and trial/metric identity checks.
#   - Side effects: bounded test-local CSV files.
# - Split-When:
#   - A second versioned raw format requires an independent test suite.
# - Merge-When:
#   - The benchmark protocol validator owns arena raw evidence admission.
# - Summary:
#   - Rejects measurement drift and incomplete or extraneous raw CSV rows.
# - Description:
#   - Verifies byte-exact source identity, not semantic verifier outcomes.
# - Usage:
#   - `python -B -m pytest benchmarks/arena/tests/test_raw_samples.py`.
# - Defaults:
#   - Every declared record must match one and only one retained raw row.
#

"""Synthetic-only checks of canonical arena raw measurements."""

# Tests intentionally assert on failure behavior.
# ruff: file-ignore[assert]

from __future__ import annotations

import copy
import csv
from hashlib import sha256
from io import StringIO
import json
import sys
from typing import Any
from typing import TYPE_CHECKING

import pytest

from benchmarks.arena import analyze
from benchmarks.arena import evidence
from benchmarks.arena import raw_samples
from benchmarks.arena.tests.test_evidence import sample_study

if TYPE_CHECKING:
    from pathlib import Path

ROOT_LABEL = "evidence/baseline.csv"
RAW_HASH_FIELD = "raw_file_sha256"
NO_AUTHENTICATION = "no provenance authentication"
NO_RAW_DIGEST = "no content digest verification"
CSV_HEADER_ERROR = "CSV header"
INVALID_RAW_ROW = r"raw|evidence"
MISSING = "missing"
DUPLICATE = "duplicate"
EXTRA = "extra"
COLUMN = "column"
UTF8 = "utf8"
NUL = "nul"
QUOTE = "unterminated-quote"
EMPTY = "empty"
OVERSIZED = "oversized"
ALGORITHM_COUNT = 2
ROW_MISMATCH = "raw CSV trial/metric rows differ"


def _render(records: list[dict[str, Any]]) -> bytes:
    """Build fixture CSV independently of the production row encoder.

    Returns:
        A canonical encoded version-one CSV for the supplied trial records.

    """
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    _ = writer.writerow(raw_samples.HEADER)
    for record in records:
        case = record["case"]
        fields = {
            "schema_version": "1",
            "algorithm": record["algorithm"],
            "family": case["family"],
            "version": str(case["version"]),
            "difficulty": str(case["difficulty"]),
            "seed": str(case["seed"]),
            "workload_sha256": case["workload_sha256"],
            "trial": str(record["trial"]),
            "outcome": record["outcome"],
            "verifier": record["verifier"],
            "verifier_verdict": record["verifier_verdict"],
            **{key: str(value) for key, value in record["metrics"].items()},
        }
        _ = writer.writerow([fields.get(key, "") for key in raw_samples.HEADER])
    return output.getvalue().encode("utf-8")


def _setup(root: Path) -> dict[str, Any]:
    doc = sample_study(root)
    for record in doc["observations"]:
        path = root / record["raw_sample"]
        _ = path.write_bytes(_render([record]))
    return doc


def _check(doc: dict[str, Any], root: Path) -> dict[str, Any]:
    admitted = analyze.parse_document(json.dumps(doc))
    return evidence.validate_links(admitted, root, require_raw_rows=True)


def test_exact_raw_matches_with_durable_content_digests(tmp_path: Path) -> None:
    """Return the bytes inspected for every path, without semantic claims."""
    doc = _setup(tmp_path)
    preflight = _check(doc, tmp_path)
    assert preflight["raw_rows_matched"] == ALGORITHM_COUNT
    assert preflight["raw_file_sha256"] == {
        row["raw_sample"]: sha256(_render([row])).hexdigest()
        for row in doc["observations"]
    }
    assert NO_AUTHENTICATION in preflight["scope"]


def test_old_identity_only_mode_remains_backward_compatible(
    tmp_path: Path,
) -> None:
    """Existing, weaker preflight retains its explicitly weaker scope."""
    doc = sample_study(tmp_path)
    admitted = analyze.parse_document(json.dumps(doc))
    preflight = evidence.validate_links(admitted, tmp_path)
    assert RAW_HASH_FIELD not in preflight
    assert NO_RAW_DIGEST in preflight["scope"]


@pytest.mark.parametrize(
    "key",
    [
        "algorithm",
        "family",
        "version",
        "difficulty",
        "seed",
        "workload_sha256",
        "trial",
        "outcome",
        "verifier",
        "verifier_verdict",
        "elapsed_ns",
        "artifact_bytes",
        "schema_version",
    ],
)
def test_corrupted_raw_field_never_passes_matching(
    tmp_path: Path,
    key: str,
) -> None:
    """Every v1 field is bound, not just a convenient time summary."""
    doc = _setup(tmp_path)
    source = (tmp_path / ROOT_LABEL).read_text(encoding="utf-8")
    rows = list(csv.reader(StringIO(source)))
    column = rows[0].index(key)
    rows[1][column] = "9"
    output = StringIO(newline="")
    writer = csv.writer(output)
    _ = writer.writerows(rows)
    _ = (tmp_path / ROOT_LABEL).write_text(
        output.getvalue(),
        encoding="utf-8",
    )
    with pytest.raises(evidence.EvidenceError, match=ROW_MISMATCH):
        _check(doc, tmp_path)


def _extra_row(row: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(row)
    result["trial"] = 4
    return result


def _invalid_raw(kind: str, row: dict[str, Any]) -> bytes:
    raw = _render([row])
    changes = {
        MISSING: lambda: _render([]),
        DUPLICATE: lambda: _render([row, row]),
        EXTRA: lambda: _render([row, _extra_row(row)]),
        COLUMN: lambda: raw.replace(b"schema_version,", b"wrong_column,", 1),
        UTF8: lambda: raw + b"\xff",
        NUL: lambda: raw + b"\x00",
        QUOTE: lambda: raw + b'"never-closed\n',
        EMPTY: lambda: b"",
        OVERSIZED: lambda: raw + b"a" * raw_samples.MAX_RAW_BYTES,
        "leading-zero": lambda: raw.replace(b",0,verified,", b",00,verified,"),
    }
    return changes[kind]()


@pytest.mark.parametrize(
    "kind",
    [
        MISSING,
        DUPLICATE,
        EXTRA,
        COLUMN,
        UTF8,
        NUL,
        QUOTE,
        EMPTY,
        OVERSIZED,
        "leading-zero",
    ],
)
def test_malformed_incomplete_or_forged_raw_data_rejected(
    tmp_path: Path,
    kind: str,
) -> None:
    """No out-of-band CSV content can substitute for a retained observation."""
    doc = _setup(tmp_path)
    row = doc["observations"][0]
    _ = (tmp_path / ROOT_LABEL).write_bytes(_invalid_raw(kind, row))
    with pytest.raises(evidence.EvidenceError, match=INVALID_RAW_ROW):
        _check(doc, tmp_path)


def test_multiple_trials_sharing_one_csv_are_matched_as_complete_set(
    tmp_path: Path,
) -> None:
    """One raw file may hold trials, but not omit or duplicate any of them."""
    doc = _setup(tmp_path)
    second = copy.deepcopy(doc["observations"][0])
    second["trial"] = 1
    third = copy.deepcopy(doc["observations"][1])
    third["trial"] = 1
    doc["observations"].extend([second, third])
    for algorithm in ("baseline", "candidate"):
        records = [
            row for row in doc["observations"] if row["algorithm"] == algorithm
        ]
        _ = (tmp_path / records[0]["raw_sample"]).write_bytes(
            _render(records),
        )
    report = _check(doc, tmp_path)
    assert report["raw_rows_matched"] == len(doc["observations"])
    # One missing row from a multi-trial sample must fail.
    _ = (tmp_path / ROOT_LABEL).write_bytes(
        _render([doc["observations"][0]]),
    )
    with pytest.raises(evidence.EvidenceError, match=ROW_MISMATCH):
        _check(doc, tmp_path)


def test_shared_raw_file_across_algorithms_checks_all_rows(
    tmp_path: Path,
) -> None:
    """A shared CSV path is a single complete comparison cohort."""
    doc = _setup(tmp_path)
    shared = "evidence/cohort.csv"
    for row in doc["observations"]:
        old = row["raw_sample"]
        row["raw_sample"] = shared
        manifest = tmp_path / row["experiment_manifest"]
        contents = manifest.read_text(encoding="utf-8")
        _ = manifest.write_text(
            contents.replace(
                f'raw_output = "{old}"', f'raw_output = "{shared}"'
            ),
            encoding="utf-8",
        )
    _ = (tmp_path / shared).write_bytes(_render(doc["observations"]))
    report = _check(doc, tmp_path)
    assert len(report["raw_file_sha256"]) == 1
    _ = (tmp_path / shared).write_bytes(
        _render([doc["observations"][0]]),
    )
    with pytest.raises(evidence.EvidenceError, match=ROW_MISMATCH):
        _check(doc, tmp_path)


def test_cli_option_controls_csv_content_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI refuses to print partial Pareto reports on raw evidence drift."""
    doc = _setup(tmp_path)
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
            "--require-raw-rows",
        ],
    )
    assert evidence.main() == 0
    reported = json.loads(capsys.readouterr().out)
    assert reported["evidence_preflight"]["raw_rows_matched"] == ALGORITHM_COUNT
    _ = (tmp_path / ROOT_LABEL).write_bytes(b"unrelated data\n")
    with pytest.raises(SystemExit, match="2"):
        evidence.main()
    result = capsys.readouterr()
    assert not result.out
    assert ROW_MISMATCH in result.err or CSV_HEADER_ERROR in result.err


@pytest.mark.parametrize(
    ("outcome", "verdict", "run_outcome"),
    [
        (analyze.VERIFIER_REJECTED, analyze.REJECTED, "candidate-invalid"),
        ("no_solution", analyze.NOT_RUN, "no-solution"),
        ("resource_exhausted", analyze.NOT_RUN, "resource-exhausted"),
        ("tool_failed", analyze.NOT_RUN, "tool-failure"),
    ],
)
def test_failed_trials_require_their_own_raw_evidence(
    tmp_path: Path,
    *,
    outcome: str,
    verdict: str,
    run_outcome: str,
) -> None:
    """A failed candidate keeps its raw duration without claiming success."""
    doc = _setup(tmp_path)
    record = doc["observations"][1]
    record["outcome"] = outcome
    record["verifier_verdict"] = verdict
    record["metrics"] = {"elapsed_ns": 25}
    raw_path = tmp_path / record["raw_sample"]
    _ = raw_path.write_bytes(_render([record]))
    manifest_path = tmp_path / record["experiment_manifest"]
    source = manifest_path.read_text(encoding="utf-8")
    _ = manifest_path.write_text(
        source.replace('outcome = "success"', f'outcome = "{run_outcome}"'),
        encoding="utf-8",
    )
    checked = _check(doc, tmp_path)
    assert checked["raw_rows_matched"] == ALGORITHM_COUNT
    report = analyze.analyze(analyze.parse_document(json.dumps(doc)))
    candidate = next(
        point
        for point in report["capacity_curve"]
        if point["algorithm"] == record["algorithm"]
    )
    assert candidate["verified"] == 0
    assert candidate["outcomes"][outcome] == 1
    _ = raw_path.write_bytes(
        _render([
            {
                **record,
                "metrics": {"elapsed_ns": 26},
            }
        ])
    )
    with pytest.raises(evidence.EvidenceError, match=ROW_MISMATCH):
        _check(doc, tmp_path)


def test_large_integer_cost_matches_exact_raw_digits(tmp_path: Path) -> None:
    """Raw cost comparisons cannot lose precision through floating point."""
    doc = _setup(tmp_path)
    record = doc["observations"][0]
    record["metrics"]["artifact_bytes"] = 2**80 + 1
    _ = (tmp_path / ROOT_LABEL).write_bytes(_render([record]))
    assert _check(doc, tmp_path)["raw_rows_matched"] == ALGORITHM_COUNT
    record["metrics"]["artifact_bytes"] += 1
    with pytest.raises(evidence.EvidenceError, match=ROW_MISMATCH):
        _check(doc, tmp_path)
