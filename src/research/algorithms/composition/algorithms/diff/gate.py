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

import builtins
from dataclasses import dataclass

from algorithms.diff.admission import AdmissionError, TreeAdmissionEvidence
from algorithms.diff.behavior import BehaviorEvidence

# Conjunctive gate validation must not trust late global builtins hooks.
_NATIVE_ANY = builtins.any
_NATIVE_TYPE = type
_NATIVE_STR = builtins.str
_NATIVE_TUPLE = tuple


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
        if _NATIVE_TYPE(self.reasons) is not _NATIVE_TUPLE or _NATIVE_ANY(
            _NATIVE_TYPE(reason) is not _NATIVE_STR for reason in self.reasons
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
    if _NATIVE_TYPE(value) is not TreeAdmissionEvidence:
        message = "transform gate requires exact TreeAdmissionEvidence"
        raise AdmissionError(message)
    return value


def _require_behavior_evidence(value: object) -> BehaviorEvidence:
    if _NATIVE_TYPE(value) is not BehaviorEvidence:
        message = "transform gate requires exact BehaviorEvidence"
        raise AdmissionError(message)
    return value


def _canonical_reasons(
    source: TreeAdmissionEvidence,
    behavior: BehaviorEvidence,
) -> tuple[str, ...]:
    reasons: list[str] = []
    # Evidence records validate their immutable rejection reasons at creation.
    # Do not delegate gate authority to late-bound consumer-visible properties.
    if source.reasons:
        reasons.append("source lineage admission failed")
    if behavior.reasons:
        reasons.append("behavior admission failed")
    return _NATIVE_TUPLE(reasons)


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
    if evidence.reasons:
        message = "; ".join(evidence.reasons)
        raise AdmissionError(message)
    return evidence
