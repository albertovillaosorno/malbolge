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
#   - Regression tests for equation-to-executable correspondence traceability.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Regression tests for equation-to-executable correspondence traceability."""

from __future__ import annotations

import pytest
from scripts.validate import math_correspondence as validator

EXPECTED_EQUATIONS = 95
REPOSITORY_RELATIVE_ERROR = "must be repository-relative"


def _expect_invalid(text: str) -> None:
    try:
        _ = validator.validate_text(text)
    except validator.CorrespondenceError:
        return
    message = "invalid mathematical correspondence unexpectedly succeeded"
    raise AssertionError(message)


def test_repository_correspondence_graph_is_closed() -> None:
    """Every normative equation label maps to existing executable evidence."""
    entries = validator.validate_repository()
    assert len(entries) == EXPECTED_EQUATIONS


def test_drive_relative_equation_path_is_not_repository_relative() -> None:
    """Windows drive-relative syntax cannot escape equation-source authority."""
    text = validator.MANIFEST.read_text(encoding="utf-8")
    marker = next(
        line for line in text.splitlines() if line.startswith("tex = ")
    )
    changed = text.replace(marker, 'tex = "D:escape"', 1)
    with pytest.raises(
        validator.CorrespondenceError,
        match=REPOSITORY_RELATIVE_ERROR,
    ):
        _ = validator.validate_text(changed)


def test_unknown_manifest_label_leaves_equation_unmapped() -> None:
    """A renamed manifest label cannot orphan the normative equation."""
    text = validator.MANIFEST.read_text(encoding="utf-8")
    changed = text.replace(
        'label = "eq:classic-crazy"',
        'label = "eq:classic-crazy-missing"',
        1,
    )
    _expect_invalid(changed)


def test_unknown_test_function_fails_closed() -> None:
    """A stale test-function reference is a correspondence failure."""
    text = validator.MANIFEST.read_text(encoding="utf-8")
    changed = text.replace(
        "crazy_chunks_match_scalar_definition_in_both_positions",
        "test_function_that_does_not_exist",
        1,
    )
    _expect_invalid(changed)


def test_duplicate_toml_key_fails_closed() -> None:
    """Duplicate manifest authority cannot be silently overwritten."""
    text = validator.MANIFEST.read_text(encoding="utf-8")
    changed = text.replace(
        "schema_version = 1",
        "schema_version = 1\nschema_version = 1",
        1,
    )
    _expect_invalid(changed)


def test_research_mirror_test_surface_is_admitted() -> None:
    """Algorithm-owned research tests are valid correspondence evidence."""
    path = "algorithms/example-research/tests/evidence.rs"
    assert validator.evidence_path_allowed(path)


def test_non_test_algorithm_surface_is_rejected() -> None:
    """Research implementation files cannot masquerade as test evidence."""
    path = "algorithms/example-research/state_graph.rs"
    assert not validator.evidence_path_allowed(path)
