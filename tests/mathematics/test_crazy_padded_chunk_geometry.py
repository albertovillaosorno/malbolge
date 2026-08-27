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
#   - Exact zero-padding correspondence for 10-through-14-trit crazy chunks.
# - Must-Not:
#   - Convert arithmetic equivalence into a wall-clock speedup claim.
# - Allows:
#   - Inputs: widths 10 through 14 and every residual third-chunk operand pair.
#   - Outputs: exact padded constants and semantic-width projections.
#   - Side effects: none.
# - Split-When:
#   - Padding width or ternary crazy semantics changes.
# - Merge-When:
#   - Another proof owns the same zero-padded five-trit tail identity.
# - Summary:
#   - Prove a uniform 5+5+5 crazy representation preserves 10..14 semantics.
# - Description:
#   - Exhausts each possible short-tail pair and checks the constant high trits.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Semantic widths stop at 14; physical padding stops at 15 trits.
#

"""Evidence for exact zero-padded crazy chunk geometry."""

from __future__ import annotations

_MINIMUM_WIDTH = 10
_MAXIMUM_WIDTH = 14
_PADDED_WIDTH = 15
_CHUNK_TRITS = 5
_LOW_CHUNK_TRITS = 10
_RADIX = 3
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


def _padding_constant(width: int) -> int:
    return (
        _integer_power(_RADIX, _PADDED_WIDTH)
        - _integer_power(_RADIX, width)
    ) // (_RADIX - 1)


def test_zero_padding_adds_exact_constant_high_trits() -> None:
    """Every zero-padded high trit contributes the constant crazy(0,0)=1."""
    assert _CRAZY_TRIT[0][0] == 1
    for width in range(_MINIMUM_WIDTH, _MAXIMUM_WIDTH + 1):
        high_trits = _PADDED_WIDTH - width
        high_output = _crazy(0, 0, high_trits) * _integer_power(_RADIX, width)
        assert high_output == _padding_constant(width)
        assert _padding_constant(width) % (_integer_power(_RADIX, width)) == 0


def test_padded_tail_lookup_matches_native_tail_for_every_residue() -> None:
    """Every short third chunk is one five-trit lookup plus a fixed constant."""
    for width in range(_MINIMUM_WIDTH, _MAXIMUM_WIDTH + 1):
        tail_trits = width - _LOW_CHUNK_TRITS
        tail_modulus = _integer_power(_RADIX, tail_trits)
        tail_constant = (
            _integer_power(_RADIX, _CHUNK_TRITS)
            - _integer_power(_RADIX, tail_trits)
        ) // (_RADIX - 1)
        for data_tail in range(tail_modulus):
            for accumulator_tail in range(tail_modulus):
                native = _crazy(data_tail, accumulator_tail, tail_trits)
                padded = _crazy(data_tail, accumulator_tail, _CHUNK_TRITS)
                assert padded == native + tail_constant
                assert padded % tail_modulus == native


def test_three_chunk_projection_has_exact_profile_constant() -> None:
    """The padded third chunk differs from native semantics only by C_N."""
    third_place = _integer_power(_RADIX, _LOW_CHUNK_TRITS)
    for width in range(_MINIMUM_WIDTH, _MAXIMUM_WIDTH + 1):
        tail_trits = width - _LOW_CHUNK_TRITS
        tail_modulus = _integer_power(_RADIX, tail_trits)
        for data_tail in range(tail_modulus):
            for accumulator_tail in range(tail_modulus):
                native_tail = _crazy(data_tail, accumulator_tail, tail_trits)
                padded_tail = _crazy(
                    data_tail,
                    accumulator_tail,
                    _CHUNK_TRITS,
                )
                delta = third_place * (padded_tail - native_tail)
                assert delta == _padding_constant(width)
                assert delta % (_integer_power(_RADIX, width)) == 0
