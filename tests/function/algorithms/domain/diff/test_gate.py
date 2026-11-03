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

"""Tests for conjunctive source-lineage and behavior admission."""

from __future__ import annotations

import builtins
import hashlib
from dataclasses import replace
from typing import TYPE_CHECKING, cast

import pytest
from algorithms.diff.admission import (
    AdmissionError,
    AdmissionPolicy,
    evaluate_admission,
    identity_tree,
)
from algorithms.diff.behavior import (
    BehaviorObservations,
    BehaviorProfile,
    BugObservation,
    BugProbe,
    BugState,
    CompatibilityObservation,
    CompatibilityProbe,
    IdentityObservation,
    IdentityProbe,
    evaluate_behavior,
)
from algorithms.diff.gate import (
    TransformAdmissionEvidence,
    combine_admission,
    require_transform_admission,
)

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
            hashlib.sha256(f"{label}:{file_index}:{block_index}".encode()).digest()
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
        identity=(IdentityProbe(probe_id="identity", expected_digest=b"expected"),),
        compatibility=(CompatibilityProbe(probe_id="compatible"),),
        bugs=(BugProbe(probe_id="bug", correction_id="fix"),),
    )
    observations = BehaviorObservations(
        identity=(IdentityObservation(probe_id="identity", digest=b"expected"),),
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
    _expect(not combined.admitted, "failed behavior was offset by source lineage")
    _expect(
        combined.reasons == ("behavior admission failed",),
        "combined gate reported the wrong failure family",
    )


def test_gate_rejects_foreign_and_forged_evidence_records() -> None:
    """Invalid gate metadata cannot forge a passing conjunctive decision."""
    source = _source_evidence("reference")
    behavior = _behavior_evidence()
    with pytest.raises(AdmissionError, match="exact TreeAdmissionEvidence"):
        _ = combine_admission(
            cast("TreeAdmissionEvidence", object()),
            behavior,
        )
    with pytest.raises(AdmissionError, match="exact BehaviorEvidence"):
        _ = combine_admission(
            source,
            cast("BehaviorEvidence", object()),
        )

    rejected_source = _source_evidence("unrelated")
    with pytest.raises(AdmissionError, match="do not match evidence"):
        _ = TransformAdmissionEvidence(
            source=rejected_source,
            behavior=behavior,
            reasons=(),
        )


@pytest.mark.parametrize("failing_family", ["source", "behavior"])
def test_gate_rejects_failed_evidence_after_admitted_descriptor_spoof(
    monkeypatch: pytest.MonkeyPatch,
    failing_family: str,
) -> None:
    """A domain callback cannot redefine the conjunctive decision property."""
    source = _source_evidence(
        "unrelated" if failing_family == "source" else "reference"
    )
    behavior = _behavior_evidence(compatible=failing_family != "behavior")
    spoofed_type = type(source) if failing_family == "source" else type(behavior)

    def forged_admitted(_: object) -> bool:
        return True

    failure = (
        "source lineage admission failed"
        if failing_family == "source"
        else "behavior admission failed"
    )
    with monkeypatch.context() as patched:
        patched.setattr(spoofed_type, "admitted", property(forged_admitted))
        with pytest.raises(AdmissionError, match=failure):
            _ = require_transform_admission(source, behavior)
        with pytest.raises(AdmissionError, match="do not match evidence"):
            _ = TransformAdmissionEvidence(source, behavior, reasons=())


def test_gate_rejects_after_its_own_admitted_property_is_spoofed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late descriptor cannot promote rejected combined evidence."""
    source = _source_evidence("unrelated")
    behavior = _behavior_evidence()
    with monkeypatch.context() as patched:
        patched.setattr(
            TransformAdmissionEvidence, "admitted", property(lambda _: True)
        )
        with pytest.raises(AdmissionError, match="source lineage"):
            _ = require_transform_admission(source, behavior)


def test_gate_rejects_foreign_reason_after_late_any_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Forged text subclasses cannot authenticate a combined gate verdict."""
    class ForeignReason(str):
        """A non-exact reason masquerading as validated text."""

    source = _source_evidence("unrelated")
    behavior = _behavior_evidence()
    valid = combine_admission(source, behavior)
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "any", lambda values: False)
        try:
            _ = replace(valid, reasons=(ForeignReason(valid.reasons[0]),))
        except AdmissionError:
            rejected = True
    assert rejected, "late any hook admitted a foreign gate reason"


def test_combined_gate_accepts_only_when_both_families_pass() -> None:
    """Admit only simultaneous source-lineage and behavior success."""
    evidence = require_transform_admission(
        _source_evidence("reference"),
        _behavior_evidence(),
    )
    _expect(evidence.admitted, "passing evidence was rejected")
