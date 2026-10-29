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
#   - Offline producer-specific target source and VM replay audit regressions.
# - Must-Not:
#   - Present synthetic tampering as a measured target performance result.
# - Allows:
#   - Inputs: freshly retained local classic echo studies and corruptions.
#   - Outputs: fail-closed source, manifest, corpus and VM replay assertions.
#   - Side effects: test-owned ignored study output and bounded VM children.
# - Split-When:
#   - General target candidate research needs a larger semantic oracle.
# - Merge-When:
#   - One native Malbolge verifier supersedes this fixed echo auditor.
# - Summary:
#   - Detects forged retained source despite consistent raw/manifest records.
# - Description:
#   - Covers exact source decode, producer claims, study populations and replay.
# - Usage:
#   - pytest benchmarks/arena/tests/test_target_echo_audit.py.
# - Defaults:
#   - Fail closed without physical replay rather than infer run authentication.
#

"""Post-run classic Malbolge target evidence and strict replay tests."""

# ruff: file-ignore[assert,private-member-access]

from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
import tempfile
import tomllib
from typing import Any
from typing import TYPE_CHECKING

import pytest

from benchmarks.arena import analyze
from benchmarks.arena import evidence
from benchmarks.arena import target_echo_audit as audit
from benchmarks.arena import target_echo_reference as producer

if TYPE_CHECKING:
    from collections.abc import Iterator

ROWS = 8
REPLAYED = 8
MAX_PHASE_TRIALS = 2
FRONTIERS = 2
INVALID_SOURCE = 33
DIFFICULTY = 1
FORGED_TRIAL = 999
ELAPSED = "elapsed_ns"
ARTIFACT_BYTES = "artifact_bytes"
EXTRA_ARTIFACT = "extra"
NOT_AUTHENTICATED = "not authenticated"
AUDIT_MESSAGE = "target audit"
BAD_PROFILE_PROVENANCE = 'implementation = "forged/fake_compiler.py"'
REAL_PROFILE_PROVENANCE = (
    'implementation = "benchmarks/arena/target_echo_reference.py"'
)


@pytest.fixture
def retained(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[Path, dict[str, Any], str]]:
    """Create a real target pilot and remove only its own ignored directory.

    Yields:
        Local output root, recorded study and canonical relative path.

    """
    if (
        not producer.DEFAULT_EMITTER.is_file()
        or not producer.DEFAULT_RUNNER.is_file()
    ):
        pytest.skip("repository Malbolge binaries are not built")
    with tempfile.TemporaryDirectory(
        dir=producer._TEMP,
        prefix="arena-target-test-tools-",
    ) as tool_directory:
        emitter = Path(tool_directory) / "malbolge_layout"
        runner = Path(tool_directory) / "malbolge"
        emitter.hardlink_to(producer.DEFAULT_EMITTER)
        runner.hardlink_to(producer.DEFAULT_RUNNER)
        monkeypatch.setattr(producer, "DEFAULT_EMITTER", emitter)
        monkeypatch.setattr(producer, "DEFAULT_RUNNER", runner)
        directory, document = producer.run_study(
            producer.StudyPlan((1, 4), 2),
            emitter=emitter,
            runner=runner,
        )
        relative = (directory / "study.json").relative_to(producer._ROOT)
        try:
            yield directory, document, relative.as_posix()
        finally:
            shutil.rmtree(directory)


def _save(directory: Path, document: dict[str, Any]) -> None:
    (directory / "study.json").write_text(
        json.dumps(document, sort_keys=True),
        encoding="utf-8",
    )


def _first_source(directory: Path, document: dict[str, Any]) -> Path:
    row = document["observations"][0]
    case, trial = row["case"], row["trial"]
    stem = f"{row["algorithm"]}-pairs-{case["difficulty"]}-trial-{trial}"
    return directory / "candidates" / f"{stem}.malbolge"


def _recheck_generic(document: dict[str, Any]) -> None:
    admitted = analyze.parse_document(json.dumps(document))
    _ = evidence.validate_links(
        admitted,
        producer._ROOT,
        policy=evidence.EvidencePolicy(
            require_raw_rows=True,
            require_trial_run_identity=True,
            require_budget_agreement=True,
        ),
    )


def test_real_retained_target_study_passes_offline_and_replay(
    retained: tuple[Path, dict[str, Any], str],
) -> None:
    """Static independent instruction decode precedes a real VM rerun."""
    _, study, relative = retained
    checked = audit.audit(relative)
    assert checked["verified_target_sources_checked"] == ROWS
    assert checked["target_sources_replayed"] == 0
    assert len(checked["source_sha256"]) == ROWS
    assert len(checked["pareto_frontiers"]) == FRONTIERS
    assert checked["evidence_preflight"]["raw_rows_matched"] == ROWS
    assert checked["reported_failed_trials_not_replayed"] == 0
    assert NOT_AUTHENTICATED in checked["scope"]
    replay = audit.audit(
        relative, options=audit.AuditOptions(replay_candidates=True)
    )
    assert replay["target_sources_replayed"] == REPLAYED
    assert replay["source_sha256"] == checked["source_sha256"]
    assert replay["capacity_curve"] == checked["capacity_curve"]
    assert study["study"]["stage"].startswith("measured-classic")


@pytest.mark.skipif(
    not producer.DEFAULT_EMITTER.is_file()
    or not producer.DEFAULT_RUNNER.is_file(),
    reason="repository Malbolge binaries are not built",
)
def test_real_64_pair_echo_crosses_two_classic_decode_phases() -> None:
    """The fixed target oracle remains exact across code positions above 94."""
    with tempfile.TemporaryDirectory(
        dir=producer._TEMP,
        prefix="arena-target-phase-tools-",
    ) as tools:
        emitter = Path(tools) / "malbolge_layout"
        runner = Path(tools) / "malbolge"
        emitter.hardlink_to(producer.DEFAULT_EMITTER)
        runner.hardlink_to(producer.DEFAULT_RUNNER)
        directory, document = producer.run_study(
            producer.StudyPlan((producer.MAX_PAIRS,), 1),
            emitter=emitter,
            runner=runner,
        )
        try:
            relative = (directory / "study.json").relative_to(producer._ROOT)
            checked = audit.audit(
                relative.as_posix(),
                options=audit.AuditOptions(
                    replay_candidates=True,
                    emitter=emitter,
                    runner=runner,
                ),
            )
            assert (
                checked["verified_target_sources_checked"] == MAX_PHASE_TRIALS
            )
            assert checked["target_sources_replayed"] == MAX_PHASE_TRIALS
            assert {
                row["algorithm"]: row["metrics"][ARTIFACT_BYTES]
                for row in document["observations"]
            } == {producer.BASELINE: 129, producer.CANDIDATE: 193}
        finally:
            shutil.rmtree(directory)


def test_same_length_source_rewrite_passes_generic_but_fails_target_decode(
    retained: tuple[Path, dict[str, Any], str],
) -> None:
    """Self-consistent metrics do not establish original target instructions."""
    directory, document, relative = retained
    path = _first_source(directory, document)
    source = bytearray(path.read_bytes())
    source[0] = (
        INVALID_SOURCE if source[0] != INVALID_SOURCE else INVALID_SOURCE + 1
    )
    path.write_bytes(source)
    _recheck_generic(document)
    with pytest.raises(audit.TargetEchoAuditError, match="source instruction"):
        audit.audit(relative)


def test_missing_verified_source_is_rejected(
    retained: tuple[Path, dict[str, Any], str],
) -> None:
    """A reported verified trial must retain its actual guest source."""
    directory, document, relative = retained
    _first_source(directory, document).unlink()
    with pytest.raises(
        audit.TargetEchoAuditError, match=r"must be|No such file"
    ):
        audit.audit(relative)


@pytest.mark.parametrize("tamper", ["extra", "link"])
def test_extra_or_linked_candidate_is_rejected(
    retained: tuple[Path, dict[str, Any], str],
    tamper: str,
) -> None:
    """Candidate directory admission checks its complete file inventory."""
    directory, document, relative = retained
    existing = _first_source(directory, document)
    if tamper == EXTRA_ARTIFACT:
        (directory / "candidates" / "foreign.malbolge").write_bytes(
            existing.read_bytes()
        )
    else:
        other = next(
            path
            for path in (directory / "candidates").iterdir()
            if path != existing
        )
        existing.unlink()
        existing.symlink_to(other)
    with pytest.raises(audit.TargetEchoAuditError, match=r"unexpected|symlink"):
        audit.audit(relative)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("question", "Did the emitter run at all?"),
        ("hypothesis", "All algorithms behave equally"),
        ("stage", "host-c-reference-not-malbolge"),
        ("rejection_observation", "No difference is ever meaningful"),
    ],
)
def test_foreign_study_claims_pass_generic_but_fail_producer_audit(
    retained: tuple[Path, dict[str, Any], str],
    field: str,
    value: str,
) -> None:
    """Arbitrary research claims cannot impersonate a fixed real producer."""
    directory, document, relative = retained
    modified = copy.deepcopy(document)
    modified["study"][field] = value
    _save(directory, modified)
    _recheck_generic(modified)
    with pytest.raises(audit.TargetEchoAuditError, match="producer policy"):
        audit.audit(relative)


def test_foreign_manifest_provenance_is_rejected(
    retained: tuple[Path, dict[str, Any], str],
) -> None:
    """Generic valid run links cannot claim foreign implementation as native."""
    _, document, relative = retained
    row = document["observations"][0]
    manifest = producer._ROOT / row["experiment_manifest"]
    raw = manifest.read_text(encoding="utf-8")
    assert REAL_PROFILE_PROVENANCE in raw
    manifest.write_text(
        raw.replace(REAL_PROFILE_PROVENANCE, BAD_PROFILE_PROVENANCE),
        encoding="utf-8",
    )
    _recheck_generic(document)
    with pytest.raises(audit.TargetEchoAuditError, match="foreign producer"):
        audit.audit(relative)


def test_unbalanced_population_fails_despite_generic_cohort_agreement(
    retained: tuple[Path, dict[str, Any], str],
) -> None:
    """Each level must retain one identical consecutive repetition plan."""
    directory, document, relative = retained
    modified = copy.deepcopy(document)
    modified["observations"] = [
        row
        for row in modified["observations"]
        if not (row["case"]["difficulty"] == DIFFICULTY and row["trial"] == 1)
    ]
    _save(directory, modified)
    _recheck_generic(modified)
    with pytest.raises(audit.TargetEchoAuditError, match="complete matched"):
        audit.audit(relative)


def test_real_study_profile_binary_digest_required_for_vm_replay(
    retained: tuple[Path, dict[str, Any], str],
) -> None:
    """Replaying with a new binary cannot claim original toolchain identity."""
    directory, document, relative = retained
    modified = copy.deepcopy(document)
    forged = "local-compiler-vm-sha256:" + "f" * 64
    modified["study"]["toolchain"] = forged
    for row in modified["observations"]:
        manifest = producer._ROOT / row["experiment_manifest"]
        original = manifest.read_text(encoding="utf-8")
        manifest.write_text(
            original.replace(document["study"]["toolchain"], forged),
            encoding="utf-8",
        )
    _save(directory, modified)
    _recheck_generic(modified)
    assert audit.audit(relative)["verified_target_sources_checked"] == ROWS
    with pytest.raises(audit.TargetEchoAuditError, match="toolchain differs"):
        audit.audit(
            relative, options=audit.AuditOptions(replay_candidates=True)
        )


def test_opt_in_git_object_admission_confirms_real_source_revision(
    retained: tuple[Path, dict[str, Any], str],
) -> None:
    """A recorded local commit is independently resolved only on opt-in."""
    _, _, relative = retained
    result = audit.audit(
        relative,
        options=audit.AuditOptions(require_source_commit_object=True),
    )
    assert result["source_commit_object_verified"] is True


@pytest.mark.parametrize("hostile_name", ["GIT_DIR", "GIT_OBJECT_DIRECTORY"])
def test_source_commit_object_lookup_ignores_hostile_git_environment(
    retained: tuple[Path, dict[str, Any], str],
    monkeypatch: pytest.MonkeyPatch,
    hostile_name: str,
) -> None:
    """Ambient Git overrides cannot replace the project's object database."""
    _, _, relative = retained
    forged = producer._TEMP / "absent-arena-git-object-database"
    monkeypatch.setenv(hostile_name, str(forged))
    result = audit.audit(
        relative,
        options=audit.AuditOptions(require_source_commit_object=True),
    )
    assert result["source_commit_object_verified"] is True


def test_source_commit_opt_in_cli_reports_checked_revision(
    retained: tuple[Path, dict[str, Any], str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Explicit CLI source-object admission has a visible checked result."""
    _, _, relative = retained
    monkeypatch.setattr(
        sys,
        "argv",
        ["target-echo-audit", relative, "--require-source-commit-object"],
    )
    assert audit.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result["source_commit_object_verified"] is True
    assert result["verified_target_sources_checked"] == ROWS


def test_forged_consistent_git_commit_is_rejected_when_requested(
    retained: tuple[Path, dict[str, Any], str],
) -> None:
    """Consistent invented source revision cannot claim local Git provenance."""
    _, document, relative = retained
    for row in document["observations"]:
        manifest = producer._ROOT / row["experiment_manifest"]
        original = manifest.read_text(encoding="utf-8")
        previous = tomllib.loads(original)["run"]["commit"]
        updated = original.replace(
            f'commit = "{previous}"',
            'commit = "' + "f" * 40 + '"',
        )
        assert updated != original
        manifest.write_text(updated, encoding="utf-8")
    assert audit.audit(relative)["source_commit_object_verified"] is False
    with pytest.raises(audit.TargetEchoAuditError, match="Git commit object"):
        audit.audit(
            relative,
            options=audit.AuditOptions(require_source_commit_object=True),
        )


def test_mutated_retained_source_during_report_is_rejected(
    retained: tuple[Path, dict[str, Any], str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A new source mutation after initial decode cannot enter the report."""
    directory, document, relative = retained
    target = _first_source(directory, document)
    actual_analyze = analyze.analyze

    def mutate_after_decode(study: dict[str, Any]) -> dict[str, Any]:
        contents = bytearray(target.read_bytes())
        contents[0] = (
            INVALID_SOURCE
            if contents[0] != INVALID_SOURCE
            else INVALID_SOURCE + 1
        )
        target.write_bytes(contents)
        return actual_analyze(study)

    monkeypatch.setattr(audit.analyze, "analyze", mutate_after_decode)
    with pytest.raises(
        audit.TargetEchoAuditError, match="changed before report"
    ):
        audit.audit(relative)


@pytest.mark.parametrize("evidence_kind", ["study", "raw", "run"])
def test_retained_evidence_changed_after_preflight_is_rejected(
    retained: tuple[Path, dict[str, Any], str],
    monkeypatch: pytest.MonkeyPatch,
    evidence_kind: str,
) -> None:
    """Source-stable but changed study/run/raw evidence cannot publish."""
    directory, document, relative = retained
    row = document["observations"][0]
    paths = {
        "study": directory / "study.json",
        "raw": producer._ROOT / row["raw_sample"],
        "run": producer._ROOT / row["experiment_manifest"],
    }
    victim = paths[evidence_kind]
    real_analyze = analyze.analyze

    def mutate_after_preflight(study: dict[str, Any]) -> dict[str, Any]:
        victim.write_bytes(victim.read_bytes() + b"\n")
        return real_analyze(study)

    monkeypatch.setattr(audit.analyze, "analyze", mutate_after_preflight)
    with pytest.raises(
        audit.TargetEchoAuditError, match="changed before report"
    ):
        audit.audit(relative)


@pytest.mark.parametrize(
    "unreported",
    [
        ("runs", "unreported.toml"),
        ("raw", "unreported.csv"),
        ("candidates", "unreported.malbolge"),
    ],
)
def test_late_unreported_evidence_file_is_rejected(
    retained: tuple[Path, dict[str, Any], str],
    monkeypatch: pytest.MonkeyPatch,
    unreported: tuple[str, str],
) -> None:
    """Post-preflight added trial files cannot enter a complete report."""
    directory, _, relative = retained
    folder, name = unreported
    added = directory / folder / name
    real_analyze = analyze.analyze

    def add_after_preflight(study: dict[str, Any]) -> dict[str, Any]:
        added.write_bytes(b"unreported")
        return real_analyze(study)

    monkeypatch.setattr(audit.analyze, "analyze", add_after_preflight)
    with pytest.raises(
        audit.TargetEchoAuditError,
        match=r"missing or unexpected|unexpected candidate",
    ):
        audit.audit(relative)


def test_injected_mismatched_vm_replay_fails_closed(
    retained: tuple[Path, dict[str, Any], str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Static source acceptance does not allow forged reexecution output."""
    _, _, relative = retained

    def wrong_output(
        runner: Path,
        source: Path,
    ) -> sp.CompletedProcess[bytes]:
        _ = (runner, source)
        return sp.CompletedProcess(["fake-vm"], 0, stdout=b"wrong", stderr=b"")

    monkeypatch.setattr(audit, "_invoke_runner", wrong_output)
    with pytest.raises(audit.TargetEchoAuditError, match="VM replay rejected"):
        audit.audit(
            relative, options=audit.AuditOptions(replay_candidates=True)
        )


@pytest.mark.parametrize(
    "relative",
    [
        "/etc/passwd",
        "study.json",
        ".temp/arena-host-c-study-evil/study.json",
        ".temp/arena-target-echo-../study.json",
        ".temp/arena-target-echo-abc/other.json",
        ".temp/arena-target-echo-a/b/study.json",
    ],
)
def test_noncanonical_study_path_never_triggers_audit(relative: str) -> None:
    """Offline audit accepts only producer-owned generated study directory."""
    with pytest.raises(audit.TargetEchoAuditError, match="target audit"):
        audit.audit(relative)


def test_audit_cli_rejects_bad_path_without_stdout(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Invalid claims never publish a misleading complete JSON report."""
    monkeypatch.setattr(sys, "argv", ["target-audit", "study.json"])
    with pytest.raises(SystemExit, match="2"):
        audit.main()
    output = capsys.readouterr()
    assert not output.out
    assert AUDIT_MESSAGE in output.err
