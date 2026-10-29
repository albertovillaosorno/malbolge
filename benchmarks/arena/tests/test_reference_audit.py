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
#   - Offline reinspection and tamper regressions for retained host-C studies.
# - Must-Not:
#   - Represent native host-C evidence as target compiler verification.
# - Allows:
#   - Inputs: bounded real pinned-Clang studies and injected file drift.
#   - Outputs: exact audit acceptance and failure-mode assertions.
#   - Side effects: ignored pilot directories, removed after tests.
# - Split-When:
#   - A target compiler study needs a different provenance verification suite.
# - Merge-When:
#   - One generic research evidence auditor owns this exact source contract.
# - Summary:
#   - Ensures a later process catches changed files and malformed metadata.
# - Description:
#   - Runs a real paired host-C pilot and checks independent retained admission.
# - Usage:
#   - `pytest benchmarks/arena/tests/test_reference_audit.py`.
# - Defaults:
#   - No retained native binary execution in the default audit.
#

"""Independent host-C retained-study audit and fail-closed CLI checks."""

# ruff: file-ignore[assert,private-member-access]

from __future__ import annotations

from hashlib import sha256
import json
import shutil
import sys
from typing import TYPE_CHECKING

import pytest

from benchmarks.arena import host_c_oracle
from benchmarks.arena import reference_audit
from benchmarks.arena import reference_study
from benchmarks.challenges import generate

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

FAMILY = "arithmetic-dag"
REPETITIONS = 2
OBSERVED_PAIRS = 4
LEVEL_COUNT = 2
STUDY_KIND = "host-c-reference-not-malbolge"
INVALID_STUDY = "host-C reference audit"
RAW_MUTATION = "raw"
MANIFEST_MUTATION = "manifest"
BUNDLE_MUTATION = "bundle"
INDEX_EXTRA = "extra"
INDEX_MISSING = "missing"
INDEX_BAD_TYPE = "bad-type"


@pytest.fixture
def live_pilot() -> Generator[tuple[Path, str]]:
    """Build an actual two-difficulty pinned-Clang host reference study.

    Yields:
        Test-owned retained directory and canonical repo-relative JSON path.

    """
    directory, _ = reference_study.run_study(
        reference_study.StudyPlan(FAMILY, (4, 8), 7, REPETITIONS),
    )
    try:
        yield (
            directory,
            (directory / "study.json")
            .relative_to(
                reference_audit._ROOT,
            )
            .as_posix(),
        )
    finally:
        shutil.rmtree(directory)


def _file_hashes(directory: Path) -> dict[str, str]:
    """Snapshot every retained file, including successful native binaries.

    Returns:
        Relative path to exact source-byte SHA-256 map.

    """
    return {
        path.relative_to(directory).as_posix(): sha256(
            path.read_bytes()
        ).hexdigest()
        for path in directory.rglob("*")
        if path.is_file()
    }


def test_audit_reopens_real_study_without_timing_or_file_mutations(
    live_pilot: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Offline admission independently checks all retained host evidence."""
    directory, relative = live_pilot
    hashes_before = _file_hashes(directory)

    def forbidden(*args: object, **kwargs: object) -> str:
        _ = (args, kwargs)
        message = "audit attempted to run the compiler"
        raise AssertionError(message)

    monkeypatch.setattr(host_c_oracle, "replay_one", forbidden)
    observed = reference_audit.audit(relative)
    assert observed["study"] == relative
    assert observed["host_c_binaries_checked"] == OBSERVED_PAIRS * 2
    assert not observed["host_c_oracle_replayed"]
    assert (
        observed["evidence_preflight"]["raw_rows_matched"] == OBSERVED_PAIRS * 2
    )
    assert (
        observed["evidence_preflight"]["regenerated_challenge_bundles"]
        == LEVEL_COUNT
    )
    assert len(observed["capacity_curve"]) == OBSERVED_PAIRS
    assert observed["scope"].endswith("budget attestation.")
    assert hashes_before == _file_hashes(directory)


def test_audit_can_replay_only_canonical_challenge_oracle(
    live_pilot: tuple[Path, str],
) -> None:
    """Optional native execution is a source oracle check, not target replay."""
    directory, relative = live_pilot
    hashes_before = _file_hashes(directory)
    observed = reference_audit.audit(relative, replay_oracles=True)
    preflight = observed["evidence_preflight"]
    assert preflight["host_c_challenge_oracles_replayed"] == LEVEL_COUNT
    assert preflight["host_c_replay_modes"] == ["O0", "O2"]
    assert observed["host_c_oracle_replayed"]
    assert hashes_before == _file_hashes(directory)


def _change_json(path: Path, update: str) -> None:
    document = json.loads(path.read_text(encoding="utf-8"))
    study = document["study"]
    first = document["observations"][0]
    changes = {
        "stage": (study, "stage", "malbolge-verified"),
        "toolchain": (study, "toolchain", "unreviewed-compiler"),
        "budget": (study["budget"], "time_ns", study["budget"]["time_ns"] + 1),
        "profile": (study, "target_profile", "malbolge-1998"),
        "verifier": (first, "verifier", "self-certified"),
        "trial": (first, "trial", 99),
        "arm": (first, "algorithm", "candidate-unchecked"),
        "objective": (study, "objectives", list(reversed(study["objectives"]))),
    }
    parent, name, value = changes[update]
    parent[name] = value
    _ = path.write_text(json.dumps(document), encoding="utf-8")


@pytest.mark.parametrize(
    "change",
    [
        "stage",
        "toolchain",
        "budget",
        "profile",
        "verifier",
        "trial",
        "arm",
        "objective",
    ],
)
def test_audit_rejects_retained_study_claim_mutations(
    live_pilot: tuple[Path, str],
    change: str,
) -> None:
    """A producer cannot reclassify host-C results as target performance."""
    directory, relative = live_pilot
    _change_json(directory / "study.json", change)
    with pytest.raises(reference_audit.ReferenceAuditError, match="host-C"):
        reference_audit.audit(relative)


@pytest.mark.parametrize("mutation", ["raw", "manifest", "bundle", "binary"])
def test_audit_rejects_retained_file_tampering(
    live_pilot: tuple[Path, str],
    mutation: str,
) -> None:
    """Raw data, run metadata, challenges, and native bytes are rechecked."""
    directory, relative = live_pilot
    if mutation == RAW_MUTATION:
        path = next((directory / "raw").glob("*.csv"))
        with path.open("ab") as writer:
            _ = writer.write(b"forged\n")
    elif mutation == MANIFEST_MUTATION:
        path = next((directory / "runs").glob("*.toml"))
        _ = path.write_text(
            path.read_text().replace(
                'outcome = "success"',
                'outcome = "tool-failure"',
            ),
            encoding="utf-8",
        )
    elif mutation == BUNDLE_MUTATION:
        path = next((directory / "bundles").rglob("oracle.bin"))
        _ = path.write_bytes(b"\x00\x00\x00\x00")
    else:
        path = next((directory / "candidates").iterdir())
        _ = path.write_bytes(path.read_bytes() + b"malformed")
    with pytest.raises(reference_audit.ReferenceAuditError, match="host-C"):
        reference_audit.audit(relative)


@pytest.mark.parametrize(
    "mutation", ["extra", "missing", "bad-type", "bad-shape"]
)
def test_audit_rejects_forged_artifact_index(
    live_pilot: tuple[Path, str],
    mutation: str,
) -> None:
    """Malformed JSON types or unlinked success binaries cannot be admitted."""
    directory, relative = live_pilot
    path = directory / "artifacts.json"
    document = json.loads(path.read_text())
    key = next(iter(document))
    if mutation == INDEX_EXTRA:
        document["forged"] = document[key].copy()
    elif mutation == INDEX_MISSING:
        _ = document.pop(key)
    elif mutation == INDEX_BAD_TYPE:
        document[key] = ["not-an-artifact"]
    else:
        document[key]["unregistered"] = 2
    _ = path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(reference_audit.ReferenceAuditError, match="host-C"):
        reference_audit.audit(relative)


@pytest.mark.parametrize(
    "relative",
    [
        "/absolute/study.json",
        "../study.json",
        ".temp/study.json",
        ".temp/other/study.json",
        ".temp/arena-host-c-study-a/other.json",
        ".temp/arena-host-c-study-a/../study.json",
        ".temp/arena-host-c-study-/.json",
    ],
)
def test_audit_rejects_noncanonical_or_unowned_study_path(
    relative: str,
) -> None:
    """Admission cannot be pointed at arbitrary repository or user files."""
    with pytest.raises(reference_audit.ReferenceAuditError, match="host-C"):
        reference_audit.audit(relative)


def test_cli_emits_checked_json_or_no_output_on_failure(
    live_pilot: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Operator report is all-or-failure for the validation boundary."""
    directory, relative = live_pilot
    monkeypatch.setattr(sys, "argv", ["reference-audit", relative])
    assert reference_audit.main() == 0
    observed = json.loads(capsys.readouterr().out)
    assert observed["host_c_binaries_checked"] == OBSERVED_PAIRS * 2
    _change_json(directory / "study.json", "stage")
    with pytest.raises(SystemExit, match="2"):
        reference_audit.main()
    captured = capsys.readouterr()
    assert not captured.out
    assert INVALID_STUDY in captured.err


def test_independent_rebuild_matches_all_retained_host_reference_binaries(
    live_pilot: tuple[Path, str],
) -> None:
    """Fresh native output reproduces each recorded binary byte-for-byte."""
    directory, relative = live_pilot
    before = _file_hashes(directory)
    report = reference_audit.audit(relative, rebuild_binaries=True)
    assert report["host_c_binaries_checked"] == OBSERVED_PAIRS * 2
    assert report["host_c_reference_builds_reproduced"] == OBSERVED_PAIRS
    assert before == _file_hashes(directory)


def test_forged_binary_and_updated_digest_cannot_pass_rebuild_audit(
    live_pilot: tuple[Path, str],
) -> None:
    """A producer-controlled digest alone cannot prove source provenance."""
    directory, relative = live_pilot
    index_path = directory / "artifacts.json"
    metadata = json.loads(index_path.read_text(encoding="utf-8"))
    name = next(iter(metadata))
    binary = reference_audit._ROOT / metadata[name]["path"]
    altered = bytearray(binary.read_bytes())
    altered[-1] ^= 1
    _ = binary.write_bytes(altered)
    metadata[name]["sha256"] = sha256(altered).hexdigest()
    _ = index_path.write_text(json.dumps(metadata), encoding="utf-8")
    assert reference_audit.audit(relative)["host_c_binaries_checked"] == (
        OBSERVED_PAIRS * 2
    )
    with pytest.raises(
        reference_audit.ReferenceAuditError,
        match="canonical rebuilt C",
    ):
        reference_audit.audit(relative, rebuild_binaries=True)


def test_source_rebuild_failure_is_a_report_failure_not_a_passing_check(
    live_pilot: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An independent compiler failure cannot yield a positive audit count."""
    _, relative = live_pilot

    def rejected(
        identity: object,
        mode: str,
    ) -> bytes:
        _ = (identity, mode)
        message = "injected independent compiler failure"
        raise host_c_oracle.HostOracleError(message)

    monkeypatch.setattr(host_c_oracle, "rebuild_reference", rejected)
    with pytest.raises(
        reference_audit.ReferenceAuditError,
        match="compiler failure",
    ):
        reference_audit.audit(relative, rebuild_binaries=True)


def test_cli_rebuild_output_checks_native_artifact_reproducibility(
    live_pilot: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The explicit flag emits independently built source provenance counts."""
    _, relative = live_pilot
    monkeypatch.setattr(
        sys,
        "argv",
        ["reference-audit", relative, "--rebuild-binaries"],
    )
    assert reference_audit.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["host_c_reference_builds_reproduced"] == OBSERVED_PAIRS
    assert report["host_c_binaries_checked"] == OBSERVED_PAIRS * 2
    assert not report["host_c_oracle_replayed"]


@pytest.mark.parametrize("mode", ["-O3", "-invalid", ""])
def test_native_rebuild_refuses_unsupported_compiler_mode(mode: str) -> None:
    """Rebuilds cannot be steered into arbitrary compiler flags."""
    identity = generate.ChallengeIdentity(
        FAMILY,
        1,
        7,
        reference_study.PROFILE,
        4,
    )
    with pytest.raises(
        host_c_oracle.HostOracleError, match="optimization mode"
    ):
        _ = host_c_oracle.rebuild_reference(identity, mode)


GIT_HASH_WIDTH = 40
FAKE_SOURCE_COMMIT = "f" * GIT_HASH_WIDTH
OPTIMIZED_MODE = "-O2"
INJECTED_SANITIZED = "injected linker?failed?with nonascii ?"
LINE_BREAK = "\n"
FAILURE_MISSING = "missing"
FAILURE_NO_ENTRY = "no-entry"
FAILURE_INVENTED = "invented"
FAILURE_INVALID_SIZE = "invalid-size"


def _rewrite_manifest_commit(directory: Path, old: str, new: str) -> None:
    for filename in (directory / "runs").glob("*.toml"):
        content = filename.read_text(encoding="utf-8")
        _ = filename.write_text(
            content.replace(f'commit = "{old}"', f'commit = "{new}"'),
            encoding="utf-8",
        )


def test_all_reported_trials_share_one_source_commit(
    live_pilot: tuple[Path, str],
) -> None:
    """A fabricated single-run commit cannot hide among otherwise valid runs."""
    directory, relative = live_pilot
    healthy = reference_audit.audit(relative)
    assert len(healthy["recorded_source_commit"]) == GIT_HASH_WIDTH
    assert not healthy["source_commit_object_verified"]
    manifest = next((directory / "runs").glob("*.toml"))
    content = manifest.read_text(encoding="utf-8")
    _ = manifest.write_text(
        content.replace(
            f'commit = "{healthy["recorded_source_commit"]}"',
            f'commit = "{FAKE_SOURCE_COMMIT}"',
        ),
        encoding="utf-8",
    )
    with pytest.raises(
        reference_audit.ReferenceAuditError,
        match="disagree on source commit",
    ):
        reference_audit.audit(relative)


def test_opt_in_git_object_check_rejects_missing_recorded_commit(
    live_pilot: tuple[Path, str],
) -> None:
    """Cross-file agreement alone does not authenticate claimed Git objects."""
    directory, relative = live_pilot
    healthy = reference_audit.audit(relative)
    _rewrite_manifest_commit(
        directory,
        healthy["recorded_source_commit"],
        FAKE_SOURCE_COMMIT,
    )
    unchecked = reference_audit.audit(relative)
    assert unchecked["recorded_source_commit"] == FAKE_SOURCE_COMMIT
    assert not unchecked["source_commit_object_verified"]
    with pytest.raises(
        reference_audit.ReferenceAuditError,
        match="local Git commit object",
    ):
        reference_audit.audit(relative, require_source_commit_object=True)


def test_opt_in_git_object_check_admits_original_real_source_commit(
    live_pilot: tuple[Path, str],
) -> None:
    """An existing real source revision remains admissible after HEAD moves."""
    _, relative = live_pilot
    checked = reference_audit.audit(relative, require_source_commit_object=True)
    assert checked["source_commit_object_verified"]
    assert len(checked["recorded_source_commit"]) == GIT_HASH_WIDTH


def test_source_commit_object_check_requires_installed_git(
    live_pilot: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unavailable Git cannot impersonate successful source-object review."""
    _, relative = live_pilot
    monkeypatch.setattr(reference_audit.shutil, "which", lambda _: None)
    with pytest.raises(
        reference_audit.ReferenceAuditError,
        match="requires local Git",
    ):
        reference_audit.audit(relative, require_source_commit_object=True)


def test_cli_source_commit_object_flag_emits_checked_provenance(
    live_pilot: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Strict post-run CLI preserves the commit-identity audit result."""
    _, relative = live_pilot
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "reference-audit",
            relative,
            "--require-source-commit-object",
        ],
    )
    assert reference_audit.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["source_commit_object_verified"]
    assert len(report["recorded_source_commit"]) == GIT_HASH_WIDTH


@pytest.fixture
def failed_pilot(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[Path, str]]:
    """Retain one real host-C successful arm and one failed O2 attempt.

    Yields:
        Failed-study directory and canonical study path for audit tampering.

    """
    original = host_c_oracle.measure_reference

    def fail_o2(
        identity: generate.ChallengeIdentity,
        mode: str,
    ) -> host_c_oracle.ReferenceMeasurement:
        if mode == OPTIMIZED_MODE:
            message = "injected linker\nfailed\twith nonascii é"
            raise host_c_oracle.HostOracleError(message)
        return original(identity, mode)

    monkeypatch.setattr(host_c_oracle, "measure_reference", fail_o2)
    directory, _ = reference_study.run_study(
        reference_study.StudyPlan(FAMILY, (4,), 7, 1),
    )
    try:
        yield (
            directory,
            (directory / "study.json")
            .relative_to(
                reference_audit._ROOT,
            )
            .as_posix(),
        )
    finally:
        shutil.rmtree(directory)


def test_failed_native_attempt_retains_bounded_diagnostic_provenance(
    failed_pilot: tuple[Path, str],
) -> None:
    """Failure outcome must have an exact separate printable diagnostic map."""
    directory, relative = failed_pilot
    source = json.loads((directory / "failures.json").read_text())
    assert source["schema_version"] == 1
    assert len(source["failures"]) == 1
    message = next(iter(source["failures"].values()))
    assert INJECTED_SANITIZED in message
    assert LINE_BREAK not in message
    result = reference_audit.audit(relative)
    assert result["host_c_failure_diagnostics_checked"] == 1
    assert result["host_c_binaries_checked"] == 1


@pytest.mark.parametrize(
    "tamper",
    ["missing", "no-entry", "invented", "invalid-size", "bad-schema"],
)
def test_audit_rejects_forged_or_missing_failure_diagnostics(
    failed_pilot: tuple[Path, str],
    tamper: str,
) -> None:
    """Recorded failures must not lose their negative-evidence explanations."""
    directory, relative = failed_pilot
    path = directory / "failures.json"
    if tamper == FAILURE_MISSING:
        path.unlink()
    else:
        record = json.loads(path.read_text())
        if tamper == FAILURE_NO_ENTRY:
            record["failures"] = {}
        elif tamper == FAILURE_INVENTED:
            record["failures"]["forged-run"] = "forged"
        elif tamper == FAILURE_INVALID_SIZE:
            name = next(iter(record["failures"]))
            record["failures"][name] = "x" * 300
        else:
            record["schema_version"] = 2
        _ = path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(reference_audit.ReferenceAuditError, match="host-C"):
        reference_audit.audit(relative)


def test_old_successful_study_without_failure_sidecar_is_admitted(
    live_pilot: tuple[Path, str],
) -> None:
    """Complete healthy legacy studies predate this optional new file."""
    directory, relative = live_pilot
    (directory / "failures.json").unlink()
    assert (
        reference_audit.audit(relative)["host_c_failure_diagnostics_checked"]
        == 0
    )


def test_failure_diagnostic_drift_fails_cli_without_reporting_pareto(
    failed_pilot: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Malformed negative evidence cannot publish a positive study report."""
    directory, relative = failed_pilot
    _ = (directory / "failures.json").write_bytes(b"broken")
    monkeypatch.setattr(sys, "argv", ["reference-audit", relative])
    with pytest.raises(SystemExit, match="2"):
        reference_audit.main()
    capture = capsys.readouterr()
    assert not capture.out
    assert INVALID_STUDY in capture.err
