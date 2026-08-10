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
#   - Synthetic tests for generic behavior-probe admission semantics.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Synthetic tests for generic behavior-probe admission semantics."""

import math
from typing import cast

from algorithms.diff.behavior import BehaviorAdmissionError
from algorithms.diff.behavior import BehaviorEvidence
from algorithms.diff.behavior import BehaviorObservations
from algorithms.diff.behavior import BehaviorPolicyError
from algorithms.diff.behavior import BehaviorProfile
from algorithms.diff.behavior import BugObservation
from algorithms.diff.behavior import BugProbe
from algorithms.diff.behavior import BugState
from algorithms.diff.behavior import CompatibilityObservation
from algorithms.diff.behavior import CompatibilityProbe
from algorithms.diff.behavior import IdentityObservation
from algorithms.diff.behavior import IdentityProbe
from algorithms.diff.behavior import evaluate_behavior
from algorithms.diff.behavior import require_behavior
import pytest

_MINIMUM_BEHAVIOR_SIMILARITY = 0.80


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


def test_behavior_evidence_rejects_incoherent_direct_construction() -> None:
    """Aggregated evidence cannot forge impossible local invariants."""
    with pytest.raises(BehaviorPolicyError, match=r"similarity.*probe counts"):
        _ = BehaviorEvidence(0.5, 1, 1, (), (), ())
    with pytest.raises(BehaviorPolicyError, match="cannot exceed total"):
        _ = BehaviorEvidence(1.0, 2, 1, (), (), ())
    with pytest.raises(BehaviorPolicyError, match="disjoint"):
        _ = BehaviorEvidence(1.0, 1, 1, ("fix",), ("fix",), ())
    with pytest.raises(BehaviorPolicyError, match="immutable tuple"):
        _ = BehaviorEvidence(
            1.0,
            1,
            1,
            cast("tuple[str, ...]", cast("object", ["fix"])),
            (),
            (),
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
