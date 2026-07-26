# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Validate the closed repository-owned Malbolge target-profile document."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Never
from typing import cast

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE = ROOT / "malbolge.json"
HISTORICAL_PROFILE = "malbolge-1998"
SCHEMA_VERSION = 1
CURRENT_KIND = "current"
HISTORICAL_KIND = "historical-conformance"
VERSIONED_KIND = "versioned"
MEMORY_MODEL = "single-word-modular"
GUEST_ORDER = "sequential"
INPUT_INSTRUCTION = "<"
OUTPUT_INSTRUCTION = "/"
OUTPUT_MODULUS = 256
HISTORICAL_WORDS = 59_049
HISTORICAL_EOF = 59_048
TERNARY_RADIX = 3
HISTORICAL_VERSION = "1998"

TOP_LEVEL_KEYS = frozenset({"current_profile", "profiles", "schema_version"})
PROFILE_KEYS = frozenset({"kind", "memory", "semantics", "version", "word"})
WORD_KEYS = frozenset({"modulus", "radix", "trits"})
MEMORY_KEYS = frozenset({"model", "words"})
SEMANTIC_KEYS = frozenset({
    "crazy_operation",
    "deterministic",
    "eof_word",
    "guest_order",
    "input_instruction",
    "output_instruction",
    "output_modulus",
    "post_instruction_encryption",
    "rotate",
    "self_modification",
})

type JsonScalar = bool | int | float | str | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


class ProfileValidationError(ValueError):
    """Deterministic target-profile schema or invariant failure."""


def _fail(message: str) -> Never:
    raise ProfileValidationError(message)


def _expect_exact_keys(
    value: JsonObject,
    expected: frozenset[str],
    context: str,
) -> None:
    observed = frozenset(value)
    if observed != expected:
        missing = sorted(expected - observed)
        unknown = sorted(observed - expected)
        _fail(f"{context} keys differ: missing={missing}, unknown={unknown}")


def _expect_int(value: JsonValue, context: str) -> int:
    if type(value) is not int:
        _fail(f"{context} must be an integer")
    return value


def _expect_mapping(value: object, context: str) -> JsonObject:
    if not isinstance(value, dict):
        _fail(f"{context} must be an object")
    raw = cast("dict[object, object]", value)
    result: JsonObject = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            _fail(f"{context} contains a non-string key")
        result[key] = cast("JsonValue", item)
    return result


def _expect_string(value: JsonValue, context: str) -> str:
    if type(value) is not str or not value:
        _fail(f"{context} must be a non-empty string")
    return value


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> JsonObject:
    result: JsonObject = {}
    for key, value in pairs:
        if key in result:
            _fail(f"duplicate JSON key: {key}")
        result[key] = cast("JsonValue", value)
    return result


def loads_document(text: str) -> JsonObject:
    """Parse one profile document while rejecting duplicate object keys.

    Returns:
        The parsed top-level target-profile object.

    """
    try:
        parsed = cast(
            "object",
            json.loads(text, object_pairs_hook=_reject_duplicate_pairs),
        )
    except json.JSONDecodeError as error:
        _fail(f"invalid JSON: {error}")
    return _expect_mapping(parsed, "target profile document")


def load_document(path: Path) -> JsonObject:
    """Load one target-profile document from disk.

    Returns:
        The parsed top-level target-profile object.

    """
    return loads_document(path.read_text(encoding="utf-8-sig"))


def _validate_memory(value: JsonValue, context: str) -> int:
    memory = _expect_mapping(value, context)
    _expect_exact_keys(memory, MEMORY_KEYS, context)
    model = _expect_string(memory["model"], f"{context}.model")
    if model != MEMORY_MODEL:
        _fail(f"{context}.model is unsupported by schema v{SCHEMA_VERSION}")
    words = _expect_int(memory["words"], f"{context}.words")
    if words <= 0:
        _fail(f"{context}.words must be positive")
    return words


def _validate_semantic_flags(semantics: JsonObject, context: str) -> None:
    if semantics["guest_order"] != GUEST_ORDER:
        _fail(f"{context}.guest_order must be {GUEST_ORDER}")
    required_true = (
        "crazy_operation",
        "deterministic",
        "post_instruction_encryption",
        "rotate",
        "self_modification",
    )
    for key in required_true:
        if semantics[key] is not True:
            _fail(f"{context}.{key} must be true")


def _validate_semantic_io(semantics: JsonObject, context: str) -> None:
    if semantics["input_instruction"] != INPUT_INSTRUCTION:
        _fail(f"{context}.input_instruction must be {INPUT_INSTRUCTION}")
    if semantics["output_instruction"] != OUTPUT_INSTRUCTION:
        _fail(f"{context}.output_instruction must be {OUTPUT_INSTRUCTION}")
    eof_word = _expect_int(semantics["eof_word"], f"{context}.eof_word")
    if eof_word < 0:
        _fail(f"{context}.eof_word must be non-negative")
    output_modulus = _expect_int(
        semantics["output_modulus"],
        f"{context}.output_modulus",
    )
    if output_modulus != OUTPUT_MODULUS:
        _fail(f"{context}.output_modulus must be {OUTPUT_MODULUS}")


def _validate_semantics(value: JsonValue, context: str) -> JsonObject:
    semantics = _expect_mapping(value, context)
    _expect_exact_keys(semantics, SEMANTIC_KEYS, context)
    _validate_semantic_flags(semantics, context)
    _validate_semantic_io(semantics, context)
    return semantics


def _validate_word(value: JsonValue, context: str) -> int:
    word = _expect_mapping(value, context)
    _expect_exact_keys(word, WORD_KEYS, context)
    radix = _expect_int(word["radix"], f"{context}.radix")
    trits = _expect_int(word["trits"], f"{context}.trits")
    modulus = _expect_int(word["modulus"], f"{context}.modulus")
    if radix != TERNARY_RADIX:
        _fail(f"{context}.radix must be ternary")
    if trits <= 0:
        _fail(f"{context}.trits must be positive")
    if modulus != radix**trits:
        _fail(f"{context}.modulus must equal radix**trits")
    return modulus


def _validate_profile(profile_id: str, value: JsonValue) -> JsonObject:
    context = f"profiles.{profile_id}"
    profile = _expect_mapping(value, context)
    _expect_exact_keys(profile, PROFILE_KEYS, context)
    _ = _expect_string(profile["version"], f"{context}.version")
    kind = _expect_string(profile["kind"], f"{context}.kind")
    admitted_kinds = {CURRENT_KIND, HISTORICAL_KIND, VERSIONED_KIND}
    if kind not in admitted_kinds:
        _fail(f"{context}.kind is not admitted")
    modulus = _validate_word(profile["word"], f"{context}.word")
    words = _validate_memory(profile["memory"], f"{context}.memory")
    if words != modulus:
        _fail(f"{context}.memory.words must equal word modulus")
    semantics = _validate_semantics(
        profile["semantics"],
        f"{context}.semantics",
    )
    eof_word = _expect_int(
        semantics["eof_word"],
        f"{context}.semantics.eof_word",
    )
    if eof_word >= modulus:
        _fail(f"{context}.semantics.eof_word escapes word domain")
    return profile


def _validate_historical_storage(profile: JsonObject) -> None:
    historical_word: JsonObject = {
        "modulus": HISTORICAL_WORDS,
        "radix": TERNARY_RADIX,
        "trits": 10,
    }
    if profile["word"] != historical_word:
        _fail(f"{HISTORICAL_PROFILE} word model changed")
    historical_memory: JsonObject = {
        "model": MEMORY_MODEL,
        "words": HISTORICAL_WORDS,
    }
    if profile["memory"] != historical_memory:
        _fail(f"{HISTORICAL_PROFILE} memory model changed")


def _validate_historical(profile: JsonObject) -> None:
    if profile["kind"] != HISTORICAL_KIND:
        _fail(f"{HISTORICAL_PROFILE} must be {HISTORICAL_KIND}")
    if profile["version"] != HISTORICAL_VERSION:
        _fail(f"{HISTORICAL_PROFILE} version must be {HISTORICAL_VERSION}")
    _validate_historical_storage(profile)
    semantics = _expect_mapping(profile["semantics"], "historical semantics")
    if semantics["eof_word"] != HISTORICAL_EOF:
        _fail(f"{HISTORICAL_PROFILE} EOF word changed")


def _validate_profile_identities(
    current_profile: str,
    validated: dict[str, JsonObject],
) -> None:
    historical = validated[HISTORICAL_PROFILE]
    _validate_historical(historical)
    current = validated[current_profile]
    if current["kind"] != CURRENT_KIND:
        _fail(f"current_profile must have kind={CURRENT_KIND}")
    if current_profile == HISTORICAL_PROFILE:
        _fail(f"current profile identity must differ from {HISTORICAL_PROFILE}")
    if current["semantics"] != historical["semantics"]:
        _fail("schema v1 current profile changed historical semantic core")


def validate_document(document: JsonObject) -> None:
    """Validate the closed schema and cross-profile governance invariants."""
    _expect_exact_keys(document, TOP_LEVEL_KEYS, "target profile document")
    schema_version = _expect_int(document["schema_version"], "schema_version")
    if schema_version != SCHEMA_VERSION:
        _fail(f"unsupported schema_version: {schema_version}")
    current_profile = _expect_string(
        document["current_profile"],
        "current_profile",
    )
    profiles = _expect_mapping(document["profiles"], "profiles")
    if HISTORICAL_PROFILE not in profiles:
        _fail(f"{HISTORICAL_PROFILE} profile is required")
    if current_profile not in profiles:
        _fail("current_profile does not exist")

    validated: dict[str, JsonObject] = {}
    for profile_id, profile_value in profiles.items():
        validated[profile_id] = _validate_profile(profile_id, profile_value)

    _validate_profile_identities(current_profile, validated)


def validate_text(text: str) -> None:
    """Parse and validate one in-memory target-profile document."""
    validate_document(loads_document(text))


def _profile_argument(arguments: list[str]) -> Path:
    if not arguments:
        return DEFAULT_PROFILE
    if arguments in (["-h"], ["--help"]):
        _ = sys.stdout.write("usage: target_profile.py [PROFILE.json]\n")
        raise SystemExit(0)
    if len(arguments) != 1:
        _fail("expected zero or one target-profile path")
    return Path(arguments[0])


def main() -> int:
    """Validate one profile path and return a process exit status.

    Returns:
        Zero for a valid profile and one for a deterministic validation failure.

    """
    try:
        profile = _profile_argument(sys.argv[1:]).resolve()
        validate_document(load_document(profile))
    except (OSError, ProfileValidationError) as error:
        _ = sys.stderr.write(f"error: {error}\n")
        return 1
    _ = sys.stdout.write(f"target profile valid: {profile}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
