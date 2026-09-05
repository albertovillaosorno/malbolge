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
#   - Differential evidence for exact finite atan2 ratio normalization.
# - Must-Not:
#   - Use host atan2, floating division, or approximate expected values.
# - Allows:
#   - Inputs: deterministic finite nonzero binary64 word pairs.
#   - Outputs: native C agreement with exact Fraction-derived kernel geometry.
#   - Side effects: temporary C harness compilation and execution only.
# - Split-When:
#   - Numerical atan approximation requires independent accuracy evidence.
# - Merge-When:
#   - Complete atan2 differential evidence subsumes exact input reduction.
# - Summary:
#   - Cross-checks finite atan2 kernel inputs over broad binary64 geometry.
# - Description:
#   - Expected ratios are reconstructed exactly as rational powers of two.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Public atan2 remains unavailable; this proves only kernel-input geometry.
#

"""Differential exact-ratio evidence for future binary64 atan2 kernels."""

from __future__ import annotations

from fractions import Fraction
from itertools import starmap
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
SIGN_BIT = 1 << 63
FRACTION_MASK = (1 << 52) - 1
HIDDEN_BIT = 1 << 52
SIGNIFICAND_BITS = 53
EXPONENT_MASK = 0x7FF
MIN_NORMAL_EXPONENT = -1022
ATAN_MARGIN_MAX_EXPONENT = -28
ALL_BITS = (1 << 64) - 1
VECTOR_COUNT = 512
LCG_MULTIPLIER = 6364136223846793005
LCG_INCREMENT = 1442695040888963407
LCG_SEED = 0x4154414E325F5631
SMALL_RATIO_LCG_SEED = 0x4154414E325F5352
SMALL_RATIO_VECTOR_COUNT = 512
EXPECTED_SMALL_RATIO_RESOLVED = 510
EXPECTED_SMALL_RATIO_UNRESOLVED = 2
RESOLVED_STATUS = 1
KERNEL_REQUIRED_STATUS = 2
ATAN_IDENTITY_MAX_BITS = 0x3E40000000000000
ATAN_IDENTITY_MAX = Fraction(1, 1 << 27)
ONE_BITS = 0x3FF0000000000000
THREE_BITS = 0x4008000000000000
EDGE_PAIRS = (
    (0x0000000000000001, 0x3FF0000000000000),
    (0x000FFFFFFFFFFFFF, 0x0010000000000000),
    (0x0010000000000000, 0x7FEFFFFFFFFFFFFF),
    (0x3FF0000000000000, 0x3FF0000000000000),
    (0x4000000000000000, 0x3FF0000000000000),
    (0xBFF8000000000000, 0x4004000000000000),
    (0x7FEFFFFFFFFFFFFF, 0x0000000000000001),
)


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


def _finite_nonzero(bits: int) -> bool:
    magnitude = bits & ~SIGN_BIT
    return magnitude != 0 and (magnitude >> 52) & EXPONENT_MASK != EXPONENT_MASK


def _deterministic_pairs() -> tuple[tuple[int, int], ...]:
    state = LCG_SEED
    pairs = list(EDGE_PAIRS)
    while len(pairs) < VECTOR_COUNT + len(EDGE_PAIRS):
        state = (state * LCG_MULTIPLIER + LCG_INCREMENT) & ALL_BITS
        y_bits = state
        state = (state * LCG_MULTIPLIER + LCG_INCREMENT) & ALL_BITS
        x_bits = state
        if _finite_nonzero(y_bits) and _finite_nonzero(x_bits):
            pairs.append((y_bits, x_bits))
    return tuple(pairs)


def _raw_fraction(bits: int) -> Fraction:
    magnitude = bits & ~SIGN_BIT
    raw_exponent = (magnitude >> 52) & EXPONENT_MASK
    fraction = magnitude & FRACTION_MASK
    if raw_exponent == 0:
        return Fraction(fraction, 1 << 1074)
    significand = HIDDEN_BIT | fraction
    exponent = raw_exponent - 1023 - 52
    if exponent >= 0:
        return Fraction(significand << exponent, 1)
    return Fraction(significand, 1 << -exponent)


def _normalized(bits: int) -> tuple[int, int]:
    magnitude = bits & ~SIGN_BIT
    raw_exponent = (magnitude >> 52) & EXPONENT_MASK
    significand = magnitude & FRACTION_MASK
    if raw_exponent == 0:
        exponent = -1074
    else:
        significand |= HIDDEN_BIT
        exponent = raw_exponent - 1023 - 52
    while significand.bit_length() < SIGNIFICAND_BITS:
        significand <<= 1
        exponent -= 1
    return significand, exponent


def _ordered_bits(y_bits: int, x_bits: int) -> tuple[int, int, int]:
    y_magnitude = y_bits & ~SIGN_BIT
    x_magnitude = x_bits & ~SIGN_BIT
    if y_magnitude > x_magnitude:
        return x_bits, y_bits, 1
    return y_bits, x_bits, 0


def _geometry_ratio(geometry: tuple[int, int, int, int, int, int]) -> Fraction:
    ratio = Fraction(geometry[0], geometry[1])
    if geometry[2] >= 0:
        return ratio * (1 << geometry[2])
    return ratio / (1 << -geometry[2])


def _expected(y_bits: int, x_bits: int) -> tuple[int, int, int, int, int, int]:
    numerator_bits, denominator_bits, swapped = _ordered_bits(y_bits, x_bits)
    numerator = _normalized(numerator_bits)
    denominator = _normalized(denominator_bits)
    result = (
        numerator[0],
        denominator[0],
        numerator[1] - denominator[1],
        swapped,
        int(bool(y_bits & SIGN_BIT)),
        int(bool(x_bits & SIGN_BIT)),
    )
    exact_ratio = min(_raw_fraction(y_bits), _raw_fraction(x_bits)) / max(
        _raw_fraction(y_bits), _raw_fraction(x_bits)
    )
    assert _geometry_ratio(result) == exact_ratio
    assert exact_ratio <= 1
    return result


def _floor_log2(value: Fraction) -> int:
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    if exponent >= 0:
        power = Fraction(1 << exponent, 1)
    else:
        power = Fraction(1, 1 << -exponent)
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


def _small_ratio_pairs() -> tuple[tuple[int, int], ...]:
    state = SMALL_RATIO_LCG_SEED
    pairs = [
        (ATAN_IDENTITY_MAX_BITS, ONE_BITS),
        (SIGN_BIT | ATAN_IDENTITY_MAX_BITS, ONE_BITS),
        (ATAN_IDENTITY_MAX_BITS + 1, ONE_BITS),
        (1, ONE_BITS),
        (ONE_BITS, 0x41A0000000000000),
    ]
    while len(pairs) < SMALL_RATIO_VECTOR_COUNT:
        state = (state * LCG_MULTIPLIER + LCG_INCREMENT) & ALL_BITS
        magnitude = 1 + state % ATAN_IDENTITY_MAX_BITS
        y_bits = magnitude | (SIGN_BIT if state & 1 else 0)
        x_bits = ONE_BITS if state & 2 else THREE_BITS
        pairs.append((y_bits, x_bits))
    return tuple(pairs)


def _small_ratio_rounding_margin_safe(ratio: Fraction) -> bool:
    exponent = _floor_log2(ratio)
    if exponent < MIN_NORMAL_EXPONENT or exponent > ATAN_MARGIN_MAX_EXPONENT:
        return False
    ulp = Fraction(1, 1 << (52 - exponent))
    scaled = ratio / ulp
    fraction = scaled - (scaled.numerator // scaled.denominator)
    return fraction < Fraction(1, 2) or fraction >= Fraction(2, 3)


def _expected_small_ratio_special(y_bits: int, x_bits: int) -> tuple[int, int]:
    ratio = _raw_fraction(y_bits) / _raw_fraction(x_bits)
    rounded = _nearest_binary64_bits(ratio)
    exactly_binary64 = _raw_fraction(rounded) == ratio
    safe = exactly_binary64 or _small_ratio_rounding_margin_safe(ratio)
    if ratio <= ATAN_IDENTITY_MAX and safe:
        return RESOLVED_STATUS, rounded | (y_bits & SIGN_BIT)
    return KERNEL_REQUIRED_STATUS, 0


def _small_ratio_row(y_bits: int, x_bits: int) -> str:
    status, bits = _expected_small_ratio_special(y_bits, x_bits)
    return (
        "  {"
        f"UINT64_C(0x{y_bits:016x}), UINT64_C(0x{x_bits:016x}), "
        f"UINT32_C({status}), UINT64_C(0x{bits:016x})"
        "}"
    )


def _small_ratio_harness_source() -> str:
    rows = ",\n".join(starmap(_small_ratio_row, _small_ratio_pairs()))
    return f"""#include \"math_transcendental_bits.h\"
#include <stdint.h>
typedef struct Vector {{
  uint64_t y_bits, x_bits;
  uint32_t status;
  uint64_t bits;
}} Vector;
static const Vector vectors[] = {{
{rows}
}};
int main(void) {{
  uint32_t i = 0;
  while (i < (uint32_t)(sizeof(vectors) / sizeof(vectors[0]))) {{
    const Vector *v = &vectors[i];
    const MalbolgeGuestMathSpecialResult result =
        malbolge_guest_math_atan2_special(v->y_bits, v->x_bits);
    if ((uint32_t)result.status != v->status || result.bits != v->bits) {{
      return 20;
    }}
    ++i;
  }}
  return 0;
}}
"""


def _row(y_bits: int, x_bits: int) -> str:
    numerator, denominator, delta, swapped, y_negative, x_negative = _expected(
        y_bits, x_bits
    )
    ratio = min(_raw_fraction(y_bits), _raw_fraction(x_bits)) / max(
        _raw_fraction(y_bits), _raw_fraction(x_bits)
    )
    rounded = _nearest_binary64_bits(ratio)
    return (
        "  {"
        f"UINT64_C(0x{y_bits:016x}), UINT64_C(0x{x_bits:016x}), "
        f"UINT64_C(0x{numerator:016x}), UINT64_C(0x{denominator:016x}), "
        f"INT32_C({delta}), UINT32_C({swapped}), UINT32_C({y_negative}), "
        f"UINT32_C({x_negative}), UINT64_C(0x{rounded:016x})"
        "}"
    )


def _harness_source() -> str:
    rows = ",\n".join(starmap(_row, _deterministic_pairs()))
    return f"""#include \"math_transcendental_bits.h\"
#include <stdint.h>
typedef struct Vector {{
  uint64_t y_bits, x_bits, numerator, denominator;
  int32_t delta;
  uint32_t swapped, y_negative, x_negative;
  uint64_t rounded;
}} Vector;
static const Vector vectors[] = {{
{rows}
}};
int main(void) {{
  uint32_t i = 0;
  while (i < (uint32_t)(sizeof(vectors) / sizeof(vectors[0]))) {{
    MalbolgeGuestMathAtan2KernelInput result;
    uint64_t rounded = UINT64_C(0);
    const Vector *v = &vectors[i];
    if (!malbolge_guest_math_atan2_kernel_input(
            v->y_bits, v->x_bits, &result) ||
        result.numerator_significand != v->numerator ||
        result.denominator_significand != v->denominator ||
        result.exponent_delta != v->delta || result.swapped != v->swapped ||
        result.y_negative != v->y_negative ||
        result.x_negative != v->x_negative ||
        !malbolge_guest_math_ratio_nearest_binary64(&result, &rounded) ||
        rounded != v->rounded) {{
      return 10;
    }}
    ++i;
  }}
  return 0;
}}
"""


def test_atan2_kernel_input_matches_exact_fraction_geometry(
    tmp_path: Path,
) -> None:
    """Match 519 exact ratios and nearest-even binary64 quotient bits."""
    harness = tmp_path / "atan2-kernel-input.c"
    executable = tmp_path / "atan2-kernel-input"
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


def test_atan2_small_ratio_classifier_matches_exact_fraction_gate(
    tmp_path: Path,
) -> None:
    """Resolve only exact binary64 ratios inside the proved atan interval."""
    harness = tmp_path / "atan2-small-ratio.c"
    executable = tmp_path / "atan2-small-ratio"
    _ = harness.write_text(_small_ratio_harness_source(), encoding="utf-8")
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


def test_small_ratio_policy_keeps_ambiguous_rounding_fail_closed() -> None:
    """Keep the bounded margin policy at 510 resolved and two unresolved."""
    statuses = [
        _expected_small_ratio_special(y_bits, x_bits)[0]
        for y_bits, x_bits in _small_ratio_pairs()
    ]
    assert statuses.count(RESOLVED_STATUS) == EXPECTED_SMALL_RATIO_RESOLVED
    assert (
        statuses.count(KERNEL_REQUIRED_STATUS)
        == EXPECTED_SMALL_RATIO_UNRESOLVED
    )
