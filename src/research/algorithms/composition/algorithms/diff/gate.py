# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
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
#   - Combined source-lineage and behavior admission gate.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Combined source-lineage and behavior admission gate."""

from __future__ import annotations

from dataclasses import dataclass

from algorithms.diff.admission import AdmissionError
from algorithms.diff.admission import TreeAdmissionEvidence
from algorithms.diff.behavior import BehaviorEvidence


@dataclass(frozen=True, slots=True)
class TransformAdmissionEvidence:
    """Independent source-lineage and behavior evidence for one candidate."""

    source: TreeAdmissionEvidence
    behavior: BehaviorEvidence
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        """Require exact evidence and canonical conjunctive rejection reasons.

        Raises:
            AdmissionError: Evidence records or reasons are inconsistent.

        """
        source = _require_source_evidence(self.source)
        behavior = _require_behavior_evidence(self.behavior)
        if type(self.reasons) is not tuple or any(
            type(reason) is not str for reason in self.reasons
        ):
            message = "transform admission reasons must use exact strings"
            raise AdmissionError(message)
        if self.reasons != _canonical_reasons(source, behavior):
            message = "transform admission reasons do not match evidence"
            raise AdmissionError(message)

    @property
    def admitted(self) -> bool:
        """Whether both independent admission families passed.

        Returns:
            True exactly when neither evidence family rejected the candidate.

        """
        return not self.reasons


def _require_source_evidence(value: object) -> TreeAdmissionEvidence:
    if type(value) is not TreeAdmissionEvidence:
        message = "transform gate requires exact TreeAdmissionEvidence"
        raise AdmissionError(message)
    return value


def _require_behavior_evidence(value: object) -> BehaviorEvidence:
    if type(value) is not BehaviorEvidence:
        message = "transform gate requires exact BehaviorEvidence"
        raise AdmissionError(message)
    return value


def _canonical_reasons(
    source: TreeAdmissionEvidence,
    behavior: BehaviorEvidence,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if not source.admitted:
        reasons.append("source lineage admission failed")
    if not behavior.admitted:
        reasons.append("behavior admission failed")
    return tuple(reasons)


def combine_admission(
    source: TreeAdmissionEvidence,
    behavior: BehaviorEvidence,
) -> TransformAdmissionEvidence:
    """Combine evidence without allowing one score to offset another.

    Returns:
        Conjunctive admission evidence preserving both underlying reports.

    """
    source = _require_source_evidence(source)
    behavior = _require_behavior_evidence(behavior)
    return TransformAdmissionEvidence(
        source=source,
        behavior=behavior,
        reasons=_canonical_reasons(source, behavior),
    )


def require_transform_admission(
    source: TreeAdmissionEvidence,
    behavior: BehaviorEvidence,
) -> TransformAdmissionEvidence:
    """Require both source lineage and behavior before transformation.

    Returns:
        Passing combined evidence.

    Raises:
        AdmissionError: Either independent evidence family rejects the
        candidate.

    """
    evidence = combine_admission(source, behavior)
    if not evidence.admitted:
        message = "; ".join(evidence.reasons)
        raise AdmissionError(message)
    return evidence
