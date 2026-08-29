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
#   - Exact zero-padding correspondence for unbounded five-trit crazy chunks.
# - Must-Not:
#   - Convert arithmetic equivalence into a wall-clock speedup claim.
# - Allows:
#   - Inputs: semantic widths N>=10 and every possible final-chunk operand pair.
#   - Outputs: exact padded constants and semantic-width projections.
#   - Side effects: none.
# - Split-When:
#   - Padding width or ternary crazy semantics changes.
# - Merge-When:
#   - Another proof owns the same parametric zero-padded five-trit identity.
# - Summary:
#   - Prove ceil(N/5) five-trit crazy chunks preserve every N>=10 semantics.
# - Description:
#   - Exhausts final-chunk residues and checks representative arbitrary widths.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Width has no mathematical maximum; only the final chunk is zero-padded.
#

"""Evidence for exact zero-padded crazy chunk geometry."""

from __future__ import annotations

import json
from math import prod
from pathlib import Path
from typing import cast

_ROOT = Path(__file__).resolve().parents[2]
_DOCUMENT = cast(
    "dict[str, object]",
    cast(
        "object",
        json.loads((_ROOT / "malbolge.json").read_text(encoding="utf-8")),
    ),
)
_WIDTH_MODEL = cast(
    "dict[str, object]",
    _DOCUMENT["semantic_width_model"],
)


_MINIMUM_WIDTH_VALUE = _WIDTH_MODEL["minimum_trits"]
_CHUNK_TRITS_VALUE = _WIDTH_MODEL["chunk_trits"]
_RADIX_VALUE = _WIDTH_MODEL["radix"]
assert type(_MINIMUM_WIDTH_VALUE) is int
assert type(_CHUNK_TRITS_VALUE) is int
assert type(_RADIX_VALUE) is int
_MINIMUM_WIDTH = _MINIMUM_WIDTH_VALUE
_CHUNK_TRITS = _CHUNK_TRITS_VALUE
_RADIX = _RADIX_VALUE
_CHUNK_MODULUS = prod([_RADIX] * _CHUNK_TRITS)
_N15_WIDTH = 15
_N15_CHUNKS = 3
_N20_WIDTH = 20
_N31_WIDTH = 31
_N31_CHUNKS = 7
_N31_PADDED_WIDTH = 35
_U32_MAX = (2**32) - 1
_EXHAUSTIVE_TAIL_WIDTHS = tuple(range(_MINIMUM_WIDTH, _MINIMUM_WIDTH + 6))
_REPRESENTATIVE_WIDTHS = (
    _MINIMUM_WIDTH,
    11,
    14,
    15,
    16,
    20,
    31,
    37,
)
_CRAZY_TRIT = (
    (1, 0, 0),
    (1, 0, 2),
    (2, 2, 1),
)


def _integer_power(base: int, exponent: int) -> int:
    result = 1
    for _ in range(exponent):
        result *= base
    return result


def _crazy(data: int, accumulator: int, trits: int) -> int:
    result = 0
    place = 1
    for _ in range(trits):
        result += _CRAZY_TRIT[data % _RADIX][accumulator % _RADIX] * place
        data //= _RADIX
        accumulator //= _RADIX
        place *= _RADIX
    return result


def _chunk_count(width: int) -> int:
    return (width + _CHUNK_TRITS - 1) // _CHUNK_TRITS


def _padded_width(width: int) -> int:
    return _chunk_count(width) * _CHUNK_TRITS


def _tail_trits(width: int) -> int:
    residual = width % _CHUNK_TRITS
    return _CHUNK_TRITS if residual == 0 else residual


def _uniform_chunked_crazy(data: int, accumulator: int, width: int) -> int:
    semantic_modulus = _integer_power(_RADIX, width)
    result = 0
    place = 1
    for _ in range(_chunk_count(width)):
        chunk_data = (data // place) % _CHUNK_MODULUS
        chunk_accumulator = (accumulator // place) % _CHUNK_MODULUS
        result += place * _crazy(
            chunk_data,
            chunk_accumulator,
            _CHUNK_TRITS,
        )
        place *= _CHUNK_MODULUS
    return result % semantic_modulus


def _tail_pairs(width: int) -> list[tuple[int, int]]:
    tail_modulus = _integer_power(_RADIX, _tail_trits(width))
    return [
        (data_tail, accumulator_tail)
        for data_tail in range(tail_modulus)
        for accumulator_tail in range(tail_modulus)
    ]


def _padding_constant(width: int) -> int:
    return (
        _integer_power(_RADIX, _padded_width(width))
        - _integer_power(_RADIX, width)
    ) // (_RADIX - 1)


def test_canonical_width_model_is_unbounded_five_trit_padding() -> None:
    """The profile authority fixes chunk arithmetic but no semantic maximum."""
    assert _WIDTH_MODEL == {
        "radix": 3,
        "minimum_trits": 10,
        "chunk_trits": 5,
        "maximum_trits": None,
        "partial_chunk_padding": "zero-high-trits",
        "result_projection": "mod-semantic-width",
    }


def test_zero_padding_adds_exact_constant_high_trits() -> None:
    """Every zero-padded high trit contributes the constant crazy(0,0)=1."""
    assert _CRAZY_TRIT[0][0] == 1
    for width in _REPRESENTATIVE_WIDTHS:
        high_trits = _padded_width(width) - width
        high_output = _crazy(0, 0, high_trits) * _integer_power(_RADIX, width)
        assert high_output == _padding_constant(width)
        assert _padding_constant(width) % (_integer_power(_RADIX, width)) == 0
    assert _padding_constant(_N15_WIDTH) == 0
    assert _padding_constant(_N20_WIDTH) == 0


def test_padded_tail_lookup_matches_native_tail_for_every_residue() -> None:
    """Every possible final chunk is one five-trit lookup plus high padding."""
    for width in _EXHAUSTIVE_TAIL_WIDTHS:
        tail_trits = _tail_trits(width)
        tail_modulus = _integer_power(_RADIX, tail_trits)
        tail_constant = (
            _integer_power(_RADIX, _CHUNK_TRITS)
            - _integer_power(_RADIX, tail_trits)
        ) // (_RADIX - 1)
        for data_tail, accumulator_tail in _tail_pairs(width):
            native = _crazy(data_tail, accumulator_tail, tail_trits)
            padded = _crazy(data_tail, accumulator_tail, _CHUNK_TRITS)
            assert padded == native + tail_constant
            assert padded % tail_modulus == native


def test_chunk_padding_has_exact_semantic_projection_constant() -> None:
    """Padding only the final physical chunk never changes the low N trits."""
    for width in _REPRESENTATIVE_WIDTHS:
        native = _crazy(0, 0, width)
        padded = _crazy(0, 0, _padded_width(width))
        assert padded - native == _padding_constant(width)
        assert padded % (_integer_power(_RADIX, width)) == native


def test_uniform_chunk_factorization_matches_arbitrary_width_semantics(
) -> None:
    """ceil(N/5) identical lookups reproduce native crazy for arbitrary N."""
    for width in _REPRESENTATIVE_WIDTHS:
        modulus = _integer_power(_RADIX, width)
        fixtures = (
            (0, 0),
            (modulus - 1, modulus - 1),
            (modulus // 7, modulus // 11),
            ((modulus // 3) + 17, (modulus // 5) + 93),
        )
        for raw_data, raw_accumulator in fixtures:
            data = raw_data % modulus
            accumulator = raw_accumulator % modulus
            assert _uniform_chunked_crazy(
                data,
                accumulator,
                width,
            ) == _crazy(data, accumulator, width)


def test_n15_is_three_full_chunks_without_padding() -> None:
    """Fifteen semantic trits use exactly three complete five-trit chunks."""
    width = _N15_WIDTH
    assert _chunk_count(width) == _N15_CHUNKS
    assert _padded_width(width) == width
    assert _tail_trits(width) == _CHUNK_TRITS
    modulus = _integer_power(_RADIX, width)
    assert _uniform_chunked_crazy(
        modulus - 2,
        modulus // 2,
        width,
    ) == _crazy(modulus - 2, modulus // 2, width)


def test_width_beyond_u32_remains_mathematically_defined() -> None:
    """Backend integer limits do not become a semantic-width language limit."""
    width = _N31_WIDTH
    modulus = _integer_power(_RADIX, width)
    assert modulus > _U32_MAX
    assert _chunk_count(width) == _N31_CHUNKS
    assert _padded_width(width) == _N31_PADDED_WIDTH
    assert _uniform_chunked_crazy(
        modulus // 13,
        modulus // 17,
        width,
    ) == _crazy(modulus // 13, modulus // 17, width)
