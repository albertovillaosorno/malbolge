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
#   - Validate the closed repository-owned Malbolge target-profile document.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Validate the closed repository-owned Malbolge target-profile document."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Never
from typing import cast

if __package__ in {None, ""}:
    composition_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(composition_root))

from scripts.repository_root import repository_root

ROOT = repository_root(Path(__file__))
DEFAULT_PROFILE = ROOT / "malbolge.json"
RUST_PROJECTION = (
    ROOT / "src/runtime/virtual-machine/domain" / "profile_generated.rs"
)
FINGERPRINT_MANIFEST = (
    ROOT
    / "src/interoperability/profile-compatibility/contract"
    / "profile-fingerprints.json"
)
HISTORICAL_PROFILE = "malbolge-1998"
CURRENT_PROFILE_ID = "malbolge-2026"
CURRENT_VERSION = "2026"
SCHEMA_VERSION = 2
CURRENT_KIND = "current"
HISTORICAL_KIND = "historical-conformance"
VERSIONED_KIND = "versioned"
MEMORY_MODEL = "single-word-modular"
GUEST_ORDER = "sequential"
INPUT_INSTRUCTION = "/"
OUTPUT_INSTRUCTION = "<"
IO_INSTRUCTIONS = frozenset({INPUT_INSTRUCTION, OUTPUT_INSTRUCTION})
OUTPUT_MODULUS = 256
HISTORICAL_WORDS = 59_049
HISTORICAL_EOF = 59_048
TERNARY_RADIX = 3
HISTORICAL_VERSION = "1998"
PROFILE_CANONICALIZATION = "malbolge-profile-v1"
PROFILE_FINGERPRINT_PREFIX = f"{PROFILE_CANONICALIZATION}:sha256:"
CUSTOM_PROFILE_SCHEMA_VERSION = 1
ASCII_SPACE = 0x20
ASCII_TILDE = 0x7E
BACKSLASH = "\\"
DOUBLE_QUOTE = '"'

TOP_LEVEL_KEYS = frozenset({"current_profile", "profiles", "schema_version"})
PROFILE_KEYS = frozenset({"kind", "memory", "semantics", "version", "word"})
PROFILE_DEFINITION_KEYS = frozenset({"memory", "semantics", "version", "word"})
CUSTOM_PROFILE_KEYS = frozenset({
    "profile",
    "profile_id",
    "schema_version",
    "target_schema_version",
})
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
SEMANTIC_CORE_KEYS = SEMANTIC_KEYS - {
    "eof_word",
    "input_instruction",
    "output_instruction",
}

type JsonScalar = bool | int | float | str | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class TargetProfileGeometry:
    """Canonical execution geometry for one target-profile identity."""

    eof_word: int
    input_instruction: str
    memory_words: int
    output_instruction: str
    profile_id: str
    word_modulus: int
    word_trits: int


class ProfileValidationError(ValueError):
    """Deterministic target-profile schema or invariant failure."""


class ProfileFingerprintMismatchError(ProfileValidationError):
    """External profile fingerprint disagrees with artifact identity."""

    def __init__(self, profile_id: str, expected: str, observed: str) -> None:
        """Build one stable mismatch diagnostic."""
        message = " ".join((
            "MALBOLGE-PROFILE-ID-001",
            f"profile={profile_id}",
            f"expected={expected}",
            f"observed={observed}",
        ))
        super().__init__(message)


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
    if type(text) is not str:
        _fail("target-profile JSON text must use the exact string type")
    try:
        parsed = cast(
            "object",
            json.loads(text, object_pairs_hook=_reject_duplicate_pairs),
        )
    except json.JSONDecodeError as error:
        _fail(f"invalid JSON: {error}")
    return _expect_mapping(parsed, "target profile document")


def _validated_profile_path(value: object) -> Path:
    if not isinstance(value, Path):
        _fail("target-profile path must use pathlib Path")
    return value


def load_document(path: Path) -> JsonObject:
    """Load one target-profile document from disk.

    Returns:
        The parsed top-level target-profile object.

    """
    admitted_path = _validated_profile_path(path)
    try:
        text = admitted_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as error:
        _fail(f"invalid target-profile UTF-8: {error}")
    return loads_document(text)


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
    input_instruction = _expect_string(
        semantics["input_instruction"],
        f"{context}.input_instruction",
    )
    output_instruction = _expect_string(
        semantics["output_instruction"],
        f"{context}.output_instruction",
    )
    if frozenset((input_instruction, output_instruction)) != IO_INSTRUCTIONS:
        _fail(
            f"{context} I/O instructions must assign '<' and '/' exactly once"
        )
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
    if eof_word != modulus - 1:
        _fail(f"{context}.semantics.eof_word must equal word maximum")
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


def _validate_historical_semantics(profile: JsonObject) -> None:
    semantics = _expect_mapping(profile["semantics"], "historical semantics")
    if semantics["eof_word"] != HISTORICAL_EOF:
        _fail(f"{HISTORICAL_PROFILE} EOF word changed")
    if semantics["input_instruction"] != INPUT_INSTRUCTION:
        _fail(f"{HISTORICAL_PROFILE} input instruction changed")
    if semantics["output_instruction"] != OUTPUT_INSTRUCTION:
        _fail(f"{HISTORICAL_PROFILE} output instruction changed")


def _validate_historical(profile: JsonObject) -> None:
    if profile["kind"] != HISTORICAL_KIND:
        _fail(f"{HISTORICAL_PROFILE} must be {HISTORICAL_KIND}")
    if profile["version"] != HISTORICAL_VERSION:
        _fail(f"{HISTORICAL_PROFILE} version must be {HISTORICAL_VERSION}")
    _validate_historical_storage(profile)
    _validate_historical_semantics(profile)


def _semantic_core(profile: JsonObject) -> JsonObject:
    semantics = _expect_mapping(profile["semantics"], "profile semantics")
    return {key: semantics[key] for key in SEMANTIC_CORE_KEYS}


def _current_profile_ids(
    validated: dict[str, JsonObject],
) -> list[str]:
    return sorted(
        profile_id
        for profile_id, profile in validated.items()
        if profile["kind"] == CURRENT_KIND
    )


def _validate_semantic_cores(
    validated: dict[str, JsonObject],
    historical: JsonObject,
) -> None:
    historical_core = _semantic_core(historical)
    for profile_id, profile in validated.items():
        if (
            profile_id != HISTORICAL_PROFILE
            and _semantic_core(profile) != historical_core
        ):
            _fail(f"schema v2 profile {profile_id} changed semantic core")


def _validate_current_profile(
    current_profile: str,
    current: JsonObject,
) -> None:
    if current_profile != CURRENT_PROFILE_ID:
        _fail(f"current_profile must be {CURRENT_PROFILE_ID}")
    if current["kind"] != CURRENT_KIND:
        _fail(f"current_profile must have kind={CURRENT_KIND}")
    if current["version"] != CURRENT_VERSION:
        _fail(f"{CURRENT_PROFILE_ID} version must be {CURRENT_VERSION}")


def _validate_profile_identities(
    current_profile: str,
    validated: dict[str, JsonObject],
) -> None:
    historical = validated[HISTORICAL_PROFILE]
    _validate_historical(historical)
    _validate_current_profile(current_profile, validated[current_profile])
    if current_profile == HISTORICAL_PROFILE:
        _fail(f"current profile identity must differ from {HISTORICAL_PROFILE}")
    if _current_profile_ids(validated) != [current_profile]:
        _fail("exactly current_profile must have kind=current")
    _validate_semantic_cores(validated, historical)


def validate_document(document: JsonObject) -> None:
    """Validate the closed schema and cross-profile governance invariants."""
    admitted = _expect_mapping(document, "target profile document")
    _expect_exact_keys(admitted, TOP_LEVEL_KEYS, "target profile document")
    schema_version = _expect_int(admitted["schema_version"], "schema_version")
    if schema_version != SCHEMA_VERSION:
        _fail(f"unsupported schema_version: {schema_version}")
    current_profile = _expect_string(
        admitted["current_profile"],
        "current_profile",
    )
    profiles = _expect_mapping(admitted["profiles"], "profiles")
    if HISTORICAL_PROFILE not in profiles:
        _fail(f"{HISTORICAL_PROFILE} profile is required")
    if current_profile not in profiles:
        _fail("current_profile does not exist")

    validated: dict[str, JsonObject] = {}
    for profile_id, profile_value in profiles.items():
        validated[profile_id] = _validate_profile(profile_id, profile_value)

    _validate_profile_identities(current_profile, validated)


def _validated_profile_id(value: object) -> str:
    if type(value) is not str or not value:
        _fail("profile identity must be a non-empty string")
    return value


def profile_geometry(
    document: JsonObject,
    profile_id: str,
) -> TargetProfileGeometry:
    """Return validated canonical geometry for one named profile.

    Returns:
        Exact word, memory, EOF, and I/O geometry owned by the profile.

    """
    validate_document(document)
    admitted_id = _validated_profile_id(profile_id)
    profiles = _expect_mapping(document["profiles"], "profiles")
    profile = _expect_mapping(
        profiles.get(admitted_id),
        f"profiles.{admitted_id}",
    )
    word = _expect_mapping(profile["word"], f"profiles.{profile_id}.word")
    memory = _expect_mapping(
        profile["memory"],
        f"profiles.{profile_id}.memory",
    )
    semantics = _expect_mapping(
        profile["semantics"],
        f"profiles.{profile_id}.semantics",
    )
    return TargetProfileGeometry(
        eof_word=_expect_int(
            semantics["eof_word"],
            f"profiles.{profile_id}.semantics.eof_word",
        ),
        input_instruction=_expect_string(
            semantics["input_instruction"],
            f"profiles.{profile_id}.semantics.input_instruction",
        ),
        memory_words=_expect_int(
            memory["words"],
            f"profiles.{profile_id}.memory.words",
        ),
        output_instruction=_expect_string(
            semantics["output_instruction"],
            f"profiles.{profile_id}.semantics.output_instruction",
        ),
        profile_id=admitted_id,
        word_modulus=_expect_int(
            word["modulus"],
            f"profiles.{profile_id}.word.modulus",
        ),
        word_trits=_expect_int(
            word["trits"],
            f"profiles.{profile_id}.word.trits",
        ),
    )


def current_profile_geometry(
    document: JsonObject | None = None,
) -> TargetProfileGeometry:
    """Return geometry for the selected annual profile.

    Returns:
        Exact canonical geometry selected by `current_profile`.

    """
    canonical = load_document(DEFAULT_PROFILE) if document is None else document
    admitted = _expect_mapping(canonical, "target profile document")
    current_profile = _expect_string(
        admitted["current_profile"],
        "current_profile",
    )
    return profile_geometry(admitted, current_profile)


def _profile_definition(profile: JsonObject, context: str) -> JsonObject:
    return {
        "memory": _expect_mapping(profile["memory"], f"{context}.memory"),
        "semantics": _expect_mapping(
            profile["semantics"],
            f"{context}.semantics",
        ),
        "version": _expect_string(profile["version"], f"{context}.version"),
        "word": _expect_mapping(profile["word"], f"{context}.word"),
    }


def _profile_identity_material(
    profile_id: str,
    profile: JsonObject,
    target_schema_version: int,
) -> JsonObject:
    return {
        "canonicalization": PROFILE_CANONICALIZATION,
        "profile": _profile_definition(profile, f"profiles.{profile_id}"),
        "profile_id": profile_id,
        "target_schema_version": target_schema_version,
    }


def _canonical_identity_bytes(
    profile_id: str,
    profile: JsonObject,
    target_schema_version: int,
) -> bytes:
    material = _profile_identity_material(
        profile_id,
        profile,
        target_schema_version,
    )
    encoded = json.dumps(
        material,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return encoded.encode("ascii")


def _fingerprint_identity(
    profile_id: str,
    profile: JsonObject,
    target_schema_version: int,
) -> str:
    digest = hashlib.sha256(
        _canonical_identity_bytes(
            profile_id,
            profile,
            target_schema_version,
        ),
        usedforsecurity=True,
    ).hexdigest()
    return PROFILE_FINGERPRINT_PREFIX + digest


def _validate_profile_definition(
    profile_id: str,
    value: JsonValue,
) -> JsonObject:
    context = f"profile {profile_id}"
    profile = _expect_mapping(value, context)
    _expect_exact_keys(profile, PROFILE_DEFINITION_KEYS, context)
    _ = _expect_string(profile["version"], f"{context}.version")
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
    if eof_word != modulus - 1:
        _fail(f"{context}.semantics.eof_word must equal word maximum")
    return profile


def _validate_custom_target_schema(
    document: JsonObject,
    canonical_document: JsonObject,
) -> None:
    schema_version = _expect_int(document["schema_version"], "schema_version")
    if schema_version != CUSTOM_PROFILE_SCHEMA_VERSION:
        _fail(f"unsupported custom profile schema_version: {schema_version}")
    target_schema = _expect_int(
        document["target_schema_version"],
        "target_schema_version",
    )
    canonical_schema = _expect_int(
        canonical_document["schema_version"],
        "canonical schema_version",
    )
    if target_schema != canonical_schema:
        _fail("custom profile target_schema_version does not match authority")


def _validate_custom_against_canonical(
    profile_id: str,
    profile: JsonObject,
    canonical_profiles: JsonObject,
) -> None:
    historical = _expect_mapping(
        canonical_profiles[HISTORICAL_PROFILE],
        f"profiles.{HISTORICAL_PROFILE}",
    )
    if _semantic_core(profile) != _semantic_core(historical):
        _fail("custom profile changed the defining Malbolge semantic core")
    if profile_id not in canonical_profiles:
        return
    canonical_profile = _expect_mapping(
        canonical_profiles[profile_id],
        f"profiles.{profile_id}",
    )
    canonical_definition = _profile_definition(
        canonical_profile,
        f"profiles.{profile_id}",
    )
    if profile != canonical_definition:
        _fail(f"canonical profile identity redefined: {profile_id}")


def validate_custom_profile_document(
    document: JsonObject,
    canonical_document: JsonObject,
) -> tuple[str, JsonObject]:
    """Validate one external custom-profile identity document.

    Returns:
        The exact profile ID and validated profile definition.

    """
    validate_document(canonical_document)
    admitted = _expect_mapping(document, "custom profile document")
    _expect_exact_keys(admitted, CUSTOM_PROFILE_KEYS, "custom profile document")
    _validate_custom_target_schema(admitted, canonical_document)
    profile_id = _expect_string(admitted["profile_id"], "profile_id")
    profile = _validate_profile_definition(profile_id, admitted["profile"])
    canonical_profiles = _expect_mapping(
        canonical_document["profiles"],
        "canonical profiles",
    )
    _validate_custom_against_canonical(
        profile_id,
        profile,
        canonical_profiles,
    )
    return profile_id, profile


def custom_profile_fingerprint(
    document: JsonObject,
    canonical_document: JsonObject,
) -> str:
    """Return one validated external profile's canonical fingerprint.

    Returns:
        The same fingerprint a canonical registry entry would receive.

    """
    admitted = _expect_mapping(document, "custom profile document")
    profile_id, profile = validate_custom_profile_document(
        admitted,
        canonical_document,
    )
    target_schema = _expect_int(
        admitted["target_schema_version"],
        "target_schema_version",
    )
    return _fingerprint_identity(profile_id, profile, target_schema)


def verify_custom_profile_fingerprint(
    document: JsonObject,
    canonical_document: JsonObject,
    expected: str,
) -> str:
    """Verify external profile identity against an artifact fingerprint.

    Returns:
        The observed canonical fingerprint when it matches `expected`.

    Raises:
        ProfileFingerprintMismatchError: When canonical identity differs.

    """
    profile_id, _ = validate_custom_profile_document(
        document,
        canonical_document,
    )
    observed = custom_profile_fingerprint(document, canonical_document)
    if observed != expected:
        raise ProfileFingerprintMismatchError(profile_id, expected, observed)
    return observed


def canonical_profile_bytes(document: JsonObject, profile_id: str) -> bytes:
    """Return canonical identity bytes for one validated registry profile.

    Registry lifecycle metadata such as `kind` is intentionally excluded so a
    published profile fingerprint remains stable when `current` later becomes
    `versioned`.

    Returns:
        Compact sorted ASCII JSON bytes for the immutable profile identity.

    """
    validate_document(document)
    admitted_id = _validated_profile_id(profile_id)
    profiles = _expect_mapping(document["profiles"], "profiles")
    if admitted_id not in profiles:
        _fail(f"unknown profile identity: {admitted_id}")
    profile = _expect_mapping(
        profiles[admitted_id], f"profiles.{admitted_id}"
    )
    schema_version = _expect_int(document["schema_version"], "schema_version")
    return _canonical_identity_bytes(admitted_id, profile, schema_version)


def profile_fingerprint(document: JsonObject, profile_id: str) -> str:
    """Return the self-describing SHA-256 fingerprint for one profile.

    Returns:
        `malbolge-profile-v1:sha256:<hex>` over canonical profile bytes.

    """
    validate_document(document)
    admitted_id = _validated_profile_id(profile_id)
    profiles = _expect_mapping(document["profiles"], "profiles")
    if admitted_id not in profiles:
        _fail(f"unknown profile identity: {admitted_id}")
    profile = _expect_mapping(
        profiles[admitted_id], f"profiles.{admitted_id}"
    )
    schema_version = _expect_int(document["schema_version"], "schema_version")
    return _fingerprint_identity(admitted_id, profile, schema_version)


def render_profile_fingerprint_manifest(document: JsonObject) -> str:
    """Render the checked-in canonical-profile fingerprint manifest.

    Returns:
        Deterministic pretty JSON with one fingerprint per canonical profile.

    """
    validate_document(document)
    profiles = _expect_mapping(document["profiles"], "profiles")
    fingerprints: JsonObject = {}
    for profile_id in sorted(profiles):
        fingerprints[profile_id] = profile_fingerprint(document, profile_id)
    payload: JsonObject = {
        "canonicalization": PROFILE_CANONICALIZATION,
        "profiles": fingerprints,
        "schema_version": 1,
        "target_schema_version": SCHEMA_VERSION,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _rust_string(value: str, context: str) -> str:
    escaped: list[str] = []
    for character in value:
        codepoint = ord(character)
        if character == BACKSLASH:
            escaped.append("\\\\")
        elif character == DOUBLE_QUOTE:
            escaped.append('\\"')
        elif ASCII_SPACE <= codepoint <= ASCII_TILDE:
            escaped.append(character)
        else:
            _fail(f"{context} must use printable ASCII for Rust projection")
    return '"' + "".join(escaped) + '"'


def _rust_integer(value: JsonValue, context: str) -> str:
    return f"{_expect_int(value, context):_}"


def _rust_byte(value: JsonValue, context: str) -> str:
    instruction = _expect_string(value, context)
    if instruction not in IO_INSTRUCTIONS:
        _fail(f"{context} is not a supported I/O instruction")
    return f"b'{instruction}'"


def _rust_profile_kind(kind: str) -> str:
    variants = {
        CURRENT_KIND: "ProfileKind::Current",
        HISTORICAL_KIND: "ProfileKind::HistoricalConformance",
        VERSIONED_KIND: "ProfileKind::Versioned",
    }
    return variants[kind]


def _rust_fingerprint_lines(fingerprint: str) -> list[str]:
    if not fingerprint.startswith(PROFILE_FINGERPRINT_PREFIX):
        _fail("profile fingerprint uses unexpected canonicalization")
    digest = fingerprint.removeprefix(PROFILE_FINGERPRINT_PREFIX)
    prefix_literal = _rust_string(
        PROFILE_FINGERPRINT_PREFIX,
        "fingerprint prefix",
    )
    digest_literal = _rust_string(digest, "fingerprint digest")
    return [
        "    fingerprint: concat!(",
        f"        {prefix_literal},",
        f"        {digest_literal},",
        "    ),",
    ]


def _profile_projection_lines(
    index: int,
    profile_id: str,
    profile: JsonObject,
    *,
    fingerprint: str,
) -> list[str]:
    word = _expect_mapping(profile["word"], f"profiles.{profile_id}.word")
    memory = _expect_mapping(
        profile["memory"],
        f"profiles.{profile_id}.memory",
    )
    semantics = _expect_mapping(
        profile["semantics"],
        f"profiles.{profile_id}.semantics",
    )
    kind = _expect_string(profile["kind"], f"profiles.{profile_id}.kind")
    version = _expect_string(
        profile["version"],
        f"profiles.{profile_id}.version",
    )
    declaration = (
        f"pub(super) const PROFILE_{index}: ProfileDescriptor = "
        "ProfileDescriptor {"
    )
    input_instruction = _rust_byte(
        semantics["input_instruction"],
        "input instruction",
    )
    output_instruction = _rust_byte(
        semantics["output_instruction"],
        "output instruction",
    )
    return [
        declaration,
        f"    eof_word: {_rust_integer(semantics["eof_word"], "eof_word")},",
        *_rust_fingerprint_lines(fingerprint),
        f"    id: {_rust_string(profile_id, "profile id")},",
        f"    input_instruction: {input_instruction},",
        f"    kind: {_rust_profile_kind(kind)},",
        f"    memory_words: {_rust_integer(memory["words"], "memory.words")},",
        f"    output_instruction: {output_instruction},",
        f"    version: {_rust_string(version, "profile version")},",
        f"    word_modulus: {_rust_integer(word["modulus"], "word.modulus")},",
        f"    word_trits: {_rust_integer(word["trits"], "word.trits")},",
        "};",
    ]


def render_rust_projection(document: JsonObject) -> str:
    """Render the checked-in Rust projection of canonical target profiles.

    Returns:
        Deterministic Rust source derived only from validated `malbolge.json`.

    """
    validate_document(document)
    current_profile = _expect_string(
        document["current_profile"],
        "current_profile",
    )
    profiles = _expect_mapping(document["profiles"], "profiles")
    profile_ids = sorted(profiles)
    current_index = profile_ids.index(current_profile)
    historical_index = profile_ids.index(HISTORICAL_PROFILE)
    lines = [
        "// Copyright:",
        "//   - Copyright (c) 2026 Alberto Villa Osorno.",
        "// SPDX-License-Identifier:",
        "//   - MIT",
        "// Confidential:",
        "//   - false",
        "// License-File:",
        "//   - LICENSE-MIT",
        "//",
        "// Boundary-Contract:",
        "// - Owns:",
        "//   - Generated Rust projection of canonical Malbolge profiles.",
        "// - Must-Not:",
        "//   - Become an independent profile authority or contain hand edits.",
        "// - Allows:",
        "//   - Inputs: validated repository-root `malbolge.json` only.",
        "//   - Outputs: immutable descriptors for the safe Rust runtime.",
        "//   - Side effects: none after deterministic generation.",
        "// - Split-When:",
        "//   - Split when another language needs an independent projection.",
        "// - Merge-When:",
        "//   - Merge when runtime consumes canonical JSON directly.",
        "// - Summary:",
        "//   - Generated canonical target-profile descriptors for Rust.",
        "// - Description:",
        "//   - Keeps runtime identity synchronized with `malbolge.json`.",
        "// - Usage:",
        "//   - Regenerate through the target-profile validator helpers.",
        "// - Defaults:",
        "//   - Any renderer drift fails the test suite.",
        "//",
        "",
        "//! Generated canonical target-profile descriptors for Rust.",
        "",
        "use super::{ProfileDescriptor, ProfileKind};",
        "",
    ]
    lines.extend([
        (
            "pub(super) const CURRENT_PROFILE: &ProfileDescriptor = "
            f"&PROFILE_{current_index};"
        ),
        (
            "pub(super) const HISTORICAL_PROFILE: &ProfileDescriptor = "
            f"&PROFILE_{historical_index};"
        ),
        "",
    ])
    for index, profile_id in enumerate(profile_ids):
        profile = _expect_mapping(
            profiles[profile_id], f"profiles.{profile_id}"
        )
        lines.extend(
            _profile_projection_lines(
                index,
                profile_id,
                profile,
                fingerprint=profile_fingerprint(document, profile_id),
            )
        )
        lines.append("")
    references = ", ".join(
        f"&PROFILE_{index}" for index in range(len(profile_ids))
    )
    descriptor_type = (
        f"pub(super) const PROFILE_DESCRIPTORS: "
        f"[&ProfileDescriptor; {len(profile_ids)}] ="
    )
    lines.extend([
        descriptor_type,
        f"    [{references}];",
        "",
    ])
    return "\n".join(lines)


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
