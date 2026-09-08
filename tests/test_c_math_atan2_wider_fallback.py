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
#   - Independent evidence for the wider integer atan2 rounding fallback.
# - Must-Not:
#   - Treat proposal searches, host transcendental functions, Q32.224, or the
#     kernel-input oracle as rounding authority for Q32.256.
# - Allows:
#   - Inputs: retained positive finite binary64 hard-rounding pairs.
#   - Outputs: exact-rational enclosure and binary64 agreement for Q32.256.
#   - Side effects: temporary C harness compilation and execution only.
# - Split-When:
#   - A fourth precision or adaptive termination proof gains its own
#     implementation contract.
# - Merge-When:
#   - Complete correctly-rounded atan2 evidence subsumes the fallback ladder.
# - Summary:
#   - Certifies the Q32.256 fallback independently of the Q32.224 evaluator.
# - Description:
#   - Uses Machin 56/16 and 98-term rational atan bounds as its authority.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Q32.256 remains fail closed when its endpoints do not round identically.
#

"""Independent exact-rational evidence for the Q32.256 atan2 fallback."""

from __future__ import annotations

from fractions import Fraction
from functools import cache
from itertools import starmap
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
SIGN_BIT = 1 << 63
FRACTION_MASK = (1 << 52) - 1
EXPONENT_MASK = 0x7FF
HIDDEN_BIT = 1 << 52
MIN_NORMAL_EXPONENT = -1022
FIXED_BITS = 256
PI_FIFTH_TERMS = 56
PI_239_TERMS = 16
ATAN_TERMS = 98
ATAN_CUT = Fraction(169, 408)
TRANSFORMED_HARD_PAIRS = (
    (0x3FEE19FA869EA9FC, 0x3FF197DD31B21770),
    (0x3FE74E55173F69A0, 0x3FF6943B1C1EE532),
    (0x3FEF179200C72129, 0x3FFBC1B4128CF396),
    (0x3FE97B1DB9A2A48C, 0x3FF781CE6A6EE8EF),
    (0x3FE9519856F5242F, 0x3FF06C408C434F0E),
    (0x3FEF7590E09E2ADD, 0x3FF629E5895F91A7),
    (0x3FE5139B1425C8A2, 0x3FF4FA0C073AF8F1),
    (0x3FE549E587E6D4CD, 0x3FF11E3639F76651),
)
DIRECT_HARD_PAIRS = (
    (0x3FD75B9A8D0A0447, 0x3FF069F1CC6166FC),
    (0x3FDF65E15A3E11FD, 0x3FF31E45227A22DE),
    (0x3FDEF69FB021F2DB, 0x3FF90CC971F74C07),
    (0x3FDABB28E6EEF14A, 0x3FF544C4908DDACE),
    (0x3FD94D130BF48845, 0x3FF2CCCC5A36B6E1),
    (0x3FD667E2DB48932E, 0x3FF41B5A664E9573),
    (0x3FDBA787A32EAF18, 0x3FF914A595604C36),
    (0x3FD88C55EA9394D5, 0x3FF6ABB1E310A1AC),
)
HARD_PAIRS = TRANSFORMED_HARD_PAIRS + DIRECT_HARD_PAIRS
LCG_MULTIPLIER = 6364136223846793005
LCG_INCREMENT = 1442695040888963407
LCG_SEED = 0x4154414E325F5631
ALL_BITS = (1 << 64) - 1
REFINEMENT_PAIR_COUNT = 512


def _run(command: list[str], cwd: Path) -> sp.CompletedProcess[str]:
    return sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        shell=False,
        text=True,
        timeout=30,
    )


def _raw_fraction(bits: int) -> Fraction:
    magnitude = bits & ~SIGN_BIT
    raw_exponent = (magnitude >> 52) & EXPONENT_MASK
    fraction = magnitude & FRACTION_MASK
    assert raw_exponent not in {0, EXPONENT_MASK}
    significand = HIDDEN_BIT | fraction
    shift = raw_exponent - 1023 - 52
    if shift >= 0:
        return Fraction(significand << shift, 1)
    return Fraction(significand, 1 << -shift)


def _alternating_atan_interval(
    value: Fraction, terms: int
) -> tuple[Fraction, Fraction]:
    total = Fraction(0)
    square = value * value
    power = value
    for index in range(terms):
        term = power / ((2 * index) + 1)
        total = total + term if index % 2 == 0 else total - term
        power *= square
    remainder = power / ((2 * terms) + 1)
    if terms % 2 == 0:
        return total, total + remainder
    return total - remainder, total


@cache
def _quarter_pi_interval() -> tuple[Fraction, Fraction]:
    fifth = _alternating_atan_interval(Fraction(1, 5), PI_FIFTH_TERMS)
    one_239 = _alternating_atan_interval(Fraction(1, 239), PI_239_TERMS)
    return (4 * fifth[0]) - one_239[1], (4 * fifth[1]) - one_239[0]


def _principal_interval(y_bits: int, x_bits: int) -> tuple[Fraction, Fraction]:
    assert y_bits & SIGN_BIT == 0
    assert x_bits & SIGN_BIT == 0
    ratio = _raw_fraction(y_bits) / _raw_fraction(x_bits)
    assert 0 < ratio < 1
    if ratio < ATAN_CUT:
        return _alternating_atan_interval(ratio, ATAN_TERMS)
    transformed = (1 - ratio) / (1 + ratio)
    assert 0 < transformed < ATAN_CUT
    atan_lower, atan_upper = _alternating_atan_interval(
        transformed, ATAN_TERMS
    )
    quarter_lower, quarter_upper = _quarter_pi_interval()
    return quarter_lower - atan_upper, quarter_upper - atan_lower


def _floor_log2(value: Fraction) -> int:
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    power = Fraction(1 << exponent, 1) if exponent >= 0 else Fraction(
        1, 1 << -exponent
    )
    return exponent - 1 if value < power else exponent


def _round_quotient(numerator: int, denominator: int) -> int:
    quotient, remainder = divmod(numerator, denominator)
    doubled = remainder * 2
    if doubled > denominator or (doubled == denominator and quotient & 1):
        quotient += 1
    return quotient


def _nearest_binary64_bits(value: Fraction) -> int:
    exponent = _floor_log2(value)
    if exponent < MIN_NORMAL_EXPONENT:
        return _round_quotient(value.numerator << 1074, value.denominator)
    shift = 52 - exponent
    if shift >= 0:
        significand = _round_quotient(
            value.numerator << shift, value.denominator
        )
    else:
        significand = _round_quotient(
            value.numerator, value.denominator << -shift
        )
    if significand == 1 << 53:
        significand >>= 1
        exponent += 1
    return ((exponent + 1023) << 52) | (significand - HIDDEN_BIT)


def _finite_nonzero(bits: int) -> bool:
    magnitude = bits & ~SIGN_BIT
    exponent = (magnitude >> 52) & EXPONENT_MASK
    return magnitude != 0 and exponent != EXPONENT_MASK


def _refinement_pairs() -> tuple[tuple[int, int], ...]:
    state = LCG_SEED
    pairs: list[tuple[int, int]] = []
    while len(pairs) < REFINEMENT_PAIR_COUNT:
        state = (state * LCG_MULTIPLIER + LCG_INCREMENT) & ALL_BITS
        y_bits = state
        state = (state * LCG_MULTIPLIER + LCG_INCREMENT) & ALL_BITS
        x_bits = state
        if _finite_nonzero(y_bits) and _finite_nonzero(x_bits):
            pairs.append((y_bits, x_bits))
    return tuple(pairs)


def _refinement_harness_source() -> str:
    rows = ",\n".join(
        f"  {{UINT64_C(0x{y:016x}), UINT64_C(0x{x:016x})}}"
        for y, x in _refinement_pairs()
    )
    return f"""#include "math_transcendental_bits.h"
#include <stdint.h>
typedef struct Pair {{ uint64_t y, x; }} Pair;
static const Pair pairs[] = {{
{rows}
}};
static int compare_256_to_224_shifted(
    const MalbolgeGuestMathFixed256 *wide,
    const MalbolgeGuestMathFixed224 *narrow) {{
  uint32_t index = UINT32_C(9);
  while (index != UINT32_C(0)) {{
    uint32_t rhs = UINT32_C(0);
    --index;
    if (index != UINT32_C(0)) rhs = narrow->limbs[index - UINT32_C(1)];
    if (wide->limbs[index] < rhs) return -1;
    if (wide->limbs[index] > rhs) return 1;
  }}
  return 0;
}}
int main(void) {{
  uint32_t index = UINT32_C(0);
  while (index < (uint32_t)(sizeof(pairs) / sizeof(pairs[0]))) {{
    MalbolgeGuestMathAtan2Interval224 q224;
    MalbolgeGuestMathAtan2Interval256 q256;
    if (!malbolge_guest_math_atan2_interval224(
            pairs[index].y, pairs[index].x, &q224) ||
        !malbolge_guest_math_atan2_interval256(
            pairs[index].y, pairs[index].x, &q256) ||
        q224.negative != q256.negative ||
        compare_256_to_224_shifted(&q256.magnitude.lower,
                                   &q224.magnitude.lower) < 0 ||
        compare_256_to_224_shifted(&q256.magnitude.upper,
                                   &q224.magnitude.upper) > 0) {{
      return 90;
    }}
    ++index;
  }}
  return index == UINT32_C({REFINEMENT_PAIR_COUNT}) ? 0 : 91;
}}
"""


def _scaled_bounds(lower: Fraction, upper: Fraction) -> tuple[int, int]:
    scale = 1 << FIXED_BITS
    lower_floor = (lower.numerator * scale) // lower.denominator
    upper_scaled = upper * scale
    upper_floor, remainder = divmod(
        upper_scaled.numerator, upper_scaled.denominator
    )
    return lower_floor, upper_floor + int(remainder != 0)


def _limbs(value: int) -> str:
    encoded = (
        (value >> (32 * index)) & 0xFFFFFFFF for index in range(9)
    )
    return "{" + ", ".join(
        f"UINT32_C(0x{limb:08x})" for limb in encoded
    ) + "}"


def _row(y_bits: int, x_bits: int) -> str:
    lower, upper = _principal_interval(y_bits, x_bits)
    lower_floor, upper_ceil = _scaled_bounds(lower, upper)
    lower_bits = _nearest_binary64_bits(lower)
    upper_bits = _nearest_binary64_bits(upper)
    assert lower_bits == upper_bits
    return (
        f"  {{UINT64_C(0x{y_bits:016x}), UINT64_C(0x{x_bits:016x}), "
        f"{_limbs(lower_floor)}, {_limbs(upper_ceil)}, "
        f"UINT64_C(0x{lower_bits:016x})}}"
    )


def _harness_source() -> str:
    rows = ",\n".join(starmap(_row, HARD_PAIRS))
    return f"""#include \"math_transcendental_bits.h\"
#include <stdint.h>
typedef struct Vector {{
  uint64_t y_bits, x_bits;
  uint32_t lower_floor[9], upper_ceil[9];
  uint64_t expected_bits;
}} Vector;
static const Vector vectors[] = {{
{rows}
}};
static int compare_fixed(const MalbolgeGuestMathFixed256 *value,
                         const uint32_t expected[9]) {{
  uint32_t index = MALBOLGE_GUEST_MATH_FIXED_256_LIMBS;
  while (index != 0) {{
    --index;
    if (value->limbs[index] < expected[index]) return -1;
    if (value->limbs[index] > expected[index]) return 1;
  }}
  return 0;
}}
int main(void) {{
  uint32_t index = UINT32_C(0);
  while (index < (uint32_t)(sizeof(vectors) / sizeof(vectors[0]))) {{
    const Vector *v = &vectors[index];
    MalbolgeGuestMathAtan2Interval256 interval;
    uint64_t magnitude_bits = UINT64_C(0);
    uint64_t output_bits = UINT64_C(0);
    if (!malbolge_guest_math_atan2_interval256(v->y_bits, v->x_bits,
                                               &interval) ||
        compare_fixed(&interval.magnitude.lower, v->lower_floor) > 0 ||
        compare_fixed(&interval.magnitude.upper, v->upper_ceil) < 0 ||
        interval.negative != UINT32_C(0) ||
        !malbolge_guest_math_fixed256_unique_binary64(&interval.magnitude,
                                                      &magnitude_bits) ||
        magnitude_bits != v->expected_bits ||
        !malbolge_guest_math_atan2_unique_binary64(v->y_bits, v->x_bits,
                                                   &output_bits) ||
        output_bits != v->expected_bits) {{
      return 86;
    }}
    ++index;
  }}
  return index == UINT32_C({len(HARD_PAIRS)}) ? 0 : 87;
}}
"""


def _atan_remainder_bound(value: Fraction, terms: int) -> Fraction:
    first_omitted = (2 * terms) + 1
    return value**first_omitted / first_omitted


def _ceil_fixed(value: Fraction, bits: int) -> Fraction:
    scale = 1 << bits
    scaled = value * scale
    floor, remainder = divmod(scaled.numerator, scaled.denominator)
    return Fraction(floor + int(remainder != 0), scale)


def test_q256_constants_and_series_have_proved_headroom() -> None:
    """Prove wider pi and atan truncation bounds fit the Q32.256 grid."""
    lower, upper = _quarter_pi_interval()
    encoded_cut = _ceil_fixed(ATAN_CUT, FIXED_BITS)
    assert upper - lower < Fraction(1, 1 << 264)
    assert _atan_remainder_bound(ATAN_CUT, 97) >= Fraction(1, 1 << 256)
    assert _atan_remainder_bound(encoded_cut, 98) < Fraction(1, 1 << 256)


def test_q256_interval_encloses_and_rounds_independent_hard_cases(
    tmp_path: Path,
) -> None:
    """Enclose and round 16 direct/transformed cases with exact authority."""
    harness = tmp_path / "atan2-q256.c"
    executable = tmp_path / "atan2-q256"
    _ = harness.write_text(_harness_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            "-Wall",
            "-Wextra",
            "-Wpedantic",
            "-Werror",
            f"-I{CONTRACT}",
            str(SOURCE),
            str(harness),
            "-o",
            str(executable),
        ],
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    executed = _run([str(executable)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr


def test_q256_refines_q192_over_deterministic_corpus(tmp_path: Path) -> None:
    """Require the wider enclosure to be a Q32.224 subinterval."""
    harness = tmp_path / "atan2-q256-refinement.c"
    executable = tmp_path / "atan2-q256-refinement"
    _ = harness.write_text(_refinement_harness_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            "-Wall",
            "-Wextra",
            "-Wpedantic",
            "-Werror",
            f"-I{CONTRACT}",
            str(SOURCE),
            str(harness),
            "-o",
            str(executable),
        ],
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    executed = _run([str(executable)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr
