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
#   - Static correctness evidence for experimental resident CUDA crazy geometry.
# - Must-Not:
#   - Require CUDA hardware or make generated kernels semantic authority.
# - Allows:
#   - Inputs: N10-N14 resident geometry and exact generated source.
#   - Outputs: deterministic table and source-structure assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when another CUDA arithmetic experiment gains separate invariants.
# - Merge-When:
#   - Merge when another test owns this exact resident crazy geometry contract.
# - Summary:
#   - Exact static evidence for tritwise, residual, and padded CUDA crazy paths.
# - Description:
#   - Exhausts the five-trit table and checks bounded geometry-specific source.
# - Usage:
#   - Run without CUDA hardware before any geometry performance measurement.
# - Defaults:
#   - Product source remains tritwise unless a caller explicitly selects a mode.
#

"""Static correctness evidence for resident CUDA crazy geometry variants."""

from __future__ import annotations

from accelerator.cuda.resident_kernel import CRAZY_CHUNK_VALUES
from accelerator.cuda.resident_kernel import CRAZY_TABLE_ENTRIES
from accelerator.cuda.resident_kernel import ResidentCrazyGeometry
from accelerator.cuda.resident_kernel import ResidentGeometry
from accelerator.cuda.resident_kernel import resident_kernel_source
import pytest

MINIMUM_WIDTH = 10
WIDTHS = range(MINIMUM_WIDTH, 15)
KERNEL_NAME = "crazy_geometry_test"
EXPECTED_TABLE_ENTRIES = 59_049
EXPECTED_CONSTANT_MEMORY_BYTES = 59_237
CONSTANT_MEMORY_BYTES = CRAZY_TABLE_ENTRIES + 94 + 94
CUDA_CONSTANT_MEMORY_BASELINE_BYTES = 64 * 1024
OUTSIDE_WIDTHS = (9, 15)
N14_WORDS = 4_782_969
N15 = 15
N15_DEFINE = "#define WORD_TRITS 15u"
TABLE_NAME = "CRAZY_CHUNK_TABLE"
TABLE_DECLARATION = "CRAZY_CHUNK_TABLE[59049]"
TABLE_ELEMENT_TYPE = "unsigned char CRAZY_CHUNK_TABLE"
TABLE_PREFIX = "CRAZY_CHUNK_TABLE[59049] = {"
TABLE_SUFFIX = "};"
TRITWISE_LOOP = "for (unsigned int trit = 0u; trit < WORD_TRITS; ++trit)"
NATIVE_TAIL_LOOP = "for (unsigned int trit = 10u; trit < WORD_TRITS; ++trit)"
NATIVE_TAIL_PREFIX = "for (unsigned int trit = 10u;"
HIGH_LOOKUP = "unsigned int high = crazy_chunk_lookup"
PADDED_PROJECTION = "return result % WORD_MODULUS;"


def _geometry(word_trits: int) -> ResidentGeometry:
    modulus = 1
    for _ in range(word_trits):
        modulus *= 3
    return ResidentGeometry(
        interpreter_authority=False,
        eof_word=modulus - 1,
        input_instruction=ord("/"),
        memory_words=modulus,
        output_instruction=ord("<"),
        word_modulus=modulus,
        word_trits=word_trits,
    )


def _crazy_trit(data: int, accumulator: int) -> int:
    relation = (
        (1, 0, 0),
        (1, 0, 2),
        (2, 2, 1),
    )
    return relation[data][accumulator]


def _crazy_chunk_scalar(data: int, accumulator: int) -> int:
    result = 0
    place = 1
    for _ in range(5):
        result += _crazy_trit(data % 3, accumulator % 3) * place
        place *= 3
        data //= 3
        accumulator //= 3
    return result


def _rendered_table() -> tuple[int, ...]:
    source = resident_kernel_source(
        _geometry(10),
        KERNEL_NAME,
        crazy_geometry=ResidentCrazyGeometry.NATIVE,
    )
    payload = source.split(TABLE_PREFIX, 1)[1].split(TABLE_SUFFIX, 1)[0]
    return tuple(int(value) for value in payload.split(","))


def test_five_trit_table_is_exhaustively_independent_and_constant_fit() -> None:
    """Every table cell matches an independent scalar five-trit computation."""
    table = _rendered_table()
    assert len(table) == CRAZY_TABLE_ENTRIES == EXPECTED_TABLE_ENTRIES
    assert CONSTANT_MEMORY_BYTES == EXPECTED_CONSTANT_MEMORY_BYTES
    assert CONSTANT_MEMORY_BYTES < CUDA_CONSTANT_MEMORY_BASELINE_BYTES
    for data in range(CRAZY_CHUNK_VALUES):
        for accumulator in range(CRAZY_CHUNK_VALUES):
            index = (data * CRAZY_CHUNK_VALUES) + accumulator
            assert table[index] == _crazy_chunk_scalar(data, accumulator)


def test_default_resident_source_remains_tritwise() -> None:
    """Ordinary product rendering does not opt into lookup paths."""
    source = resident_kernel_source(_geometry(14), KERNEL_NAME)
    assert TABLE_NAME not in source
    assert TRITWISE_LOOP in source
    assert f"#define WORD_MODULUS {N14_WORDS}u" in source


@pytest.mark.parametrize("word_trits", list(WIDTHS))
def test_native_residual_source_uses_two_lookups_plus_exact_tail(
    word_trits: int,
) -> None:
    """Native N10-N14 uses two full chunks plus the semantic residual tail."""
    source = resident_kernel_source(
        _geometry(word_trits),
        KERNEL_NAME,
        crazy_geometry=ResidentCrazyGeometry.NATIVE,
    )
    assert TABLE_DECLARATION in source
    assert TABLE_ELEMENT_TYPE in source
    assert NATIVE_TAIL_LOOP in source
    assert HIGH_LOOKUP not in source


@pytest.mark.parametrize("word_trits", list(WIDTHS))
def test_padded_source_uses_only_full_five_trit_lookups(
    word_trits: int,
) -> None:
    """Padded N10 uses two lookups; N11-N14 use exactly three then project."""
    source = resident_kernel_source(
        _geometry(word_trits),
        KERNEL_NAME,
        crazy_geometry=ResidentCrazyGeometry.PADDED,
    )
    assert TABLE_DECLARATION in source
    assert NATIVE_TAIL_PREFIX not in source
    assert PADDED_PROJECTION in source
    has_high_lookup = HIGH_LOOKUP in source
    assert has_high_lookup is (word_trits > MINIMUM_WIDTH)


def test_chunked_resident_modes_are_bounded_to_research_matrix() -> None:
    """Lookup geometry cannot silently widen beyond preregistered N10-N14."""
    for width in OUTSIDE_WIDTHS:
        for mode in (
            ResidentCrazyGeometry.NATIVE,
            ResidentCrazyGeometry.PADDED,
        ):
            with pytest.raises(ValueError, match="limited to N10 through N14"):
                _ = resident_kernel_source(
                    _geometry(width),
                    KERNEL_NAME,
                    crazy_geometry=mode,
                )
    tritwise = resident_kernel_source(_geometry(N15), KERNEL_NAME)
    assert N15_DEFINE in tritwise


def test_resident_crazy_geometry_rejects_non_enum_selector() -> None:
    """A forged string cannot gain experimental kernel-selection authority."""
    with pytest.raises(TypeError, match="must use the exact enum"):
        _ = resident_kernel_source(
            _geometry(10),
            KERNEL_NAME,
            crazy_geometry="padded-5+5+5",
        )
