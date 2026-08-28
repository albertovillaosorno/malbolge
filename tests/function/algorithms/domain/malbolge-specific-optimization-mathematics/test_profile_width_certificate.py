# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Functional regression coverage for the research width-certificate module.
# - Must-Not:
#   - Treat research acceptance as trusted runtime profile selection.
# - Allows:
#   - Inputs: explicit finite systems and candidate-width result maps.
#   - Outputs: fail-closed checker and selector assertions.
#   - Side effects: none.
# - Split-When:
#   - A trusted certificate verifier gains an independent product owner.
# - Merge-When:
#   - Another test owns this exact research API boundary.
# - Summary:
#   - Functional tests for experimental profile-width certificate checking.
# - Description:
#   - Exercises public research APIs independently from correspondence tests.
# - Usage:
#   - Runs with the malbolge-specific optimization research test surface.
# - Defaults:
#   - Incomplete or invalid evidence returns canonical width or false.
#

"""Functional tests for the experimental profile-width certificate module."""

from __future__ import annotations

from algorithms.profile_width.certificate import CANONICAL_WIDTH
from algorithms.profile_width.certificate import FiniteSystem
from algorithms.profile_width.certificate import certificate_valid
from algorithms.profile_width.certificate import minimum_certified_width


def test_certificate_fails_closed_when_state_surface_is_missing() -> None:
    """A relation cannot authorize a state missing from the declared surface."""
    wide = FiniteSystem(
        initial={"input": "w0"},
        observation={"w0": (0,)},
        successor={"w0": None},
    )
    narrow = FiniteSystem(
        initial={"input": "n0"},
        observation={},
        successor={"n0": None},
    )
    relation = frozenset({("w0", "n0")})
    assert not certificate_valid(wide, narrow, relation)


def test_selector_fails_closed_on_missing_or_invalid_result() -> None:
    """Incomplete or non-boolean certificate results retain width fourteen."""
    missing = {10: True, 11: True, 12: True}
    assert minimum_certified_width(missing) == CANONICAL_WIDTH

    invalid: dict[int, bool] = {10: True, 11: True, 12: True, 13: True}
    invalid[12] = 1  # pyright: ignore[reportArgumentType] - invalid fixture.
    assert minimum_certified_width(invalid) == CANONICAL_WIDTH
