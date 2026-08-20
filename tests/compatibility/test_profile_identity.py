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
#   - Canonical and custom Malbolge target-profile identity tests.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Canonical and custom Malbolge target-profile identity tests."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.validate import target_profile as validator

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PATH = (
    ROOT
    / "src/interoperability/profile-compatibility/contract"
    / "custom-profile.example.json"
)
PROFILE_PATH = ROOT / "malbolge.json"
CURRENT_PROFILE = "malbolge-2026"
CUSTOM_PROFILE = "custom-14-example"
EXAMPLE_FINGERPRINT = (
    "malbolge-profile-v1:sha256:"
    "221015e0ac4cbde88444ad6d55c703a2e2cc96904bd65b81cb44e256aa1f3177"
)
MISMATCH_FINGERPRINT = "malbolge-profile-v1:sha256:" + ("0" * 64)
FIFTEEN_TRIT_WORDS = 14_348_907


def _clone(document: validator.JsonObject) -> validator.JsonObject:
    text = json.dumps(document, sort_keys=False)
    return validator.loads_document(text)


def _object(value: validator.JsonValue) -> validator.JsonObject:
    assert isinstance(value, dict)
    return value


def _string(value: validator.JsonValue) -> str:
    assert isinstance(value, str)
    return value


def _canonical() -> validator.JsonObject:
    return validator.load_document(PROFILE_PATH)


def _example() -> validator.JsonObject:
    return validator.load_document(EXAMPLE_PATH)


def _external_for_canonical(profile_id: str) -> validator.JsonObject:
    canonical = _canonical()
    profiles = _object(canonical["profiles"])
    profile = _object(profiles[profile_id])
    definition: validator.JsonObject = {
        "memory": _object(profile["memory"]),
        "semantics": _object(profile["semantics"]),
        "version": _string(profile["version"]),
        "word": _object(profile["word"]),
    }
    return {
        "profile": definition,
        "profile_id": profile_id,
        "schema_version": validator.CUSTOM_PROFILE_SCHEMA_VERSION,
        "target_schema_version": validator.SCHEMA_VERSION,
    }


def _expect_profile_invalid(document: validator.JsonObject) -> None:
    try:
        _ = validator.custom_profile_fingerprint(document, _canonical())
    except validator.ProfileValidationError:
        return
    message = "custom profile validation unexpectedly succeeded"
    raise AssertionError(message)


def _mismatch_message(document: validator.JsonObject) -> str | None:
    try:
        _ = validator.verify_custom_profile_fingerprint(
            document,
            _canonical(),
            MISMATCH_FINGERPRINT,
        )
    except validator.ProfileFingerprintMismatchError as error:
        return str(error)
    return None


def test_example_custom_profile_has_stable_fingerprint() -> None:
    """The versioned custom example locks canonicalization output."""
    observed = validator.custom_profile_fingerprint(_example(), _canonical())
    assert observed == EXAMPLE_FINGERPRINT


def test_canonical_profile_external_form_has_same_fingerprint() -> None:
    """External and registry forms bind to one immutable profile identity."""
    canonical = _canonical()
    external = _external_for_canonical(CURRENT_PROFILE)
    external_fingerprint = validator.custom_profile_fingerprint(
        external,
        canonical,
    )
    registry_fingerprint = validator.profile_fingerprint(
        canonical,
        CURRENT_PROFILE,
    )
    assert external_fingerprint == registry_fingerprint


def test_json_key_order_does_not_change_fingerprint() -> None:
    """Canonicalization ignores object insertion order and source whitespace."""
    document = _example()
    profile = _object(document["profile"])
    reordered_profile: validator.JsonObject = {
        key: profile[key] for key in reversed(tuple(profile))
    }
    reordered: validator.JsonObject = {
        key: document[key] for key in reversed(tuple(document))
    }
    reordered["profile"] = reordered_profile
    assert validator.custom_profile_fingerprint(
        reordered,
        _canonical(),
    ) == validator.custom_profile_fingerprint(document, _canonical())


def test_custom_profile_id_participates_in_identity() -> None:
    """Identical geometry under another published ID receives another hash."""
    original = _example()
    renamed = _clone(original)
    renamed["profile_id"] = "custom-14-renamed"
    assert validator.custom_profile_fingerprint(
        original,
        _canonical(),
    ) != validator.custom_profile_fingerprint(renamed, _canonical())


def test_custom_profile_cannot_change_semantic_core() -> None:
    """Custom geometry cannot turn sequential Malbolge into another language."""
    changed = _clone(_example())
    profile = _object(changed["profile"])
    semantics = _object(profile["semantics"])
    semantics["guest_order"] = "parallel"
    _expect_profile_invalid(changed)


def test_canonical_id_cannot_be_redefined_externally() -> None:
    """A canonical profile ID cannot be rebound to different geometry."""
    changed = _external_for_canonical(CURRENT_PROFILE)
    profile = _object(changed["profile"])
    word = _object(profile["word"])
    memory = _object(profile["memory"])
    semantics = _object(profile["semantics"])
    word["trits"] = 15
    word["modulus"] = FIFTEEN_TRIT_WORDS
    memory["words"] = FIFTEEN_TRIT_WORDS
    semantics["eof_word"] = FIFTEEN_TRIT_WORDS - 1
    _expect_profile_invalid(changed)


def test_artifact_fingerprint_mismatch_has_stable_diagnostic() -> None:
    """An external config mismatch is detected instead of reinterpreted."""
    expected = " ".join((
        "MALBOLGE-PROFILE-ID-001",
        f"profile={CUSTOM_PROFILE}",
        f"expected={MISMATCH_FINGERPRINT}",
        f"observed={EXAMPLE_FINGERPRINT}",
    ))
    assert _mismatch_message(_example()) == expected
