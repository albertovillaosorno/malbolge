# File:
#   - test_gate.py
# Path:
#   - algorithms/diff/tests/test_gate.py
#
# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE
# Path-Rule:
#   - All paths in this header are repository-root relative.
#
# Boundary-Contract:
# - Owns:
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Tests for conjunctive source-lineage and behavior admission.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#
# Related documents:
# - None.
#
# Large file:
#   - false
#

"""Tests for conjunctive source-lineage and behavior admission."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import pytest

from algorithms.diff.admission import AdmissionError
from algorithms.diff.admission import AdmissionPolicy
from algorithms.diff.admission import evaluate_admission
from algorithms.diff.admission import identity_tree
from algorithms.diff.behavior import BehaviorObservations
from algorithms.diff.behavior import BehaviorProfile
from algorithms.diff.behavior import BugObservation
from algorithms.diff.behavior import BugProbe
from algorithms.diff.behavior import BugState
from algorithms.diff.behavior import CompatibilityObservation
from algorithms.diff.behavior import CompatibilityProbe
from algorithms.diff.behavior import IdentityObservation
from algorithms.diff.behavior import IdentityProbe
from algorithms.diff.behavior import evaluate_behavior
from algorithms.diff.gate import combine_admission
from algorithms.diff.gate import require_transform_admission

if TYPE_CHECKING:
    from algorithms.diff.admission import TreeAdmissionEvidence
    from algorithms.diff.behavior import BehaviorEvidence

_FILE_COUNT = 3
_BLOCK_COUNT = 96


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _tree(label: str) -> dict[str, bytes]:
    return {
        f"src/file-{file_index}.c": b"".join(
            hashlib.sha256(
                f"{label}:{file_index}:{block_index}".encode()
            ).digest()
            for block_index in range(_BLOCK_COUNT)
        )
        for file_index in range(_FILE_COUNT)
    }


def _source_evidence(candidate_label: str) -> TreeAdmissionEvidence:
    policy = AdmissionPolicy(
        minimum_source_similarity=0.50,
        minimum_anchor_coverage=0.66,
        minimum_anchor_files=2,
        minimum_anchors_per_file=2,
    )
    return evaluate_admission(
        identity_tree(_tree("reference")),
        identity_tree(_tree(candidate_label)),
        policy,
    )


def _behavior_evidence(*, compatible: bool = True) -> BehaviorEvidence:
    profile = BehaviorProfile(
        identity=(
            IdentityProbe(probe_id="identity", expected_digest=b"expected"),
        ),
        compatibility=(CompatibilityProbe(probe_id="compatible"),),
        bugs=(BugProbe(probe_id="bug", correction_id="fix"),),
    )
    observations = BehaviorObservations(
        identity=(
            IdentityObservation(probe_id="identity", digest=b"expected"),
        ),
        compatibility=(
            CompatibilityObservation(
                probe_id="compatible",
                compatible=compatible,
            ),
        ),
        bugs=(BugObservation(probe_id="bug", state=BugState.FIXED),),
    )
    return evaluate_behavior(profile, observations, minimum_similarity=0.80)


def test_behavior_only_clone_cannot_replace_source_lineage() -> None:
    """Reject perfect behavior when structural source lineage is unrelated."""
    source = _source_evidence("unrelated")
    behavior = _behavior_evidence()

    _expect(not source.admitted, "unrelated source unexpectedly passed lineage")
    _expect(behavior.admitted, "synthetic behavior clone did not pass behavior")
    with pytest.raises(AdmissionError, match="source lineage admission failed"):
        _ = require_transform_admission(source, behavior)


def test_source_lineage_cannot_replace_failed_compatibility() -> None:
    """Reject valid lineage when a mandatory behavior precondition fails."""
    source = _source_evidence("reference")
    behavior = _behavior_evidence(compatible=False)

    _expect(source.admitted, "exact source lineage unexpectedly failed")
    _expect(not behavior.admitted, "failed compatibility passed behavior")
    combined = combine_admission(source, behavior)
    _expect(
        not combined.admitted, "failed behavior was offset by source lineage"
    )
    _expect(
        combined.reasons == ("behavior admission failed",),
        "combined gate reported the wrong failure family",
    )


def test_combined_gate_accepts_only_when_both_families_pass() -> None:
    """Admit only simultaneous source-lineage and behavior success."""
    evidence = require_transform_admission(
        _source_evidence("reference"),
        _behavior_evidence(),
    )
    _expect(evidence.admitted, "passing evidence was rejected")
