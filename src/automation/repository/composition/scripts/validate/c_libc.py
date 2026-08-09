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
#   - Validation and typed access for the canonical guest C library contract.
# - Must-Not:
#   - Infer availability from host libc, installed headers, or ambient
#     libraries.
# - Allows:
#   - Inputs: the tracked malbolge-libc-v1 JSON authority and guest-C ABI.
#   - Outputs: closed routine/header availability and deterministic failures.
#   - Side effects: reading tracked authority files only.
# - Split-When:
#   - Split when another guest-library schema version gains its own lifecycle.
# - Merge-When:
#   - Merge when another validator owns this exact guest libc authority.
# - Summary:
#   - Validates the closed malbolge-libc-v1 contract.
# - Description:
#   - Keeps guest library support independent from host standard libraries.
# - Usage:
#   - Imported by source preflight and executable contract regression tests.
# - Defaults:
#   - Duplicate, unknown, drifted, or ABI-incompatible data fails closed.
#

"""Validate the closed malbolge-libc-v1 guest C library authority."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Never
from typing import cast

if __package__ in {None, ""}:
    composition_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(composition_root))

from scripts.repository_root import repository_root
from scripts.validate import c_abi

ROOT = repository_root(Path(__file__))
DEFAULT_LIBC = ROOT / "docs/technical/specification/c-libc-v1.json"
INCLUDE_ROOT = ROOT / "src/runtime/guest-c-library/contract/include"
LIBC_ID = "malbolge-libc-v1"
SCHEMA_VERSION = 1

COMPILER_HEADERS = (
    "float.h",
    "iso646.h",
    "limits.h",
    "stdalign.h",
    "stdarg.h",
    "stdbool.h",
    "stdckdint.h",
    "stddef.h",
    "stdint.h",
    "stdnoreturn.h",
)
GUEST_HEADERS = ("math.h", "stdio.h", "stdlib.h", "string.h")
UNAVAILABLE_HEADERS = ("stdbit.h",)
AVAILABLE_ROUTINES = (
    "ceil",
    "fabs",
    "floor",
    "memcmp",
    "memcpy",
    "memmove",
    "memset",
    "strcat",
    "strcmp",
    "strcpy",
    "strlen",
    "strncpy",
    "trunc",
)
UNAVAILABLE_ROUTINES = (
    "atan2",
    "calloc",
    "cos",
    "free",
    "getchar",
    "malloc",
    "putchar",
    "realloc",
    "sin",
    "snprintf",
    "sqrt",
    "vsnprintf",
)
FORBIDDEN_ROUTINES = (
    "fopen",
    "getenv",
    "setlocale",
    "signal",
    "system",
    "time",
    "tmpfile",
)
TOP_LEVEL_KEYS = frozenset({
    "abi_id",
    "available_routines",
    "compiler_headers",
    "contracted_unavailable",
    "failure",
    "forbidden_routines",
    "guest_headers",
    "libc_id",
    "schema_version",
    "target_profile",
    "unavailable_headers",
})
AVAILABLE_KEYS = frozenset({
    "header",
    "implementation",
    "name",
    "semantics",
    "signature",
})
UNAVAILABLE_KEYS = frozenset({
    "header",
    "name",
    "owner",
    "semantics",
    "signature",
})
FORBIDDEN_KEYS = frozenset({"name", "reason"})
FAILURE_KEYS = frozenset({
    "forbidden_routine",
    "host_library_fallback",
    "unavailable_routine",
    "unknown_guest_header",
})


type JsonScalar = bool | int | float | str | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class CLibcProjection:
    """Typed availability data consumed by guest-C source validation."""

    abi_id: str
    available_routines: frozenset[str]
    forbidden_routines: frozenset[str]
    guest_headers: tuple[str, ...]
    include_root: Path
    libc_id: str
    target_profile: str
    unavailable_routines: frozenset[str]


class CLibcValidationError(ValueError):
    """Canonical guest libc schema or invariant failure."""


def _fail(message: str) -> Never:
    raise CLibcValidationError(message)


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> JsonObject:
    result: JsonObject = {}
    for key, value in pairs:
        if key in result:
            _fail(f"duplicate JSON key: {key}")
        result[key] = cast("JsonValue", value)
    return result


def _mapping(value: object, context: str) -> JsonObject:
    if not isinstance(value, dict):
        _fail(f"{context} must be an object")
    return cast("JsonObject", value)


def _expect_keys(
    value: JsonObject,
    expected: frozenset[str],
    context: str,
) -> None:
    observed = frozenset(value)
    if observed != expected:
        missing = sorted(expected - observed)
        unknown = sorted(observed - expected)
        _fail(f"{context} keys differ: missing={missing}, unknown={unknown}")


def _string_list(value: JsonValue, context: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        _fail(f"{context} must be an array")
    raw = cast("list[JsonValue]", value)
    if not all(isinstance(item, str) and item for item in raw):
        _fail(f"{context} entries must be nonempty strings")
    result = tuple(cast("list[str]", raw))
    if len(result) != len(set(result)):
        _fail(f"{context} must not contain duplicates")
    return result


def _routine_name(
    raw: JsonValue,
    *,
    keys: frozenset[str],
    context: str,
) -> str:
    item = _mapping(raw, context)
    _expect_keys(item, keys, context)
    name = item.get("name")
    if not isinstance(name, str) or not name:
        _fail(f"{context}.name must be a nonempty string")
    invalid = [
        key
        for key, field in item.items()
        if not isinstance(field, str) or not field
    ]
    if invalid:
        _fail(f"{context}.{invalid[0]} must be a nonempty string")
    return name


def _routine_names(
    value: JsonValue,
    *,
    keys: frozenset[str],
    context: str,
) -> tuple[str, ...]:
    if not isinstance(value, list):
        _fail(f"{context} must be an array")
    names = tuple(
        _routine_name(
            raw,
            keys=keys,
            context=f"{context}[{index}]",
        )
        for index, raw in enumerate(cast("list[JsonValue]", value))
    )
    if len(names) != len(set(names)):
        _fail(f"{context} names must not contain duplicates")
    return names


def loads_document(text: str) -> JsonObject:
    """Parse guest libc JSON while rejecting duplicate object keys.

    Returns:
        Parsed top-level contract object.

    """
    try:
        parsed = cast(
            "object",
            json.loads(text, object_pairs_hook=_reject_duplicate_pairs),
        )
    except json.JSONDecodeError as error:
        _fail(f"invalid JSON: {error}")
    return _mapping(parsed, "C libc document")


def load_document(path: Path = DEFAULT_LIBC) -> JsonObject:
    """Load a UTF-8 guest libc contract from disk.

    Returns:
        Parsed top-level contract object.

    """
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as error:
        _fail(f"invalid C libc UTF-8: {error}")
    except OSError as error:
        _fail(f"failed to read C libc document {path}: {error}")
    return loads_document(text)


def _expect_literal(actual: JsonValue, expected: object, context: str) -> None:
    if type(actual) is not type(expected) or actual != expected:
        _fail(f"{context} must be {expected!r}")


def _expect_sequence(
    observed: tuple[str, ...],
    expected: tuple[str, ...],
    context: str,
) -> None:
    if observed != expected:
        _fail(f"{context} must match malbolge-libc-v1")


def _expect_name_set(
    observed: tuple[str, ...],
    expected: tuple[str, ...],
    context: str,
) -> None:
    if frozenset(observed) != frozenset(expected):
        _fail(f"{context} names must match malbolge-libc-v1")


def validate_document(document: JsonObject) -> CLibcProjection:
    """Validate the closed contract and return its source-admission projection.

    Returns:
        Immutable availability sets for source validation.

    """
    _expect_keys(document, TOP_LEVEL_KEYS, "C libc document")
    abi = c_abi.canonical_projection()
    _expect_literal(
        document["schema_version"],
        SCHEMA_VERSION,
        "schema_version",
    )
    _expect_literal(document["libc_id"], LIBC_ID, "libc_id")
    _expect_literal(document["abi_id"], abi.abi_id, "abi_id")
    _expect_literal(
        document["target_profile"],
        abi.target_profile,
        "target_profile",
    )
    compiler_headers = _string_list(
        document["compiler_headers"],
        "compiler_headers",
    )
    guest_headers = _string_list(document["guest_headers"], "guest_headers")
    unavailable_headers = _string_list(
        document["unavailable_headers"],
        "unavailable_headers",
    )
    _expect_sequence(compiler_headers, COMPILER_HEADERS, "compiler_headers")
    _expect_sequence(guest_headers, GUEST_HEADERS, "guest_headers")
    _expect_sequence(
        unavailable_headers,
        UNAVAILABLE_HEADERS,
        "unavailable_headers",
    )
    available = _routine_names(
        document["available_routines"],
        keys=AVAILABLE_KEYS,
        context="available_routines",
    )
    unavailable = _routine_names(
        document["contracted_unavailable"],
        keys=UNAVAILABLE_KEYS,
        context="contracted_unavailable",
    )
    forbidden = _routine_names(
        document["forbidden_routines"],
        keys=FORBIDDEN_KEYS,
        context="forbidden_routines",
    )
    _expect_name_set(available, AVAILABLE_ROUTINES, "available_routines")
    _expect_name_set(
        unavailable,
        UNAVAILABLE_ROUTINES,
        "contracted_unavailable",
    )
    _expect_name_set(forbidden, FORBIDDEN_ROUTINES, "forbidden_routines")
    failure = _mapping(document["failure"], "failure")
    _expect_keys(failure, FAILURE_KEYS, "failure")
    _expect_literal(
        failure["unavailable_routine"],
        "source-diagnostic-before-lowering",
        "failure.unavailable_routine",
    )
    _expect_literal(
        failure["forbidden_routine"],
        "source-diagnostic-before-lowering",
        "failure.forbidden_routine",
    )
    _expect_literal(
        failure["unknown_guest_header"],
        "not-admitted-by-libc-contract",
        "failure.unknown_guest_header",
    )
    _expect_literal(
        failure["host_library_fallback"],
        "forbidden",
        "failure.host_library_fallback",
    )
    return CLibcProjection(
        abi_id=abi.abi_id,
        available_routines=frozenset(available),
        forbidden_routines=frozenset(forbidden),
        guest_headers=guest_headers,
        include_root=INCLUDE_ROOT,
        libc_id=LIBC_ID,
        target_profile=abi.target_profile,
        unavailable_routines=frozenset(unavailable),
    )


def canonical_projection(path: Path = DEFAULT_LIBC) -> CLibcProjection:
    """Load and validate the canonical guest libc authority.

    Returns:
        Immutable canonical guest libc projection.

    """
    return validate_document(load_document(path))


def main() -> int:
    """Validate the canonical guest libc authority.

    Returns:
        Zero for a valid contract, otherwise one with a deterministic error.

    """
    try:
        projection = canonical_projection()
    except (c_abi.CAbiValidationError, CLibcValidationError) as error:
        _ = sys.stderr.write(f"error: {error}\n")
        return 1
    message = "C libc contract ready: " + projection.libc_id
    message += f" ({projection.abi_id})"
    _ = sys.stdout.write(message + chr(10))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
