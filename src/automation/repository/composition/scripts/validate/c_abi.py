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
#   - Validation and typed access for the canonical deterministic guest-C ABI.
# - Must-Not:
#   - Infer ABI properties from the host Python process or native compiler.
# - Allows:
#   - Inputs: canonical ABI JSON and canonical Malbolge target-profile data.
#   - Outputs: validated ABI constants and deterministic validation failures.
#   - Side effects: reading tracked authority files only.
# - Split-When:
#   - Split when another ABI schema version gains an independent lifecycle.
# - Merge-When:
#   - Merge when another validator owns this exact guest-C ABI authority.
# - Summary:
#   - Validates the closed malbolge-c32-v1 ABI authority.
# - Description:
#   - Prevents host ABI leakage before compiler or tidy consumers use C layout.
# - Usage:
#   - Imported by guest-C validation and executed directly for conformance.
# - Defaults:
#   - Unknown keys, duplicate keys, drift, and target mismatch fail closed.
#

"""Validate the closed malbolge-c32-v1 guest-C ABI authority."""

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
from scripts.validate import target_profile

ROOT = repository_root(Path(__file__))
DEFAULT_ABI = ROOT / "docs/technical/specification/c-abi-v1.json"
ABI_ID = "malbolge-c32-v1"
TARGET_PROFILE = target_profile.CURRENT_PROFILE_ID
CLANG_TARGET = "wasm32-unknown-unknown"
LLVM_DATA_LAYOUT = (
    "e-m:e-p:32:32-p10:8:8-p20:8:8-i64:64-i128:128-n32:64-S128-ni:1:10:20"
)
SCHEMA_VERSION = 1
MAX_ALIGNMENT = 16
POINTER_BITS = 32
POINTER_SIZE = 4
POINTER_ALIGNMENT = 4
STACK_ALIGNMENT = 16
FRAME_HEADER_BYTES = 32

TOP_LEVEL_KEYS = frozenset({
    "abi_id",
    "aggregate",
    "byte",
    "call",
    "failure",
    "floating",
    "frontend_projection",
    "integer",
    "io",
    "pointer",
    "schema_version",
    "target_profile",
})
FRONTEND_KEYS = frozenset({"clang_target", "llvm_data_layout"})
BYTE_KEYS = frozenset({"bits", "endianness"})
SCALAR_LAYOUT_KEYS = frozenset({"alignment", "size"})
WCHAR_KEYS = frozenset({"alignment", "signed", "size"})
ENUM_KEYS = frozenset({"default_underlying", "fixed_underlying"})
INTEGER_KEYS = frozenset({
    "bool",
    "char",
    "enum",
    "int",
    "long",
    "long_long",
    "negative_right_shift",
    "plain_char_signed",
    "short",
    "signed_representation",
    "unsigned_arithmetic",
    "wchar_t",
})
FLOAT_LAYOUT_KEYS = frozenset({
    "alignment",
    "format",
    "mantissa_bits",
    "max_exponent",
    "size",
})
FLOATING_KEYS = frozenset({
    "double",
    "excess_precision",
    "float",
    "long_double",
    "nan_result",
    "radix",
    "rounding",
    "subnormals",
})
POINTER_KEYS = frozenset({
    "address_spaces",
    "alignment",
    "bits",
    "function_encoding",
    "intptr_t",
    "null",
    "object_encoding",
    "ptrdiff_t",
    "size",
    "size_t",
    "uintptr_t",
})
AGGREGATE_KEYS = frozenset({
    "array_stride",
    "bit_fields",
    "bit_precise_integers",
    "extended_alignment",
    "max_alignment",
    "packed_layout",
    "padding",
    "struct_layout",
    "union_layout",
})
CALL_KEYS = frozenset({
    "argument_order",
    "frame_fields",
    "frame_header_bytes",
    "result_rule",
    "stack_alignment",
    "stack_direction",
    "variadic_rule",
})
FRAME_FIELD_KEYS = frozenset({"name", "offset", "type"})
IO_KEYS = frozenset({"eof_value", "read_result", "write_input"})
FAILURE_KEYS = frozenset({
    "invalid_pointer",
    "signed_overflow",
    "stack_exhaustion",
    "unknown_abi",
})


type JsonScalar = bool | int | float | str | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class _FloatLayoutSpec:
    """Expected representation for one canonical floating type."""

    alignment: int
    format_name: str
    mantissa_bits: int
    max_exponent: int
    name: str
    size: int


@dataclass(frozen=True, slots=True)
class CAbiProjection:
    """Typed values required by executable frontend consumers."""

    abi_id: str
    clang_target: str
    llvm_data_layout: str
    max_alignment: int
    pointer_bits: int
    stack_alignment: int
    target_profile: str


class CAbiValidationError(ValueError):
    """Canonical guest-C ABI schema or invariant failure."""


def _fail(message: str) -> Never:
    raise CAbiValidationError(message)


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
    raw = cast("dict[object, object]", value)
    result: JsonObject = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            _fail(f"{context} contains a non-string key")
        result[key] = cast("JsonValue", item)
    return result


def _expect_keys(
    value: JsonObject,
    expected: frozenset[str],
    context: str,
) -> None:
    observed = frozenset(value)
    if observed == expected:
        return
    message = f"{context} keys differ: missing={sorted(expected - observed)}, "
    message += f"unknown={sorted(observed - expected)}"
    _fail(message)


def _expect_literal(actual: object, expected: object, context: str) -> None:
    if type(actual) is not type(expected) or actual != expected:
        _fail(f"{context} must be {expected!r}")


def loads_document(text: str) -> JsonObject:
    """Parse an ABI document while rejecting duplicate object keys.

    Returns:
        The parsed top-level ABI object.

    """
    try:
        parsed = cast(
            "object",
            json.loads(text, object_pairs_hook=_reject_duplicate_pairs),
        )
    except json.JSONDecodeError as error:
        _fail(f"invalid JSON: {error}")
    return _mapping(parsed, "C ABI document")


def load_document(path: Path = DEFAULT_ABI) -> JsonObject:
    """Load a UTF-8 ABI document from disk.

    Returns:
        The parsed top-level ABI object.

    """
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as error:
        _fail(f"invalid C ABI UTF-8: {error}")
    except OSError as error:
        _fail(f"failed to read C ABI document {path}: {error}")
    return loads_document(text)


def _validate_frontend(value: JsonValue) -> None:
    frontend = _mapping(value, "frontend_projection")
    _expect_keys(frontend, FRONTEND_KEYS, "frontend_projection")
    _expect_literal(
        frontend["clang_target"],
        CLANG_TARGET,
        "frontend_projection.clang_target",
    )
    raw_layout = frontend["llvm_data_layout"]
    if not isinstance(raw_layout, list) or not all(
        isinstance(segment, str) for segment in raw_layout
    ):
        _fail("frontend_projection.llvm_data_layout must be a string array")
    layout = "".join(cast("list[str]", raw_layout))
    _expect_literal(
        layout,
        LLVM_DATA_LAYOUT,
        "frontend_projection.llvm_data_layout",
    )


def _validate_byte(value: JsonValue) -> None:
    byte = _mapping(value, "byte")
    _expect_keys(byte, BYTE_KEYS, "byte")
    _expect_literal(byte["bits"], 8, "byte.bits")
    _expect_literal(byte["endianness"], "little", "byte.endianness")


def _validate_scalar_layout(
    value: JsonValue,
    *,
    context: str,
    size: int,
    alignment: int,
) -> None:
    layout = _mapping(value, context)
    _expect_keys(layout, SCALAR_LAYOUT_KEYS, context)
    _expect_literal(layout["size"], size, f"{context}.size")
    _expect_literal(layout["alignment"], alignment, f"{context}.alignment")


def _validate_wchar(value: JsonValue) -> None:
    wchar = _mapping(value, "integer.wchar_t")
    _expect_keys(wchar, WCHAR_KEYS, "integer.wchar_t")
    _expect_literal(wchar["size"], 4, "integer.wchar_t.size")
    _expect_literal(wchar["alignment"], 4, "integer.wchar_t.alignment")
    _expect_literal(
        wchar["signed"],
        expected=True,
        context="integer.wchar_t.signed",
    )


def _validate_enum(value: JsonValue) -> None:
    enum = _mapping(value, "integer.enum")
    _expect_keys(enum, ENUM_KEYS, "integer.enum")
    _expect_literal(
        enum["default_underlying"],
        "int32-if-representable-else-uint32",
        "integer.enum.default_underlying",
    )
    _expect_literal(
        enum["fixed_underlying"],
        "declared-canonical-integer-type",
        "integer.enum.fixed_underlying",
    )


def _validate_integer(value: JsonValue) -> None:
    integer = _mapping(value, "integer")
    _expect_keys(integer, INTEGER_KEYS, "integer")
    _expect_literal(
        integer["signed_representation"],
        "twos-complement",
        "integer.signed_representation",
    )
    _expect_literal(
        integer["plain_char_signed"],
        expected=True,
        context="integer.plain_char_signed",
    )
    _expect_literal(
        integer["unsigned_arithmetic"],
        "modulo-2-to-width",
        "integer.unsigned_arithmetic",
    )
    _expect_literal(
        integer["negative_right_shift"],
        "arithmetic",
        "integer.negative_right_shift",
    )
    layouts = (
        ("bool", 1, 1),
        ("char", 1, 1),
        ("short", 2, 2),
        ("int", 4, 4),
        ("long", 4, 4),
        ("long_long", 8, 8),
    )
    for name, size, alignment in layouts:
        _validate_scalar_layout(
            integer[name],
            context=f"integer.{name}",
            size=size,
            alignment=alignment,
        )
    _validate_wchar(integer["wchar_t"])
    _validate_enum(integer["enum"])


def _validate_float_layout(
    value: JsonValue,
    spec: _FloatLayoutSpec,
) -> None:
    context = f"floating.{spec.name}"
    layout = _mapping(value, context)
    _expect_keys(layout, FLOAT_LAYOUT_KEYS, context)
    _expect_literal(layout["size"], spec.size, f"{context}.size")
    _expect_literal(
        layout["alignment"],
        spec.alignment,
        f"{context}.alignment",
    )
    _expect_literal(
        layout["format"],
        spec.format_name,
        f"{context}.format",
    )
    _expect_literal(
        layout["mantissa_bits"],
        spec.mantissa_bits,
        f"{context}.mantissa_bits",
    )
    _expect_literal(
        layout["max_exponent"],
        spec.max_exponent,
        f"{context}.max_exponent",
    )


def _validate_floating(value: JsonValue) -> None:
    floating = _mapping(value, "floating")
    _expect_keys(floating, FLOATING_KEYS, "floating")
    _expect_literal(floating["radix"], 2, "floating.radix")
    _expect_literal(
        floating["rounding"],
        "nearest-ties-to-even",
        "floating.rounding",
    )
    _expect_literal(floating["subnormals"], "preserve", "floating.subnormals")
    _expect_literal(
        floating["excess_precision"],
        "none",
        "floating.excess_precision",
    )
    _expect_literal(
        floating["nan_result"],
        "canonical-quiet-payload-zero",
        "floating.nan_result",
    )
    layouts = (
        _FloatLayoutSpec(4, "binary32", 24, 128, "float", 4),
        _FloatLayoutSpec(8, "binary64", 53, 1024, "double", 8),
        _FloatLayoutSpec(16, "binary128", 113, 16384, "long_double", 16),
    )
    for spec in layouts:
        _validate_float_layout(floating[spec.name], spec)


def _validate_pointer(value: JsonValue) -> None:
    pointer = _mapping(value, "pointer")
    _expect_keys(pointer, POINTER_KEYS, "pointer")
    expected: dict[str, object] = {
        "address_spaces": "default-only",
        "bits": POINTER_BITS,
        "size": POINTER_SIZE,
        "alignment": POINTER_ALIGNMENT,
        "null": 0,
        "object_encoding": "linear-byte-address-plus-one",
        "function_encoding": "function-table-index-plus-one",
        "size_t": "unsigned long",
        "ptrdiff_t": "long",
        "intptr_t": "long",
        "uintptr_t": "unsigned long",
    }
    for key, expected_value in expected.items():
        _expect_literal(pointer[key], expected_value, f"pointer.{key}")


def _validate_aggregate(value: JsonValue) -> None:
    aggregate = _mapping(value, "aggregate")
    _expect_keys(aggregate, AGGREGATE_KEYS, "aggregate")
    expected: dict[str, object] = {
        "max_alignment": MAX_ALIGNMENT,
        "array_stride": "round-up-size-to-element-alignment",
        "struct_layout": "declaration-order-natural-alignment",
        "union_layout": "offset-zero-max-size",
        "padding": "zero-filled",
        "bit_fields": "unsupported-v1",
        "packed_layout": "unsupported-v1",
        "extended_alignment": "unsupported-above-16",
        "bit_precise_integers": "unsupported-v1",
    }
    for key, expected_value in expected.items():
        _expect_literal(aggregate[key], expected_value, f"aggregate.{key}")


def _validate_frame_fields(value: JsonValue) -> None:
    if not isinstance(value, list):
        _fail("call.frame_fields must be an array")
    expected = (
        (0, "previous_frame", "u32"),
        (4, "continuation_id", "u32"),
        (8, "function_id", "u32"),
        (12, "frame_extent", "u32"),
        (16, "argument_block", "object_pointer"),
        (20, "result_block", "object_pointer"),
        (24, "variadic_begin", "object_pointer"),
        (28, "flags", "u32-zero-v1"),
    )
    if len(value) != len(expected):
        _fail(f"call.frame_fields length must be {len(expected)}")
    pairs = zip(value, expected, strict=True)
    for index, (raw, field_spec) in enumerate(pairs):
        context = f"call.frame_fields[{index}]"
        field = _mapping(raw, context)
        _expect_keys(field, FRAME_FIELD_KEYS, context)
        offset, name, type_name = field_spec
        _expect_literal(field["offset"], offset, f"{context}.offset")
        _expect_literal(field["name"], name, f"{context}.name")
        _expect_literal(field["type"], type_name, f"{context}.type")


def _validate_call(value: JsonValue) -> None:
    call = _mapping(value, "call")
    _expect_keys(call, CALL_KEYS, "call")
    expected: dict[str, object] = {
        "stack_alignment": STACK_ALIGNMENT,
        "stack_direction": "down",
        "argument_order": "source-order-natural-alignment",
        "variadic_rule": "default-promotions-natural-alignment",
        "result_rule": "caller-owned-storage",
        "frame_header_bytes": FRAME_HEADER_BYTES,
    }
    for key, expected_value in expected.items():
        _expect_literal(call[key], expected_value, f"call.{key}")
    _validate_frame_fields(call["frame_fields"])


def _validate_io(value: JsonValue) -> None:
    io = _mapping(value, "io")
    _expect_keys(io, IO_KEYS, "io")
    _expect_literal(
        io["read_result"],
        "int32-byte-or-minus-one-eof",
        "io.read_result",
    )
    _expect_literal(io["write_input"], "low-eight-bits", "io.write_input")
    _expect_literal(io["eof_value"], -1, "io.eof_value")


def _validate_failure(value: JsonValue) -> None:
    failure = _mapping(value, "failure")
    _expect_keys(failure, FAILURE_KEYS, "failure")
    expected: dict[str, object] = {
        "signed_overflow": "undefined-source-rejected-or-proven-unreachable",
        "invalid_pointer": "undefined-source-rejected-or-runtime-fail-closed",
        "stack_exhaustion": "deterministic-runtime-failure",
        "unknown_abi": "fail-closed",
    }
    for key, expected_value in expected.items():
        _expect_literal(failure[key], expected_value, f"failure.{key}")


def validate_document(document: JsonObject) -> CAbiProjection:
    """Validate one parsed ABI authority.

    Returns:
        The executable frontend projection after all invariants pass.

    """
    _expect_keys(document, TOP_LEVEL_KEYS, "C ABI document")
    _expect_literal(
        document["schema_version"],
        SCHEMA_VERSION,
        "schema_version",
    )
    _expect_literal(document["abi_id"], ABI_ID, "abi_id")
    _expect_literal(
        document["target_profile"],
        TARGET_PROFILE,
        "target_profile",
    )
    _validate_frontend(document["frontend_projection"])
    _validate_byte(document["byte"])
    _validate_integer(document["integer"])
    _validate_floating(document["floating"])
    _validate_pointer(document["pointer"])
    _validate_aggregate(document["aggregate"])
    _validate_call(document["call"])
    _validate_io(document["io"])
    _validate_failure(document["failure"])
    return CAbiProjection(
        abi_id=ABI_ID,
        clang_target=CLANG_TARGET,
        llvm_data_layout=LLVM_DATA_LAYOUT,
        max_alignment=MAX_ALIGNMENT,
        pointer_bits=POINTER_BITS,
        stack_alignment=STACK_ALIGNMENT,
        target_profile=TARGET_PROFILE,
    )


def validate_text(text: str) -> CAbiProjection:
    """Validate one UTF-8-decoded ABI JSON string.

    Returns:
        The executable frontend projection after validation.

    """
    return validate_document(loads_document(text))


def canonical_projection() -> CAbiProjection:
    """Validate the ABI authority and target-profile binding.

    Returns:
        The executable frontend projection of the canonical ABI.

    """
    projection = validate_document(load_document())
    profile = target_profile.load_document(target_profile.DEFAULT_PROFILE)
    target_profile.validate_document(profile)
    selected = profile["current_profile"]
    if selected != projection.target_profile:
        message = (
            "C ABI target profile disagrees with canonical current profile: "
        )
        message += f"abi={projection.target_profile!r}, current={selected!r}"
        _fail(message)
    return projection


def main() -> int:
    """Validate the tracked ABI authority and target-profile binding.

    Returns:
        Zero when both authorities agree, otherwise one.

    """
    try:
        projection = canonical_projection()
    except (
        CAbiValidationError,
        target_profile.ProfileValidationError,
    ) as error:
        _ = sys.stderr.write(f"error: {error}\n")
        return 1
    message = f"{projection.abi_id} target={projection.target_profile} "
    message += f"clang={projection.clang_target}\n"
    _ = sys.stdout.write(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
