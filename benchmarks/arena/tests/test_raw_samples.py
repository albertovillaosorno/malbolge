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
    from collections.abc import Iterator
    from pathlib import Path

ROOT_LABEL = "evidence/baseline.csv"
RAW_HASH_FIELD = "raw_file_sha256"
NO_AUTHENTICATION = "no provenance authentication"
NO_RAW_DIGEST = "no content digest verification"
CSV_HEADER_ERROR = "CSV header"
NO_VERIFIER_REPLAY = "no verifier replay"
REPETITION_DIAGNOSTIC = "repetition"
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
CSV_FIRST_EXCESS_ROW = 3
ENERGY_METRIC = "energy_uj"
BASELINE_NAME = "baseline"
MISSING_ENERGY = "missing"
WRONG_ENERGY = "wrong"
NEGATIVE_ENERGY = "negative"


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
    return evidence.validate_links(
        admitted,
        root,
        policy=evidence.EvidencePolicy(require_raw_rows=True),
    )


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


@pytest.mark.parametrize("version", [1, 2])
def test_unreported_csv_rows_stop_at_first_excess_row(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    version: int,
) -> None:
    """Reject a tiny CSV row bomb before materializing all unreported rows."""
    record = _setup(tmp_path)["observations"][0]
    expected = _render([record]) if version == 1 else _render_v2([record])
    hostile = expected + b"\n" * 100_000
    reader = raw_samples.csv.reader
    consumed = 0

    def bounded_reader(
        source: StringIO, *, strict: bool
    ) -> Iterator[list[str]]:
        nonlocal consumed
        for row in reader(source, strict=strict):
            consumed += 1
            if consumed > CSV_FIRST_EXCESS_ROW:
                pytest.fail("CSV parser read past the first unreported row")
            yield row

    monkeypatch.setattr(raw_samples.csv, "reader", bounded_reader)
    with pytest.raises(raw_samples.RawSampleError, match="more rows"):
        raw_samples.check_rows(hostile, [record], ROOT_LABEL)
    # Header + the one reported trial + the first unexpected empty row.
    assert consumed == CSV_FIRST_EXCESS_ROW


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


def _bind_trial_extensions(doc: dict[str, Any], root: Path) -> None:
    """Bind each synthetic run record to its exact inspected CSV bytes."""
    written: set[str] = set()
    for row in doc["observations"]:
        if row["experiment_manifest"] in written:
            continue
        written.add(row["experiment_manifest"])
        path = root / row["experiment_manifest"]
        raw = (root / row["raw_sample"]).read_bytes()
        with path.open("a", encoding="utf-8") as stream:
            _ = stream.write(
                "\n[arena_trial]\nschema_version = 1\n"
                f"trial = {row["trial"]}\n"
                f'raw_sha256 = "{sha256(raw).hexdigest()}"\n'
            )


def _strict_check(doc: dict[str, Any], root: Path) -> dict[str, Any]:
    admitted = analyze.parse_document(json.dumps(doc))
    return evidence.validate_links(
        admitted,
        root,
        policy=evidence.EvidencePolicy(require_trial_run_identity=True),
    )


def test_strict_trial_link_admits_versioned_run_and_complete_raw(
    tmp_path: Path,
) -> None:
    """Strict mode binds run identity, trial index, and matching CSV digest."""
    doc = _setup(tmp_path)
    _bind_trial_extensions(doc, tmp_path)
    report = _strict_check(doc, tmp_path)
    assert report["trial_run_links_checked"] == ALGORITHM_COUNT
    assert report["raw_rows_matched"] == ALGORITHM_COUNT
    assert NO_VERIFIER_REPLAY in report["scope"]
    # The historical optional mode still works without the new extension.
    assert _check(doc, tmp_path)["raw_rows_matched"] == ALGORITHM_COUNT


@pytest.mark.parametrize(
    ("old", "new", "diagnostic"),
    [
        ("schema_version = 1", "schema_version = 2", "schema_version"),
        ("trial = 0", "trial = 1", "repetition"),
        ("trial = 0", "trial = true", "nonnegative integer"),
        ("trial = 0", "trial = -1", "nonnegative integer"),
        ("[arena_trial]", "[unrelated_extension]", "arena_trial requires"),
        ("trial = 0", "trial = 0\nunexpected = 1", "exact"),
    ],
)
def test_invalid_trial_run_extension_rejected(
    tmp_path: Path,
    old: str,
    new: str,
    *,
    diagnostic: str,
) -> None:
    """Strict preflight rejects schema drift without certifying any outcome."""
    doc = _setup(tmp_path)
    _bind_trial_extensions(doc, tmp_path)
    manifest = tmp_path / doc["observations"][0]["experiment_manifest"]
    contents = manifest.read_text(encoding="utf-8")
    header, marker, extension = contents.partition("[arena_trial]")
    _ = manifest.write_text(
        header + marker.replace(old, new) + extension.replace(old, new),
        encoding="utf-8",
    )
    with pytest.raises(evidence.EvidenceError, match=diagnostic):
        _strict_check(doc, tmp_path)


def test_missing_trial_extension_is_not_silent_in_strict_mode(
    tmp_path: Path,
) -> None:
    """Opt-in trial identity cannot be substituted by an aggregate manifest."""
    doc = _setup(tmp_path)
    with pytest.raises(evidence.EvidenceError, match="arena_trial requires"):
        _strict_check(doc, tmp_path)
    admitted = analyze.parse_document(json.dumps(doc))
    assert (
        evidence.validate_links(admitted, tmp_path)["manifest_links_checked"]
        == ALGORITHM_COUNT
    )


def test_strict_trial_link_rejects_raw_change_after_manifest_creation(
    tmp_path: Path,
) -> None:
    """Even an internally consistent report fails if recorded bytes drift."""
    doc = _setup(tmp_path)
    _bind_trial_extensions(doc, tmp_path)
    row = doc["observations"][0]
    row["metrics"]["elapsed_ns"] = 77
    _ = (tmp_path / row["raw_sample"]).write_bytes(_render([row]))
    with pytest.raises(evidence.EvidenceError, match="raw SHA-256"):
        _strict_check(doc, tmp_path)


def test_one_aggregate_manifest_cannot_claim_distinct_trial_repetitions(
    tmp_path: Path,
) -> None:
    """No single manifest may masquerade as independent per-trial runs."""
    doc = _setup(tmp_path)
    for name in ("baseline", "candidate"):
        first = next(
            row for row in doc["observations"] if row["algorithm"] == name
        )
        second = copy.deepcopy(first)
        second["trial"] = 1
        doc["observations"].append(second)
        _ = (tmp_path / first["raw_sample"]).write_bytes(
            _render([first, second]),
        )
    _bind_trial_extensions(doc, tmp_path)
    with pytest.raises(evidence.EvidenceError, match="multiple trials"):
        _strict_check(doc, tmp_path)


def test_distinct_run_manifests_can_reference_one_multi_trial_raw_file(
    tmp_path: Path,
) -> None:
    """All run records can bind the full retained CSV without hidden rows."""
    doc = _setup(tmp_path)
    for name in ("baseline", "candidate"):
        first = next(
            row for row in doc["observations"] if row["algorithm"] == name
        )
        second = copy.deepcopy(first)
        second["trial"] = 1
        old_manifest = tmp_path / first["experiment_manifest"]
        second_path = f"evidence/{name}-trial1.toml"
        _ = (tmp_path / second_path).write_bytes(old_manifest.read_bytes())
        second["experiment_manifest"] = second_path
        doc["observations"].append(second)
        _ = (tmp_path / first["raw_sample"]).write_bytes(
            _render([first, second]),
        )
    _bind_trial_extensions(doc, tmp_path)
    result = _strict_check(doc, tmp_path)
    assert result["trial_run_links_checked"] == len(doc["observations"])
    assert result["raw_sample_paths_checked"] == ALGORITHM_COUNT


def test_strict_evidence_cli_fails_closed_on_unbound_trial(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A declined strict trial link must never print partial capacity data."""
    doc = _setup(tmp_path)
    _bind_trial_extensions(doc, tmp_path)
    study = tmp_path / "study.json"
    _ = study.write_text(json.dumps(doc), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "arena-evidence",
            str(study),
            "--root",
            str(tmp_path),
            "--require-trial-run-identity",
        ],
    )
    assert evidence.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert (
        report["evidence_preflight"]["trial_run_links_checked"]
        == ALGORITHM_COUNT
    )
    manifest = tmp_path / doc["observations"][0]["experiment_manifest"]
    _ = manifest.write_text(
        manifest.read_text(encoding="utf-8").replace("trial = 0", "trial = 1"),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit, match="2"):
        evidence.main()
    result = capsys.readouterr()
    assert not result.out
    assert REPETITION_DIAGNOSTIC in result.err


@pytest.mark.parametrize(
    "replacement",
    [
        'raw_sha256 = "short"',
        'raw_sha256 = "' + "F" * analyze.SHA256_HEX_LENGTH + '"',
        "raw_sha256 = 1234",
        "unexpected_field = true",
    ],
)
def test_strict_run_raw_digest_requires_exact_declared_sha256(
    tmp_path: Path,
    replacement: str,
) -> None:
    """Malformed or padded digest declarations never pass manifest binding."""
    doc = _setup(tmp_path)
    _bind_trial_extensions(doc, tmp_path)
    manifest = tmp_path / doc["observations"][0]["experiment_manifest"]
    contents = manifest.read_text(encoding="utf-8")
    declared = (
        'raw_sha256 = "'
        + sha256(
            (tmp_path / doc["observations"][0]["raw_sample"]).read_bytes()
        ).hexdigest()
        + '"'
    )
    _ = manifest.write_text(
        contents.replace(declared, replacement),
        encoding="utf-8",
    )
    with pytest.raises(evidence.EvidenceError, match="arena_trial"):
        _strict_check(doc, tmp_path)


def test_strict_trial_run_can_also_require_exact_run_budget_agreement(
    tmp_path: Path,
) -> None:
    """All optional contracts coexist without weakening prior checks."""
    doc = _setup(tmp_path)
    doc["study"]["budget"] = {
        "time_ns": 1_000_000_000,
        "memory_bytes": 128 * 1_048_576,
    }
    for row in doc["observations"]:
        path = tmp_path / row["experiment_manifest"]
        _ = path.write_text(
            path.read_text(encoding="utf-8").replace(
                "seconds = 1",
                "seconds = 1\nmemory_mib = 128",
            ),
            encoding="utf-8",
        )
    _bind_trial_extensions(doc, tmp_path)
    policy = evidence.EvidencePolicy(
        require_raw_rows=True,
        require_trial_run_identity=True,
        require_budget_agreement=True,
    )
    admitted = analyze.parse_document(json.dumps(doc))
    checked = evidence.validate_links(admitted, tmp_path, policy=policy)
    assert checked["trial_run_links_checked"] == ALGORITHM_COUNT
    assert checked["run_budget_links_checked"] == ALGORITHM_COUNT
    assert checked["raw_rows_matched"] == ALGORITHM_COUNT
    path = tmp_path / doc["observations"][0]["experiment_manifest"]
    _ = path.write_text(
        path.read_text(encoding="utf-8").replace(
            "memory_mib = 128",
            "memory_mib = 256",
        ),
        encoding="utf-8",
    )
    with pytest.raises(evidence.EvidenceError, match="declared budget differs"):
        evidence.validate_links(admitted, tmp_path, policy=policy)


def _render_v2(records: list[dict[str, Any]]) -> bytes:
    """Build synthetic v2 rows independently of the production CSV renderer.

    Returns:
        A complete version-two CSV retaining the additional energy column.

    """
    previous = list(csv.reader(StringIO(_render(records).decode("utf-8"))))
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    _ = writer.writerow(raw_samples.HEADER_2)
    for row, record in zip(previous[1:], records, strict=True):
        fields = dict(zip(previous[0], row, strict=True))
        fields["schema_version"] = "2"
        if ENERGY_METRIC in record["metrics"]:
            fields[ENERGY_METRIC] = str(record["metrics"][ENERGY_METRIC])
        _ = writer.writerow([
            fields.get(name, "") for name in raw_samples.HEADER_2
        ])
    return output.getvalue().encode("utf-8")


def _energy_study(root: Path) -> dict[str, Any]:
    document = _setup(root)
    document["study"]["objectives"].append(ENERGY_METRIC)
    for record in document["observations"]:
        record["metrics"][ENERGY_METRIC] = (
            10 if record["algorithm"] == BASELINE_NAME else 20
        )
        if record["algorithm"] != BASELINE_NAME:
            record["metrics"]["elapsed_ns"] = 8
        _ = (root / record["raw_sample"]).write_bytes(_render_v2([record]))
    return document


def test_version_two_energy_cost_enters_exact_pareto_and_raw_digest(
    tmp_path: Path,
) -> None:
    """A real energy objective remains cost-minimized, never estimated."""
    document = _energy_study(tmp_path)
    report = analyze.analyze(analyze.parse_document(json.dumps(document)))
    assert report["pareto_frontiers"][0]["algorithms"] == [
        BASELINE_NAME,
        "candidate",
    ]
    points = {point["algorithm"]: point for point in report["capacity_curve"]}
    assert points["baseline"]["medians"]["energy_uj"] == [10, 1]
    assert points["candidate"]["medians"]["energy_uj"] == [20, 1]
    checked = _check(document, tmp_path)
    assert checked["raw_rows_matched"] == ALGORITHM_COUNT
    assert checked["raw_file_sha256"] == {
        row["raw_sample"]: sha256(_render_v2([row])).hexdigest()
        for row in document["observations"]
    }


def test_v1_csv_header_and_rows_remain_byte_exact_after_v2_admission(
    tmp_path: Path,
) -> None:
    """The old wire header and byte identity never acquire an energy cell."""
    document = _setup(tmp_path)
    assert ENERGY_METRIC not in raw_samples.HEADER
    assert ENERGY_METRIC in raw_samples.HEADER_2
    assert (
        *raw_samples.IDENTITY_FIELDS,
        "artifact_bytes",
        "elapsed_ns",
        "peak_rss_bytes",
        "peak_vram_bytes",
        "runtime_steps",
        "verifier_ns",
    ) == (raw_samples.HEADER)
    checked = _check(document, tmp_path)
    assert checked["raw_rows_matched"] == ALGORITHM_COUNT


def test_v1_csv_cannot_silently_discard_reported_energy(
    tmp_path: Path,
) -> None:
    """An energy value carried in JSON must not vanish from a v1 raw file."""
    document = _setup(tmp_path)
    document["observations"][0]["metrics"][ENERGY_METRIC] = 11
    with pytest.raises(evidence.EvidenceError, match="omit reported energy_uj"):
        _check(document, tmp_path)


@pytest.mark.parametrize("change", ["missing", "wrong", "negative", "header"])
def test_energy_raw_drift_and_cross_version_substitution_rejected(
    tmp_path: Path,
    change: str,
) -> None:
    """V2 must preserve every declared microjoule and the schema marker."""
    document = _energy_study(tmp_path)
    record = document["observations"][0]
    raw_path = tmp_path / record["raw_sample"]
    if change == MISSING_ENERGY:
        record["metrics"][ENERGY_METRIC] = 14
    elif change == WRONG_ENERGY:
        raw = raw_path.read_bytes()
        raw_path.write_bytes(raw.replace(b",10,", b",11,", 1))
    elif change == NEGATIVE_ENERGY:
        record["metrics"][ENERGY_METRIC] = -1
    else:
        raw_path.write_bytes(_render([record]))
    if change == NEGATIVE_ENERGY:
        with pytest.raises(analyze.ArenaError, match="nonnegative integer"):
            _check(document, tmp_path)
    else:
        with pytest.raises(evidence.EvidenceError, match=r"energy|raw CSV"):
            _check(document, tmp_path)


def test_undeclared_energy_metric_is_allowed_but_retained_in_v2(
    tmp_path: Path,
) -> None:
    """Optional observed energy remains raw evidence even when not scored."""
    document = _energy_study(tmp_path)
    document["study"]["objectives"].remove(ENERGY_METRIC)
    assert _check(document, tmp_path)["raw_rows_matched"] == ALGORITHM_COUNT
    report = analyze.analyze(analyze.parse_document(json.dumps(document)))
    assert ENERGY_METRIC not in report["objectives"]


def test_verified_energy_objective_without_value_fails_before_raw_check(
    tmp_path: Path,
) -> None:
    """The analyzer refuses an absent declared energy metric on success."""
    document = _energy_study(tmp_path)
    del document["observations"][0]["metrics"][ENERGY_METRIC]
    with pytest.raises(analyze.ArenaError, match="missing declared objective"):
        _check(document, tmp_path)


def test_version_two_energy_raw_can_bind_distinct_trial_run_digests(
    tmp_path: Path,
) -> None:
    """The stronger run manifest digest covers the additional energy bytes."""
    document = _energy_study(tmp_path)
    _bind_trial_extensions(document, tmp_path)
    assert _strict_check(document, tmp_path)["trial_run_links_checked"] == (
        ALGORITHM_COUNT
    )
    record = document["observations"][0]
    record["metrics"][ENERGY_METRIC] += 1
    _ = (tmp_path / record["raw_sample"]).write_bytes(_render_v2([record]))
    with pytest.raises(evidence.EvidenceError, match="raw SHA-256"):
        _strict_check(document, tmp_path)


def test_version_two_reports_unknown_energy_as_empty_cell_not_zero(
    tmp_path: Path,
) -> None:
    """Unmeasured energy remains absent while elapsed is still objective."""
    document = _energy_study(tmp_path)
    document["study"]["objectives"].remove(ENERGY_METRIC)
    for record in document["observations"]:
        del record["metrics"][ENERGY_METRIC]
        _ = (tmp_path / record["raw_sample"]).write_bytes(
            _render_v2([record]),
        )
    assert _check(document, tmp_path)["raw_rows_matched"] == ALGORITHM_COUNT
    for row in document["observations"]:
        raw = (tmp_path / row["raw_sample"]).read_text(encoding="utf-8")
        line = next(iter(csv.DictReader(StringIO(raw))))
        assert not line[ENERGY_METRIC]
