# File:
#   - gate.py
# Path:
#   - algorithms/diff/gate.py
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
#   - Combined source-lineage and behavior admission gate.
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

"""Combined source-lineage and behavior admission gate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from algorithms.diff.admission import AdmissionError

if TYPE_CHECKING:
    from algorithms.diff.admission import TreeAdmissionEvidence
    from algorithms.diff.behavior import BehaviorEvidence


@dataclass(frozen=True, slots=True)
class TransformAdmissionEvidence:
    """Independent source-lineage and behavior evidence for one candidate."""

    source: TreeAdmissionEvidence
    behavior: BehaviorEvidence
    reasons: tuple[str, ...]

    @property
    def admitted(self) -> bool:
        """Whether both independent admission families passed.

        Returns:
            True exactly when neither evidence family rejected the candidate.

        """
        return not self.reasons


def combine_admission(
    source: TreeAdmissionEvidence,
    behavior: BehaviorEvidence,
) -> TransformAdmissionEvidence:
    """Combine evidence without allowing one score to offset another.

    Returns:
        Conjunctive admission evidence preserving both underlying reports.

    """
    reasons: list[str] = []
    if not source.admitted:
        reasons.append("source lineage admission failed")
    if not behavior.admitted:
        reasons.append("behavior admission failed")
    return TransformAdmissionEvidence(
        source=source,
        behavior=behavior,
        reasons=tuple(reasons),
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
