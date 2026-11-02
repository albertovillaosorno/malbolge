# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - Apache-2.0
# Confidential:
#   - false
# License-File:
#   - LICENSE
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

import json
import os
import sys
from dataclasses import dataclass
from math import isnan
from pathlib import Path
from stat import S_ISREG
from typing import Never, TextIO, cast

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
MAX_DOCUMENT_BYTES = 1024 * 1024
_NATIVE_JSON_LOADS = json.loads

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
    "cos",
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
    "sin",
    "sqrt",
    "trunc",
)
UNAVAILABLE_ROUTINES = (
    "atan2",
    "calloc",
    "free",
    "getchar",
    "malloc",
    "putchar",
    "realloc",
    "snprintf",
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
TOP_LEVEL_KEYS = frozenset(
    {
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
    }
)
AVAILABLE_KEYS = frozenset(
    {
        "header",
        "implementation",
        "name",
        "semantics",
        "signature",
    }
)
UNAVAILABLE_KEYS = frozenset(
    {
        "header",
        "name",
        "owner",
        "semantics",
        "signature",
    }
)
FORBIDDEN_KEYS = frozenset({"name", "reason"})
FAILURE_KEYS = frozenset(
    {
        "forbidden_routine",
        "host_library_fallback",
        "unavailable_routine",
        "unknown_guest_header",
    }
)


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
        key for key, field in item.items() if not isinstance(field, str) or not field
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


def _same_native_json(actual: object, source: object) -> bool:
    """Compare parser receipts to source without calling foreign equality."""
    kind = type(source)
    if type(actual) is not kind:
        return False
    if kind is dict:
        received = cast("dict[object, object]", actual)
        original = cast("dict[object, object]", source)
        # Check all key types before looking any key up: a str subclass with
        # colliding hash/equality can otherwise run foreign comparison code.
        if any(type(key) is not str for key in received):
            _fail("C libc JSON decoder provider returned a non-native string "
                  "key")
        return len(received) == len(original) and all(
            key in received and _same_native_json(received[key], value)
            for key, value in original.items()
        )
    if kind is list:
        received_items = cast("list[object]", actual)
        original_items = cast("list[object]", source)
        return len(received_items) == len(original_items) and all(
            _same_native_json(received_value, source_value)
            for received_value, source_value in zip(
                received_items, original_items, strict=True
            )
        )
    if kind is float and isnan(cast("float", source)):
        return isnan(cast("float", actual))
    return kind in (str, int, bool, float, type(None)) and actual == source


def loads_document(text: str) -> JsonObject:
    """Parse bounded guest libc JSON while rejecting duplicate object keys.

    Returns:
        Parsed top-level contract object.

    """
    if type(text) is not str:
        _fail("C libc JSON requires exact str text")
    if len(text) > MAX_DOCUMENT_BYTES:
        _fail("C libc JSON exceeds byte limit")
    try:
        if len(text.encode("utf-8")) > MAX_DOCUMENT_BYTES:
            _fail("C libc JSON exceeds byte limit")
    except UnicodeEncodeError as error:
        raise CLibcValidationError("C libc JSON requires strict UTF-8") from error
    try:
        parsed = cast(
            "object",
            json.loads(text, object_pairs_hook=_reject_duplicate_pairs),
        )
    except CLibcValidationError:
        raise
    except (ValueError, RecursionError) as error:
        raise CLibcValidationError("invalid C libc JSON") from error
    document = _mapping(parsed, "C libc document")
    # A substituted public decoder can yield native, schema-valid values that
    # do not occur in the source. Corroborate against the import-bound native
    # parser, retaining duplicate-key rejection and original syntax failures.
    if json.loads is not _NATIVE_JSON_LOADS:
        try:
            source = cast(
                "object",
                _NATIVE_JSON_LOADS(
                    text, object_pairs_hook=_reject_duplicate_pairs
                ),
            )
            if not _same_native_json(document, source):
                _fail("C libc JSON decoder provider differs from source")
        except CLibcValidationError:
            raise
        except (ValueError, RecursionError, TypeError, RuntimeError) as error:
            raise CLibcValidationError("invalid C libc JSON") from error
    return document


def _regular_identity(status: object) -> tuple[int, int, int, int, int]:
    if type(status) is not os.stat_result:
        _fail("C libc document requires native stat receipt")
    return (
        status.st_dev,
        status.st_ino,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )


def _verify_regular_snapshot(
    expected: os.stat_result,
    observed: os.stat_result,
) -> None:
    if type(expected) is not os.stat_result or type(observed) is not os.stat_result:
        _fail("C libc document requires native stat receipt")
    if (
        not S_ISREG(observed.st_mode)
        or observed.st_size > MAX_DOCUMENT_BYTES
        or _regular_identity(expected) != _regular_identity(observed)
    ):
        _fail("C libc document must be a stable regular file")


def _require_unredirected_path(path: Path, *, leaf: bool = False) -> None:
    """Inspect native link/junction verdicts without coercing foreign values."""
    for verdict in (path.is_symlink, path.is_junction):
        redirected = verdict()
        if type(redirected) is not bool:
            _fail("C libc document requires native redirect receipt")
        if redirected:
            if leaf:
                _fail("C libc document must be a regular non-redirected file")
            _fail("C libc document path must not redirect")


def _check_parent_paths(path: Path) -> None:
    for parent in path.parents:
        _require_unredirected_path(parent)


def _native_source_descriptor(value: object) -> int:
    """Admit only an owned native fd before wrapper or status access."""
    if type(value) is not int or value < 0:
        _fail("C libc document requires native descriptor")
    return value


def _read_regular_bytes(path: Path) -> bytes:
    # A Path subclass can redirect host filesystem methods or __fspath__.
    if type(path) is not type(Path()):
        _fail("C libc document requires an exact native Path")
    # Reject redirects and specials before opening. O_NOFOLLOW and O_NONBLOCK
    # also protect the leaf open against symlink races and writerless FIFOs.
    _check_parent_paths(path)
    status = path.lstat()
    if type(status) is not os.stat_result:
        _fail("C libc document requires native stat receipt")
    _require_unredirected_path(path, leaf=True)
    if not S_ISREG(status.st_mode):
        _fail("C libc document must be a regular non-redirected file")
    if status.st_size > MAX_DOCUMENT_BYTES:
        _fail("C libc document exceeds byte limit")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    descriptor = _native_source_descriptor(os.open(path, flags))
    try:
        stream = os.fdopen(descriptor, "rb")
    except BaseException:
        # The raw descriptor belongs to this reader until fdopen succeeds.
        try:
            os.close(descriptor)
        except (OSError, ValueError, RuntimeError, TypeError, AttributeError):
            pass
        raise
    with stream:
        opened_descriptor = _native_source_descriptor(stream.fileno())
        if opened_descriptor != descriptor:
            _fail("C libc document stream descriptor mismatch before read")
        opened = os.fstat(opened_descriptor)
        _verify_regular_snapshot(status, opened)
        data = stream.read(MAX_DOCUMENT_BYTES + 1)
        after_descriptor = _native_source_descriptor(stream.fileno())
        if after_descriptor != descriptor:
            _fail("C libc document stream descriptor mismatch after read")
        _verify_regular_snapshot(opened, os.fstat(after_descriptor))
        _check_parent_paths(path)
        _verify_regular_snapshot(opened, path.lstat())
        if (
            type(data) is not bytes
            or len(data) != opened.st_size
            or len(data) > MAX_DOCUMENT_BYTES
        ):
            _fail("C libc document changed during read or exceeds byte limit")
    return data


def load_document(path: Path = DEFAULT_LIBC) -> JsonObject:
    """Load a stable regular UTF-8 guest libc contract from disk.

    Returns:
        The parsed top-level contract object.

    """
    try:
        text = _read_regular_bytes(path).decode("utf-8-sig")
    except CLibcValidationError:
        raise
    except UnicodeDecodeError as error:
        detail = (
            str(error) if type(error) is UnicodeDecodeError else type(error).__name__
        )
        raise CLibcValidationError(f"invalid C libc UTF-8: {detail}") from error
    except (OSError, ValueError, RuntimeError, TypeError, AttributeError) as error:
        message = f"failed to read C libc document {path}"
        raise CLibcValidationError(message) from error
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


def _write_cli_record(stream: TextIO, message: str) -> bool:
    """Return whether exact native CLI text write and flush both completed."""
    try:
        written = stream.write(message)
        if type(written) is not int or written != len(message):
            return False
        return stream.flush() is None
    except (
        AttributeError,
        IndexError,
        OSError,
        OverflowError,
        RuntimeError,
        TypeError,
        ValueError,
    ):
        return False


def main() -> int:
    """Validate the canonical guest libc authority.

    Returns:
        Zero for a valid contract with delivered CLI output, otherwise one.

    """
    try:
        projection = canonical_projection()
        message = "C libc contract ready: " + projection.libc_id
        message += f" ({projection.abi_id})\n"
        if not _write_cli_record(sys.stdout, message):
            _fail("C libc CLI output write or flush failed")
    except (c_abi.CAbiValidationError, CLibcValidationError) as error:
        detail = (
            str(error)
            if type(error) in (c_abi.CAbiValidationError, CLibcValidationError)
            else type(error).__name__
        )
        _ = _write_cli_record(sys.stderr, f"error: {detail}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
