# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Regression tests for the closed Malbolge target-profile schema."""

from __future__ import annotations

from pathlib import Path

from scripts.validate import target_profile as validator

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "malbolge.json"


def _canonical_text() -> str:
    return PROFILE_PATH.read_text(encoding="utf-8-sig")


def _expect_invalid(text: str) -> None:
    try:
        validator.validate_text(text)
    except validator.ProfileValidationError:
        return
    message = "profile validation unexpectedly succeeded"
    raise AssertionError(message)


def test_canonical_profile_is_valid() -> None:
    """The committed canonical profile satisfies schema v1."""
    validator.validate_text(_canonical_text())


def test_current_profile_identity_is_distinct() -> None:
    """Current-language identity never aliases historical conformance."""
    document = validator.load_document(PROFILE_PATH)
    assert document["current_profile"] != validator.HISTORICAL_PROFILE


def test_duplicate_json_keys_fail_closed() -> None:
    """Duplicate object keys are rejected before semantic validation."""
    _expect_invalid('{"schema_version":1,"schema_version":1}')


def test_historical_word_model_cannot_drift() -> None:
    """The frozen 1998 ten-trit word domain cannot be enlarged in place."""
    changed = _canonical_text().replace('"trits": 10', '"trits": 11', 1)
    _expect_invalid(changed)


def test_current_semantic_core_cannot_drift_in_schema_v1() -> None:
    """Schema v1 does not admit a parallel current guest profile."""
    marker = '"guest_order": "sequential"'
    before, separator, current = _canonical_text().rpartition(marker)
    assert separator == marker
    changed = before + '"guest_order": "parallel"' + current
    _expect_invalid(changed)


def test_single_word_memory_matches_word_modulus() -> None:
    """Single-word modular memory cannot escape its address word domain."""
    marker = '"words": 59049'
    before, separator, current = _canonical_text().rpartition(marker)
    assert separator == marker
    _expect_invalid(before + '"words": 59048' + current)


def test_unknown_schema_key_fails_closed() -> None:
    """Unknown top-level policy is rejected instead of ignored."""
    changed = _canonical_text().replace(
        '"schema_version": 1,',
        '"schema_version": 1, "implicit_fallback": true,',
        1,
    )
    _expect_invalid(changed)
