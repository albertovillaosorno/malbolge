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
#   - Live host-C reference pilot and retained-evidence integration checks.
# - Must-Not:
#   - Claim that real host-C timing measures Malbolge candidate performance.
# - Allows:
#   - Inputs: bounded generated C challenge families and injected run failures.
#   - Outputs: paired cross-difficulty raw/manifests and accepted-stage checks.
#   - Side effects: session-local ignored native executable and CSV samples.
# - Split-When:
#   - Product compiler measurements require separately trusted verifier tests.
# - Merge-When:
#   - Research reference measurement tests become a governed runner suite.
# - Summary:
#   - Tests real measured host stages and fail-closed retained trial outcomes.
# - Description:
#   - Uses pinned Clang and the original canonical challenge oracle.
# - Usage:
#   - `pytest benchmarks/arena/tests/test_reference_study.py`.
# - Defaults:
#   - A source-reported host result is never Malbolge compiler evidence.
#

"""Bounded real host-C pilot studies, not Malbolge candidate measurements."""

# ruff: file-ignore[assert]

from __future__ import annotations

import json
import shutil
import sys
from hashlib import sha256
from typing import TYPE_CHECKING, Any, cast

import pytest

from benchmarks.arena import (
    analyze,
    evidence,
    host_c_oracle,
    reference_study,
    report_output,
)

if TYPE_CHECKING:
    from pathlib import Path

    from benchmarks.challenges import generate

REPETITIONS = 2
CAPACITY_POINTS = 4
OPTIMIZED_MODE = "-O2"
FAILED = "tool_failed"
ARTIFACT_METRIC = "artifact_bytes"
EXPECTED_ROWS = 8
FAMILY = "arithmetic-dag"
OUTPUT_FAULT = "injected short stdout write"


def _pilot() -> tuple[Path, dict[str, Any]]:
    path, document = reference_study.run_study(
        reference_study.StudyPlan(FAMILY, (4, 8), 7, REPETITIONS),
    )
    return path, document


@pytest.mark.skipif(
    not host_c_oracle._PINNED_CLANG.is_file(),  # ruff: ignore[private-member-access]
    reason="repository pinned native Clang is unavailable",
)
def test_real_host_c_reference_pilot_links_all_trial_evidence() -> None:
    """Two real difficulty levels retain paired observed stage evidence."""
    path, document = _pilot()
    try:
        rows = document["observations"]
        assert len(rows) == EXPECTED_ROWS
        assert {row["case"]["difficulty"] for row in rows} == {4, 8}
        assert all(row["outcome"] == analyze.VERIFIED for row in rows)
        assert all(row["metrics"]["elapsed_ns"] > 0 for row in rows)
        assert all(row["metrics"]["peak_rss_bytes"] > 0 for row in rows)
        assert document["study"]["objectives"] == [
            "elapsed_ns",
            "artifact_bytes",
            "peak_rss_bytes",
        ]
        report = analyze.analyze(analyze.parse_document(json.dumps(document)))
        assert len(report["capacity_curve"]) == CAPACITY_POINTS
        linked = evidence.validate_links(
            analyze.parse_document(json.dumps(document)),
            reference_study._ROOT,  # ruff: ignore[private-member-access]
            policy=evidence.EvidencePolicy(
                require_trial_run_identity=True,
                require_budget_agreement=True,
                challenge_root=f"{path.relative_to(reference_study._ROOT)}/bundles",  # ruff: ignore[private-member-access]
                require_host_c_challenge_oracle=True,
            ),
        )
        assert linked["raw_rows_matched"] == EXPECTED_ROWS
        assert linked["trial_run_links_checked"] == EXPECTED_ROWS
        assert linked["regenerated_challenge_bundles"] == REPETITIONS
        assert linked["host_c_challenge_oracles_replayed"] == REPETITIONS
        artifacts = json.loads((path / "artifacts.json").read_text())
        assert len(artifacts) == EXPECTED_ROWS
        for artifact in artifacts.values():
            executable = reference_study._ROOT / artifact["path"]  # ruff: ignore[private-member-access]
            assert (
                sha256(executable.read_bytes()).hexdigest()
                == artifact["sha256"]
            )
    finally:
        shutil.rmtree(path)


@pytest.mark.parametrize(
    "plan",
    [
        reference_study.StudyPlan(FAMILY, (), 7, 1),
        reference_study.StudyPlan(FAMILY, (4, 4), 7, 1),
        reference_study.StudyPlan(FAMILY, (1, 2, 3, 4, 5), 7, 1),
        reference_study.StudyPlan(FAMILY, (4,), 7, 0),
        reference_study.StudyPlan(FAMILY, (4,), 7, 6),
        reference_study.StudyPlan(FAMILY, (513,), 7, 1),
    ],
)
def test_invalid_study_plan_fails_before_creating_output(
    plan: reference_study.StudyPlan,
) -> None:
    """Rejected setup does not create an empty published study directory."""
    with pytest.raises((reference_study.ReferenceStudyError, ValueError)):
        reference_study.run_study(plan)


@pytest.mark.parametrize("trial_count", [True, 1.5, "2", None])
def test_noninteger_trial_count_rejects_before_native_or_output_setup(
    trial_count: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign trial count must never probe resource tools or create a run."""

    def forbid_resource_probe() -> None:
        pytest.fail("malformed trial count reached native resource admission")

    monkeypatch.setattr(
        host_c_oracle, "require_child_resource_controls", forbid_resource_probe
    )
    with pytest.raises(reference_study.ReferenceStudyError, match="trial count"):
        reference_study.run_study(
            reference_study.StudyPlan(FAMILY, (4,), 7, cast("int", trial_count))
        )


@pytest.mark.skipif(
    not host_c_oracle._PINNED_CLANG.is_file(),  # ruff: ignore[private-member-access]
    reason="repository pinned native Clang is unavailable",
)
def test_failed_reference_arm_retains_failure_not_fabricated_cost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Source-reported failed O2 stage remains visible to a paired study."""
    original = host_c_oracle.measure_reference

    def reject_o2(
        identity: generate.ChallengeIdentity, mode: str
    ) -> host_c_oracle.ReferenceMeasurement:
        if mode == OPTIMIZED_MODE:
            message = "injected compiler failure"
            raise host_c_oracle.HostOracleError(message)
        return original(identity, mode)

    monkeypatch.setattr(host_c_oracle, "measure_reference", reject_o2)
    path, document = reference_study.run_study(
        reference_study.StudyPlan(FAMILY, (4,), 7, 1),
    )
    try:
        rows = document["observations"]
        failed = next(
            row for row in rows if row["algorithm"] == reference_study.CANDIDATE
        )
        assert failed["outcome"] == FAILED
        assert failed["verifier_verdict"] == analyze.NOT_RUN
        assert ARTIFACT_METRIC not in failed["metrics"]
        result = analyze.analyze(analyze.parse_document(json.dumps(document)))
        assert result["capacity_curve"][1]["verified"] == 0
    finally:
        shutil.rmtree(path)


TAMPER_BYTES = "bytes"
TAMPER_SIZE = "size"
TAMPER_PATH = "path"
TAMPER_MISSING = "missing"
TAMPER_EXTRA = "extra"
TAMPER_SYMLINK = "symlink"


def _tamper_size(document: dict[str, Any], manifest: str) -> None:
    for row in document["observations"]:
        if row["experiment_manifest"] == manifest:
            row["metrics"][ARTIFACT_METRIC] += 1


def _tamper_record(
    tamper: str,
    document: dict[str, Any],
    reference: dict[str, str],
    *,
    manifest: str,
) -> None:
    executable = reference_study._ROOT / reference["path"]  # ruff: ignore[private-member-access]
    if tamper == TAMPER_BYTES:
        original = executable.read_bytes()
        _ = executable.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    elif tamper == TAMPER_SIZE:
        _tamper_size(document, manifest)
    elif tamper == TAMPER_PATH:
        reference["path"] = ".temp/unrelated-executable"
    elif tamper == TAMPER_SYMLINK:
        other = executable.parent / "alternate-file"
        _ = other.write_bytes(executable.read_bytes())
        executable.unlink()
        executable.symlink_to(other)


def _tamper(
    tamper: str,
    document: dict[str, Any],
    artifacts: dict[str, dict[str, str]],
) -> None:
    name = next(iter(artifacts))
    if tamper == TAMPER_MISSING:
        _ = artifacts.pop(name)
    elif tamper == TAMPER_EXTRA:
        artifacts["extra-trial"] = artifacts[name].copy()
    else:
        _tamper_record(tamper, document, artifacts[name], manifest=name)


def test_retained_artifact_check_rejects_duplicate_verified_manifests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A direct map check cannot collapse two successes into one file claim."""
    manifest = "runs/duplicate.toml"
    row = {"experiment_manifest": manifest, "outcome": analyze.VERIFIED}

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("duplicate manifest reached artifact filesystem verification")

    monkeypatch.setattr(reference_study, "_checked_artifact", forbidden)
    with pytest.raises(reference_study.ReferenceStudyError, match="duplicate"):
        reference_study.check_retained_artifacts(
            {"observations": [row, row.copy()]},
            {manifest: {"path": "not-checked", "sha256": "not-checked"}},
        )


def test_retained_failures_reject_duplicate_failure_manifests() -> None:
    """One diagnostic entry cannot stand in for two reported failed trials."""
    manifest = "runs/duplicate.toml"
    row = {"experiment_manifest": manifest, "outcome": FAILED}
    with pytest.raises(reference_study.ReferenceStudyError, match="duplicate"):
        reference_study.check_retained_failures(
            {"observations": [row, row.copy()]},
            {manifest: "compiler exited without output"},
        )


@pytest.mark.skipif(
    not host_c_oracle._PINNED_CLANG.is_file(),  # ruff: ignore[private-member-access]
    reason="repository pinned native Clang is unavailable",
)
@pytest.mark.parametrize(
    "tamper",
    [
        TAMPER_BYTES,
        TAMPER_SIZE,
        TAMPER_PATH,
        TAMPER_MISSING,
        TAMPER_EXTRA,
        TAMPER_SYMLINK,
    ],
)
def test_reference_artifact_audit_rejects_retained_drift(tamper: str) -> None:
    """Source-reported native hashes and sizes reject mutated binaries."""
    path, document = reference_study.run_study(
        reference_study.StudyPlan(FAMILY, (4,), 7, 1),
    )
    try:
        artifacts = json.loads((path / "artifacts.json").read_text())
        assert (
            reference_study.check_retained_artifacts(document, artifacts)
            == REPETITIONS
        )
        _tamper(tamper, document, artifacts)
        with pytest.raises(reference_study.ReferenceStudyError, match="host-C"):
            reference_study.check_retained_artifacts(document, artifacts)
    finally:
        shutil.rmtree(path)


def _fake_study_for_stdout(
    plan: reference_study.StudyPlan,
) -> tuple[Path, dict[str, Any]]:
    """Avoid rerunning native Clang for an unrelated stdout framing check.

    Returns:
        A path and documented observation count for the operator summary.

    """
    _ = plan
    return (
        reference_study._ROOT / ".temp" / "host-c-output-probe",  # ruff: ignore[private-member-access]
        {"observations": [{"trial": 0}, {"trial": 1}]},
    )


def test_reference_cli_output_is_checked_and_complete(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A healthy operator stream emits exactly one complete JSON object."""
    monkeypatch.setattr(reference_study, "run_study", _fake_study_for_stdout)
    monkeypatch.setattr(sys, "argv", ["reference-study", FAMILY])
    assert reference_study.main() == 0
    observed = json.loads(capsys.readouterr().out)
    assert observed["observations"] == REPETITIONS
    assert observed["study"].endswith("/host-c-output-probe/study.json")


def test_reference_cli_rejects_unflushed_or_truncated_operator_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Publishing failure cannot be reported as a successful command."""
    monkeypatch.setattr(reference_study, "run_study", _fake_study_for_stdout)
    monkeypatch.setattr(sys, "argv", ["reference-study", FAMILY])

    def broken_publisher(
        report: dict[str, Any],
        stream: report_output.TextReportStream,
    ) -> None:
        _ = (report, stream)
        message = OUTPUT_FAULT
        raise report_output.ReportOutputError(message)

    monkeypatch.setattr(report_output, "publish", broken_publisher)
    with pytest.raises(SystemExit, match="2"):
        reference_study.main()
    result = capsys.readouterr()
    assert not result.out
    assert OUTPUT_FAULT in result.err


def test_reference_study_refuses_missing_kernel_limit_launcher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No purportedly protected host study can start without prlimit."""
    monkeypatch.setattr(
        host_c_oracle.shutil, "which", lambda *_args, **_kwargs: None
    )
    with pytest.raises(
        reference_study.ReferenceStudyError, match="child limits"
    ):
        reference_study.run_study(
            reference_study.StudyPlan(FAMILY, (4,), 7, 1),
        )
