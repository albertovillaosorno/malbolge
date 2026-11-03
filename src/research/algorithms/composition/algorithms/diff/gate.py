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
from collections.abc import Callable
from dataclasses import dataclass
from types import MemberDescriptorType
from typing import cast

from algorithms.diff.admission import AdmissionError, TreeAdmissionEvidence
from algorithms.diff.behavior import BehaviorEvidence

# Conjunctive gate validation must not trust late global builtins hooks.
_NATIVE_ANY = builtins.any
_NATIVE_TYPE = type
_NATIVE_STR = builtins.str
_NATIVE_TUPLE = tuple
_NATIVE_OBJECT_NEW = object.__new__
# Slotted frozen dataclass fields still have mutable *class* descriptors.
# Retain the original slot readers before loading any consumer hooks.
_SOURCE_REASONS_SLOT = cast(
    "MemberDescriptorType", TreeAdmissionEvidence.__dict__["reasons"]
)
_BEHAVIOR_REASONS_SLOT = cast(
    "MemberDescriptorType", BehaviorEvidence.__dict__["reasons"]
)


@dataclass(frozen=True, slots=True, init=False)
class TransformAdmissionEvidence:
    """Independent source-lineage and behavior evidence for one candidate."""

    source: TreeAdmissionEvidence
    behavior: BehaviorEvidence
    reasons: tuple[str, ...]

    def __init__(
        self,
        source: TreeAdmissionEvidence,
        behavior: BehaviorEvidence,
        reasons: tuple[str, ...],
    ) -> None:
        """Validate conjunctive admission with the captured native guard."""
        _GATE_SOURCE_SLOT.__set__(self, source)
        _GATE_BEHAVIOR_SLOT.__set__(self, behavior)
        _GATE_REASONS_SLOT.__set__(self, reasons)
        _TRANSFORM_ADMISSION_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require exact evidence and canonical conjunctive rejection reasons.

        Raises:
            AdmissionError: Evidence records or reasons are inconsistent.

        """
        owner = TransformAdmissionEvidence
        source = _require_source_evidence(
            cast("object", _GATE_SOURCE_SLOT.__get__(self, owner))
        )
        behavior = _require_behavior_evidence(
            cast("object", _GATE_BEHAVIOR_SLOT.__get__(self, owner))
        )
        reasons = cast(
            "tuple[object, ...]", _GATE_REASONS_SLOT.__get__(self, owner)
        )
        if _NATIVE_TYPE(reasons) is not _NATIVE_TUPLE or _NATIVE_ANY(
            _NATIVE_TYPE(reason) is not _NATIVE_STR for reason in reasons
        ):
            message = "transform admission reasons must use exact strings"
            raise AdmissionError(message)
        if reasons != _canonical_reasons(source, behavior):
            message = "transform admission reasons do not match evidence"
            raise AdmissionError(message)

    @property
    def admitted(self) -> bool:
        """Whether both independent admission families passed.

        Returns:
            True exactly when neither evidence family rejected the candidate.

        """
        return not _GATE_REASONS_SLOT.__get__(self, TransformAdmissionEvidence)


# Original admission cannot be weakened or forged via late class hooks.
_TRANSFORM_ADMISSION_VALIDATOR = cast(
    "Callable[[TransformAdmissionEvidence], None]",
    TransformAdmissionEvidence.__dict__["__post_init__"],
)

_GATE_REASONS_SLOT = cast(
    "MemberDescriptorType", TransformAdmissionEvidence.__dict__["reasons"]
)
_GATE_SOURCE_SLOT = cast(
    "MemberDescriptorType", TransformAdmissionEvidence.__dict__["source"]
)
_GATE_BEHAVIOR_SLOT = cast(
    "MemberDescriptorType", TransformAdmissionEvidence.__dict__["behavior"]
)

_GATE_INIT = cast(
    Callable[
        [
            TransformAdmissionEvidence,
            TreeAdmissionEvidence,
            BehaviorEvidence,
            tuple[str, ...],
        ],
        None,
    ],
    TransformAdmissionEvidence.__dict__["__init__"],
)


def _new_transform_admission(
    source: TreeAdmissionEvidence,
    behavior: BehaviorEvidence,
    reasons: tuple[str, ...],
) -> TransformAdmissionEvidence:
    """Construct trusted gate evidence without late class allocation hooks."""
    evidence = _NATIVE_OBJECT_NEW(TransformAdmissionEvidence)
    _GATE_INIT(evidence, source, behavior, reasons)
    return evidence


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
    if _SOURCE_REASONS_SLOT.__get__(source, TreeAdmissionEvidence):
        reasons.append("source lineage admission failed")
    if _BEHAVIOR_REASONS_SLOT.__get__(behavior, BehaviorEvidence):
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
    return _new_transform_admission(
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
    reasons = cast(
        "tuple[str, ...]",
        _GATE_REASONS_SLOT.__get__(evidence, TransformAdmissionEvidence),
    )
    if reasons:
        message = "; ".join(reasons)
        raise AdmissionError(message)
    return evidence
