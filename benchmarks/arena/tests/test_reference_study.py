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

from hashlib import sha256
import json
import shutil
from typing import Any
from typing import TYPE_CHECKING

import pytest

from benchmarks.arena import analyze
from benchmarks.arena import evidence
from benchmarks.arena import host_c_oracle
from benchmarks.arena import reference_study

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
