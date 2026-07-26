# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Regression tests for the closed Malbolge target-profile schema."""

from __future__ import annotations

from pathlib import Path

from scripts.validate import target_profile as validator

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "malbolge.json"
CURRENT_PROFILE = "malbolge-2026.2"
CURRENT_TRITS = 14
CURRENT_WORDS = 4_782_969
CURRENT_EOF = CURRENT_WORDS - 1


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
    """The committed canonical profile satisfies schema v2."""
    validator.validate_text(_canonical_text())


def test_current_profile_identity_is_distinct() -> None:
    """Current-language identity never aliases historical conformance."""
    document = validator.load_document(PROFILE_PATH)
    assert document["current_profile"] != validator.HISTORICAL_PROFILE


def test_duplicate_json_keys_fail_closed() -> None:
    """Duplicate object keys are rejected before semantic validation."""
    _expect_invalid('{"schema_version":2,"schema_version":2}')


def test_historical_word_model_cannot_drift() -> None:
    """The frozen 1998 ten-trit word domain cannot be enlarged in place."""
    changed = _canonical_text().replace('"trits": 10', '"trits": 11', 1)
    _expect_invalid(changed)


def test_current_semantic_core_cannot_drift_in_schema_v2() -> None:
    """Schema v2 does not admit a parallel current guest profile."""
    marker = '"guest_order": "sequential"'
    before, separator, current = _canonical_text().rpartition(marker)
    assert separator == marker
    changed = before + '"guest_order": "parallel"' + current
    _expect_invalid(changed)


def test_single_word_memory_matches_word_modulus() -> None:
    """Single-word modular memory cannot escape its address word domain."""
    marker = '"words": 4782969'
    before, separator, current = _canonical_text().rpartition(marker)
    assert separator == marker
    _expect_invalid(before + '"words": 4782968' + current)


def test_unknown_schema_key_fails_closed() -> None:
    """Unknown top-level policy is rejected instead of ignored."""
    changed = _canonical_text().replace(
        '"schema_version": 2,',
        '"schema_version": 2, "implicit_fallback": true,',
        1,
    )
    _expect_invalid(changed)


def test_current_profile_is_fourteen_trit_scalable_geometry() -> None:
    """The current profile is the first selected scalable ternary geometry."""
    document = validator.load_document(PROFILE_PATH)
    profiles = document["profiles"]
    assert isinstance(profiles, dict)
    current_id = document["current_profile"]
    assert isinstance(current_id, str)
    assert current_id == CURRENT_PROFILE
    current = profiles[current_id]
    assert isinstance(current, dict)
    word = current["word"]
    memory = current["memory"]
    semantics = current["semantics"]
    assert isinstance(word, dict)
    assert isinstance(memory, dict)
    assert isinstance(semantics, dict)
    assert word["trits"] == CURRENT_TRITS
    assert word["modulus"] == CURRENT_WORDS
    assert memory["words"] == CURRENT_WORDS
    assert semantics["eof_word"] == CURRENT_EOF


def test_scaled_eof_must_track_word_maximum() -> None:
    """EOF remains the all-two-trit maximum word for every geometry."""
    changed = _canonical_text().replace(
        '"eof_word": 4782968',
        '"eof_word": 59048',
        1,
    )
    _expect_invalid(changed)


def test_only_selected_profile_has_current_kind() -> None:
    """Old profile identities cannot also claim to be the current default."""
    changed = _canonical_text().replace(
        '"kind": "versioned"',
        '"kind": "current"',
        1,
    )
    _expect_invalid(changed)


def test_rust_projection_matches_canonical_profile() -> None:
    """Checked-in Rust profile data is a byte-exact JSON projection."""
    document = validator.load_document(PROFILE_PATH)
    expected = validator.render_rust_projection(document)
    observed = validator.RUST_PROJECTION.read_text(encoding="utf-8")
    assert observed == expected


def test_fingerprint_manifest_matches_canonical_profile() -> None:
    """Checked-in fingerprints are a byte-exact canonical projection."""
    document = validator.load_document(PROFILE_PATH)
    expected = validator.render_profile_fingerprint_manifest(document)
    observed = validator.FINGERPRINT_MANIFEST.read_text(encoding="utf-8")
    assert observed == expected


def test_transition_and_historical_fingerprints_are_distinct() -> None:
    """Equal geometry does not collapse distinct published identities."""
    document = validator.load_document(PROFILE_PATH)
    historical = validator.profile_fingerprint(document, "malbolge-1998")
    transition = validator.profile_fingerprint(document, "malbolge-2026.1")
    assert historical != transition
