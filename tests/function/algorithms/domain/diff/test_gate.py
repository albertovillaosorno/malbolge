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
from collections.abc import Iterable
from dataclasses import replace
from types import MemberDescriptorType
from typing import TYPE_CHECKING, Self, cast

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


class _ForeignReason(str):
    """Non-native string alias impersonating a canonical gate reason."""

    __slots__: tuple[str, ...] = ()


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


def test_gate_rejects_failed_source_after_late_tuple_subclass_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A tuple constructor cannot erase both rounds of rejection checks."""
    source = _source_evidence("unrelated")
    behavior = _behavior_evidence()
    native_tuple = tuple
    calls = 0

    class ErasingTuple(native_tuple[str, ...]):
        def __new__(cls, values: Iterable[str]) -> Self:
            nonlocal calls
            calls += 1
            if list(values) == ["source lineage admission failed"]:
                return native_tuple.__new__(cls, ())
            return native_tuple.__new__(cls, values)

    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "tuple", ErasingTuple)
        try:
            _ = require_transform_admission(source, behavior)
        except AdmissionError:
            rejected = True

    _expect(rejected, "tuple substitution erased mandatory source rejection")
    _expect(calls == 0, "mutable tuple constructor was consulted")


def test_gate_rejects_foreign_source_after_late_type_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged type check cannot promote arbitrary source evidence."""
    foreign = object()
    native_type = type
    native_source_type = native_type(_source_evidence("reference"))
    forged_source = cast("TreeAdmissionEvidence", foreign)
    behavior = _behavior_evidence()
    calls = 0

    def forge_source_type(value: object) -> type[object]:
        nonlocal calls
        if value is foreign:
            calls += 1
            return native_source_type
        return native_type(value)

    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "type", forge_source_type)
        try:
            _ = combine_admission(forged_source, behavior)
        except AdmissionError:
            rejected = True

    _expect(rejected, "foreign source evidence passed after type spoof")
    _expect(calls == 0, "mutable type function was consulted")


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


@pytest.mark.parametrize("failing_family", ["source", "behavior"])
def test_gate_rejects_late_reasons_slot_spoof(
    monkeypatch: pytest.MonkeyPatch, failing_family: str
) -> None:
    """A replaced evidence slot descriptor cannot erase a failed gate."""
    source = _source_evidence(
        "unrelated" if failing_family == "source" else "reference"
    )
    behavior = _behavior_evidence(compatible=failing_family != "behavior")
    family = type(source) if failing_family == "source" else type(behavior)
    reason = (
        "source lineage admission failed"
        if failing_family == "source"
        else "behavior admission failed"
    )
    with monkeypatch.context() as patched:
        patched.setattr(family, "reasons", property(lambda _: ()))
        with pytest.raises(AdmissionError, match=reason):
            _ = require_transform_admission(source, behavior)
        with pytest.raises(AdmissionError, match="do not match evidence"):
            _ = TransformAdmissionEvidence(source, behavior, reasons=())


@pytest.mark.parametrize("failing_family", ["source", "behavior"])
def test_gate_rejects_late_reason_getattribute_spoof(
    monkeypatch: pytest.MonkeyPatch, failing_family: str
) -> None:
    """Late class attribute hooks cannot hide recorded admission failures."""
    source = _source_evidence(
        "unrelated" if failing_family == "source" else "reference"
    )
    behavior = _behavior_evidence(compatible=failing_family != "behavior")
    family = type(source) if failing_family == "source" else type(behavior)
    calls = 0

    def forged_attribute(value: object, name: str) -> object:
        nonlocal calls
        if name == "reasons":
            calls += 1
            return ()
        return object.__getattribute__(value, name)

    with monkeypatch.context() as patched:
        patched.setattr(family, "__getattribute__", forged_attribute)
        with pytest.raises(AdmissionError, match="admission failed"):
            _ = require_transform_admission(source, behavior)
    assert calls == 0, "late evidence attribute hook was consulted"


def test_gate_admitted_ignores_late_own_reasons_slot_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A constructed rejected gate cannot be promoted through a slot hook."""
    rejected = combine_admission(
        _source_evidence("unrelated"), _behavior_evidence()
    )
    assert not rejected.admitted
    with monkeypatch.context() as patched:
        patched.setattr(
            TransformAdmissionEvidence, "reasons", property(lambda _: ())
        )
        assert not rejected.admitted


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
    source = _source_evidence("unrelated")
    behavior = _behavior_evidence()
    valid = combine_admission(source, behavior)
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "any", lambda values: False)
        try:
            _ = replace(valid, reasons=(_ForeignReason(valid.reasons[0]),))
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


def test_gate_rejects_late_string_alias_for_foreign_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late string aliases cannot certify non-native rejection reasons."""
    source = _source_evidence("unrelated")
    evidence = combine_admission(source, _behavior_evidence())
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "str", _ForeignReason)
        try:
            _ = replace(
                evidence, reasons=(_ForeignReason(evidence.reasons[0]),)
            )
        except AdmissionError:
            rejected = True
    assert rejected, "foreign reason passed a late string alias"


def test_gate_accepts_native_reasons_after_late_string_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late consumer aliases cannot reject valid native gate evidence."""
    source = _source_evidence("unrelated")
    behavior = _behavior_evidence()
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "str", _ForeignReason)
        evidence = combine_admission(source, behavior)
    assert evidence.reasons == ("source lineage admission failed",)


@pytest.mark.parametrize("hook", ["getattribute", "slot"])
@pytest.mark.parametrize(
    "case",
    [
        "source_foreign",
        "source_rejected",
        "behavior_foreign",
        "behavior_rejected",
        "reasons_foreign_text",
        "reasons_foreign_tuple",
    ],
)
def test_gate_constructor_rejects_late_field_forgery(
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    hook: str,
) -> None:
    """Direct gate construction must validate stored evidence and reasons."""
    valid_source = _source_evidence("reference")
    rejected_source = _source_evidence("unrelated")
    valid_behavior = _behavior_evidence()
    rejected_behavior = _behavior_evidence(compatible=False)
    source = valid_source
    behavior = valid_behavior
    reasons: tuple[str, ...] = ()

    if case == "source_foreign":
        source = cast("TreeAdmissionEvidence", object())
    elif case == "source_rejected":
        source = rejected_source
    elif case == "behavior_foreign":
        behavior = cast("BehaviorEvidence", object())
    elif case == "behavior_rejected":
        behavior = rejected_behavior
    elif case == "reasons_foreign_text":
        source = rejected_source
        reasons = (_ForeignReason("source lineage admission failed"),)
    else:
        class ForeignReasons(tuple[str, ...]):
            pass

        reasons = ForeignReasons(())

    field = "reasons" if case.startswith("reasons_") else case.split("_")[0]
    forged: object = {
        "source": valid_source,
        "behavior": valid_behavior,
        "reasons": (
            ("source lineage admission failed",)
            if case == "reasons_foreign_text"
            else ()
        ),
    }[field]
    calls = 0

    def forged_attribute(
        value: TransformAdmissionEvidence, name: str
    ) -> object:
        nonlocal calls
        if name == field:
            calls += 1
            return forged
        return cast("object", object.__getattribute__(value, name))

    def forged_property(value: TransformAdmissionEvidence) -> object:
        return forged_attribute(value, field)

    with monkeypatch.context() as patch:
        if hook == "slot":
            original_slot = cast(
                "MemberDescriptorType",
                TransformAdmissionEvidence.__dict__[field],
            )

            def store(
                value: TransformAdmissionEvidence, stored: object
            ) -> None:
                original_slot.__set__(value, stored)

            patch.setattr(
                TransformAdmissionEvidence,
                field,
                property(forged_property, store),
            )
        else:
            patch.setattr(
                TransformAdmissionEvidence, "__getattribute__", forged_attribute
            )
        with pytest.raises(AdmissionError):
            _ = TransformAdmissionEvidence(source, behavior, reasons)
    assert calls == 0, "late gate getter participated in admission"
