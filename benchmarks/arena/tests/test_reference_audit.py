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

import json
import shutil
import sys
from dataclasses import replace
from hashlib import sha256
from typing import TYPE_CHECKING, Any, cast

import pytest

from benchmarks.arena import (
    analyze,
    evidence,
    host_c_oracle,
    reference_audit,
    reference_study,
    report_output,
)
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
        path.relative_to(directory).as_posix(): sha256(path.read_bytes()).hexdigest()
        for path in directory.rglob("*")
        if path.is_file()
    }


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("replay_oracles", "false"),
        ("replay_oracles", 0),
        ("rebuild_binaries", "no"),
        ("rebuild_binaries", 1),
        ("require_source_commit_object", None),
        ("require_source_commit_object", 1),
        ("require_resource_controls_record", 0),
        ("require_resource_controls_record", object()),
    ],
)
def test_direct_host_c_audit_rejects_nonboolean_options_before_access(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    invalid: object,
) -> None:
    """Foreign option values must not opt in to native replay or emit claims."""
    options = replace(reference_audit.AuditOptions(), **{field: invalid})

    def forbidden_prefix(*args: object, **kwargs: object) -> str:
        _ = (args, kwargs)
        message = "invalid options reached path and native replay admission"
        raise AssertionError(message)

    monkeypatch.setattr(reference_audit, "_prefix", forbidden_prefix)
    with pytest.raises(reference_audit.ReferenceAuditError, match="exact booleans"):
        reference_audit.audit(
            ".temp/arena-host-c-study-options/study.json", options=options
        )


@pytest.mark.parametrize("invalid", [None, False, 0, "disabled", object()])
def test_direct_host_c_audit_rejects_foreign_option_container(
    monkeypatch: pytest.MonkeyPatch,
    invalid: object,
) -> None:
    """A non-options object must fail before path or native tool admission."""

    def forbidden_prefix(*args: object, **kwargs: object) -> str:
        _ = (args, kwargs)
        message = "foreign options reached audit path admission"
        raise AssertionError(message)

    monkeypatch.setattr(reference_audit, "_prefix", forbidden_prefix)
    with pytest.raises(reference_audit.ReferenceAuditError, match="exact booleans"):
        reference_audit.audit(
            ".temp/arena-host-c-study-options/study.json",
            options=cast("reference_audit.AuditOptions", invalid),
        )


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
    assert observed["evidence_preflight"]["raw_rows_matched"] == OBSERVED_PAIRS * 2
    assert (
        observed["evidence_preflight"]["regenerated_challenge_bundles"] == LEVEL_COUNT
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
    observed = reference_audit.audit(
        relative, options=reference_audit.AuditOptions(replay_oracles=True)
    )
    preflight = observed["evidence_preflight"]
    assert preflight["host_c_challenge_oracles_replayed"] == LEVEL_COUNT
    assert preflight["host_c_replay_modes"] == ["O0", "O2"]
    assert observed["host_c_oracle_replayed"]
    assert hashes_before == _file_hashes(directory)


@pytest.mark.parametrize(
    "family",
    ("composed-pipeline", "ternary-fold", "pointer-walk", "alias-walk"),
)
def test_strict_host_c_audit_replays_diverse_challenge_families(
    family: str,
) -> None:
    """Independent strict replay remains source-bound beyond arithmetic DAGs."""
    directory, document = reference_study.run_study(
        reference_study.StudyPlan(family, (8,), 23, 1),
    )
    try:
        relative = (
            (directory / "study.json").relative_to(reference_audit._ROOT).as_posix()
        )
        before = _file_hashes(directory)
        report = reference_audit.audit(
            relative,
            options=reference_audit.AuditOptions(
                replay_oracles=True,
                rebuild_binaries=True,
                require_source_commit_object=True,
                require_resource_controls_record=True,
            ),
        )
        assert len(document["observations"]) == 2
        assert all(
            row["outcome"] == analyze.VERIFIED for row in document["observations"]
        )
        assert report["evidence_preflight"]["raw_rows_matched"] == 2
        assert report["evidence_preflight"]["host_c_challenge_oracles_replayed"] == 1
        assert report["host_c_binaries_checked"] == 2
        assert report["host_c_reference_builds_reproduced"] == 2
        assert report["source_commit_object_verified"]
        assert report["resource_controls_record_version"] == 2
        assert before == _file_hashes(directory)
    finally:
        shutil.rmtree(directory)


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


@pytest.mark.parametrize("missing_trial", [0, 1])
def test_audit_rejects_uneven_repetitions_between_difficulties(
    live_pilot: tuple[Path, str],
    missing_trial: int,
) -> None:
    """Paired arms at each level still need one common source-run trial plan."""
    directory, relative = live_pilot
    path = directory / "study.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["observations"] = [
        row
        for row in document["observations"]
        if not (row["case"]["difficulty"] == 8 and row["trial"] == missing_trial)
    ]
    # The generic arena legitimately accepts different sample sizes per level.
    # The host-C producer cannot create this plan: every level uses 2 trials.
    _ = analyze.analyze(analyze.parse_document(json.dumps(document)))
    _ = path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(
        reference_audit.ReferenceAuditError,
        match="same trials at every difficulty",
    ):
        reference_audit.audit(relative)


def test_host_c_audit_rejects_rekeyed_native_trial_artifacts(
    live_pilot: tuple[Path, str],
) -> None:
    """Matching file digests cannot legitimize a foreign producer filename."""
    directory, relative = live_pilot
    study_path = directory / "study.json"
    study = json.loads(study_path.read_text(encoding="utf-8"))
    row = study["observations"][0]
    original_manifest = row["experiment_manifest"]
    original_raw = row["raw_sample"]
    old_stem = original_manifest.rsplit("/", maxsplit=1)[1].removesuffix(".toml")
    new_stem = f"forged-{old_stem}"
    new_manifest = original_manifest.replace(old_stem, new_stem)
    new_raw = original_raw.replace(old_stem, new_stem)
    old_manifest_path = reference_audit._ROOT / original_manifest
    manifest_source = old_manifest_path.read_text(encoding="utf-8")
    assert manifest_source.count(original_raw) == 1
    _ = old_manifest_path.rename(reference_audit._ROOT / new_manifest)
    _ = (reference_audit._ROOT / new_manifest).write_text(
        manifest_source.replace(original_raw, new_raw), encoding="utf-8"
    )
    _ = (reference_audit._ROOT / original_raw).rename(reference_audit._ROOT / new_raw)
    artifacts_path = directory / "artifacts.json"
    artifacts = json.loads(artifacts_path.read_text(encoding="utf-8"))
    artifact = artifacts.pop(original_manifest)
    old_binary = reference_audit._ROOT / artifact["path"]
    artifact["path"] = artifact["path"].replace(old_stem, new_stem)
    _ = old_binary.rename(reference_audit._ROOT / artifact["path"])
    artifacts[new_manifest] = artifact
    _ = artifacts_path.write_text(json.dumps(artifacts), encoding="utf-8")
    row["experiment_manifest"] = new_manifest
    row["raw_sample"] = new_raw
    _ = study_path.write_text(json.dumps(study), encoding="utf-8")

    # Every generic identity, raw-row, binary digest and budget remains valid.
    admitted = analyze.parse_document(json.dumps(study))
    _ = analyze.analyze(admitted)
    linked = evidence.validate_links(
        admitted,
        reference_audit._ROOT,
        policy=evidence.EvidencePolicy(
            require_trial_run_identity=True,
            require_budget_agreement=True,
            challenge_root=f"{directory.relative_to(reference_audit._ROOT)}/bundles",
        ),
    )
    assert linked["raw_rows_matched"] == OBSERVED_PAIRS * 2
    assert reference_study.check_retained_artifacts(study, artifacts) == (
        OBSERVED_PAIRS * 2
    )
    with pytest.raises(
        reference_audit.ReferenceAuditError,
        match="trial paths differ from native producer",
    ):
        reference_audit.audit(relative)


@pytest.mark.parametrize("field", ["question", "hypothesis", "rejection_observation"])
def test_host_c_reference_rejects_forged_fixed_research_claim(
    live_pilot: tuple[Path, str],
    field: str,
) -> None:
    """A native reference study cannot silently substitute its experiment."""
    directory, relative = live_pilot
    path = directory / "study.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["study"][field] = "An unrelated research question on native C."
    _ = analyze.analyze(analyze.parse_document(json.dumps(document)))
    _ = path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(
        reference_audit.ReferenceAuditError,
        match="producer research claims",
    ):
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


@pytest.mark.parametrize("mutation", ["extra", "missing", "bad-type", "bad-shape"])
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


class _ForeignIndexKey(str):
    """A claimed JSON mapping key with hostile string equality."""

    def __eq__(self, _: object) -> bool:
        raise AssertionError("foreign artifact index key equality executed")

    __hash__ = str.__hash__


class _ForeignIndexMap(dict):
    """A mapping subclass which must not be used as a canonical JSON map."""

    def __len__(self) -> int:
        raise AssertionError("foreign artifact index map length executed")

    def __iter__(self) -> Any:
        raise AssertionError("foreign artifact index map iteration executed")


@pytest.mark.parametrize("kind", ["root-map", "root-key", "entry-map", "entry-key"])
def test_direct_artifact_index_rejects_foreign_container_or_keys(
    kind: str,
) -> None:
    """Caller-defined JSON map equality, size and iteration are not authority."""
    name = "runs/one.toml"
    entry = {"path": "candidates/one", "sha256": "a" * 64}
    source: dict[str, Any] = {name: entry}
    if kind == "root-map":
        source = _ForeignIndexMap(source)
    elif kind == "root-key":
        source = {_ForeignIndexKey(name): entry}
    elif kind == "entry-map":
        source = {name: _ForeignIndexMap(entry)}
    else:
        value = entry.pop("path")
        entry[_ForeignIndexKey("path")] = value
    with pytest.raises(reference_audit.ReferenceAuditError, match="artifact index"):
        reference_audit._check_artifact_index(source, {"observations": [{}]})


def test_direct_artifact_index_accepts_native_record() -> None:
    """Native identity maps remain usable after exact admission."""
    source = {"runs/one.toml": {
        "path": "candidates/one", "sha256": "a" * 64,
    }}
    assert reference_audit._check_artifact_index(
        source, {"observations": [{}]}
    ) == source


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
    report = reference_audit.audit(
        relative, options=reference_audit.AuditOptions(rebuild_binaries=True)
    )
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
        reference_audit.audit(
            relative,
            options=reference_audit.AuditOptions(rebuild_binaries=True),
        )


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
        reference_audit.audit(
            relative,
            options=reference_audit.AuditOptions(rebuild_binaries=True),
        )


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
    with pytest.raises(host_c_oracle.HostOracleError, match="optimization mode"):
        _ = host_c_oracle.rebuild_reference(identity, mode)


GIT_HASH_WIDTH = 40
RSS_CONTROL_SCHEMA = 2
MISSING_RECORD_FIELD = "no-field"
LINKED_RECORD = "symlink"
RESOURCE_RECORD_ERROR = "resource-control record"
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


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (
            'implementation = "benchmarks/arena/reference_study.py"',
            'implementation = "benchmarks/arena/foreign_study.py"',
        ),
        (
            'configuration = "benchmarks/arena/README.md"',
            'configuration = "benchmarks/arena/foreign.md"',
        ),
        ('method_class = "benchmarking"', 'method_class = "engineering"'),
        ('accelerator = "none"', 'accelerator = "cuda"'),
    ],
)
def test_host_c_audit_rejects_foreign_run_manifest_provenance(
    live_pilot: tuple[Path, str],
    old: str,
    new: str,
) -> None:
    """Valid research metadata may still contradict this native producer."""
    directory, relative = live_pilot
    path = next((directory / "runs").glob("*.toml"))
    source = path.read_text(encoding="utf-8")
    assert source.count(old) == 1
    _ = path.write_text(source.replace(old, new), encoding="utf-8")
    with pytest.raises(
        reference_audit.ReferenceAuditError,
        match="producer provenance",
    ):
        reference_audit.audit(relative)


def test_host_c_audit_rejects_foreign_recorded_output_root(
    live_pilot: tuple[Path, str],
) -> None:
    """The recorded run-output root must be this exact local study."""
    directory, relative = live_pilot
    path = next((directory / "runs").glob("*.toml"))
    source = path.read_text(encoding="utf-8")
    old = f'output = "{directory.relative_to(reference_audit._ROOT)}"'
    assert source.count(old) == 1
    _ = path.write_text(
        source.replace(old, 'output = "benchmarks/arena/foreign"'),
        encoding="utf-8",
    )
    with pytest.raises(
        reference_audit.ReferenceAuditError,
        match="producer provenance",
    ):
        reference_audit.audit(relative)


@pytest.mark.parametrize("mutation_point", ["after_preflight", "after_analysis"])
def test_host_c_audit_rejects_manifest_drift_between_checks(
    live_pilot: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    mutation_point: str,
) -> None:
    """A later reread must not change the preflight-approved Git provenance."""
    directory, relative = live_pilot
    original_commit = reference_audit.audit(relative)["recorded_source_commit"]
    assert original_commit != FAKE_SOURCE_COMMIT

    def replace_commits() -> None:
        _rewrite_manifest_commit(directory, original_commit, FAKE_SOURCE_COMMIT)

    if mutation_point == "after_preflight":
        preflight = evidence.validate_links

        def mutate_after_preflight(
            document: dict[str, Any],
            root: Path,
            *,
            policy: evidence.EvidencePolicy,
            _snapshot_out: list[Any] | None = None,
        ) -> dict[str, Any]:
            result = preflight(
                document, root, policy=policy, _snapshot_out=_snapshot_out
            )
            replace_commits()
            return result

        monkeypatch.setattr(evidence, "validate_links", mutate_after_preflight)
    else:
        analyze_report = analyze.analyze

        def mutate_after_analysis(document: dict[str, Any]) -> dict[str, Any]:
            result = analyze_report(document)
            replace_commits()
            return result

        monkeypatch.setattr(analyze, "analyze", mutate_after_analysis)

    with pytest.raises(reference_audit.ReferenceAuditError, match="manifest.*changed"):
        reference_audit.audit(relative)


@pytest.mark.parametrize("mutation_point", ["after_preflight", "after_analysis"])
def test_host_c_audit_rejects_study_json_rewrite_during_audit(
    live_pilot: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    mutation_point: str,
) -> None:
    """Report admission must refer to the same study JSON the caller supplied."""
    directory, relative = live_pilot
    original_question = reference_audit.PRODUCER_RESEARCH_CLAIMS["question"]

    def rewrite_study() -> None:
        path = directory / "study.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        assert document["study"]["question"] == original_question
        document["study"]["question"] = "forged research question"
        _ = path.write_text(json.dumps(document), encoding="utf-8")

    if mutation_point == "after_preflight":
        preflight = evidence.validate_links

        def mutate_after_preflight(
            document: dict[str, Any],
            root: Path,
            *,
            policy: evidence.EvidencePolicy,
            _snapshot_out: list[Any] | None = None,
        ) -> dict[str, Any]:
            checked = preflight(
                document, root, policy=policy, _snapshot_out=_snapshot_out
            )
            rewrite_study()
            return checked

        monkeypatch.setattr(evidence, "validate_links", mutate_after_preflight)
    else:
        analyze_report = analyze.analyze

        def mutate_after_analysis(document: dict[str, Any]) -> dict[str, Any]:
            report = analyze_report(document)
            rewrite_study()
            return report

        monkeypatch.setattr(analyze, "analyze", mutate_after_analysis)

    with pytest.raises(
        reference_audit.ReferenceAuditError, match="study JSON.*changed"
    ):
        reference_audit.audit(relative)


@pytest.mark.parametrize("mutation_point", ["after_binary_check", "after_analysis"])
def test_host_c_audit_rejects_retained_binary_rewrite_during_audit(
    live_pilot: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    mutation_point: str,
) -> None:
    """An admitted native artifact cannot drift before the audit reports it."""
    directory, relative = live_pilot
    executable = next((directory / "candidates").iterdir())

    def rewrite_executable() -> None:
        _ = executable.write_bytes(executable.read_bytes() + b"forged")

    if mutation_point == "after_binary_check":
        check_artifacts = reference_study.check_retained_artifacts
        called = False

        def mutate_after_check(
            document: dict[str, Any], artifacts: dict[str, dict[str, str]]
        ) -> int:
            nonlocal called
            result = check_artifacts(document, artifacts)
            if not called:
                called = True
                rewrite_executable()
            return result

        monkeypatch.setattr(
            reference_study, "check_retained_artifacts", mutate_after_check
        )
    else:
        analyze_report = analyze.analyze

        def mutate_after_analysis(document: dict[str, Any]) -> dict[str, Any]:
            result = analyze_report(document)
            rewrite_executable()
            return result

        monkeypatch.setattr(analyze, "analyze", mutate_after_analysis)

    with pytest.raises(
        reference_audit.ReferenceAuditError, match="retained executable differs"
    ):
        reference_audit.audit(relative)


@pytest.mark.parametrize(
    "sidecar",
    ["artifacts", "failures", "resource-controls", "removed-failures", "new-failures"],
)
def test_host_c_audit_rejects_sidecar_drift_after_analysis(
    live_pilot: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    sidecar: str,
) -> None:
    """Reports cannot outlive the exact metadata bytes used at admission."""
    directory, relative = live_pilot
    failure_path = directory / "failures.json"
    if sidecar == "new-failures":
        failure_path.unlink()
    original_analyze = analyze.analyze

    def mutate_after_analysis(document: dict[str, Any]) -> dict[str, Any]:
        report = original_analyze(document)
        if sidecar == "removed-failures":
            failure_path.unlink()
        elif sidecar == "new-failures":
            _ = failure_path.write_text(
                json.dumps({"schema_version": 1, "failures": {"forged": "failed"}}),
                encoding="utf-8",
            )
        else:
            path = directory / f"{sidecar}.json"
            retained = json.loads(path.read_text(encoding="utf-8"))
            if sidecar == "artifacts":
                first = next(iter(retained.values()))
                first["sha256"] = "0" * 64
            elif sidecar == "failures":
                retained["failures"]["forged"] = "failed"
            else:
                retained["cpu_seconds"] += 1
            _ = path.write_text(json.dumps(retained), encoding="utf-8")
        return report

    monkeypatch.setattr(analyze, "analyze", mutate_after_analysis)
    with pytest.raises(
        reference_audit.ReferenceAuditError, match="sidecar.*changed during audit"
    ):
        reference_audit.audit(relative)


class _ForeignSidecarReaderFault(IndexError):
    """A substituted dependency exception cannot render its own diagnostic."""

    def __str__(self) -> str:
        raise AssertionError("foreign retained sidecar exception formatted")


@pytest.mark.parametrize(
    "fault_type", [ValueError, RuntimeError, TypeError, _ForeignSidecarReaderFault]
)
def test_late_host_c_sidecar_read_faults_remain_typed(
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """A failed late read must not publish an untyped audit exception."""
    fault = fault_type("unanticipated sidecar reread failure")

    def fail_read(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise fault

    monkeypatch.setattr(evidence, "read_bounded_regular", fail_read)
    prefix = ".temp/arena-host-c-study-failure"
    fingerprints: dict[str, bytes | None] = {
        f"{prefix}/{leaf}": b"original"
        for leaf in (
            reference_audit.ARTIFACT_LEAF,
            reference_audit.FAILURES_LEAF,
            reference_audit.RESOURCE_CONTROLS_LEAF,
        )
    }
    with pytest.raises(
        reference_audit.ReferenceAuditError, match="sidecar changed during audit"
    ) as caught:
        reference_audit._require_unchanged_sidecars(prefix, fingerprints)
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize("fault_type", [ValueError, RuntimeError, _ForeignSidecarReaderFault])
def test_absent_host_c_sidecar_probe_faults_remain_typed(
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """An inaccessible previously missing sidecar fails without raw host errors."""
    fault = fault_type("unanticipated sidecar absence probe")

    class FailingPath:
        def lstat(self) -> None:
            raise fault

    class FailingRoot:
        def __truediv__(self, _: str) -> FailingPath:
            return FailingPath()

    monkeypatch.setattr(reference_audit, "_ROOT", FailingRoot())
    prefix = ".temp/arena-host-c-study-absent-probe"
    fingerprints: dict[str, bytes | None] = {
        f"{prefix}/{reference_audit.ARTIFACT_LEAF}": None,
    }
    with pytest.raises(
        reference_audit.ReferenceAuditError, match="sidecar changed during audit"
    ) as caught:
        reference_audit._require_unchanged_sidecars(prefix, fingerprints)
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize(
    "source",
    ["raw", "program.c", "oracle.bin", "manifest.json"],
)
def test_host_c_audit_rejects_linked_source_drift_after_analysis(
    live_pilot: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    source: str,
) -> None:
    """A preflight-approved raw row or bundle cannot change before reporting."""
    directory, relative = live_pilot
    path = (
        next((directory / "raw").glob("*.csv"))
        if source == "raw"
        else next((directory / "bundles").rglob(source))
    )
    original_analyze = analyze.analyze

    def mutate_after_analysis(document: dict[str, Any]) -> dict[str, Any]:
        report = original_analyze(document)
        original = path.read_bytes()
        _ = path.write_bytes(bytes([original[0] ^ 1]) + original[1:])
        return report

    monkeypatch.setattr(analyze, "analyze", mutate_after_analysis)
    with pytest.raises(
        reference_audit.ReferenceAuditError,
        match="raw CSV changed|challenge bundle changed",
    ):
        reference_audit.audit(relative)


@pytest.mark.parametrize("folder", ["runs", "raw", "candidates"])
@pytest.mark.parametrize("injection_point", ["before_audit", "after_analysis"])
def test_host_c_audit_rejects_unindexed_trial_file_inventory(
    live_pilot: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    folder: str,
    injection_point: str,
) -> None:
    """An extra run, raw sample, or binary cannot be hidden in the study."""
    directory, relative = live_pilot
    leaf = {
        "runs": "unindexed-run.toml",
        "raw": "unindexed-sample.csv",
        "candidates": "unindexed-binary",
    }[folder]
    path = directory / folder / leaf

    def introduce_extra_file() -> None:
        _ = path.write_bytes(b"foreign trial evidence")

    if injection_point == "before_audit":
        introduce_extra_file()
    else:
        original_analyze = analyze.analyze

        def mutate_after_analysis(document: dict[str, Any]) -> dict[str, Any]:
            report = original_analyze(document)
            introduce_extra_file()
            return report

        monkeypatch.setattr(analyze, "analyze", mutate_after_analysis)

    with pytest.raises(
        reference_audit.ReferenceAuditError,
        match="unregistered host-C trial file",
    ):
        reference_audit.audit(relative)


@pytest.mark.parametrize(
    "invalid",
    [True, 0, b"/usr/bin/git", "", "git", "../git", "/usr/bin/git\0bad", "\ud800"],
    ids=[
        "boolean",
        "integer",
        "bytes",
        "empty",
        "relative",
        "parent",
        "nul",
        "unicode",
    ],
)
def test_audit_git_resolver_rejects_noncanonical_paths_before_launch(
    monkeypatch: pytest.MonkeyPatch, invalid: object
) -> None:
    """A malformed host Git path cannot attest a recorded commit object."""

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("malformed Git path launched a host tool")

    monkeypatch.setattr(
        reference_audit.shutil, "which", lambda *_args, **_kwargs: invalid
    )
    monkeypatch.setattr(reference_audit.sp, "run", forbidden)
    with pytest.raises(reference_audit.ReferenceAuditError, match="Git executable"):
        reference_audit._require_git_commit("0" * 40)


@pytest.mark.parametrize("kind", ["symlink", "directory", "missing", "non-executable"])
def test_audit_git_resolver_requires_physical_executable_before_launch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """A redirected or non-executable Git path cannot attest source commits."""
    fake = tmp_path / "candidate-git"
    if kind == "symlink":
        fake.symlink_to(sys.executable)
    elif kind == "directory":
        fake.mkdir()
    elif kind == "non-executable":
        _ = fake.write_bytes(b"not an executable")
        fake.chmod(0o644)

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("unadmitted Git path reached child launch")

    monkeypatch.setattr(reference_audit.shutil, "which", lambda *_a, **_kw: str(fake))
    monkeypatch.setattr(reference_audit.sp, "run", forbidden)
    diagnostic = "path inspection" if kind == "missing" else "physical executable"
    with pytest.raises(reference_audit.ReferenceAuditError, match=diagnostic):
        reference_audit._require_git_commit("0" * 40)


@pytest.mark.parametrize("operation", ["lstat", "access"])
@pytest.mark.parametrize(
    "failure_type",
    [OSError, ValueError, RuntimeError, TypeError, AttributeError, IndexError, OverflowError, Exception],
)
def test_audit_git_executable_inspection_faults_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    failure_type: type[Exception],
) -> None:
    """Host Git binary metadata and permissions remain typed audit evidence."""
    fake = tmp_path / "candidate-git"
    _ = fake.write_bytes(b"test executable")
    fake.chmod(0o755)
    fault = failure_type("injected Git executable inspection failure")
    original_lstat = type(fake).lstat
    original_access = reference_audit.os.access

    def broken_lstat(path: Path) -> object:
        if path == fake:
            raise fault
        return original_lstat(path)

    def broken_access(path: str, mode: int) -> bool:
        if str(path) == str(fake):
            raise fault
        return original_access(path, mode)

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("faulty Git executable reached child launch")

    monkeypatch.setattr(reference_audit.shutil, "which", lambda *_a, **_kw: str(fake))
    monkeypatch.setattr(reference_audit.sp, "run", forbidden)
    if operation == "lstat":
        monkeypatch.setattr(type(fake), "lstat", broken_lstat)
    else:
        monkeypatch.setattr(reference_audit.os, "access", broken_access)
    with pytest.raises(
        reference_audit.ReferenceAuditError, match="path inspection"
    ) as caught:
        reference_audit._require_git_commit("0" * 40)
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize(
    "failure_type",
    [OSError, ValueError, RuntimeError, TypeError, AttributeError, IndexError, OverflowError, Exception],
)
def test_audit_git_resolver_fault_is_typed(
    monkeypatch: pytest.MonkeyPatch, failure_type: type[Exception]
) -> None:
    """Host resolver exceptions retain a typed audit error and original cause."""

    def broken(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise failure_type("injected audit Git lookup failure")

    monkeypatch.setattr(reference_audit.shutil, "which", broken)
    with pytest.raises(
        reference_audit.ReferenceAuditError, match="Git lookup"
    ) as error:
        reference_audit._require_git_commit("0" * 40)
    assert type(error.value.__cause__) is failure_type


@pytest.mark.parametrize(
    "failure_type",
    [
        OSError,
        ValueError,
        RuntimeError,
        TypeError,
        AttributeError,
        IndexError,
        OverflowError,
        Exception,
        reference_audit.sp.SubprocessError,
    ],
)
def test_audit_git_runner_fault_is_typed(
    monkeypatch: pytest.MonkeyPatch, failure_type: type[Exception]
) -> None:
    """Unexpected host execution errors cannot leak through optional audit."""

    def broken(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise failure_type("injected audit Git process failure")

    monkeypatch.setattr(reference_audit.sp, "run", broken)
    with pytest.raises(
        reference_audit.ReferenceAuditError, match="object lookup"
    ) as error:
        reference_audit._require_git_commit("0" * 40)
    assert type(error.value.__cause__) is failure_type


def test_audit_git_runner_rejects_foreign_result_accessor_fault(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A returned process receipt cannot run a hostile property accessor."""

    class OpaqueFault(Exception):
        def __str__(self) -> str:
            raise AssertionError("foreign Git receipt formatter executed")

    fault = OpaqueFault("process response fault")

    class BadCompleted:
        @property
        def returncode(self) -> int:
            raise fault

    monkeypatch.setattr(reference_audit.sp, "run", lambda *_args, **_kwargs: BadCompleted())
    with pytest.raises(
        reference_audit.ReferenceAuditError,
        match="object lookup",
    ) as caught:
        reference_audit._require_git_commit("0" * 40)
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize(
    ("returncode", "stdout"),
    [
        (None, b"commit"),
        (False, b"commit"),
        ("0", b"commit"),
        (0, None),
        (0, "commit"),
        (0, object()),
    ],
)
def test_audit_git_rejects_noncanonical_process_receipt(
    monkeypatch: pytest.MonkeyPatch, returncode: object, stdout: object
) -> None:
    """Malformed child return fields cannot impersonate a Git commit receipt."""

    def fake_run(*args: object, **kwargs: object) -> object:
        del args, kwargs
        return type("FakeCompleted", (), {"returncode": returncode, "stdout": stdout})()

    monkeypatch.setattr(reference_audit.sp, "run", fake_run)
    with pytest.raises(
        reference_audit.ReferenceAuditError, match="local Git commit object"
    ):
        reference_audit._require_git_commit("0" * 40)


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
        reference_audit.audit(
            relative,
            options=reference_audit.AuditOptions(require_source_commit_object=True),
        )


def test_opt_in_git_object_check_admits_original_real_source_commit(
    live_pilot: tuple[Path, str],
) -> None:
    """An existing real source revision remains admissible after HEAD moves."""
    _, relative = live_pilot
    checked = reference_audit.audit(
        relative,
        options=reference_audit.AuditOptions(require_source_commit_object=True),
    )
    assert checked["source_commit_object_verified"]
    assert len(checked["recorded_source_commit"]) == GIT_HASH_WIDTH


def test_source_commit_object_check_requires_installed_git(
    live_pilot: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unavailable Git cannot impersonate successful source-object review."""
    _, relative = live_pilot
    monkeypatch.setattr(reference_audit.shutil, "which", lambda *_args, **_kwargs: None)
    with pytest.raises(
        reference_audit.ReferenceAuditError,
        match="requires local Git",
    ):
        reference_audit.audit(
            relative,
            options=reference_audit.AuditOptions(require_source_commit_object=True),
        )


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
    assert reference_audit.audit(relative)["host_c_failure_diagnostics_checked"] == 0


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


@pytest.mark.parametrize(
    "tamper",
    [
        "virtual-memory",
        "cpu",
        "wall",
        "bool-version",
        "extra-field",
        "no-field",
        "symlink",
        "invalid-json",
    ],
)
def test_host_child_resource_record_tampering_is_rejected(
    live_pilot: tuple[Path, str],
    tamper: str,
) -> None:
    """A declared Linux resource policy cannot silently change after a run."""
    directory, relative = live_pilot
    path = directory / "resource-controls.json"
    record = json.loads(path.read_text())
    changes: dict[str, tuple[str, object]] = {
        "virtual-memory": ("virtual_address_space_bytes", 123),
        "cpu": ("cpu_seconds", 20),
        "wall": ("wall_timeout_seconds", 25),
        "bool-version": ("schema_version", True),
        "extra-field": ("forged", True),
    }
    if tamper in changes:
        key, value = changes[tamper]
        record[key] = value
        _ = path.write_text(json.dumps(record), encoding="utf-8")
    elif tamper == MISSING_RECORD_FIELD:
        _ = record.pop("limiter")
        _ = path.write_text(json.dumps(record), encoding="utf-8")
    elif tamper == LINKED_RECORD:
        other = directory / "forged.json"
        _ = other.write_text(json.dumps(record), encoding="utf-8")
        path.unlink()
        path.symlink_to(other)
    else:
        _ = path.write_bytes(b"bad-json")
    with pytest.raises(reference_audit.ReferenceAuditError, match="host-C"):
        reference_audit.audit(relative)


@pytest.mark.parametrize("sidecar", ["artifacts", "nested", "failures", "policy"])
def test_host_c_sidecars_reject_duplicate_json_fields(
    live_pilot: tuple[Path, str],
    sidecar: str,
) -> None:
    """Repeated identical keys cannot mask ambiguous retained audit evidence."""
    directory, relative = live_pilot
    if sidecar in {"artifacts", "nested"}:
        path = directory / "artifacts.json"
        recorded = json.loads(path.read_text(encoding="utf-8"))
        key, entry = next(iter(recorded.items()))
        if sidecar == "artifacts":
            payload = (
                f"{{{json.dumps(key)}:{json.dumps(entry)}," + (json.dumps(recorded)[1:])
            )
        else:
            raw = path.read_text(encoding="utf-8")
            payload = raw.replace(
                '"path":', f'"path": {json.dumps(entry["path"])}, "path":', 1
            )
    elif sidecar == "failures":
        path = directory / "failures.json"
        payload = '{"schema_version":1,"failures":{},"failures":{}}'
    else:
        path = directory / "resource-controls.json"
        recorded = json.loads(path.read_text(encoding="utf-8"))
        payload = '{"schema_version":2,' + json.dumps(recorded)[1:]
    _ = path.write_text(payload, encoding="utf-8")
    with pytest.raises(reference_audit.ReferenceAuditError, match="duplicate"):
        reference_audit.audit(relative)


@pytest.mark.parametrize("payload", ["NaN", "Infinity", "-Infinity"])
def test_host_c_resource_receipt_rejects_nonfinite_json(
    live_pilot: tuple[Path, str],
    payload: str,
) -> None:
    """Non-standard JSON numbers never become admissible resource receipts."""
    directory, relative = live_pilot
    path = directory / "resource-controls.json"
    raw = path.read_text(encoding="utf-8")
    _ = path.write_text(raw.replace('"cpu_seconds": 16', f'"cpu_seconds": {payload}'))
    with pytest.raises(reference_audit.ReferenceAuditError, match="nonfinite"):
        reference_audit.audit(relative)


def test_host_c_sidecar_recursion_exhaustion_is_a_typed_audit_failure(
    live_pilot: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """JSON scanner nesting failures do not leak untyped audit exceptions."""
    _, relative = live_pilot

    def exhausted(_pairs: list[tuple[str, object]]) -> dict[str, object]:
        message = "injected scanner nesting limit"
        raise RecursionError(message)

    monkeypatch.setattr(reference_audit, "_unique_pairs", exhausted)
    with pytest.raises(reference_audit.ReferenceAuditError, match="not valid"):
        reference_audit.audit(relative)


def test_new_study_retains_versioned_resource_controls_receipt(
    live_pilot: tuple[Path, str],
) -> None:
    """A current native study records its declared per-child Linux policy."""
    directory, relative = live_pilot
    recorded = json.loads((directory / "resource-controls.json").read_text())
    assert recorded == host_c_oracle.resource_controls_record()
    report = reference_audit.audit(
        relative,
        options=reference_audit.AuditOptions(
            require_resource_controls_record=True,
        ),
    )
    assert report["resource_controls_record_checked"]
    assert report["resource_controls_record_version"] == RSS_CONTROL_SCHEMA
    assert report["host_c_binaries_checked"] == OBSERVED_PAIRS * 2


def test_missing_child_controls_are_explicitly_legacy_not_attested(
    live_pilot: tuple[Path, str],
) -> None:
    """An older study without this sidecar never gains a policy assertion."""
    directory, relative = live_pilot
    (directory / "resource-controls.json").unlink()
    with pytest.raises(
        reference_audit.ReferenceAuditError,
        match="peak-RSS study requires v2",
    ):
        reference_audit.audit(relative)
    old_path = directory / "study.json"
    old = json.loads(old_path.read_text(encoding="utf-8"))
    old["study"]["objectives"] = ["elapsed_ns", "artifact_bytes"]
    _ = old_path.write_text(json.dumps(old), encoding="utf-8")
    old_report = reference_audit.audit(relative)
    assert not old_report["resource_controls_record_checked"]
    with pytest.raises(
        reference_audit.ReferenceAuditError,
        match="resource-control record",
    ):
        reference_audit.audit(
            relative,
            options=reference_audit.AuditOptions(
                require_resource_controls_record=True,
            ),
        )


def test_cli_requires_child_resource_controls_when_requested(
    live_pilot: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Strict CLI policy checks recorded local child-control metadata."""
    directory, relative = live_pilot
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "reference-audit",
            relative,
            "--require-resource-controls-record",
        ],
    )
    assert reference_audit.main() == 0
    assert json.loads(capsys.readouterr().out)["resource_controls_record_checked"]
    (directory / "resource-controls.json").unlink()
    with pytest.raises(SystemExit, match="2"):
        reference_audit.main()
    result = capsys.readouterr()
    assert not result.out
    assert RESOURCE_RECORD_ERROR in result.err


def test_v1_resource_controls_still_admit_two_cost_reference_studies(
    live_pilot: tuple[Path, str],
) -> None:
    """The first Linux-controlled schema survives subsequent RSS extension."""
    directory, relative = live_pilot
    path = directory / "resource-controls.json"
    data = json.loads(path.read_text())
    _ = data.pop("rss_measurement")
    _ = data.pop("rss_tool")
    data["schema_version"] = 1
    _ = path.write_text(json.dumps(data), encoding="utf-8")
    study_path = directory / "study.json"
    study = json.loads(study_path.read_text())
    study["study"]["objectives"] = ["elapsed_ns", "artifact_bytes"]
    _ = study_path.write_text(json.dumps(study), encoding="utf-8")
    report = reference_audit.audit(relative)
    assert report["resource_controls_record_version"] == 1
    assert report["resource_controls_record_checked"]


def test_rss_claim_requires_v2_recorded_linux_measurement_policy(
    live_pilot: tuple[Path, str],
) -> None:
    """One cannot pretend old resource-control metadata measured peak RSS."""
    directory, relative = live_pilot
    path = directory / "resource-controls.json"
    data = json.loads(path.read_text())
    _ = data.pop("rss_tool")
    _ = data.pop("rss_measurement")
    data["schema_version"] = 1
    _ = path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(
        reference_audit.ReferenceAuditError,
        match="peak-RSS study requires v2",
    ):
        reference_audit.audit(relative)


@pytest.mark.parametrize(
    "fault_type",
    [
        analyze.ArenaError,
        evidence.EvidenceError,
        reference_study.ReferenceStudyError,
        host_c_oracle.HostOracleError,
        OSError,
        UnicodeError,
        IndexError,
        OverflowError,
        Exception,
    ],
)
def test_host_c_audit_never_formats_foreign_dependency_errors(
    monkeypatch: pytest.MonkeyPatch, fault_type: type[Exception]
) -> None:
    """Auditing dependency failures cannot execute untrusted formatters."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("foreign host-C audit dependency formatter executed")

    foreign = type("ForeignHostAuditFault", (fault_type,), {"__str__": unsafe_str})
    fault = foreign("unsafe dependency fault")

    def fail_admit(*_args: object, **_kwargs: object) -> None:
        raise fault

    monkeypatch.setattr(reference_audit, "_admit_data", fail_admit)
    with pytest.raises(
        reference_audit.ReferenceAuditError,
        match="host-C reference evidence audit failed",
    ) as caught:
        reference_audit.audit(".temp/arena-host-c-study-foreign/study.json")
    assert caught.value.__cause__ is fault
    assert "ForeignHostAuditFault" in str(caught.value)


@pytest.mark.parametrize(
    "fault_type", [reference_audit.ReferenceAuditError, report_output.ReportOutputError]
)
def test_host_c_audit_cli_rejects_foreign_formatter_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fault_type: type[Exception],
) -> None:
    """CLI typed failures remain exit status two without exception hook calls."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("foreign host-C CLI formatter executed")

    foreign = type("ForeignHostAuditCliFault", (fault_type,), {"__str__": unsafe_str})
    fault = foreign("unsafe CLI fault")

    def fail_audit(*_args: object, **_kwargs: object) -> None:
        raise fault

    monkeypatch.setattr(reference_audit, "audit", fail_audit)
    monkeypatch.setattr(
        reference_audit.sys,
        "argv",
        ["reference-audit", ".temp/arena-host-c-study-foreign/study.json"],
    )
    with pytest.raises(SystemExit) as caught:
        reference_audit.main()
    assert caught.value.code == 2
    output = capsys.readouterr()
    assert not output.out
    assert "ForeignHostAuditCliFault" in output.err


@pytest.mark.parametrize(
    "fault_type",
    [reference_audit.ReferenceAuditError, report_output.ReportOutputError],
)
def test_host_c_audit_cli_never_formats_native_error_foreign_argument(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fault_type: type[Exception],
) -> None:
    """An exact native error class cannot launder an unsafe argument."""

    class HostileArgument:
        def __str__(self) -> str:
            raise AssertionError("native audit error formatted caller argument")

    fault = fault_type(HostileArgument())

    def fail_audit(*_args: object, **_kwargs: object) -> None:
        raise fault

    monkeypatch.setattr(reference_audit, "audit", fail_audit)
    monkeypatch.setattr(
        reference_audit.sys,
        "argv",
        ["reference-audit", ".temp/arena-host-c-study-foreign/study.json"],
    )
    with pytest.raises(SystemExit) as caught:
        reference_audit.main()
    assert caught.value.code == 2
    output = capsys.readouterr()
    assert not output.out
    assert fault_type.__name__ in output.err


@pytest.mark.parametrize("fault_type", [OSError, ValueError, analyze.ArenaError])
def test_host_c_audit_never_formats_native_dependency_foreign_argument(
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """Audit admission must not stringify objects stored in error.args."""

    class HostileArgument:
        def __str__(self) -> str:
            raise AssertionError("native audit dependency formatted caller argument")

    fault = fault_type(HostileArgument())

    def fail_admit(*_args: object, **_kwargs: object) -> None:
        raise fault

    monkeypatch.setattr(reference_audit, "_admit_data", fail_admit)
    with pytest.raises(
        reference_audit.ReferenceAuditError,
        match="host-C reference evidence audit failed",
    ) as caught:
        reference_audit.audit(".temp/arena-host-c-study-foreign/study.json")
    assert caught.value.__cause__ is fault
    assert fault_type.__name__ in str(caught.value)


@pytest.mark.parametrize("fault_type", [IndexError, OverflowError, Exception])
def test_host_c_retained_json_parser_types_unexpected_faults(
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """A direct retained JSON reader must contain all ordinary parser faults."""

    class HostileFault(fault_type):
        def __str__(self) -> str:
            raise AssertionError("retained JSON dependency formatter executed")

    fault = HostileFault("opaque decoder fault")

    def fail_parse(*_args: object, **_kwargs: object) -> None:
        raise fault

    monkeypatch.setattr(reference_audit.evidence, "read_bounded_regular", lambda *_args, **_kwargs: b"{}")
    monkeypatch.setattr(reference_audit.json, "loads", fail_parse)
    with pytest.raises(reference_audit.ReferenceAuditError, match="not valid") as caught:
        reference_audit._read_json(
            ".temp/arena-host-c-study-test/failures.json",
            limit=reference_audit.MAX_FAILURES_BYTES,
            fingerprints={},
        )
    assert caught.value.__cause__ is fault


def test_host_c_audit_native_failure_retains_causal_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Safe exact project errors retain actionable diagnostics and causes."""
    fault = evidence.EvidenceError("raw evidence fingerprint changed")

    def fail_admit(*_args: object, **_kwargs: object) -> None:
        raise fault

    monkeypatch.setattr(reference_audit, "_admit_data", fail_admit)
    with pytest.raises(
        reference_audit.ReferenceAuditError, match="raw evidence fingerprint changed"
    ) as caught:
        reference_audit.audit(".temp/arena-host-c-study-native/study.json")
    assert caught.value.__cause__ is fault
