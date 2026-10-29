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
