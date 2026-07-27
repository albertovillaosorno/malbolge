# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Regression tests for equation-to-executable correspondence traceability."""

from __future__ import annotations

from scripts.validate import math_correspondence as validator

EXPECTED_EQUATIONS = 21


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
