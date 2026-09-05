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
#   - Drift checks tying guest-runtime C constants to ABI/profile authorities.
# - Must-Not:
#   - Treat duplicated C literals as independent semantic authority.
# - Allows:
#   - Inputs: tracked runtime headers, ABI JSON, profile JSON, and libc JSON.
#   - Outputs: exact cross-authority equality and staged-availability
#     assertions.
#   - Side effects: tracked file reads only.
# - Split-When:
#   - Runtime schema becomes generated directly from one canonical authority.
# - Merge-When:
#   - ABI/profile validation owns these exact guest-runtime projection checks.
# - Summary:
#   - Prevents frame, EOF, alignment, intrinsic, and availability drift.
# - Description:
#   - Runtime constants remain projections of existing repository authorities.
# - Usage:
#   - Collected by the repository Python test suite on every platform.
# - Defaults:
#   - Implemented wrappers do not imply source availability before integration.
#

"""Cross-authority checks for deterministic guest-runtime constants."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
ABI_PATH = ROOT / "docs/technical/specification/c-abi-v1.json"
PROFILE_PATH = ROOT / "malbolge.json"
LIBC_PATH = ROOT / "docs/technical/specification/c-libc-v1.json"
RUNTIME_CONTRACT = (
    ROOT / "src/runtime/guest-runtime/contract/guest-runtime-v1.json"
)
RUNTIME_HEADER = ROOT / "src/runtime/guest-runtime/contract/guest_runtime.h"
INTRINSIC_HEADER = (
    ROOT / "src/runtime/guest-runtime/contract/guest_intrinsics.h"
)
FRAME_SOURCE = ROOT / "src/runtime/guest-runtime/domain/frame.c"
HEAP_SOURCE = ROOT / "src/runtime/guest-runtime/domain/heap.c"

RUNTIME_ID = "malbolge-guest-runtime-v1"
ABI_ID = "malbolge-c32-v1"
TARGET_PROFILE = "malbolge-2026"
HOST_FALLBACK = "forbidden"
OUTPUT_MODULUS = 256
INPUT_INSTRUCTION = "/"
OUTPUT_INSTRUCTION = "<"
INPUT_DECLARATION = "uint32_t malbolge_guest_intrinsic_input_word(void);"
OUTPUT_DECLARATION = "void malbolge_guest_intrinsic_output_byte(uint8_t value);"
INTRINSIC_SOURCE_NAME = "guest_intrinsics.c"
FORMAT_KERNEL_VISIBILITY = "internal-typed-kernel-not-public-snprintf"
FORMAT_PARSER = "c23-narrow-tokenizer-implemented"
FORMAT_PARSER_BINARY = "b-and-uppercase-B-supported"
FORMAT_PARSER_DYNAMIC_FIELDS = "width-and-precision-asterisk-preserved"
FORMAT_PARSER_SPECIFIC_WIDTH = "wN-and-wfN-positive-u32-no-leading-zero"
FORMAT_PARSER_SEMANTIC_VALIDATION = "c23-directive-admission-implemented"
FORMAT_SPECIFIC_WIDTH_BITS = [8, 16, 32, 64]
FORMAT_VARIADIC_DECODER = "canonical-promoted-block-cursor-implemented"
FORMAT_VARIADIC_ADDRESS = "decoded-object-pointer-zero-based-offset"
FORMAT_VARIADIC_MAX_OFFSET = 0xFFFFFFFE
FORMAT_VARIADIC_KINDS = [
    "i32",
    "u32",
    "i64",
    "u64",
    "f64-bits",
    "f128-bits",
    "pointer32",
]
FORMAT_VA_LIST_BRIDGE = "compiler-lowering-required"
FORMAT_ARGUMENT_RESOLUTION = "atomic-dynamic-fields-and-promoted-conversion"
FORMAT_SCALAR_EXECUTION = "d-i-u-o-x-X-b-B-c-p-percent-implemented"
FORMAT_WIDE_CHARACTER = "wint-t-not-defined-v1-fail-closed"
FORMAT_POINTER_EXECUTION = "p-object-pointer-encoding-hex-implemented"
FORMAT_POINTER_NULL = "0"
FORMAT_POINTER_NONNULL = "0x-lowercase-guest-encoding"
FORMAT_MEMORY_VIEW = "caller-proven-live-object-bounded-v1"
FORMAT_MEMORY_POINTER_ENCODING = "logical-byte-offset-plus-one"
FORMAT_MEMORY_MAX_OFFSET = 0xFFFFFFFE
FORMAT_MEMORY_EXECUTION = "narrow-s-and-integer-n-implemented"
FORMAT_MEMORY_COUNT_ENCODING = "little-endian-signed-abi-width"
FORMAT_FLOATING = "binary64-binary128-a-A-implemented-decimal-open"
FORMAT_FLOAT_HEX_ROUNDING = "nearest-ties-even"
FORMAT_FLOAT_HEX_STYLE = "normalized-leading-one"
FORMAT_FLOAT_HEX_DEFAULT = "minimal-exact-trailing-zero-trim"
FORMAT_FLOAT_BINARY128 = "a-A-implemented"
FORMAT_DECIMAL_EXACT = "digits-times-power10-implemented"
FORMAT_DECIMAL_MAX_DIGITS = 767
FORMAT_DECIMAL_SCRATCH = "base-10000-u32-only-bounded"
FORMAT_DECIMAL_EXECUTION = "binary64-e-E-implemented-f-g-f128-open"
FORMAT_DECIMAL_ROUNDING = "nearest-ties-even"
FORMAT_SCIENTIFIC_DEFAULT_PRECISION = 6
FORMAT_SCIENTIFIC_EXPONENT_DIGITS = 2
FORMAT_NOT_IMPLEMENTED = "not-implemented"
FORMAT_BASES = [2, 8, 10, 16]
FORMAT_PUBLIC_ROUTINES = ["snprintf", "vsnprintf"]
FORMAT_PRECISION_POLICY = "u32-0xffffffff-means-omitted"

GATED_ROUTINES = frozenset({
    "malloc",
    "calloc",
    "realloc",
    "free",
    "getchar",
    "putchar",
    "snprintf",
    "vsnprintf",
})

STATUS_PATTERN = re.compile(
    r"^  MALBOLGE_GUEST_RUNTIME_(?P<name>[A-Z_]+) = (?P<value>[0-9]+)[,]?$",
    re.MULTILINE,
)
HEAP_OFFSET_PATTERN = re.compile(
    r"^#define OFFSET_(?P<name>[A-Z_]+) UINT32_C\((?P<value>[0-9]+)\)$",
    re.MULTILINE,
)
RUNTIME_TOP_LEVEL_KEYS = frozenset({
    "schema_version",
    "runtime_id",
    "abi_id",
    "target_profile",
    "status",
    "heap",
    "startup",
    "frame",
    "byte_io",
    "formatting_kernel",
    "host_fallback",
})

MACRO_PATTERN = re.compile(
    r"^#define (?P<name>[A-Z0-9_]+) UINT32_C\((?P<value>[0-9]+)\)$",
    re.MULTILINE,
)
OFFSET_PATTERN = re.compile(
    r"^#define OFFSET_(?P<name>[A-Z_]+) UINT32_C\((?P<value>[0-9]+)\)$",
    re.MULTILINE,
)


def load_object(path: Path) -> dict[str, object]:
    """Load one tracked JSON authority as an object.

    Returns:
        The parsed top-level JSON object.

    """
    parsed = cast("object", json.loads(path.read_text(encoding="utf-8")))
    assert isinstance(parsed, dict)
    return cast("dict[str, object]", parsed)


def numeric_macros(path: Path) -> dict[str, int]:
    """Project fixed UINT32_C macro values from one runtime C source.

    Returns:
        Macro names mapped to their decimal integer values.

    """
    return {
        match.group("name"): int(match.group("value"))
        for match in MACRO_PATTERN.finditer(path.read_text(encoding="utf-8"))
    }


def frame_offsets() -> dict[str, int]:
    """Project named frame offsets from the runtime codec source.

    Returns:
        Lowercase frame field names mapped to byte offsets.

    """
    return {
        match.group("name").lower(): int(match.group("value"))
        for match in OFFSET_PATTERN.finditer(
            FRAME_SOURCE.read_text(encoding="utf-8")
        )
    }


def runtime_status_values() -> dict[str, int]:
    """Project stable runtime status values from the public C header.

    Returns:
        Lowercase status names mapped to their fixed integer values.

    """
    text = RUNTIME_HEADER.read_text(encoding="utf-8")
    return {
        match.group("name").lower(): int(match.group("value"))
        for match in STATUS_PATTERN.finditer(text)
    }


def heap_offsets() -> dict[str, int]:
    """Project guest heap metadata offsets from the allocator source.

    Returns:
        Lowercase metadata field names mapped to byte offsets.

    """
    text = HEAP_SOURCE.read_text(encoding="utf-8")
    return {
        match.group("name").lower(): int(match.group("value"))
        for match in HEAP_OFFSET_PATTERN.finditer(text)
    }


def test_runtime_contract_is_closed_and_matches_c_projection() -> None:
    """Version-one runtime policy and its C projection remain identical."""
    contract = load_object(RUNTIME_CONTRACT)
    assert frozenset(contract) == RUNTIME_TOP_LEVEL_KEYS
    assert contract["schema_version"] == 1
    assert contract["runtime_id"] == RUNTIME_ID
    assert contract["abi_id"] == ABI_ID
    assert contract["target_profile"] == TARGET_PROFILE
    assert contract["host_fallback"] == HOST_FALLBACK

    status = cast("dict[str, int]", contract["status"])
    assert runtime_status_values() == status

    heap = cast("dict[str, object]", contract["heap"])
    macros = numeric_macros(RUNTIME_HEADER)
    assert macros["MALBOLGE_GUEST_HEAP_ALIGNMENT"] == heap["alignment"]
    assert macros["MALBOLGE_GUEST_HEAP_HEADER_SIZE"] == heap["header_bytes"]
    fields = cast("list[dict[str, object]]", heap["metadata_fields"])
    expected_offsets = {
        cast("str", field["name"]): cast("int", field["offset"])
        for field in fields
    }
    assert heap_offsets() == expected_offsets


def _assert_parser_formatting(formatting: dict[str, object]) -> None:
    assert formatting["format_parser"] == FORMAT_PARSER
    assert formatting["format_parser_binary"] == FORMAT_PARSER_BINARY
    assert (
        formatting["format_parser_dynamic_fields"]
        == FORMAT_PARSER_DYNAMIC_FIELDS
    )
    assert (
        formatting["format_parser_specific_width"]
        == FORMAT_PARSER_SPECIFIC_WIDTH
    )
    assert (
        formatting["format_parser_semantic_validation"]
        == FORMAT_PARSER_SEMANTIC_VALIDATION
    )
    assert (
        formatting["format_specific_width_supported_bits"]
        == FORMAT_SPECIFIC_WIDTH_BITS
    )


def _assert_variadic_formatting(formatting: dict[str, object]) -> None:
    assert formatting["variadic_decoder"] == FORMAT_VARIADIC_DECODER
    assert formatting["variadic_cursor_address"] == FORMAT_VARIADIC_ADDRESS
    assert (
        formatting["variadic_cursor_maximum_byte_offset"]
        == FORMAT_VARIADIC_MAX_OFFSET
    )
    assert formatting["variadic_kinds"] == FORMAT_VARIADIC_KINDS
    assert formatting["source_va_list_bridge"] == FORMAT_VA_LIST_BRIDGE
    assert (
        formatting["format_argument_resolution"] == FORMAT_ARGUMENT_RESOLUTION
    )


def _assert_pointer_formatting(formatting: dict[str, object]) -> None:
    assert (
        formatting["pointer_conversion_execution"] == FORMAT_POINTER_EXECUTION
    )
    assert formatting["pointer_null_format"] == FORMAT_POINTER_NULL
    assert formatting["pointer_nonnull_format"] == FORMAT_POINTER_NONNULL


def _assert_guest_memory_formatting(formatting: dict[str, object]) -> None:
    assert formatting["guest_memory_view"] == FORMAT_MEMORY_VIEW
    assert (
        formatting["guest_memory_pointer_encoding"]
        == FORMAT_MEMORY_POINTER_ENCODING
    )
    assert (
        formatting["guest_memory_maximum_byte_offset"]
        == FORMAT_MEMORY_MAX_OFFSET
    )
    assert formatting["memory_conversion_execution"] == FORMAT_MEMORY_EXECUTION
    assert formatting["memory_count_encoding"] == FORMAT_MEMORY_COUNT_ENCODING
    assert formatting["wide_string_execution"] == FORMAT_NOT_IMPLEMENTED


def _assert_float_formatting(formatting: dict[str, object]) -> None:
    assert formatting["floating_formatting"] == FORMAT_FLOATING
    assert formatting["floating_hex_rounding"] == FORMAT_FLOAT_HEX_ROUNDING
    assert formatting["floating_hex_nonzero_style"] == FORMAT_FLOAT_HEX_STYLE
    assert (
        formatting["floating_hex_default_precision"]
        == FORMAT_FLOAT_HEX_DEFAULT
    )
    assert formatting["floating_decimal_binary64_exact"] == FORMAT_DECIMAL_EXACT
    assert (
        formatting["floating_decimal_binary64_max_exact_digits"]
        == FORMAT_DECIMAL_MAX_DIGITS
    )
    assert formatting["floating_decimal_binary64_scratch"] == (
        FORMAT_DECIMAL_SCRATCH
    )
    assert formatting["floating_decimal_execution"] == FORMAT_DECIMAL_EXECUTION
    assert formatting["floating_decimal_rounding"] == FORMAT_DECIMAL_ROUNDING
    assert (
        formatting["floating_scientific_default_precision"]
        == FORMAT_SCIENTIFIC_DEFAULT_PRECISION
    )
    assert (
        formatting["floating_scientific_exponent_minimum_digits"]
        == FORMAT_SCIENTIFIC_EXPONENT_DIGITS
    )
    assert formatting["floating_binary128_execution"] == FORMAT_FLOAT_BINARY128


def test_formatting_kernel_stays_private_and_gated() -> None:
    """Keep typed formatting progress below the complete public C contract."""
    contract = load_object(RUNTIME_CONTRACT)
    formatting = cast("dict[str, object]", contract["formatting_kernel"])
    assert formatting["visibility"] == FORMAT_KERNEL_VISIBILITY
    assert formatting["integer_bases"] == FORMAT_BASES
    assert formatting["precision"] == FORMAT_PRECISION_POLICY
    _assert_parser_formatting(formatting)
    _assert_variadic_formatting(formatting)
    assert formatting["scalar_conversion_execution"] == FORMAT_SCALAR_EXECUTION
    assert formatting["wide_character_argument"] == FORMAT_WIDE_CHARACTER
    _assert_pointer_formatting(formatting)
    _assert_guest_memory_formatting(formatting)
    _assert_float_formatting(formatting)
    assert formatting["public_routines"] == FORMAT_PUBLIC_ROUTINES
    assert formatting["public_routines_available"] is False


def test_runtime_constants_match_abi_and_current_profile() -> None:
    """Verify runtime constants are exact tracked-authority projections."""
    abi = load_object(ABI_PATH)
    profile = load_object(PROFILE_PATH)
    macros = numeric_macros(RUNTIME_HEADER)

    call = cast("dict[str, object]", abi["call"])
    current_name = cast("str", profile["current_profile"])
    profiles = cast("dict[str, object]", profile["profiles"])
    current = cast("dict[str, object]", profiles[current_name])
    semantics = cast("dict[str, object]", current["semantics"])

    assert (
        macros["MALBOLGE_GUEST_FRAME_HEADER_SIZE"] == call["frame_header_bytes"]
    )
    assert macros["MALBOLGE_GUEST_HEAP_ALIGNMENT"] == call["stack_alignment"]
    assert macros["MALBOLGE_GUEST_PROFILE_EOF_WORD"] == semantics["eof_word"]
    assert semantics["output_modulus"] == OUTPUT_MODULUS
    assert semantics["input_instruction"] == INPUT_INSTRUCTION
    assert semantics["output_instruction"] == OUTPUT_INSTRUCTION


def test_frame_codec_offsets_match_c_abi_authority() -> None:
    """Runtime frame codec field offsets exactly match c-abi-v1."""
    abi = load_object(ABI_PATH)
    call = cast("dict[str, object]", abi["call"])
    fields = cast("list[dict[str, object]]", call["frame_fields"])
    expected = {
        cast("str", field["name"]): cast("int", field["offset"])
        for field in fields
    }
    assert frame_offsets() == expected


def test_byte_intrinsics_match_profile_and_remain_declaration_only() -> None:
    """Keep stable byte intrinsic identities declaration-only for lane 9."""
    text = INTRINSIC_HEADER.read_text(encoding="utf-8")
    assert INPUT_DECLARATION in text
    assert OUTPUT_DECLARATION in text
    assert not any(
        path.name == INTRINSIC_SOURCE_NAME
        for path in (ROOT / "src/runtime/guest-runtime").rglob("*.c")
    )


def test_wrappers_do_not_prematurely_change_libc_availability() -> None:
    """Keep allocation and byte I/O source-unavailable until their gates."""
    libc = load_object(LIBC_PATH)
    unavailable = cast(
        "list[dict[str, object]]",
        libc["contracted_unavailable"],
    )
    names = {cast("str", item["name"]) for item in unavailable}
    assert names >= GATED_ROUTINES
