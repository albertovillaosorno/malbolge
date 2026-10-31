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
from typing import SupportsIndex
from typing import TYPE_CHECKING
from typing import cast

import pytest

from benchmarks.arena import analyze
from benchmarks.arena import budget_links
from benchmarks.arena import evidence
from benchmarks.arena import trial_runs

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterator
    from os import stat_result
    from typing import IO


class _UnanticipatedEvidenceError(Exception):
    """Ordinary dependency faults cannot require foreign string rendering."""

    def __str__(self) -> str:
        raise AssertionError("unexpected evidence exception formatted")


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


class _HostileSnapshotSink(list[evidence.EvidenceSnapshot]):
    """Foreign list append must not become a late evidence-approval hook."""

    def append(self, item: evidence.EvidenceSnapshot) -> None:
        del item
        message = "foreign snapshot append executed after admission"
        raise AssertionError(message)


class _HostileEvidenceSnapshot:
    """Snapshot attribute lookup must not execute a caller-owned property."""

    @property
    def bundle(self) -> object:
        message = "foreign snapshot property executed"
        raise AssertionError(message)


@pytest.mark.parametrize("invalid", [{}, (), object(), _HostileSnapshotSink()])
def test_snapshot_sink_requires_exact_native_list_before_work(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    invalid: object,
) -> None:
    """Malformed direct snapshot output must fail before any evidence reads."""

    def forbidden_root(root: Path) -> None:
        del root
        message = "invalid snapshot output reached file admission"
        raise AssertionError(message)

    monkeypatch.setattr(evidence, "_admit_root", forbidden_root)
    with pytest.raises(evidence.EvidenceError, match="snapshot"):
        evidence.validate_links(
            {}, tmp_path, _snapshot_out=cast("list[evidence.EvidenceSnapshot]", invalid)
        )


@pytest.mark.parametrize("invalid", [None, object(), _HostileEvidenceSnapshot()])
def test_snapshot_recheck_rejects_foreign_container_before_hooks(
    invalid: object,
) -> None:
    """A foreign recheck object cannot expose properties to the auditor."""
    with pytest.raises(evidence.EvidenceError, match="snapshot"):
        evidence.recheck_evidence_snapshot(cast("evidence.EvidenceSnapshot", invalid))


@pytest.mark.parametrize("field", ["context", "contents", "bundle"])
def test_snapshot_recheck_rejects_foreign_fields_before_file_work(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, field: str
) -> None:
    """A native wrapper alone cannot conceal unsupported nested containers."""
    context = evidence._EvidenceContext(
        tmp_path, {}, {}, set(), set(), evidence.EvidencePolicy()
    )
    snapshot = evidence.EvidenceSnapshot(context, None, None)
    object.__setattr__(snapshot, field, object())

    def forbidden_recheck(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        message = "invalid snapshot reached retained evidence recheck"
        raise AssertionError(message)

    monkeypatch.setattr(evidence, "_recheck_retained_links", forbidden_recheck)
    monkeypatch.setattr(evidence, "_recheck_bundle_files", forbidden_recheck)
    with pytest.raises(evidence.EvidenceError, match="snapshot"):
        evidence.recheck_evidence_snapshot(snapshot)


@pytest.mark.parametrize(
    "invalid_field",
    [
        "manifests-map",
        "manifests-entry",
        "manifest-key",
        "sample-map",
        "sample-key",
        "raw-map",
        "raw-key",
        "bundle-sources",
        "bundle-retained",
        "bundle-foreign-leaf",
        "policy",
    ],
)
def test_snapshot_recheck_preflights_nested_native_records(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    invalid_field: str,
) -> None:
    """Forged native wrappers fail before their nested maps are traversed."""
    context = evidence._EvidenceContext(
        tmp_path, {}, {}, set(), set(), evidence.EvidencePolicy()
    )
    snapshot = evidence.EvidenceSnapshot(context, None, None)
    if invalid_field == "manifests-map":
        context.manifests = cast("dict[str, evidence._ManifestLink]", object())
    elif invalid_field == "manifests-entry":
        context.manifests["forged.toml"] = cast("evidence._ManifestLink", object())
    elif invalid_field == "manifest-key":
        context.manifests[cast("str", 1)] = cast("evidence._ManifestLink", object())
    elif invalid_field == "sample-map":
        context.samples = cast("set[str]", object())
    elif invalid_field == "sample-key":
        context.samples.add(cast("str", 42))
    elif invalid_field == "raw-map":
        object.__setattr__(snapshot, "contents", object())
    elif invalid_field == "raw-key":
        object.__setattr__(snapshot, "contents", {1: "abcd"})
    elif invalid_field == "bundle-sources":
        object.__setattr__(
            snapshot,
            "bundle",
            evidence._BundleInspection(cast("dict[str, str]", object()), {}),
        )
    elif invalid_field == "bundle-retained":
        object.__setattr__(
            snapshot,
            "bundle",
            evidence._BundleInspection({}, cast("dict[str, str]", object())),
        )
    elif invalid_field == "bundle-foreign-leaf":
        object.__setattr__(
            snapshot, "bundle", evidence._BundleInspection({}, {"forged.bin": "abcd"})
        )
    else:
        context.policy = cast("evidence.EvidencePolicy", object())

    def forbidden_recheck(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        message = "invalid nested snapshot reached retained filesystem"
        raise AssertionError(message)

    monkeypatch.setattr(evidence, "_recheck_retained_links", forbidden_recheck)
    monkeypatch.setattr(evidence, "_recheck_bundle_files", forbidden_recheck)
    with pytest.raises(evidence.EvidenceError, match="snapshot"):
        evidence.recheck_evidence_snapshot(snapshot)


def test_native_snapshot_sink_retains_recheckable_evidence(tmp_path: Path) -> None:
    """The native list outparam returns a snapshot of real fixture links."""
    document = sample_study(tmp_path)
    snapshots: list[evidence.EvidenceSnapshot] = []
    _ = evidence.validate_links(document, tmp_path, _snapshot_out=snapshots)
    assert len(snapshots) == 1
    evidence.recheck_evidence_snapshot(snapshots[0])


def test_empty_native_evidence_snapshot_recheck_succeeds(tmp_path: Path) -> None:
    """A correctly shaped no-link snapshot remains a valid empty recheck."""
    context = evidence._EvidenceContext(
        tmp_path, {}, {}, set(), set(), evidence.EvidencePolicy()
    )
    evidence.recheck_evidence_snapshot(evidence.EvidenceSnapshot(context, None, None))


def test_links_are_checked_without_certification(tmp_path: Path) -> None:
    """Existing manifest parser cross-checks exactly two distinct run links."""
    document = sample_study(tmp_path)
    result = _admit(document, tmp_path)
    assert result["manifest_links_checked"] == ALGORITHM_COUNT
    assert result["raw_sample_paths_checked"] == ALGORITHM_COUNT
    assert result["reported_trials_checked"] == ALGORITHM_COUNT
    assert DIGEST_SCOPE in result["scope"]


@pytest.mark.parametrize("tamper", ["rewrite", "missing", "symlink"])
def test_run_manifest_rechecked_after_late_report_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tamper: str,
) -> None:
    """A reported run identity may not disappear or change after admission."""
    doc = sample_study(tmp_path)
    admitted = analyze.parse_document(json.dumps(doc))
    original_report = evidence._report_links

    def modify_after_report(*args: Any, **kwargs: Any) -> dict[str, Any]:
        report = original_report(*args, **kwargs)
        path = tmp_path / doc["observations"][0]["experiment_manifest"]
        if tamper == "rewrite":
            source = path.read_text(encoding="utf-8")
            assert 'id = "baseline"' in source
            _ = path.write_text(
                source.replace('id = "baseline"', 'id = "caseline"', 1),
                encoding="utf-8",
            )
        else:
            path.unlink()
            if tamper == "symlink":
                path.symlink_to(tmp_path / doc["observations"][1]["experiment_manifest"])
        return report

    monkeypatch.setattr(evidence, "_report_links", modify_after_report)
    with pytest.raises(evidence.EvidenceError, match=r"manifest|evidence|symlink"):
        evidence.validate_links(admitted, tmp_path)


def test_evidence_cli_rejects_late_manifest_drift_without_stdout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """No partial capacity report is published after a late manifest rewrite."""
    doc = sample_study(tmp_path)
    source = tmp_path / "study.json"
    _ = source.write_text(json.dumps(doc), encoding="utf-8")
    original_report = evidence._report_links

    def corrupt_after_report(*args: Any, **kwargs: Any) -> dict[str, Any]:
        report = original_report(*args, **kwargs)
        path = tmp_path / doc["observations"][0]["experiment_manifest"]
        contents = path.read_text(encoding="utf-8")
        _ = path.write_text(
            contents.replace('id = "baseline"', 'id = "caseline"', 1),
            encoding="utf-8",
        )
        return report

    monkeypatch.setattr(evidence, "_report_links", corrupt_after_report)
    monkeypatch.setattr(
        sys, "argv", ["arena-evidence", str(source), "--root", str(tmp_path)]
    )
    with pytest.raises(SystemExit, match="2"):
        evidence.main()
    failure = capsys.readouterr()
    assert not failure.out
    assert "run manifest changed" in failure.err


def test_evidence_cli_rechecks_manifest_mutated_after_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Post-preflight report analysis cannot certify rewritten manifest bytes."""
    doc = sample_study(tmp_path)
    source = tmp_path / "study.json"
    _ = source.write_text(json.dumps(doc), encoding="utf-8")
    original_analyze = analyze.analyze

    def rewrite_during_analysis(*args: Any, **kwargs: Any) -> dict[str, Any]:
        report = original_analyze(*args, **kwargs)
        path = tmp_path / doc["observations"][0]["experiment_manifest"]
        original = path.read_text(encoding="utf-8")
        assert 'id = "baseline"' in original
        _ = path.write_text(
            original.replace('id = "baseline"', 'id = "caseline"', 1),
            encoding="utf-8",
        )
        return report

    monkeypatch.setattr(analyze, "analyze", rewrite_during_analysis)
    monkeypatch.setattr(
        sys, "argv", ["arena-evidence", str(source), "--root", str(tmp_path)]
    )
    with pytest.raises(SystemExit, match="2"):
        evidence.main()
    failure = capsys.readouterr()
    assert not failure.out
    assert "run manifest changed" in failure.err


@pytest.mark.parametrize("tamper", ["missing", "symlink"])
def test_default_raw_presence_rechecked_after_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tamper: str,
) -> None:
    """Default evidence still requires retained raw paths at report return."""
    doc = sample_study(tmp_path)
    admitted = analyze.parse_document(json.dumps(doc))
    original_report = evidence._report_links

    def remove_after_report(*args: Any, **kwargs: Any) -> dict[str, Any]:
        report = original_report(*args, **kwargs)
        path = tmp_path / doc["observations"][0]["raw_sample"]
        path.unlink()
        if tamper == "symlink":
            path.symlink_to(tmp_path / doc["observations"][1]["raw_sample"])
        return report

    monkeypatch.setattr(evidence, "_report_links", remove_after_report)
    with pytest.raises(evidence.EvidenceError, match=r"evidence|symlink"):
        evidence.validate_links(admitted, tmp_path)


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


@pytest.mark.parametrize(
    ("violation", "diagnostic"),
    [
        ("schema", "unsupported arena schema version"),
        ("duplicate", "duplicate algorithm/case/trial"),
        ("verdict", "inconsistent independent verifier evidence"),
        ("budget", "verified elapsed time exceeds study budget"),
        ("root_extra", "root: expected fields"),
        ("root_foreign", "root: expected fields"),
    ],
)
def test_direct_evidence_requires_admitted_arena_document_before_file_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    violation: str,
    diagnostic: str,
) -> None:
    """A direct link check cannot certify malformed or duplicated trial data."""

    def forbidden(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        pytest.fail("unadmitted source reached retained evidence files")

    monkeypatch.setattr(evidence, "_admit_observation", forbidden)
    document = sample_study(tmp_path)
    row = document["observations"][0]
    if violation == "schema":
        document["schema_version"] = 2
    elif violation == "duplicate":
        document["observations"].append(row.copy())
    elif violation == "verdict":
        row["verifier_verdict"] = analyze.NOT_RUN
    elif violation == "budget":
        row["metrics"]["elapsed_ns"] = document["study"]["budget"]["time_ns"] + 1
    elif violation == "root_extra":
        document["unregistered"] = "untrusted"
    else:
        document = cast("dict[str, Any]", [])
    with pytest.raises(evidence.EvidenceError, match=diagnostic):
        evidence.validate_links(document, tmp_path)


@pytest.mark.parametrize(
    "flag",
    [
        "require_raw_rows",
        "require_trial_run_identity",
        "require_budget_agreement",
        "require_matched_accelerator",
        "require_host_c_challenge_oracle",
    ],
)
@pytest.mark.parametrize("invalid", ["false", 0, None, object()])
def test_direct_evidence_policy_rejects_nonboolean_flags_before_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    flag: str,
    invalid: object,
) -> None:
    """Direct evidence replay cannot be switched on by truthy foreign flags."""

    def forbidden(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        pytest.fail("invalid evidence policy reached evidence admission")

    monkeypatch.setattr(evidence, "_admit_observation", forbidden)
    options: dict[str, Any] = {flag: invalid}
    policy = evidence.EvidencePolicy(**options)
    with pytest.raises(evidence.EvidenceError, match="exact booleans"):
        evidence.validate_links(
            {"study": {}, "observations": [{}]}, tmp_path, policy=policy
        )


@pytest.mark.parametrize("foreign", [None, {}, object()])
def test_direct_evidence_rejects_foreign_policy_before_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    foreign: object,
) -> None:
    """A non-policy object cannot bypass admission through dynamic attributes."""

    def forbidden(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        pytest.fail("foreign policy reached evidence admission")

    monkeypatch.setattr(evidence, "_admit_observation", forbidden)
    with pytest.raises(evidence.EvidenceError, match="exact EvidencePolicy"):
        evidence.validate_links(
            {"study": {}, "observations": [{}]},
            tmp_path,
            policy=cast("evidence.EvidencePolicy", foreign),
        )


@pytest.mark.parametrize("foreign", [1, False, b"bundles", [], "", "../escape"])
def test_direct_evidence_rejects_invalid_challenge_root_before_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    foreign: object,
) -> None:
    """A challenge-root policy must be canonical before any manifest lookup."""

    def forbidden(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        pytest.fail("invalid challenge root reached evidence admission")

    monkeypatch.setattr(evidence, "_admit_observation", forbidden)
    policy = evidence.EvidencePolicy(challenge_root=cast("str", foreign))
    with pytest.raises(evidence.EvidenceError, match="challenge root"):
        evidence.validate_links(
            {"study": {}, "observations": [{}]}, tmp_path, policy=policy
        )


class _ForgedEvidenceRoot(type(Path())):
    """Caller-owned path can substitute its resolution target before I/O."""

    __slots__ = ()

    def resolve(self, strict: bool = False) -> Path:
        """Never permit this forged accessor to be called.

        Returns:
            No resolved path; the expected type gate must reject first.

        """
        del strict
        message = "foreign root resolved before evidence type admission"
        raise AssertionError(message)


@pytest.mark.parametrize("reader", ["regular", "bounded", "links"])
def test_direct_evidence_rejects_foreign_root_before_resolution(
    tmp_path: Path,
    reader: str,
) -> None:
    """A forged path subclass cannot redirect evidence to a different root."""
    root = _ForgedEvidenceRoot(str(tmp_path))
    with pytest.raises(evidence.EvidenceError, match="native Path"):
        if reader == "regular":
            evidence.regular_path(root, "raw.csv")
        elif reader == "bounded":
            evidence.read_bounded_regular(root, "raw.csv", limit=100)
        else:
            evidence.validate_links({"study": {}, "observations": [{}]}, root)


def test_direct_link_api_rejects_parent_traversal(tmp_path: Path) -> None:
    """Even a caller bypassing schema admission cannot read a parent path."""
    document = sample_study(tmp_path)
    document["observations"][0]["experiment_manifest"] = "../escape.toml"
    with pytest.raises(evidence.EvidenceError, match="canonical repository-relative"):
        evidence.validate_links(document, tmp_path)


class _ForgedParentSegment(str):  # ruff: ignore[subclass-builtin]
    """Path traversal component whose equality check lies to the guard."""

    __slots__ = ()

    def __hash__(self) -> int:
        """Ensure membership checks skip the real dot-dot string.

        Returns:
            An intentionally incorrect hash for the underlying value.

        """
        return hash("..") + 1

    def __eq__(self, other: object) -> bool:
        """Deny equality even when the underlying path is a parent.

        Returns:
            False, independent of the actual string value.

        """
        del other
        return False


class _ForgedRelative(str):  # ruff: ignore[subclass-builtin]
    """Present safe lexical text while returning escaping path components."""

    __slots__ = ()

    def split(
        self, sep: str | None = None, maxsplit: SupportsIndex = -1
    ) -> list[str]:
        """Return a fake traversal segment despite a benign source string.

        Returns:
            Deliberately inconsistent parts of the purported relative path.

        """
        del self, sep, maxsplit
        return [_ForgedParentSegment(".."), "outside.txt"]


class _ForeignLimit(int):
    """A caller-owned integer subclass cannot supply evidence byte policy."""


@pytest.mark.parametrize(
    "invalid_limit",
    [None, False, True, 0, -1, float("nan"), float("inf"), 1.5, "8", _ForeignLimit(8)],
)
def test_direct_bounded_evidence_reader_rejects_invalid_limits_before_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_limit: object,
) -> None:
    """A noninteger or nonpositive cap cannot silently disable byte bounds."""
    _ = (tmp_path / "raw.csv").write_bytes(b"real evidence exceeds a one-byte limit")

    def forbidden_segments(*args: object, **kwargs: object) -> list[str]:
        _ = (args, kwargs)
        message = "malformed byte limit reached filesystem admission"
        raise AssertionError(message)

    monkeypatch.setattr(evidence, "_segments", forbidden_segments)
    with pytest.raises(evidence.EvidenceError, match="byte limit"):
        evidence.read_bounded_regular(
            tmp_path, "raw.csv", limit=cast("int", invalid_limit)
        )


@pytest.mark.parametrize(
    "invalid_limit", [False, True, 0, -1, float("nan"), float("inf"), 1.5, "8", _ForeignLimit(8)]
)
def test_direct_regular_path_rejects_invalid_optional_limits(
    tmp_path: Path,
    invalid_limit: object,
) -> None:
    """Optional path budget is either absent or an exact positive integer."""
    _ = (tmp_path / "raw.csv").write_bytes(b"real evidence exceeds a one-byte limit")
    with pytest.raises(evidence.EvidenceError, match="byte limit"):
        evidence.regular_path(
            tmp_path, "raw.csv", limit=cast("int", invalid_limit)
        )
    assert evidence.regular_path(tmp_path, "raw.csv") == tmp_path / "raw.csv"


@pytest.mark.parametrize("read_bytes", [False, True], ids=["path", "bytes"])
def test_direct_evidence_path_admission_rejects_forged_str_parts(
    tmp_path: Path,
    *,
    read_bytes: bool,
) -> None:
    """No direct caller can substitute escaped path parts for lexical text."""
    admitted_root = tmp_path / "admitted"
    admitted_root.mkdir()
    _ = (tmp_path / "outside.txt").write_bytes(b"not-in-root")
    relative = _ForgedRelative("safe.txt")
    admit = (
        evidence.read_bounded_regular if read_bytes else evidence.regular_path
    )
    with pytest.raises(evidence.EvidenceError, match="canonical relative"):
        admit(admitted_root, relative, limit=100)


@pytest.mark.parametrize(
    ("parser", "text", "expected"),
    [
        (
            budget_links.parse_run_budgets,
            "[budget]\nseconds = " + "1" * 4500 + "\nmemory_mib = 128\n",
            (budget_links.BudgetLinkError, ValueError),
        ),
        (
            trial_runs.parse_trial_run,
            "[arena_trial]\nschema_version = 1\ntrial = "
            + "1" * 4500
            + '\nraw_sha256 = "'
            + "a" * 64
            + '"\n',
            (trial_runs.TrialRunError, ValueError),
        ),
        (
            budget_links.parse_run_budgets,
            "[budget]\nseconds = " + "[" * 1000 + "1" + "]" * 1000,
            (budget_links.BudgetLinkError, RecursionError),
        ),
        (
            trial_runs.parse_trial_run,
            "[arena_trial]\ntrial = " + "[" * 1000 + "1" + "]" * 1000,
            (trial_runs.TrialRunError, RecursionError),
        ),
    ],
    ids=["budget-integer", "trial-integer", "budget-depth", "trial-depth"],
)
def test_optional_run_extension_parser_contains_toml_capacity_failure(
    parser: Callable[[str], object],
    text: str,
    expected: tuple[type[ValueError], type[Exception]],
) -> None:
    """Direct run extensions type TOML parser resource failures."""
    with pytest.raises(expected[0], match=r"invalid .* TOML") as error:
        parser(text)
    assert isinstance(error.value.__cause__, expected[1])


BUDGET_MANIFEST = "[budget]\nseconds = 1\nmemory_mib = 128\n"
TRIAL_MANIFEST = (
    '[arena_trial]\nschema_version = 1\ntrial = 0\nraw_sha256 = "'
    + "a" * analyze.SHA256_HEX_LENGTH
    + '"\n'
)


class _ForgedManifestText(str):  # ruff: ignore[subclass-builtin]
    """Malformed wire text that replaces itself with a different TOML input."""

    __slots__ = ()
    replacement = ""

    def replace(self, old: str, new: str, count: SupportsIndex = -1) -> str:
        """Supply a different document during tomllib normalization.

        Returns:
            The forged text, unrelated to the underlying source string.

        """
        del old, new, count
        return self.replacement


@pytest.mark.parametrize(
    ("parser", "valid", "error_type"),
    [
        (
            budget_links.parse_run_budgets,
            BUDGET_MANIFEST,
            budget_links.BudgetLinkError,
        ),
        (trial_runs.parse_trial_run, TRIAL_MANIFEST, trial_runs.TrialRunError),
    ],
    ids=["budget", "trial"],
)
def test_direct_run_extension_parser_admits_only_bounded_exact_utf8_text(
    parser: Callable[[str], object],
    valid: str,
    error_type: type[ValueError],
) -> None:
    """Direct manifest parsers cannot bypass the one-MiB wire-file boundary."""
    padding = "#" + "x" * (evidence.MAX_MANIFEST_BYTES - len(valid) - 1)
    assert parser(valid + padding)
    with pytest.raises(error_type, match="byte limit"):
        parser(valid + padding + "x")
    with pytest.raises(error_type, match="byte limit"):
        parser(valid + "#" + "é" * (evidence.MAX_MANIFEST_BYTES // 2))
    with pytest.raises(error_type, match="UTF-8"):
        parser(valid + "#\ud800")

    _ForgedManifestText.replacement = valid
    with pytest.raises(error_type, match="exact str"):
        parser(_ForgedManifestText("invalid = {"))
    for foreign in (None, b"[budget]", bytearray(b"[budget]"), 1):
        with pytest.raises(error_type, match="exact str"):
            parser(cast("str", foreign))


@pytest.mark.parametrize(
    ("parser", "valid", "error_type"),
    [
        (
            budget_links.parse_run_budgets,
            BUDGET_MANIFEST,
            budget_links.BudgetLinkError,
        ),
        (trial_runs.parse_trial_run, TRIAL_MANIFEST, trial_runs.TrialRunError),
    ],
    ids=["budget", "trial"],
)
@pytest.mark.parametrize(
    "fault_type",
    [OSError, RuntimeError, TypeError, AttributeError, IndexError, OverflowError],
)
def test_direct_run_extensions_type_toml_host_failures(
    monkeypatch: pytest.MonkeyPatch,
    parser: Callable[[str], object],
    valid: str,
    error_type: type[ValueError],
    fault_type: type[Exception],
) -> None:
    """Host parser failures become typed extension errors with original cause."""
    fault = fault_type("injected TOML parser failure")

    def fail_parse(_value: str) -> None:
        raise fault

    monkeypatch.setattr(budget_links.tomllib, "loads", fail_parse)
    with pytest.raises(error_type, match=r"invalid .* TOML") as caught:
        parser(valid)
    assert caught.value.__cause__ is fault


class _UnexpectedHostileTomlError(Exception):
    """An unanticipated parser error must not control error formatting."""

    def __str__(self) -> str:
        raise AssertionError("unexpected foreign TOML formatter was invoked")


@pytest.mark.parametrize(
    ("parser", "valid", "error_type"),
    [
        (budget_links.parse_run_budgets, BUDGET_MANIFEST, budget_links.BudgetLinkError),
        (trial_runs.parse_trial_run, TRIAL_MANIFEST, trial_runs.TrialRunError),
    ],
    ids=["budget", "trial"],
)
def test_direct_run_extensions_type_unexpected_foreign_parser_fault(
    monkeypatch: pytest.MonkeyPatch,
    parser: Callable[[str], object],
    valid: str,
    error_type: type[ValueError],
) -> None:
    """Unexpected ordinary dependency faults stay typed with the exact cause."""
    fault = _UnexpectedHostileTomlError("opaque parser failure")

    def fail_parse(_value: str) -> None:
        raise fault

    monkeypatch.setattr(budget_links.tomllib, "loads", fail_parse)
    with pytest.raises(error_type, match=r"invalid .* TOML") as caught:
        parser(valid)
    assert caught.value.__cause__ is fault


class _HostileTomlError(ValueError):
    """An injected parser failure with an unsafe diagnostic hook."""

    def __str__(self) -> str:
        message = "foreign TOML exception formatting executed"
        raise AssertionError(message)


@pytest.mark.parametrize(
    ("parser", "valid", "error_type"),
    [
        (
            budget_links.parse_run_budgets,
            BUDGET_MANIFEST,
            budget_links.BudgetLinkError,
        ),
        (trial_runs.parse_trial_run, TRIAL_MANIFEST, trial_runs.TrialRunError),
    ],
    ids=["budget", "trial"],
)
def test_direct_run_extensions_never_format_toml_parser_faults(
    monkeypatch: pytest.MonkeyPatch,
    parser: Callable[[str], object],
    valid: str,
    error_type: type[ValueError],
) -> None:
    """A parser diagnostic hook cannot replace the typed rejection."""
    fault = _HostileTomlError("injected TOML parser failure")

    def fail_parse(_value: str) -> None:
        raise fault

    monkeypatch.setattr(budget_links.tomllib, "loads", fail_parse)
    with pytest.raises(error_type, match=r"invalid .* TOML") as caught:
        parser(valid)
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize(
    ("parser", "valid", "error_type"),
    [
        (
            budget_links.parse_run_budgets,
            BUDGET_MANIFEST,
            budget_links.BudgetLinkError,
        ),
        (trial_runs.parse_trial_run, TRIAL_MANIFEST, trial_runs.TrialRunError),
    ],
    ids=["budget", "trial"],
)
@pytest.mark.parametrize("bad_root", [None, [], 42])
def test_direct_run_extensions_reject_malformed_toml_root(
    monkeypatch: pytest.MonkeyPatch,
    parser: Callable[[str], object],
    valid: str,
    error_type: type[ValueError],
    bad_root: object,
) -> None:
    """A malformed dependency result must not escape through .get access."""
    monkeypatch.setattr(budget_links.tomllib, "loads", lambda _value: bad_root)
    with pytest.raises(error_type, match=r"invalid .* TOML root"):
        parser(valid)


class _HostileTomlTable(dict[str, object]):
    """A foreign mapping cannot supply parser-created manifest fields."""

    def get(self, _key: str, _default: object = None) -> object:
        message = "foreign TOML mapping access executed"
        raise AssertionError(message)


@pytest.mark.parametrize(
    ("parser", "valid", "error_type", "table_name", "diagnostic"),
    [
        (
            budget_links.parse_run_budgets,
            BUDGET_MANIFEST,
            budget_links.BudgetLinkError,
            "budget",
            "budget table is missing",
        ),
        (
            trial_runs.parse_trial_run,
            TRIAL_MANIFEST,
            trial_runs.TrialRunError,
            "arena_trial",
            "arena_trial requires exact",
        ),
    ],
    ids=["budget", "trial"],
)
@pytest.mark.parametrize("foreign_part", ["root", "table"])
def test_direct_run_extensions_reject_foreign_parser_mappings(
    monkeypatch: pytest.MonkeyPatch,
    parser: Callable[[str], object],
    valid: str,
    error_type: type[ValueError],
    table_name: str,
    diagnostic: str,
    foreign_part: str,
) -> None:
    """Only native TOML maps can enter run identity and budget admission."""
    table = _HostileTomlTable()
    returned: object = (
        _HostileTomlTable({table_name: {}})
        if foreign_part == "root"
        else {table_name: table}
    )
    monkeypatch.setattr(budget_links.tomllib, "loads", lambda _value: returned)
    expected = "invalid .* TOML root" if foreign_part == "root" else diagnostic
    with pytest.raises(error_type, match=expected):
        parser(valid)


class _ForgedTomlDigest(str):  # ruff: ignore[subclass-builtin]
    """Foreign digest text can fake length, characters, and equality."""

    def __len__(self) -> int:
        return analyze.SHA256_HEX_LENGTH

    def __iter__(self) -> Iterator[str]:
        return iter("a" * analyze.SHA256_HEX_LENGTH)

    def __eq__(self, _other: object) -> bool:
        return True

    def __ne__(self, _other: object) -> bool:
        return False

    __hash__ = str.__hash__


def test_trial_run_digest_rejects_foreign_text_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged reported raw hash cannot approve itself via string hooks."""
    document = {
        "arena_trial": {
            "schema_version": 1,
            "trial": 0,
            "raw_sha256": _ForgedTomlDigest("not-a-real-sha256"),
        }
    }
    monkeypatch.setattr(trial_runs.tomllib, "loads", lambda _value: document)
    with pytest.raises(trial_runs.TrialRunError, match="lowercase SHA-256"):
        trial_runs.parse_trial_run(TRIAL_MANIFEST)


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


@pytest.mark.skipif(
    sys.platform != "linux",
    reason="Linux opened-descriptor path provenance is required",
)
def test_bounded_reader_rejects_transient_symlink_parent_to_equal_inode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hard-link equality must not conceal a symlink hop outside the root."""
    root = tmp_path / "root"
    root.mkdir()
    doc = sample_study(root)
    relative = doc["observations"][0]["raw_sample"]
    path = root / relative
    directory = path.parent
    parked = root / "parked-evidence"
    outside = tmp_path / "outside-root"
    outside.mkdir()
    _ = evidence.os.link(path, outside / path.name)
    original_open = evidence.os.open
    swapped = False

    def swap_parent_during_open(target: Path, flags: int) -> int:
        nonlocal swapped
        if target != path:
            return original_open(target, flags)
        swapped = True
        directory.rename(parked)
        directory.symlink_to(outside, target_is_directory=True)
        try:
            return original_open(target, flags)
        finally:
            directory.unlink()
            parked.rename(directory)

    monkeypatch.setattr(evidence.os, "open", swap_parent_during_open)
    with pytest.raises(evidence.EvidenceError, match="opened path changed"):
        evidence.read_bounded_regular(root, relative, limit=1024)
    assert swapped
    assert path.read_bytes() == (outside / path.name).read_bytes()


@pytest.mark.skipif(
    sys.platform != "linux",
    reason="Linux opened-descriptor path provenance is required",
)
def test_bounded_reader_fails_closed_when_fd_path_provenance_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unavailable procfs path evidence rejects and closes the raw descriptor."""
    doc = sample_study(tmp_path)
    relative = doc["observations"][0]["raw_sample"]
    actual_open = evidence.os.open
    actual_readlink = evidence.os.readlink
    opened: list[int] = []

    def capture_open(target: Path, flags: int) -> int:
        descriptor = actual_open(target, flags)
        opened.append(descriptor)
        return descriptor

    def reject_proc_path(target: str) -> str:
        if target.startswith("/proc/self/fd/"):
            raise OSError("simulated missing procfs")
        return actual_readlink(target)

    with monkeypatch.context() as context:
        context.setattr(evidence.os, "open", capture_open)
        context.setattr(evidence.os, "readlink", reject_proc_path)
        with pytest.raises(evidence.EvidenceError, match="stream could not open"):
            evidence.read_bounded_regular(tmp_path, relative, limit=1024)
    assert len(opened) == 1
    with pytest.raises(OSError):
        _ = evidence.os.fstat(opened[0])


@pytest.mark.parametrize(
    "fault",
    [
        OSError,
        ValueError,
        RuntimeError,
        TypeError,
        AttributeError,
        IndexError,
        _UnanticipatedEvidenceError,
    ],
)
def test_evidence_stream_constructor_failure_closes_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """Failed ownership transfer leaves no raw descriptor or untyped error."""
    document = sample_study(tmp_path)
    relative = document["observations"][0]["raw_sample"]
    opened: list[int] = []
    actual_open = evidence.os.open

    def capture_open(target: Path, flags: int) -> int:
        descriptor = actual_open(target, flags)
        opened.append(descriptor)
        return descriptor

    def reject_stream(*args: object, **kwargs: object) -> IO[bytes]:
        del args, kwargs
        raise fault("injected evidence stream constructor failure")

    with monkeypatch.context() as context:
        context.setattr(evidence.os, "open", capture_open)
        context.setattr(evidence.os, "fdopen", reject_stream)
        with pytest.raises(
            evidence.EvidenceError, match="stream could not open"
        ) as failure:
            evidence.read_bounded_regular(tmp_path, relative, limit=1024)
    assert len(opened) == 1
    with pytest.raises(OSError):
        _ = evidence.os.fstat(opened[0])
    assert type(failure.value.__cause__) is fault


def test_evidence_stream_constructor_cleanup_cannot_mask_primary_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even an erroneous close records the primary constructor failure."""
    document = sample_study(tmp_path)
    relative = document["observations"][0]["raw_sample"]
    actual_close = evidence.os.close
    closed: list[int] = []

    def reject_stream(*args: object, **kwargs: object) -> IO[bytes]:
        del args, kwargs
        raise RuntimeError("primary evidence fdopen failure")

    def fail_after_closing(descriptor: int) -> None:
        actual_close(descriptor)
        closed.append(descriptor)
        raise ValueError("secondary evidence close failure")

    with monkeypatch.context() as context:
        context.setattr(evidence.os, "fdopen", reject_stream)
        context.setattr(evidence.os, "close", fail_after_closing)
        with pytest.raises(
            evidence.EvidenceError, match="stream could not open"
        ) as failure:
            evidence.read_bounded_regular(tmp_path, relative, limit=1024)
    assert len(closed) == 1
    with pytest.raises(OSError):
        _ = evidence.os.fstat(closed[0])
    primary = failure.value.__cause__
    assert isinstance(primary, RuntimeError)
    assert str(primary) == "primary evidence fdopen failure"
    assert primary.__notes__ == [
        "evidence descriptor cleanup also failed: secondary evidence close failure"
    ]


def _foreign_primary_with_hostile_note(fault_type: type[Exception]) -> Exception:
    """Create a caught host fault that forbids its own add_note override."""

    def reject_note(self: BaseException, note: str) -> None:
        del self, note
        raise AssertionError("foreign primary evidence note hook executed")

    foreign = type("ForeignEvidenceHostError", (fault_type,), {"add_note": reject_note})
    return foreign("primary evidence admission failure")


@pytest.mark.parametrize("fault_type", [OSError, RuntimeError, ValueError])
def test_evidence_descriptor_cleanup_bypasses_foreign_primary_note_hook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """Failed fdopen and close preserve the primary without foreign hooks."""
    document = sample_study(tmp_path)
    relative = document["observations"][0]["raw_sample"]
    primary = _foreign_primary_with_hostile_note(fault_type)
    original_close = evidence.os.close

    def reject_stream(*args: object, **kwargs: object) -> IO[bytes]:
        del args, kwargs
        raise primary

    def fail_close(descriptor: int) -> None:
        original_close(descriptor)
        raise OSError("secondary descriptor close failure")

    with monkeypatch.context() as patch:
        patch.setattr(evidence.os, "fdopen", reject_stream)
        patch.setattr(evidence.os, "close", fail_close)
        with pytest.raises(
            evidence.EvidenceError, match="stream could not open"
        ) as caught:
            evidence.read_bounded_regular(tmp_path, relative, limit=1024)

    assert caught.value.__cause__ is primary
    assert any("descriptor cleanup" in note for note in primary.__notes__)


class _UnformattableCleanupError(ValueError):
    def __str__(self) -> str:
        raise AssertionError("cleanup exception formatting is untrusted")


class _UnformattableCleanupArgument:
    def __str__(self) -> str:
        raise AssertionError("cleanup exception argument formatting is untrusted")


@pytest.mark.parametrize(
    "cleanup_error",
    [
        _UnformattableCleanupError("foreign cleanup"),
        ValueError(_UnformattableCleanupArgument()),
    ],
    ids=["foreign-exception-subclass", "native-error-with-foreign-argument"],
)
def test_evidence_descriptor_cleanup_never_formats_foreign_exceptions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cleanup_error: ValueError,
) -> None:
    """Hostile cleanup diagnostics must not replace descriptor open failures."""
    document = sample_study(tmp_path)
    relative = document["observations"][0]["raw_sample"]
    actual_close = evidence.os.close

    def reject_stream(*args: object, **kwargs: object) -> IO[bytes]:
        del args, kwargs
        raise RuntimeError("original evidence stream failure")

    def fail_close(descriptor: int) -> None:
        actual_close(descriptor)
        raise cleanup_error

    with monkeypatch.context() as context:
        context.setattr(evidence.os, "fdopen", reject_stream)
        context.setattr(evidence.os, "close", fail_close)
        with pytest.raises(
            evidence.EvidenceError, match="stream could not open"
        ) as failure:
            evidence.read_bounded_regular(tmp_path, relative, limit=1024)
    primary = failure.value.__cause__
    assert type(primary) is RuntimeError
    assert primary.args == ("original evidence stream failure",)
    assert primary.__notes__ == ["evidence descriptor cleanup also failed"]


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
    [
        OSError,
        ValueError,
        RuntimeError,
        TypeError,
        AttributeError,
        IndexError,
        _UnanticipatedEvidenceError,
    ],
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


@pytest.mark.parametrize(
    "fault",
    [
        OSError,
        ValueError,
        RuntimeError,
        TypeError,
        AttributeError,
        IndexError,
        _UnanticipatedEvidenceError,
    ],
)
def test_evidence_stream_close_failure_is_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """Close-only defects must be rejected through evidence admission."""
    document = sample_study(tmp_path)
    relative = document["observations"][0]["raw_sample"]
    original_open = evidence._open_evidence

    @contextmanager
    def fail_close(path: Path) -> Iterator[IO[bytes]]:
        with original_open(path) as stream:
            yield stream
        raise fault("injected evidence close failure")

    monkeypatch.setattr(evidence, "_open_evidence", fail_close)
    with pytest.raises(evidence.EvidenceError, match="stream access failed") as error:
        evidence.read_bounded_regular(tmp_path, relative, limit=1024)
    assert type(error.value.__cause__) is fault


def test_evidence_stream_close_error_cannot_hide_primary_read_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Read rejection remains the primary cause when cleanup also fails."""
    document = sample_study(tmp_path)
    relative = document["observations"][0]["raw_sample"]
    original_open = evidence._open_evidence

    @contextmanager
    def fail_both(path: Path) -> Iterator[_FaultEvidenceReader]:
        try:
            with original_open(path) as stream:
                yield _FaultEvidenceReader(stream, RuntimeError)
        finally:
            raise ValueError("secondary evidence stream close failure")

    monkeypatch.setattr(evidence, "_open_evidence", fail_both)
    with pytest.raises(evidence.EvidenceError, match="read failed") as error:
        evidence.read_bounded_regular(tmp_path, relative, limit=1024)
    assert isinstance(error.value.__cause__, RuntimeError)
    assert error.value.__notes__ == [
        "evidence stream cleanup also failed: secondary evidence stream close failure"
    ]


@pytest.mark.parametrize(
    "cleanup_error",
    [
        _UnformattableCleanupError("foreign cleanup"),
        ValueError(_UnformattableCleanupArgument()),
    ],
    ids=["foreign-exception-subclass", "native-error-with-foreign-argument"],
)
def test_evidence_stream_cleanup_never_formats_foreign_exceptions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cleanup_error: ValueError,
) -> None:
    """Hostile close diagnostics must not replace a typed read failure."""
    document = sample_study(tmp_path)
    relative = document["observations"][0]["raw_sample"]
    original_open = evidence._open_evidence

    @contextmanager
    def fail_both(path: Path) -> Iterator[_FaultEvidenceReader]:
        try:
            with original_open(path) as stream:
                yield _FaultEvidenceReader(stream, RuntimeError)
        finally:
            raise cleanup_error

    monkeypatch.setattr(evidence, "_open_evidence", fail_both)
    with pytest.raises(evidence.EvidenceError, match="read failed") as failure:
        evidence.read_bounded_regular(tmp_path, relative, limit=1024)
    assert type(failure.value.__cause__) is RuntimeError
    assert failure.value.__notes__ == ["evidence stream cleanup also failed"]


@pytest.mark.parametrize("fault_type", [OSError, RuntimeError, ValueError])
def test_evidence_stream_cleanup_bypasses_foreign_primary_note_hook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """Failed reads and stream close preserve the primary without hooks."""
    document = sample_study(tmp_path)
    relative = document["observations"][0]["raw_sample"]
    primary = _foreign_primary_with_hostile_note(fault_type)
    original_open = evidence._open_evidence

    @contextmanager
    def fail_close(path: Path) -> Iterator[IO[bytes]]:
        try:
            with original_open(path) as stream:
                yield stream
        finally:
            raise ValueError("secondary stream cleanup failure")

    def fail_read(stream: IO[bytes], *, size: int, relative: str) -> bytes:
        del stream, size, relative
        raise primary

    with monkeypatch.context() as patch:
        patch.setattr(evidence, "_open_evidence", fail_close)
        patch.setattr(evidence, "_read_complete", fail_read)
        with pytest.raises(
            evidence.EvidenceError, match="stream access failed"
        ) as caught:
            evidence.read_bounded_regular(tmp_path, relative, limit=1024)

    assert caught.value.__cause__ is primary
    assert any("stream cleanup" in note for note in primary.__notes__)


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


@pytest.mark.parametrize("reader", ["regular", "bounded"])
@pytest.mark.parametrize("relative", ["", "../escape.csv", "/outside.csv", b"raw.csv"])
def test_invalid_evidence_relative_rejected_without_root_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reader: str,
    relative: object,
) -> None:
    """Malformed relative names cannot dispatch host filesystem operations."""

    def forbidden_resolve(*args: object, **kwargs: object) -> Path:
        del args, kwargs
        raise AssertionError("invalid evidence path reached host resolution")

    with monkeypatch.context() as context:
        context.setattr(Path, "resolve", forbidden_resolve)
        with pytest.raises(evidence.EvidenceError, match="canonical relative"):
            if reader == "regular":
                evidence.regular_path(tmp_path, cast("str", relative))
            else:
                evidence.read_bounded_regular(
                    tmp_path, cast("str", relative), limit=1024
                )


@pytest.mark.parametrize("reader", ["regular", "bounded"])
@pytest.mark.parametrize("stage", ["root-resolve", "leaf-lstat"])
def test_foreign_missing_path_faults_are_typed_without_laundered_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reader: str,
    stage: str,
) -> None:
    """Only native missing files retain the deliberate missing-path signal."""
    _ = (tmp_path / "raw.csv").write_bytes(b"raw evidence")
    class ForeignMissingPath(FileNotFoundError):
        def __str__(self) -> str:
            raise AssertionError("foreign missing-path formatter executed")

    foreign = ForeignMissingPath("foreign missing evidence")
    original_resolve = Path.resolve
    original_lstat = Path.lstat

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == tmp_path:
            raise foreign
        return original_resolve(path, strict=strict)

    def fail_lstat(path: Path, *args: object, **kwargs: object) -> object:
        if path == tmp_path / "raw.csv":
            raise foreign
        return original_lstat(path, *args, **kwargs)

    with monkeypatch.context() as context:
        if stage == "root-resolve":
            context.setattr(Path, "resolve", fail_resolve)
        else:
            context.setattr(Path, "lstat", fail_lstat)
        with pytest.raises(evidence.EvidenceError, match="path inspection") as caught:
            if reader == "regular":
                evidence.regular_path(tmp_path, "raw.csv")
            else:
                evidence.read_bounded_regular(tmp_path, "raw.csv", limit=1024)
    assert caught.value.__cause__ is foreign


def test_native_missing_evidence_path_keeps_missing_file_contract(
    tmp_path: Path,
) -> None:
    """Native missing paths remain distinguishable for historical importers."""
    with pytest.raises(FileNotFoundError) as missing:
        evidence.regular_path(tmp_path, "absent.csv")
    assert type(missing.value) is FileNotFoundError


@pytest.mark.parametrize(
    "fault",
    [
        OSError,
        ValueError,
        RuntimeError,
        TypeError,
        AttributeError,
        IndexError,
        _UnanticipatedEvidenceError,
    ],
)
@pytest.mark.parametrize("stage", ["root-resolve", "segment-lstat", "leaf-lstat"])
def test_direct_evidence_path_inspection_faults_remain_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
    stage: str,
) -> None:
    """Unreliable host path inspection must not leak raw host exceptions."""
    _ = (tmp_path / "raw.csv").write_bytes(b"raw evidence")
    original_resolve = Path.resolve
    original_lstat = Path.lstat
    if stage == "segment-lstat":
        directory = tmp_path / "nested"
        directory.mkdir()
        _ = (directory / "raw.csv").write_bytes(b"nested raw evidence")
        target = directory
        relative = "nested/raw.csv"
    else:
        target = tmp_path if stage == "root-resolve" else tmp_path / "raw.csv"
        relative = "raw.csv"

    def failing_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == target:
            raise fault("injected evidence root resolve failure")
        return original_resolve(path, strict=strict)

    def failing_lstat(path: Path, *args: object, **kwargs: object) -> object:
        if path == target:
            raise fault("injected evidence path stat failure")
        return original_lstat(path, *args, **kwargs)

    if stage == "root-resolve":
        monkeypatch.setattr(Path, "resolve", failing_resolve)
    else:
        monkeypatch.setattr(Path, "lstat", failing_lstat)
    with pytest.raises(evidence.EvidenceError, match="path inspection") as failure:
        evidence.regular_path(tmp_path, relative, limit=1024)
    assert type(failure.value.__cause__) is fault


@pytest.mark.parametrize(
    "fault",
    [
        ValueError,
        RuntimeError,
        TypeError,
        AttributeError,
        IndexError,
        _UnanticipatedEvidenceError,
    ],
)
def test_evidence_raw_descriptor_open_failures_remain_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """A failing host open rejects before any stream is constructed."""
    _ = (tmp_path / "raw.csv").write_bytes(b"raw evidence")

    def failing_open(*args: object, **kwargs: object) -> int:
        del args, kwargs
        raise fault("injected evidence descriptor open failure")

    monkeypatch.setattr(evidence.os, "open", failing_open)
    with pytest.raises(
        evidence.EvidenceError, match="could not open safely"
    ) as failure:
        evidence.read_bounded_regular(tmp_path, "raw.csv", limit=1024)
    assert type(failure.value.__cause__) is fault


@pytest.mark.parametrize(
    "fault",
    [
        OSError,
        ValueError,
        RuntimeError,
        TypeError,
        AttributeError,
        IndexError,
        _UnanticipatedEvidenceError,
    ],
)
@pytest.mark.parametrize("target_call", [3, 6], ids=["pre-open", "post-read"])
def test_bounded_evidence_reader_types_late_path_stat_faults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
    target_call: int,
) -> None:
    """A path disappearing after regular-path admission is a typed failure."""
    target = tmp_path / "raw.csv"
    _ = target.write_bytes(b"raw evidence")
    original_lstat = Path.lstat
    lookups = 0

    def failing_lstat(path: Path, *args: object, **kwargs: object) -> object:
        nonlocal lookups
        if path == target:
            lookups += 1
            if lookups == target_call:
                raise fault("injected evidence late path stat failure")
        return original_lstat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", failing_lstat)
    with pytest.raises(evidence.EvidenceError, match="path inspection") as failure:
        evidence.read_bounded_regular(tmp_path, "raw.csv", limit=1024)
    assert lookups == target_call
    assert type(failure.value.__cause__) is fault


@pytest.mark.parametrize(
    ("boundary", "kind"),
    [
        ("document", analyze.ArenaError),
        ("links", evidence.EvidenceError),
        ("links", OSError),
        ("links", UnicodeError),
        ("links", RuntimeError),
        ("links", evidence.experiment_manifest.ExperimentManifestError),
        ("document", IndexError),
        ("document", _UnanticipatedEvidenceError),
        ("links", IndexError),
        ("links", _UnanticipatedEvidenceError),
    ],
)
def test_validate_links_does_not_format_foreign_dependency_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    boundary: str,
    kind: type[Exception],
) -> None:
    """Foreign verifier/preflight errors cannot mask linked evidence rejection."""

    class HostileDependencyError(kind):
        def __str__(self) -> str:
            raise AssertionError("foreign evidence formatter invoked")

    failure = HostileDependencyError("untrusted diagnostic")

    def fail(*_args: object, **_kwargs: object) -> None:
        raise failure

    document = sample_study(tmp_path)
    if boundary == "document":
        monkeypatch.setattr(analyze, "admit_document", fail)
    else:
        monkeypatch.setattr(evidence, "_admit_observation", fail)
    with pytest.raises(evidence.EvidenceError, match=LINKED_ERROR) as caught:
        _ = evidence.validate_links(document, tmp_path)
    assert caught.value.__cause__ is failure


@pytest.mark.parametrize(
    "kind",
    [
        analyze.ArenaError,
        evidence.EvidenceError,
        OSError,
        UnicodeError,
        IndexError,
        _UnanticipatedEvidenceError,
    ],
)
def test_evidence_cli_does_not_format_foreign_input_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: type[Exception],
) -> None:
    """The operator exits with status two even for hostile exception hooks."""

    class HostileInputError(kind):
        def __str__(self) -> str:
            raise AssertionError("foreign evidence CLI formatter invoked")

    failure = HostileInputError("untrusted operator diagnostic")

    def fail_read(*_args: object, **_kwargs: object) -> None:
        raise failure

    monkeypatch.setattr(analyze, "read_input", fail_read)
    monkeypatch.setattr(sys, "argv", ["evidence", str(tmp_path / "study.json")])
    with pytest.raises(SystemExit) as caught:
        evidence.main()
    assert caught.value.code == 2
    captured = capsys.readouterr()
    assert captured.err.startswith("arena evidence:")
    assert not captured.out


@pytest.mark.parametrize(
    "fault_type", [evidence.report_output.ReportOutputError, IndexError, Exception]
)
def test_evidence_cli_output_does_not_format_foreign_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fault_type: type[Exception],
) -> None:
    """Output diagnostics preserve the exit status without calling __str__."""
    import argparse

    class HostileReportError(fault_type):
        def __str__(self) -> str:
            raise AssertionError("foreign report error formatter invoked")

    failure = HostileReportError("untrusted report diagnostic")

    def fail_publish(*_args: object, **_kwargs: object) -> None:
        raise failure

    monkeypatch.setattr(evidence.report_output, "publish", fail_publish)
    with pytest.raises(SystemExit) as caught:
        evidence._publish_cli_report({}, argparse.ArgumentParser())
    assert caught.value.code == 2
    captured = capsys.readouterr()
    assert captured.err.startswith("arena evidence:")
    assert not captured.out


def test_evidence_direct_and_operator_retain_exact_native_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exact project exception types still retain useful rejection details."""
    document = sample_study(tmp_path)

    def fail_admit(_document: object) -> None:
        raise analyze.ArenaError("exact native study diagnostic")

    with monkeypatch.context() as context:
        context.setattr(analyze, "admit_document", fail_admit)
        with pytest.raises(
            evidence.EvidenceError, match="exact native study diagnostic"
        ):
            _ = evidence.validate_links(document, tmp_path)

    def fail_read(*_args: object) -> None:
        raise analyze.ArenaError("exact native operator diagnostic")

    monkeypatch.setattr(analyze, "read_input", fail_read)
    monkeypatch.setattr(sys, "argv", ["evidence", str(tmp_path / "study.json")])
    with pytest.raises(SystemExit, match="2"):
        evidence.main()
    assert "exact native operator diagnostic" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("boundary", "kind"),
    [
        ("document", analyze.ArenaError),
        ("links", evidence.EvidenceError),
        ("links", OSError),
        ("operator", analyze.ArenaError),
        ("report", evidence.report_output.ReportOutputError),
    ],
)
def test_exact_native_exception_with_foreign_argument_never_formats_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    boundary: str,
    kind: type[Exception],
) -> None:
    """An exact native class cannot launder a caller-owned diagnostic value."""

    class HostileArgument:
        def __str__(self) -> str:
            raise AssertionError("foreign exception argument formatter invoked")

    failure = kind(HostileArgument())

    def fail(*_args: object, **_kwargs: object) -> None:
        raise failure

    if boundary in {"document", "links"}:
        document = sample_study(tmp_path)
        if boundary == "document":
            monkeypatch.setattr(analyze, "admit_document", fail)
        else:
            monkeypatch.setattr(evidence, "_admit_observation", fail)
        with pytest.raises(evidence.EvidenceError, match=LINKED_ERROR) as caught:
            _ = evidence.validate_links(document, tmp_path)
        assert caught.value.__cause__ is failure
        return

    if boundary == "operator":
        monkeypatch.setattr(analyze, "read_input", fail)
        monkeypatch.setattr(sys, "argv", ["evidence", str(tmp_path / "study.json")])
        with pytest.raises(SystemExit) as caught:
            evidence.main()
    else:
        import argparse

        monkeypatch.setattr(evidence.report_output, "publish", fail)
        with pytest.raises(SystemExit) as caught:
            evidence._publish_cli_report({}, argparse.ArgumentParser())
    assert caught.value.code == 2
    captured = capsys.readouterr()
    assert captured.err.startswith("arena evidence:")
    assert not captured.out


@pytest.mark.parametrize("fault_type", [IndexError, _UnanticipatedEvidenceError])
def test_unanticipated_stream_close_preserves_primary_evidence_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """Unexpected close errors cannot replace an existing raw-read rejection."""
    _ = (tmp_path / "raw.csv").write_bytes(b"evidence")
    original_open = evidence._open_evidence
    primary = evidence.EvidenceError("primary evidence read failure")
    secondary = fault_type("unanticipated stream close failure")

    @contextmanager
    def fail_close(path: Path) -> Iterator[IO[bytes]]:
        try:
            with original_open(path) as stream:
                yield stream
        finally:
            raise secondary

    def fail_read(_stream: IO[bytes], *, size: int, relative: str) -> bytes:
        del size, relative
        raise primary

    monkeypatch.setattr(evidence, "_open_evidence", fail_close)
    monkeypatch.setattr(evidence, "_read_complete", fail_read)
    with pytest.raises(evidence.EvidenceError, match="primary evidence") as caught:
        evidence.read_bounded_regular(tmp_path, "raw.csv", limit=1024)
    assert caught.value is primary
    assert primary.__notes__ == ["evidence stream cleanup also failed"]


@pytest.mark.parametrize("fault_type", [IndexError, _UnanticipatedEvidenceError])
def test_unanticipated_descriptor_close_retains_evidence_constructor_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """Unexpected raw descriptor cleanup must retain the fdopen rejection."""
    _ = (tmp_path / "raw.csv").write_bytes(b"evidence")
    original_close = evidence.os.close
    primary = RuntimeError("primary evidence constructor failure")
    secondary = fault_type("unanticipated descriptor close failure")
    closed: list[int] = []

    def fail_fdopen(*_args: object, **_kwargs: object) -> IO[bytes]:
        raise primary

    def fail_close(descriptor: int) -> None:
        original_close(descriptor)
        closed.append(descriptor)
        raise secondary

    with monkeypatch.context() as context:
        context.setattr(evidence.os, "fdopen", fail_fdopen)
        context.setattr(evidence.os, "close", fail_close)
        with pytest.raises(
            evidence.EvidenceError, match="stream could not open"
        ) as caught:
            evidence.read_bounded_regular(tmp_path, "raw.csv", limit=1024)
    assert caught.value.__cause__ is primary
    assert primary.__notes__ == ["evidence descriptor cleanup also failed"]
    assert len(closed) == 1
    with pytest.raises(OSError):
        evidence.os.fstat(closed[0])


@pytest.mark.parametrize("scope", ["root", "budget"])
def test_budget_links_reject_foreign_toml_keys_before_mapping_access(
    monkeypatch: pytest.MonkeyPatch, scope: str
) -> None:
    """Colliding foreign TOML keys cannot run comparison hooks during admission."""

    class CollidingKey:
        def __hash__(self) -> int:
            return hash("budget" if scope == "root" else "seconds")

        def __eq__(self, other: object) -> bool:
            del other
            raise AssertionError("foreign budget TOML equality executed")

    budget: dict[object, object] = {"memory_mib": 128}
    if scope == "root":
        budget["seconds"] = 1
        document: dict[object, object] = {CollidingKey(): budget}
    else:
        budget[CollidingKey()] = 1
        document = {"budget": budget}

    monkeypatch.setattr(budget_links.tomllib, "loads", lambda _: document)
    with pytest.raises(budget_links.BudgetLinkError, match="native string keys"):
        budget_links.parse_run_budgets(BUDGET_MANIFEST)
