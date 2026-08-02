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
#   - Synthetic semantic-placement tests using the DOOM C mapped identity.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Synthetic semantic-placement tests using the DOOM C mapped identity."""

from algorithms.diff.semantic import SemanticPlacementError
from algorithms.diff.semantic import apply_semantic_plan
from algorithms.diff.semantic import build_semantic_plan
from algorithms.doom.generator.doom import mapped_c_identity
import pytest

_SOURCE = b"int f(void){return 1;}\n"
_TARGET = b"int f(void){return 2;}\n"
_FORMATTED_CANDIDATE = b"int  f ( void ) {\n/* keep me */ return 1 ;\n}\n"
_FORMATTED_EXPECTED = b"int  f ( void ) {\n/* keep me */ return 2 ;\n}\n"
_HELPER = b"int helper(void){return 7;}\n"


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_c_semantic_replacement_preserves_presentation() -> None:
    """Apply one semantic fix without replacing candidate presentation bytes."""
    plan = build_semantic_plan(
        mapped_c_identity(_SOURCE),
        mapped_c_identity(_TARGET),
    )

    output = apply_semantic_plan(
        mapped_c_identity(_FORMATTED_CANDIDATE),
        plan,
        mapped_c_identity,
    )

    _expect(
        output == _FORMATTED_EXPECTED, "C semantic patch rewrote presentation"
    )


def test_c_semantic_replacement_preserves_unrelated_upstream_function() -> None:
    """Keep semantic additions outside the local edit context unchanged."""
    plan = build_semantic_plan(
        mapped_c_identity(_SOURCE),
        mapped_c_identity(_TARGET),
    )
    candidate = _HELPER + _FORMATTED_CANDIDATE

    output = apply_semantic_plan(
        mapped_c_identity(candidate), plan, mapped_c_identity
    )

    _expect(
        output == _HELPER + _FORMATTED_EXPECTED,
        "unrelated candidate function was discarded",
    )


def test_c_format_only_oracle_difference_does_not_rewrite_candidate() -> None:
    """Treat presentation as identity-neutral for placement edits."""
    source = b"int f(void){return 1;}\n"
    target = b"int  f ( void ) { /* oracle */ return 1 ; }\n"
    candidate = b"int\tf(void) { /* upstream */ return 1; }\n"
    plan = build_semantic_plan(
        mapped_c_identity(source), mapped_c_identity(target)
    )

    output = apply_semantic_plan(
        mapped_c_identity(candidate), plan, mapped_c_identity
    )

    _expect(not plan.edits, "format-only C difference authored semantic edits")
    _expect(output == candidate, "format-only C plan rewrote candidate bytes")


def test_c_changed_edit_region_fails_until_bug_routing_skips_it() -> None:
    """Fail closed when candidate no longer has the source state."""
    plan = build_semantic_plan(
        mapped_c_identity(_SOURCE),
        mapped_c_identity(_TARGET),
    )
    already_changed = b"int f(void){return 3;}\n"

    with pytest.raises(SemanticPlacementError, match="missing or ambiguous"):
        _ = apply_semantic_plan(
            mapped_c_identity(already_changed),
            plan,
            mapped_c_identity,
        )
