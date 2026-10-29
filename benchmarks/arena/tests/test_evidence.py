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
# ruff: file-ignore[assert,private-member-access]

from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import sys
from typing import Any
from typing import TYPE_CHECKING

import pytest

from benchmarks.arena import analyze
from benchmarks.arena import evidence

if TYPE_CHECKING:
    from collections.abc import Iterator
    from os import stat_result
    from typing import IO

REPLACE_AFTER_LSTAT_COUNT = 3
SECOND_FSTAT_CALL = 2
PAIRED_TEST_METHOD = "two-sided-exact-conditional-binomial"
VERIFICATION_ASYMMETRY_FIELD = "verification_asymmetry_test"
HOLM_METHOD = "Holm-Bonferroni"
HOLM_REQUIREMENT_ERROR = "requires --paired-exact-tests"

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


ACCELERATOR_DIAGNOSTIC = "different accelerator identities"
DEVICE_UNATTESTED = "no physical device attestation"
CUDA_BACKEND = "CUDA-registered-device"


def _accelerator_preflight(doc: dict[str, Any], root: Path) -> dict[str, Any]:
    admitted = analyze.parse_document(json.dumps(doc))
    return evidence.validate_links(
        admitted,
        root,
        policy=evidence.EvidencePolicy(require_matched_accelerator=True),
    )


def test_optional_accelerator_cohort_agreement_is_source_reported(
    tmp_path: Path,
) -> None:
    """Every admitted run must name the same accelerator in strict mode."""
    doc = sample_study(tmp_path)
    checked = _accelerator_preflight(doc, tmp_path)
    assert checked["declared_run_accelerators"] == {
        row["experiment_manifest"]: "none" for row in doc["observations"]
    }
    assert DEVICE_UNATTESTED in checked["scope"]
    for row in doc["observations"]:
        _modify_manifest(
            tmp_path,
            row["algorithm"],
            old='accelerator = "none"',
            new=f'accelerator = "{CUDA_BACKEND}"',
        )
    checked = _accelerator_preflight(doc, tmp_path)
    assert set(checked["declared_run_accelerators"].values()) == {CUDA_BACKEND}


def test_mixed_accelerators_remain_allowed_when_not_requiring_parity(
    tmp_path: Path,
) -> None:
    """Heterogeneous research is still available without strict opt-in."""
    doc = sample_study(tmp_path)
    _modify_manifest(
        tmp_path,
        "candidate",
        old='accelerator = "none"',
        new=f'accelerator = "{CUDA_BACKEND}"',
    )
    assert _admit(doc, tmp_path)["reported_trials_checked"] == ALGORITHM_COUNT
    with pytest.raises(evidence.EvidenceError, match=ACCELERATOR_DIAGNOSTIC):
        _accelerator_preflight(doc, tmp_path)


def test_accelerator_cli_mismatch_never_emits_partial_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An incompatible run device fails before printing capacity metrics."""
    doc = sample_study(tmp_path)
    study_file = tmp_path / "study.json"
    _ = study_file.write_text(json.dumps(doc), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "arena-evidence",
            str(study_file),
            "--root",
            str(tmp_path),
            "--require-matched-accelerator",
        ],
    )
    assert evidence.main() == 0
    checked = json.loads(capsys.readouterr().out)
    assert DEVICE_UNATTESTED in checked["evidence_preflight"]["scope"]
    _modify_manifest(
        tmp_path,
        "baseline",
        old='accelerator = "none"',
        new=f'accelerator = "{CUDA_BACKEND}"',
    )
    with pytest.raises(SystemExit, match="2"):
        evidence.main()
    failure = capsys.readouterr()
    assert not failure.out
    assert ACCELERATOR_DIAGNOSTIC in failure.err


def test_bounded_reader_rejects_file_replacement_between_check_and_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The opened descriptor must match the inode admitted at path lookup."""
    doc = sample_study(tmp_path)
    target = tmp_path / doc["observations"][0]["raw_sample"]
    staged = tmp_path / "replacement.csv"
    _ = staged.write_bytes(b"replaced-with-other-evidence\n")
    real_lstat = Path.lstat
    file_lookups = 0

    def swap_after_admitted_stat(path: Path) -> stat_result:
        nonlocal file_lookups
        details = real_lstat(path)
        if path == target:
            file_lookups += 1
            if file_lookups == REPLACE_AFTER_LSTAT_COUNT:
                _ = staged.replace(target)
        return details

    monkeypatch.setattr(Path, "lstat", swap_after_admitted_stat)
    with pytest.raises(evidence.EvidenceError, match="opened file changed"):
        evidence.read_bounded_regular(
            tmp_path,
            doc["observations"][0]["raw_sample"],
            limit=1024,
        )


def test_bounded_reader_rejects_in_place_change_during_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Post-read descriptor size and change-time detect an observed rewrite."""
    doc = sample_study(tmp_path)
    path = tmp_path / doc["observations"][0]["raw_sample"]
    real_fstat = evidence.os.fstat
    calls = 0

    def rewrite_before_second_stat(fd: int) -> stat_result:
        nonlocal calls
        calls += 1
        if calls == SECOND_FSTAT_CALL:
            with path.open("ab") as stream:
                _ = stream.write(b"x")
        return real_fstat(fd)

    monkeypatch.setattr(evidence.os, "fstat", rewrite_before_second_stat)
    with pytest.raises(evidence.EvidenceError, match="changed during read"):
        evidence.read_bounded_regular(
            tmp_path,
            doc["observations"][0]["raw_sample"],
            limit=1024,
        )


def test_bounded_reader_returns_original_bytes_for_ordinary_file(
    tmp_path: Path,
) -> None:
    """Stable ordinary file identity passes the same no-link boundary."""
    doc = sample_study(tmp_path)
    row = doc["observations"][0]
    original = (tmp_path / row["raw_sample"]).read_bytes()
    assert (
        evidence.read_bounded_regular(
            tmp_path,
            row["raw_sample"],
            limit=1024,
        )
        == original
    )


class _ShortEvidenceReader:
    def __init__(self, stream: IO[bytes], *, premature_eof: bool) -> None:
        self.stream = stream
        self.premature_eof = premature_eof
        self.calls = 0

    def fileno(self) -> int:
        return self.stream.fileno()

    def read(self, count: int) -> bytes:
        self.calls += 1
        if self.premature_eof and self.calls > 1:
            return b""
        return self.stream.read(min(count, 3))


@pytest.mark.parametrize("premature_eof", [False, True])
def test_bounded_reader_requires_complete_bytes_across_short_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    premature_eof: bool,
) -> None:
    """A stable inode never authenticates a truncated stream prefix."""
    document = sample_study(tmp_path)
    relative = document["observations"][0]["raw_sample"]
    expected = (tmp_path / relative).read_bytes()
    original_open = evidence._open_evidence

    @contextmanager
    def short_open(path: Path) -> Iterator[_ShortEvidenceReader]:
        with original_open(path) as stream:
            yield _ShortEvidenceReader(stream, premature_eof=premature_eof)

    monkeypatch.setattr(evidence, "_open_evidence", short_open)
    if premature_eof:
        with pytest.raises(evidence.EvidenceError, match="ended before"):
            evidence.read_bounded_regular(tmp_path, relative, limit=1024)
    else:
        assert (
            evidence.read_bounded_regular(tmp_path, relative, limit=1024)
            == expected
        )


class _FaultEvidenceReader:
    def __init__(self, stream: IO[bytes], fault: type[Exception]) -> None:
        self.stream = stream
        self.fault = fault

    def fileno(self) -> int:
        return self.stream.fileno()

    def read(self, count: int) -> bytes:
        _ = count
        message = "injected stream failure"
        raise self.fault(message)


@pytest.mark.parametrize(
    "fault",
    [OSError, ValueError, RuntimeError, TypeError, AttributeError],
)
def test_bounded_reader_classifies_stream_read_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """Malformed or failing file streams retain typed evidence diagnostics."""
    document = sample_study(tmp_path)
    relative = document["observations"][0]["raw_sample"]
    original_open = evidence._open_evidence

    @contextmanager
    def broken_open(path: Path) -> Iterator[_FaultEvidenceReader]:
        with original_open(path) as stream:
            yield _FaultEvidenceReader(stream, fault)

    monkeypatch.setattr(evidence, "_open_evidence", broken_open)
    with pytest.raises(evidence.EvidenceError, match="read failed") as error:
        evidence.read_bounded_regular(tmp_path, relative, limit=1024)
    assert isinstance(error.value.__cause__, fault)


NONBINARY_READ_KIND = "text"


NONBINARY_READ_KIND = "text"


NONBINARY_READ_KIND = "text"


class _InvalidChunkEvidenceReader:
    def __init__(self, stream: IO[bytes], kind: str) -> None:
        self.stream = stream
        self.kind = kind

    def fileno(self) -> int:
        return self.stream.fileno()

    def read(self, count: int) -> object:
        if self.kind == NONBINARY_READ_KIND:
            return "forged nonbinary read"
        return b"x" * (count + 1)


@pytest.mark.parametrize("kind", [NONBINARY_READ_KIND, "oversized"])
def test_bounded_reader_rejects_malformed_chunk_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """Reader byte shape and requested count are both hard admission bounds."""
    document = sample_study(tmp_path)
    relative = document["observations"][0]["raw_sample"]
    original_open = evidence._open_evidence

    @contextmanager
    def invalid_open(path: Path) -> Iterator[_InvalidChunkEvidenceReader]:
        with original_open(path) as stream:
            yield _InvalidChunkEvidenceReader(stream, kind)

    monkeypatch.setattr(evidence, "_open_evidence", invalid_open)
    with pytest.raises(evidence.EvidenceError, match="invalid bytes"):
        evidence.read_bounded_regular(tmp_path, relative, limit=1024)


@pytest.mark.skipif(
    not hasattr(evidence.os, "mkfifo")
    or not getattr(evidence.os, "O_NONBLOCK", 0),
    reason="nonblocking FIFO admission is a POSIX capability",
)
def test_bounded_reader_never_blocks_on_raced_fifo_leaf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A substituted FIFO opens nonblocking and is rejected as nonregular."""
    document = sample_study(tmp_path)
    target = tmp_path / document["observations"][0]["raw_sample"]
    real_lstat = Path.lstat
    lookups = 0

    def replace_with_fifo(path: Path) -> stat_result:
        nonlocal lookups
        details = real_lstat(path)
        if path == target:
            lookups += 1
            if lookups == REPLACE_AFTER_LSTAT_COUNT:
                target.unlink()
                mkfifo = getattr(evidence.os, "mkfifo", None)
                assert callable(mkfifo)
                mkfifo(target)
        return details

    monkeypatch.setattr(Path, "lstat", replace_with_fifo)
    with pytest.raises(evidence.EvidenceError, match="opened file changed"):
        evidence.read_bounded_regular(
            tmp_path,
            document["observations"][0]["raw_sample"],
            limit=1024,
        )


def test_evidence_cli_passes_opt_in_median_intervals_without_replacing_links(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Evidence-aware CLI retains its link checks and honest small-n nulls."""
    document = sample_study(tmp_path)
    input_path = tmp_path / "study.json"
    _ = input_path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "arena-evidence",
            str(input_path),
            "--root",
            str(tmp_path),
            "--median-intervals-95",
        ],
    )
    assert evidence.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["evidence_preflight"]["reported_trials_checked"] == (
        ALGORITHM_COUNT
    )
    assert report["median_interval_policy"]["requested_confidence"] == [19, 20]
    for point in report["capacity_curve"]:
        assert point["median_confidence_intervals_95"]["elapsed_ns"] is None
        assert (
            point["all_attempt_elapsed_ns"]["median_confidence_interval_95"]
            is None
        )
    for pair in report["paired_baseline_comparisons"]:
        assert (
            pair["cost_differences"]["elapsed_ns"][
                "median_confidence_interval_95"
            ]
            is None
        )


def test_evidence_cli_opt_in_paired_tests_preserve_evidence_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Source-reported paired tests never replace run-link verification."""
    document = sample_study(tmp_path)
    study_path = tmp_path / "study.json"
    _ = study_path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "arena-evidence",
            str(study_path),
            "--root",
            str(tmp_path),
            "--paired-exact-tests",
            "--median-intervals-95",
        ],
    )
    assert evidence.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["evidence_preflight"]["reported_trials_checked"] == (
        ALGORITHM_COUNT
    )
    assert report["paired_exact_test_policy"]["method"] == PAIRED_TEST_METHOD
    assert report["median_interval_policy"]["requested_confidence"] == [19, 20]
    assert (
        VERIFICATION_ASYMMETRY_FIELD in report["paired_baseline_comparisons"][0]
    )


def test_evidence_cli_rejects_holm_without_paired_hypotheses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Missing mandatory inference option never emits a capacity summary."""
    document = sample_study(tmp_path)
    path = tmp_path / "study.json"
    _ = path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "arena-evidence",
            str(path),
            "--root",
            str(tmp_path),
            "--adjust-paired-tests",
        ],
    )
    with pytest.raises(SystemExit, match="2"):
        evidence.main()
    result = capsys.readouterr()
    assert not result.out
    assert HOLM_REQUIREMENT_ERROR in result.err


def test_evidence_cli_retains_source_linkage_during_holm_inference(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Inference remains downstream of reported manifest admission."""
    document = sample_study(tmp_path)
    path = tmp_path / "study.json"
    _ = path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "arena-evidence",
            str(path),
            "--root",
            str(tmp_path),
            "--paired-exact-tests",
            "--adjust-paired-tests",
        ],
    )
    assert evidence.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["evidence_preflight"]["reported_trials_checked"] == (
        ALGORITHM_COUNT
    )
    assert (
        report["paired_exact_test_policy"]["multiple_testing_adjustment"]
        == HOLM_METHOD
    )
    assert report["paired_exact_test_policy"]["adjustment_family_size"] == 0


def test_evidence_cli_success_intervals_remain_downstream_of_source_links(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Success uncertainty preserves the identity preflight."""
    document = sample_study(tmp_path)
    path = tmp_path / "study.json"
    _ = path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "arena-evidence",
            str(path),
            "--root",
            str(tmp_path),
            "--success-intervals-95",
        ],
    )
    assert evidence.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result["evidence_preflight"]["reported_trials_checked"] == (
        ALGORITHM_COUNT
    )
    assert result["verification_success_interval_policy"][
        "requested_confidence"
    ] == [19, 20]
    for point in result["capacity_curve"]:
        interval = point["verification_success_probability_interval_95"]
        assert interval is not None
        assert interval["verified"] == point["verified"]
        assert interval["sample_count"] == point["attempts"]
    assert result["pareto_frontiers"][0]["algorithms"] == [
        "baseline",
        "candidate",
    ]
