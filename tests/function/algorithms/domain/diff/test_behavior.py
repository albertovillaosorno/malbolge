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
#   - Synthetic tests for generic behavior-probe admission semantics.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Synthetic tests for generic behavior-probe admission semantics."""

import builtins
import math
from collections import UserString
from dataclasses import replace
from types import MemberDescriptorType
from typing import cast

import pytest
from algorithms.diff.behavior import (
    BehaviorAdmissionError,
    BehaviorEvidence,
    BehaviorObservations,
    BehaviorPolicyError,
    BehaviorProfile,
    BugObservation,
    BugProbe,
    BugState,
    CompatibilityObservation,
    CompatibilityProbe,
    IdentityObservation,
    IdentityProbe,
    evaluate_behavior,
    require_behavior,
)

_MINIMUM_BEHAVIOR_SIMILARITY = 0.80
_FOREIGN_PROBE = "probe"


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _profile() -> BehaviorProfile:
    return BehaviorProfile(
        identity=tuple(
            IdentityProbe(
                probe_id=f"identity-{index}", expected_digest=bytes([index])
            )
            for index in range(5)
        ),
        compatibility=(CompatibilityProbe(probe_id="can-transform"),),
        bugs=(BugProbe(probe_id="historical-bug", correction_id="fix-bug"),),
    )


def _observations(
    *,
    identity_matches: int = 5,
    compatible: bool | None = True,
    bug_state: BugState = BugState.PRESENT,
) -> BehaviorObservations:
    identity = tuple(
        IdentityObservation(
            probe_id=f"identity-{index}",
            digest=bytes([index]) if index < identity_matches else b"wrong",
        )
        for index in range(5)
    )
    return BehaviorObservations(
        identity=identity,
        compatibility=(
            CompatibilityObservation(
                probe_id="can-transform",
                compatible=compatible,
            ),
        ),
        bugs=(BugObservation(probe_id="historical-bug", state=bug_state),),
    )


def test_behavior_valid_threshold_ignores_late_math_finite_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Domain hooks must not reject an already-valid behavior threshold."""
    calls = 0

    def forged_finite(value: float) -> bool:
        nonlocal calls
        del value
        calls += 1
        return False

    with monkeypatch.context() as patched:
        patched.setattr(math, "isfinite", forged_finite)
        admitted = require_behavior(
            _profile(), _observations(), _MINIMUM_BEHAVIOR_SIMILARITY
        )
    assert admitted.admitted
    assert calls == 0


def test_behavior_valid_evidence_ignores_late_math_finite_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Existing observation receipts remain valid after domain hook swaps."""
    evidence = require_behavior(
        _profile(), _observations(), _MINIMUM_BEHAVIOR_SIMILARITY
    )
    calls = 0

    def forged_finite(value: float) -> bool:
        nonlocal calls
        del value
        calls += 1
        return False

    with monkeypatch.context() as patched:
        patched.setattr(math, "isfinite", forged_finite)
        reconstructed = replace(evidence)
    assert reconstructed.admitted
    assert calls == 0


def test_behavior_evidence_rejects_incoherent_direct_construction() -> None:
    """Aggregated evidence cannot forge impossible local invariants."""
    with pytest.raises(BehaviorPolicyError, match=r"similarity.*probe counts"):
        _ = BehaviorEvidence(
            0.5, 1, 1, (), (), (), _profile(), _observations(), 0.80
        )
    with pytest.raises(BehaviorPolicyError, match="cannot exceed total"):
        _ = BehaviorEvidence(
            1.0, 2, 1, (), (), (), _profile(), _observations(), 0.80
        )
    with pytest.raises(BehaviorPolicyError, match="disjoint"):
        _ = BehaviorEvidence(
            1.0, 1, 1, ("fix",), ("fix",), (), _profile(), _observations(), 0.80
        )
    with pytest.raises(BehaviorPolicyError, match="immutable tuple"):
        _ = BehaviorEvidence(
            1.0,
            1,
            1,
            cast("tuple[str, ...]", cast("object", ["fix"])),
            (),
            (),
            _profile(),
            _observations(),
            _MINIMUM_BEHAVIOR_SIMILARITY,
        )


def test_behavior_evidence_rejects_late_reason_getattribute_forgery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Consumer class hooks cannot approve erased compatibility failures."""
    rejected = evaluate_behavior(
        _profile(), _observations(compatible=False),
        _MINIMUM_BEHAVIOR_SIMILARITY,
    )
    original_reasons = rejected.reasons
    calls = 0

    def forged_attribute(value: object, name: str) -> object:
        nonlocal calls
        if name == "reasons":
            calls += 1
            return original_reasons
        return object.__getattribute__(value, name)

    with monkeypatch.context() as patched:
        patched.setattr(
            BehaviorEvidence, "__getattribute__", forged_attribute
        )
        with pytest.raises(BehaviorPolicyError, match="reasons do not match"):
            _ = replace(rejected, reasons=())
    assert calls == 0, "late reason getter participated in evidence binding"


@pytest.mark.parametrize("hook", ["slot", "getattribute"])
def test_behavior_evidence_admitted_ignores_late_reason_hook(
    monkeypatch: pytest.MonkeyPatch, hook: str
) -> None:
    """An existing failed behavior receipt cannot be promoted by a hook."""
    rejected = evaluate_behavior(
        _profile(), _observations(compatible=False),
        _MINIMUM_BEHAVIOR_SIMILARITY,
    )
    assert not rejected.admitted

    def forged_attribute(value: object, name: str) -> object:
        if name == "reasons":
            return ()
        return object.__getattribute__(value, name)

    with monkeypatch.context() as patched:
        if hook == "slot":
            patched.setattr(
                BehaviorEvidence, "reasons", property(lambda _: ())
            )
        else:
            patched.setattr(
                BehaviorEvidence, "__getattribute__", forged_attribute
            )
        assert not rejected.admitted


def test_require_behavior_ignores_late_reason_getattribute_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Compatibility failure retains its typed admission error under hooks."""

    def forged_attribute(value: object, name: str) -> object:
        if name == "reasons":
            return ()
        return object.__getattribute__(value, name)

    with monkeypatch.context() as patched:
        patched.setattr(
            BehaviorEvidence, "__getattribute__", forged_attribute
        )
        with pytest.raises(BehaviorAdmissionError, match="compatibility"):
            _ = require_behavior(
                _profile(), _observations(compatible=False),
                _MINIMUM_BEHAVIOR_SIMILARITY,
            )


def test_direct_behavior_evidence_cannot_erase_compatibility_failure() -> None:
    """Reconstructing evidence cannot turn failed preconditions into success."""
    rejected = evaluate_behavior(
        _profile(),
        _observations(compatible=False),
        _MINIMUM_BEHAVIOR_SIMILARITY,
    )
    assert not rejected.admitted
    with pytest.raises(BehaviorPolicyError, match="behavior evidence reasons"):
        _ = replace(rejected, reasons=())


def test_direct_behavior_evidence_cannot_change_bug_route() -> None:
    """Correction application must reflect the original bug probe result."""
    fixed = evaluate_behavior(
        _profile(),
        _observations(bug_state=BugState.FIXED),
        _MINIMUM_BEHAVIOR_SIMILARITY,
    )
    assert fixed.admitted
    with pytest.raises(BehaviorPolicyError, match=r"behavior evidence.*route"):
        _ = replace(
            fixed,
            corrections_to_apply=("fix-bug",),
            corrections_to_skip=(),
        )


def test_direct_behavior_evidence_cannot_lower_threshold() -> None:
    """Evidence must retain the threshold that caused an admission failure."""
    rejected = evaluate_behavior(
        _profile(), _observations(identity_matches=4), 1.0
    )
    with pytest.raises(BehaviorPolicyError, match="behavior evidence reasons"):
        _ = replace(rejected, reasons=())


def test_direct_behavior_evidence_cannot_hide_unknown_bug() -> None:
    """Unknown historical defects may not be admitted via edited evidence."""
    rejected = evaluate_behavior(
        _profile(),
        _observations(bug_state=BugState.UNKNOWN),
        _MINIMUM_BEHAVIOR_SIMILARITY,
    )
    with pytest.raises(BehaviorPolicyError, match="behavior evidence reasons"):
        _ = replace(rejected, reasons=())


def test_direct_behavior_evidence_rejects_foreign_inputs() -> None:
    """Evidence rejects foreign profiles, observations, and thresholds."""
    evidence = evaluate_behavior(
        _profile(), _observations(), _MINIMUM_BEHAVIOR_SIMILARITY
    )
    with pytest.raises(BehaviorPolicyError, match="exact BehaviorProfile"):
        _ = replace(evidence, profile=cast("BehaviorProfile", object()))
    with pytest.raises(BehaviorPolicyError, match="exact BehaviorObservations"):
        _ = replace(
            evidence, observations=cast("BehaviorObservations", object())
        )
    invalid_threshold: object = True
    with pytest.raises(BehaviorPolicyError, match="minimum_similarity"):
        _ = replace(
            evidence, minimum_similarity=cast("float", invalid_threshold)
        )


def test_direct_behavior_evidence_rejects_observation_count_forgery() -> None:
    """A changed summary cannot invent successful identity executions."""
    rejected = evaluate_behavior(
        _profile(),
        _observations(identity_matches=4),
        _MINIMUM_BEHAVIOR_SIMILARITY,
    )
    with pytest.raises(BehaviorPolicyError, match="probe counts"):
        _ = replace(
            rejected,
            similarity=1.0,
            matched_identity_probes=5,
        )


def test_present_bug_routes_correction_without_rejecting_source() -> None:
    """Apply a known correction when the historical defect is still present."""
    evidence = require_behavior(
        _profile(),
        _observations(bug_state=BugState.PRESENT),
        _MINIMUM_BEHAVIOR_SIMILARITY,
    )
    _expect(evidence.corrections_to_apply == ("fix-bug",), "fix not routed")
    _expect(not evidence.corrections_to_skip, "present bug was skipped")


def test_already_fixed_bug_skips_correction_without_rejection() -> None:
    """Treat an upstream-fixed defect as compatible and skip its correction."""
    evidence = require_behavior(
        _profile(),
        _observations(bug_state=BugState.FIXED),
        _MINIMUM_BEHAVIOR_SIMILARITY,
    )
    _expect(
        not evidence.corrections_to_apply, "already-fixed bug was re-applied"
    )
    _expect(
        evidence.corrections_to_skip == ("fix-bug",), "fixed bug not skipped"
    )


def test_behavior_similarity_accepts_exact_threshold() -> None:
    """Accept four of five identity matches at the provisional 0.80 gate."""
    evidence = require_behavior(
        _profile(),
        _observations(identity_matches=4),
        _MINIMUM_BEHAVIOR_SIMILARITY,
    )
    _expect(math.isclose(evidence.similarity, 0.80), "behavior score changed")


def test_behavior_similarity_fails_immediately_above_observed_score() -> None:
    """Reject the next threshold above measured identity behavior."""
    observations = _observations(identity_matches=4)
    baseline = evaluate_behavior(_profile(), observations, 0.0)
    above = math.nextafter(baseline.similarity, 1.0)
    with pytest.raises(
        BehaviorAdmissionError, match="behavior identity similarity"
    ):
        _ = require_behavior(_profile(), observations, above)


def test_identity_probe_unavailable_fails_even_when_threshold_could_pass() -> (
    None
):
    """Require every mandatory identity probe to execute."""
    observations = _observations()
    identity = list(observations.identity)
    identity[-1] = IdentityObservation(probe_id="identity-4", digest=None)
    unavailable = BehaviorObservations(
        identity=tuple(identity),
        compatibility=observations.compatibility,
        bugs=observations.bugs,
    )
    with pytest.raises(
        BehaviorAdmissionError, match="identity probe unavailable"
    ):
        _ = require_behavior(_profile(), unavailable, 0.0)


def test_compatibility_probe_failure_rejects_perfect_identity() -> None:
    """Require compatibility even at behavior similarity 1.0."""
    with pytest.raises(
        BehaviorAdmissionError, match="compatibility probe failed"
    ):
        _ = require_behavior(
            _profile(),
            _observations(compatible=False),
            _MINIMUM_BEHAVIOR_SIMILARITY,
        )


@pytest.mark.parametrize(
    ("identity_matches", "compatible", "bug_state", "reason"),
    [
        (3, True, BugState.PRESENT, "insufficient behavior identity"),
        (5, False, BugState.PRESENT, "compatibility probe failed"),
        (5, True, BugState.UNKNOWN, "bug probe unresolved"),
    ],
)
def test_behavior_rejection_ignores_late_admitted_property_swap(
    monkeypatch: pytest.MonkeyPatch,
    identity_matches: int,
    compatible: bool,
    bug_state: BugState,
    reason: str,
) -> None:
    """A replaced evidence descriptor cannot authorize rejected behavior."""
    called = 0

    def forged_admitted(_evidence: BehaviorEvidence) -> bool:
        nonlocal called
        called += 1
        return True

    with monkeypatch.context() as patch:
        patch.setattr(BehaviorEvidence, "admitted", property(forged_admitted))
        with pytest.raises(BehaviorAdmissionError, match=reason):
            _ = require_behavior(
                _profile(),
                _observations(
                    identity_matches=identity_matches,
                    compatible=compatible,
                    bug_state=bug_state,
                ),
                _MINIMUM_BEHAVIOR_SIMILARITY,
            )
    assert called == 0, "hostile admission descriptor was consulted"


def test_unknown_bug_state_fails_closed() -> None:
    """Do not guess whether a source correction should be applied."""
    with pytest.raises(BehaviorAdmissionError, match="bug probe unresolved"):
        _ = require_behavior(
            _profile(),
            _observations(bug_state=BugState.UNKNOWN),
            _MINIMUM_BEHAVIOR_SIMILARITY,
        )


def test_behavior_metadata_rejects_foreign_runtime_types() -> None:
    """Probe and observation records admit only exact canonical metadata."""
    with pytest.raises(BehaviorPolicyError, match="non-empty string"):
        _ = IdentityProbe(cast("str", object()), b"digest")
    with pytest.raises(BehaviorPolicyError, match="exact bytes"):
        _ = IdentityProbe(
            "identity",
            cast("bytes", cast("object", bytearray(b"digest"))),
        )
    with pytest.raises(BehaviorPolicyError, match="non-empty string"):
        _ = BugProbe("bug", cast("str", object()))
    with pytest.raises(BehaviorPolicyError, match="bool or None"):
        _ = CompatibilityObservation(
            "compat",
            cast("bool | None", cast("object", 1)),
        )
    with pytest.raises(BehaviorPolicyError, match="exact BugState"):
        _ = BugObservation("bug", cast("BugState", object()))


@pytest.mark.parametrize(
    "invalid", ["nul\x00identifier", "surrogate\ud800identifier"]
)
def test_behavior_identifiers_require_portable_unicode(invalid: str) -> None:
    """Direct behavior metadata never admits nonportable probe labels."""
    constructors = (
        lambda: IdentityProbe(invalid, b"digest"),
        lambda: CompatibilityProbe(invalid),
        lambda: BugProbe(invalid, "fix"),
        lambda: BugProbe("bug", invalid),
        lambda: IdentityObservation(invalid, b"digest"),
        lambda: CompatibilityObservation(invalid, compatible=True),
        lambda: BugObservation(invalid, BugState.PRESENT),
    )
    for build in constructors:
        with pytest.raises(BehaviorPolicyError, match="portable"):
            _ = build()


def test_behavior_profile_rejects_unsorted_ids_after_sort_hook_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late global sort hooks cannot authorize unordered probe metadata."""
    profile = _profile()
    unordered = (
        profile.identity[1],
        profile.identity[0],
        *profile.identity[2:],
    )

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "sorted", lambda values: list(values))
        with pytest.raises(BehaviorPolicyError, match="sorted by probe_id"):
            _ = BehaviorProfile(
                identity=unordered,
                compatibility=profile.compatibility,
                bugs=profile.bugs,
            )


@pytest.mark.parametrize("duplicate_kind", ["probe", "correction"])
def test_behavior_profile_rejects_duplicates_after_set_hook_swap(
    monkeypatch: pytest.MonkeyPatch,
    duplicate_kind: str,
) -> None:
    """Late set hooks cannot authorize duplicate identity or correction IDs."""
    profile = _profile()
    identity = profile.identity
    bugs = profile.bugs
    if duplicate_kind == "probe":
        identity = (identity[0], *identity)
        message = "globally unique"
    else:
        bugs = (*bugs, BugProbe("historical-bug-other", "fix-bug"))
        message = "correction identifiers must be unique"

    def construct_after_hook_swap() -> BehaviorProfile:
        with monkeypatch.context() as patch:
            patch.setattr(builtins, "set", lambda values: list(values))
            return BehaviorProfile(
                identity=identity,
                compatibility=profile.compatibility,
                bugs=bugs,
            )

    with pytest.raises(BehaviorPolicyError, match=message):
        _ = construct_after_hook_swap()


def test_behavior_containers_require_exact_records() -> None:
    """Profiles and observations reject mutable or foreign collections."""
    profile = _profile()
    observations = _observations()
    with pytest.raises(BehaviorPolicyError, match="immutable tuple"):
        _ = BehaviorProfile(
            identity=cast(
                "tuple[IdentityProbe, ...]",
                cast("object", list(profile.identity)),
            ),
            compatibility=profile.compatibility,
            bugs=profile.bugs,
        )
    with pytest.raises(BehaviorPolicyError, match="foreign probe"):
        _ = BehaviorProfile(
            identity=(cast("IdentityProbe", object()),),
            compatibility=profile.compatibility,
            bugs=profile.bugs,
        )
    with pytest.raises(BehaviorPolicyError, match="immutable tuple"):
        _ = BehaviorObservations(
            identity=cast(
                "tuple[IdentityObservation, ...]",
                cast("object", list(observations.identity)),
            ),
            compatibility=observations.compatibility,
            bugs=observations.bugs,
        )
    with pytest.raises(BehaviorPolicyError, match="foreign observation"):
        _ = BehaviorObservations(
            identity=(cast("IdentityObservation", object()),),
            compatibility=observations.compatibility,
            bugs=observations.bugs,
        )


def test_behavior_threshold_rejects_huge_integer_fractions() -> None:
    """Oversized integer thresholds fail through typed behavior policy."""
    huge_values: tuple[int, int] = (10**400, 10**5000)
    for huge in huge_values:
        for invalid in (huge, -huge):
            with pytest.raises(BehaviorPolicyError, match="finite fraction"):
                _ = evaluate_behavior(_profile(), _observations(), invalid)


def test_behavior_threshold_keeps_integral_endpoints() -> None:
    """Both valid native-int endpoints still participate in comparisons."""
    for admitted in (0, 1):
        evidence = require_behavior(_profile(), _observations(), admitted)
        assert evidence.admitted
        assert math.isclose(evidence.similarity, 1.0)


def test_behavior_evaluation_rejects_boolean_threshold_and_foreign_inputs() -> (
    None
):
    """Behavior authority fails typed before dereferencing untrusted inputs."""
    with pytest.raises(BehaviorPolicyError, match="finite numeric fraction"):
        _ = evaluate_behavior(
            _profile(), _observations(), minimum_similarity=True
        )
    with pytest.raises(BehaviorPolicyError, match="exact BehaviorProfile"):
        _ = evaluate_behavior(
            cast("BehaviorProfile", object()),
            _observations(),
            _MINIMUM_BEHAVIOR_SIMILARITY,
        )
    with pytest.raises(BehaviorPolicyError, match="exact BehaviorObservations"):
        _ = evaluate_behavior(
            _profile(),
            cast("BehaviorObservations", object()),
            _MINIMUM_BEHAVIOR_SIMILARITY,
        )


def test_behavior_rejects_late_type_spoofed_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged type verdict cannot admit mutable identity digests."""
    foreign = bytearray(b"digest")
    native_type = type
    rejected = False

    def forged_type(value: object) -> type:
        return bytes if value is foreign else native_type(value)

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "type", forged_type)
        try:
            _ = IdentityProbe(
                "identity", cast("bytes", cast("object", foreign))
            )
        except BehaviorPolicyError:
            rejected = True
    assert rejected, "late type hook admitted mutable behavior digest"


@pytest.mark.parametrize("record_kind", [_FOREIGN_PROBE, "observation"])
def test_behavior_rejects_late_any_spoofed_record(
    monkeypatch: pytest.MonkeyPatch,
    record_kind: str,
) -> None:
    """A false native-any verdict cannot admit foreign evidence records."""

    class ForeignIdentity:
        probe_id: str = "identity"
        expected_digest: bytes = b"digest"
        digest: bytes = b"digest"

    def forged_any(values: object) -> bool:
        del values
        return False

    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "any", forged_any)
        try:
            if record_kind == _FOREIGN_PROBE:
                _ = BehaviorProfile(
                    identity=(
                        cast(
                            "IdentityProbe", cast("object", ForeignIdentity())
                        ),
                    ),
                    compatibility=(),
                    bugs=(),
                )
            else:
                _ = BehaviorObservations(
                    identity=(
                        cast(
                            "IdentityObservation",
                            cast("object", ForeignIdentity()),
                        ),
                    ),
                    compatibility=(),
                    bugs=(),
                )
        except BehaviorPolicyError:
            rejected = True
    assert rejected, "late any hook admitted foreign behavior record"


def test_behavior_rejects_late_len_similarity_inflation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged identity count cannot inflate the admission score."""
    profile = _profile()
    observations = _observations(identity_matches=3)
    native_len = len
    rejected = False

    def forged_len(value: object) -> int:
        if value is profile.identity:
            return 3
        return native_len(cast("tuple[object, ...]", value))

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "len", forged_len)
        try:
            _ = require_behavior(
                profile, observations, _MINIMUM_BEHAVIOR_SIMILARITY
            )
        except BehaviorAdmissionError:
            rejected = True
    assert rejected, "late len hook inflated identity similarity"


def test_behavior_rejection_preserves_type_under_late_tuple_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late tuple replacement cannot erase a compatibility rejection."""
    profile = _profile()
    observations = _observations(compatible=False)
    native_tuple = tuple
    caught = None
    expected_reason = "compatibility probe failed: can-transform"

    def forged_tuple(values: object = ()) -> tuple[object, ...]:
        recorded = native_tuple(cast("list[object]", values))
        if recorded == (expected_reason,):
            return ()
        return recorded

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "tuple", forged_tuple)
        try:
            _ = require_behavior(
                profile, observations, _MINIMUM_BEHAVIOR_SIMILARITY
            )
        except BehaviorAdmissionError as error:
            caught = str(error)
    assert caught == expected_reason


def test_behavior_rejects_late_string_type_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A string-compatible foreign identifier cannot masquerade as str."""
    rejected = False
    foreign = cast("str", cast("object", UserString("identity")))
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "str", UserString)
        try:
            _ = IdentityProbe(foreign, b"digest")
        except BehaviorPolicyError:
            rejected = True
    assert rejected, "late str hook admitted a foreign identifier"


def test_behavior_rejects_late_bytes_type_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replacing the bytes class cannot admit a mutable digest."""
    foreign = cast("bytes", cast("object", bytearray(b"digest")))
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "bytes", bytearray)
        try:
            _ = IdentityProbe("identity", foreign)
        except BehaviorPolicyError:
            rejected = True
    assert rejected, "late bytes hook admitted mutable evidence"


def test_behavior_rejects_late_bool_type_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replacing bool with int cannot admit integer compatibility evidence."""
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "bool", int)
        try:
            _ = CompatibilityObservation(
                "compat", cast("bool | None", cast("object", 1))
            )
        except BehaviorPolicyError:
            rejected = True
    assert rejected, "late bool hook admitted integer compatibility state"


def test_behavior_keeps_integral_threshold_under_late_int_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replacing int cannot invalidate a genuine native integral threshold."""
    profile = _profile()
    observations = _observations()
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "int", bool)
        evidence = require_behavior(profile, observations, 1)
    assert evidence.admitted


def test_behavior_preserves_threshold_under_late_float_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged float conversion cannot lower an integral threshold."""
    profile = _profile()
    observations = _observations(identity_matches=3)
    expected_reason = "insufficient behavior identity"
    rejected = False

    def forged_float(value: object) -> float:
        del value
        return 0.0

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "float", forged_float)
        try:
            _ = require_behavior(profile, observations, 1)
        except BehaviorAdmissionError as error:
            rejected = expected_reason in str(error)
    assert rejected, "late float hook lowered minimum similarity"


def test_behavior_rejects_late_list_erasure_of_unavailable_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A replaced list constructor cannot erase unavailable probe evidence."""
    profile = _profile()
    observations = _observations()
    unavailable = replace(
        observations,
        identity=(
            IdentityObservation("identity-0", None),
            *observations.identity[1:],
        ),
    )
    rejected = False

    def forged_list(values: object) -> list[object]:
        del values
        return []

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "list", forged_list)
        try:
            _ = require_behavior(profile, unavailable, 0.0)
        except BehaviorAdmissionError:
            rejected = True
    assert rejected, "late list hook erased unavailable identity rejection"


@pytest.mark.parametrize(
    "record_type",
    [IdentityObservation, CompatibilityObservation, BugObservation],
)
@pytest.mark.parametrize("revalidate", [False, True])
def test_behavior_native_observation_routing_ignores_late_isinstance(
    monkeypatch: pytest.MonkeyPatch,
    record_type: type[object],
    revalidate: bool,
) -> None:
    """Admitted probe records must not depend on mutable consumer type hooks."""
    profile = _profile()
    observations = _observations()
    evidence = require_behavior(profile, observations, 1.0)
    native_isinstance = isinstance
    calls = 0

    def forged_isinstance(value: object, expected: type[object]) -> bool:
        nonlocal calls
        if expected is record_type:
            calls += 1
            return False
        return native_isinstance(value, expected)

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "isinstance", forged_isinstance)
        if revalidate:
            checked = replace(evidence)
        else:
            checked = require_behavior(profile, observations, 1.0)
    assert checked.admitted
    assert checked.corrections_to_apply == ("fix-bug",)
    assert calls == 0, "late isinstance hook received admitted probe evidence"


@pytest.mark.parametrize("hook", ["getattribute", "slot"])
@pytest.mark.parametrize(
    "field",
    [
        "similarity",
        "matched_identity_probes",
        "total_identity_probes",
        "corrections_to_apply",
        "corrections_to_skip",
        "profile",
        "observations",
        "minimum_similarity",
    ],
)
def test_behavior_evidence_constructor_rejects_late_field_forgery(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    hook: str,
) -> None:
    """Direct evidence cannot validate forged class-level scores or inputs."""
    evidence = evaluate_behavior(_profile(), _observations(), 0.8)
    valid: dict[str, object] = {
        "similarity": evidence.similarity,
        "matched_identity_probes": evidence.matched_identity_probes,
        "total_identity_probes": evidence.total_identity_probes,
        "corrections_to_apply": evidence.corrections_to_apply,
        "corrections_to_skip": evidence.corrections_to_skip,
        "profile": evidence.profile,
        "observations": evidence.observations,
        "minimum_similarity": evidence.minimum_similarity,
    }
    invalid: dict[str, object] = {
        "similarity": 0.0,
        "matched_identity_probes": 0,
        "total_identity_probes": 0,
        "corrections_to_apply": (),
        "corrections_to_skip": ("fix-bug",),
        "profile": object(),
        "observations": object(),
        "minimum_similarity": True,
    }
    values = valid | {field: invalid[field]}
    calls = 0

    def forged_attribute(value: BehaviorEvidence, name: str) -> object:
        nonlocal calls
        if name == field:
            calls += 1
            return valid[field]
        return cast("object", object.__getattribute__(value, name))

    def forged_property(value: BehaviorEvidence) -> object:
        return forged_attribute(value, field)

    with monkeypatch.context() as patch:
        if hook == "slot":
            original_slot = cast(
                "MemberDescriptorType", BehaviorEvidence.__dict__[field]
            )

            def store(value: BehaviorEvidence, stored: object) -> None:
                original_slot.__set__(value, stored)

            patch.setattr(
                BehaviorEvidence, field, property(forged_property, store)
            )
        else:
            patch.setattr(
                BehaviorEvidence, "__getattribute__", forged_attribute
            )
        with pytest.raises(BehaviorPolicyError):
            _ = BehaviorEvidence(
                similarity=cast("float", values["similarity"]),
                matched_identity_probes=cast(
                    "int", values["matched_identity_probes"]
                ),
                total_identity_probes=cast(
                    "int", values["total_identity_probes"]
                ),
                corrections_to_apply=cast(
                    "tuple[str, ...]", values["corrections_to_apply"]
                ),
                corrections_to_skip=cast(
                    "tuple[str, ...]", values["corrections_to_skip"]
                ),
                reasons=evidence.reasons,
                profile=cast("BehaviorProfile", values["profile"]),
                observations=cast(
                    "BehaviorObservations", values["observations"]
                ),
                minimum_similarity=cast("float", values["minimum_similarity"]),
            )
    assert calls == 0, "late behavior getter participated in admission"


@pytest.mark.parametrize("hook", ["getattribute", "slot"])
@pytest.mark.parametrize("field", ["identity", "compatibility", "bugs"])
@pytest.mark.parametrize("kind", ["profile", "observations"])
def test_behavior_collection_constructor_ignores_late_getters(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    field: str,
    hook: str,
) -> None:
    """Behavior collections must validate the original tuple slots."""
    model = _profile() if kind == "profile" else _observations()
    owner = BehaviorProfile if kind == "profile" else BehaviorObservations
    expected = cast("object", object.__getattribute__(model, field))
    other = {
        name: getattr(model, name)
        for name in ("identity", "compatibility", "bugs")
    }
    other[field] = []
    calls = 0

    def forged_attribute(value: object, name: str) -> object:
        nonlocal calls
        if name == field:
            calls += 1
            return expected
        return cast("object", object.__getattribute__(value, name))

    def forged_property(value: object) -> object:
        return forged_attribute(value, field)

    with monkeypatch.context() as patch:
        if hook == "slot":
            original_slot = cast("MemberDescriptorType", owner.__dict__[field])

            def store(value: object, stored: object) -> None:
                original_slot.__set__(value, stored)

            patch.setattr(owner, field, property(forged_property, store))
        else:
            patch.setattr(owner, "__getattribute__", forged_attribute)
        with pytest.raises(BehaviorPolicyError):
            if kind == "profile":
                _ = BehaviorProfile(
                    cast("tuple[IdentityProbe, ...]", other["identity"]),
                    cast(
                        "tuple[CompatibilityProbe, ...]",
                        other["compatibility"],
                    ),
                    cast("tuple[BugProbe, ...]", other["bugs"]),
                )
            else:
                _ = BehaviorObservations(
                    cast("tuple[IdentityObservation, ...]", other["identity"]),
                    cast(
                        "tuple[CompatibilityObservation, ...]",
                        other["compatibility"],
                    ),
                    cast("tuple[BugObservation, ...]", other["bugs"]),
                )
    assert calls == 0, "class getter participated in collection admission"


@pytest.mark.parametrize("hook", ["getattribute", "slot"])
@pytest.mark.parametrize("field", ["identity", "compatibility", "bugs"])
@pytest.mark.parametrize("kind", ["profile", "observations"])
def test_behavior_evaluation_ignores_late_collection_getter(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    field: str,
    hook: str,
) -> None:
    """An admitted profile or observation set cannot change via class hooks."""
    profile = _profile()
    observations = _observations()
    expected = require_behavior(profile, observations, 0.8)
    owner = BehaviorProfile if kind == "profile" else BehaviorObservations
    calls = 0

    def forged_attribute(value: object, name: str) -> object:
        nonlocal calls
        if name == field:
            calls += 1
            return ()
        return cast("object", object.__getattribute__(value, name))

    with monkeypatch.context() as patch:
        if hook == "slot":
            def forged_property(value: object) -> object:
                return forged_attribute(value, field)

            patch.setattr(owner, field, property(forged_property))
        else:
            patch.setattr(owner, "__getattribute__", forged_attribute)
        actual = require_behavior(profile, observations, 0.8)
    assert actual == expected
    assert calls == 0, "late collection getter participated in behavior verdict"


@pytest.mark.parametrize("hook", ["getattribute", "slot"])
@pytest.mark.parametrize("kind", ["identity", "compatibility", "bug"])
@pytest.mark.parametrize("phase", ["constructor", "evaluation"])
def test_behavior_observation_outcomes_ignore_late_getters(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    hook: str,
    phase: str,
) -> None:
    """Probe results must use stored outcomes, not late class getters."""
    profile = _profile()
    valid = _observations()
    forged: object
    bad: object
    field: str
    if kind == "identity":
        owner = IdentityObservation
        field = "digest"
        forged = bytes([0])
        bad = b"" if phase == "constructor" else b"different"
        args: tuple[object, ...] = ("identity-0", bad)
    elif kind == "compatibility":
        owner = CompatibilityObservation
        field = "compatible"
        forged = True
        bad = 1 if phase == "constructor" else False
        args = ("can-transform", bad)
    else:
        owner = BugObservation
        field = "state"
        forged = BugState.PRESENT
        bad = "present" if phase == "constructor" else BugState.UNKNOWN
        args = ("historical-bug", bad)

    invalid = valid
    if phase == "evaluation":
        if kind == "identity":
            invalid = replace(
                valid,
                identity=(IdentityObservation("identity-0", b"different"),)
                + valid.identity[1:],
            )
        elif kind == "compatibility":
            invalid = replace(
                valid,
                compatibility=(
                    CompatibilityObservation("can-transform", False),
                ),
            )
        else:
            invalid = replace(
                valid,
                bugs=(BugObservation("historical-bug", BugState.UNKNOWN),),
            )
    calls = 0

    def forged_attribute(value: object, name: str) -> object:
        nonlocal calls
        if name == field:
            calls += 1
            return forged
        return cast("object", object.__getattribute__(value, name))

    def forged_property(value: object) -> object:
        return forged_attribute(value, field)

    with monkeypatch.context() as patch:
        if hook == "slot":
            original_slot = cast("MemberDescriptorType", owner.__dict__[field])

            def store(value: object, stored: object) -> None:
                original_slot.__set__(value, stored)

            patch.setattr(owner, field, property(forged_property, store))
        else:
            patch.setattr(owner, "__getattribute__", forged_attribute)
        if phase == "constructor":
            with pytest.raises(BehaviorPolicyError):
                if kind == "identity":
                    _ = IdentityObservation(
                        cast("str", args[0]), cast("bytes | None", args[1])
                    )
                elif kind == "compatibility":
                    _ = CompatibilityObservation(
                        cast("str", args[0]), cast("bool | None", args[1])
                    )
                else:
                    _ = BugObservation(
                        cast("str", args[0]), cast("BugState", args[1])
                    )
        else:
            with pytest.raises(BehaviorAdmissionError):
                _ = require_behavior(profile, invalid, 1.0)
    assert calls == 0, "late outcome getter participated in behavior evidence"
