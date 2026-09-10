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
#   - Fixed Q512 sub-four sine/cosine interval and final-rounding evidence.
# - Must-Not:
#   - Use host trigonometric functions or periodic range reduction.
# - Allows:
#   - Inputs: finite binary64 magnitudes above the cosine preproof and below 4.
#   - Outputs: Q512 directed intervals and uniquely rounded binary64 words.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Another precision layer needs an independent fixed resource policy.
# - Merge-When:
#   - Public sin/cos directly owns this fixed sub-four kernel.
# - Summary:
#   - Checks Q512/64 direct Taylor against exact Fraction enclosures.
# - Description:
#   - Exercises cutoffs, pi/2 and pi neighbors, near-four, and both signs.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - The interval is narrower than 2^52 Q512 ulps or fails closed.
#

"""Fixed Q512 sub-four sine/cosine evaluation evidence."""

from __future__ import annotations

import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
SIGN = 1 << 63
EXPONENT_MASK = 0x7FF
FRACTION_MASK = (1 << 52) - 1
HIDDEN = 1 << 52
EXPONENT_BIAS = 1023
Q512 = 1 << 512
ORACLE_TERMS = 90
SIN = 1
COS = 2
CASES = (
    (SIN, 0x3E46A00000000001),
    (COS, 0x3E46A00000000001),
    (SIN, 0x3E57000000000001),
    (SIN, 0x3FE0000000000000),
    (COS, 0x3FE0000000000000),
    (SIN, 0x3FF921FB54442D17),
    (COS, 0x3FF921FB54442D18),
    (COS, 0x3FF921FB54442D19),
    (SIN, 0x400921FB54442D17),
    (SIN, 0x400921FB54442D18),
    (SIN, 0x400921FB54442D19),
    (COS, 0x400FFFFFFFFFFFFF),
    (SIN, 0xBFF921FB54442D18),
    (COS, 0xC00921FB54442D18),
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


def _pow2(exponent: int) -> Fraction:
    if exponent >= 0:
        return Fraction(1 << exponent, 1)
    return Fraction(1, 1 << -exponent)


def _binary64_fraction(bits: int) -> Fraction:
    negative = bool(bits & SIGN)
    magnitude = bits & ~SIGN
    raw_exponent = (magnitude >> 52) & EXPONENT_MASK
    fraction = magnitude & FRACTION_MASK
    assert 0 < raw_exponent < EXPONENT_MASK
    significand = HIDDEN | fraction
    value = Fraction(significand) * _pow2(raw_exponent - EXPONENT_BIAS - 52)
    return -value if negative else value


def _round_integer(value: Fraction) -> int:
    quotient, remainder = divmod(value.numerator, value.denominator)
    twice = 2 * remainder
    if twice > value.denominator or (
        twice == value.denominator and bool(quotient & 1)
    ):
        quotient += 1
    return quotient


def _floor_log2(value: Fraction) -> int:
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    return exponent - 1 if value < _pow2(exponent) else exponent


def _binary64_bits(value: Fraction) -> int:
    negative = value < 0
    magnitude = abs(value)
    if magnitude == 0:
        return SIGN if negative else 0
    if magnitude < _pow2(-1022):
        quantized = _round_integer(magnitude / _pow2(-1074))
        bits = HIDDEN if quantized == HIDDEN else quantized
    else:
        exponent = _floor_log2(magnitude)
        quantized = _round_integer(magnitude / _pow2(exponent - 52))
        if quantized == 1 << 53:
            quantized >>= 1
            exponent += 1
        bits = ((exponent + EXPONENT_BIAS) << 52) | (quantized & FRACTION_MASK)
    return bits | (SIGN if negative else 0)


def _positive_taylor_bounds(
    value: Fraction,
    *,
    cosine: bool,
) -> tuple[Fraction, Fraction]:
    square = value * value
    term = Fraction(1) if cosine else value
    total = term
    for index in range(1, ORACLE_TERMS):
        left = 2 * index - 1 if cosine else 2 * index
        right = 2 * index if cosine else 2 * index + 1
        term = term * square / (left * right)
        total = total - term if index & 1 else total + term
    next_index = ORACLE_TERMS
    left = 2 * next_index - 1 if cosine else 2 * next_index
    right = 2 * next_index if cosine else 2 * next_index + 1
    omitted = term * square / (left * right)
    return (total, total + omitted) if ORACLE_TERMS % 2 == 0 else (
        total - omitted,
        total,
    )


def _oracle(operation: int, bits: int) -> tuple[Fraction, Fraction, int]:
    value = _binary64_fraction(bits)
    magnitude = abs(value)
    lower, upper = _positive_taylor_bounds(magnitude, cosine=operation == COS)
    if operation == SIN and value < 0:
        lower, upper = -upper, -lower
    lower_bits = _binary64_bits(lower)
    upper_bits = _binary64_bits(upper)
    assert lower_bits == upper_bits
    return lower, upper, lower_bits


def _source() -> str:
    rows = ",\n".join(
        f"  {{UINT32_C({operation}), UINT64_C(0x{bits:016x})}}"
        for operation, bits in CASES
    )
    return f'''#include "math_transcendental_bits.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
typedef struct Case {{ uint32_t operation; uint64_t bits; }} Case;
static const Case cases[] = {{
{rows}
}};
static void print_fixed(const MalbolgeGuestMathFixed512 *value) {{
  uint32_t index = MALBOLGE_GUEST_MATH_FIXED_512_LIMBS;
  while (index != UINT32_C(0)) {{
    --index;
    (void)printf("%08" PRIx32, value->limbs[index]);
  }}
}}
int main(void) {{
  uint32_t scratch[MALBOLGE_GUEST_MATH_SUBFOUR_Q512_SCRATCH_LIMBS];
  uint32_t index = UINT32_C(0);
  (void)printf("terms=%u scratch=%u widthbits=%u\\n",
      MALBOLGE_GUEST_MATH_SUBFOUR_Q512_TAYLOR_TERMS,
      MALBOLGE_GUEST_MATH_SUBFOUR_Q512_SCRATCH_LIMBS,
      MALBOLGE_GUEST_MATH_SUBFOUR_Q512_WIDTH_ULP_BITS_MAX);
  while (index < (uint32_t)(sizeof(cases) / sizeof(cases[0]))) {{
    MalbolgeGuestMathSincosInterval512 interval;
    uint64_t result = UINT64_C(0);
    if (!malbolge_guest_math_sincos_subfour_interval512(
            cases[index].bits, &interval, scratch,
            MALBOLGE_GUEST_MATH_SUBFOUR_Q512_SCRATCH_LIMBS) ||
        !malbolge_guest_math_sincos_subfour_unique_binary64_q512(
            (MalbolgeGuestMathUnaryOperation)cases[index].operation,
            cases[index].bits, &result, scratch,
            MALBOLGE_GUEST_MATH_SUBFOUR_Q512_SCRATCH_LIMBS)) return 80;
    (void)printf("%u %016" PRIx64 " %016" PRIx64 " %u ",
                 cases[index].operation, cases[index].bits, result,
                 interval.sin.lower_negative);
    print_fixed(&interval.sin.lower);
    (void)printf(" %u ", interval.sin.upper_negative);
    print_fixed(&interval.sin.upper);
    (void)printf(" %u ", interval.cos.lower_negative);
    print_fixed(&interval.cos.lower);
    (void)printf(" %u ", interval.cos.upper_negative);
    print_fixed(&interval.cos.upper); (void)printf("\\n");
    ++index;
  }}
  {{
    MalbolgeGuestMathSincosInterval512 value;
    uint64_t result = UINT64_C(0xdeadbeef);
    value.sin.lower.limbs[0] = UINT32_C(0x12345678);
    if (malbolge_guest_math_sincos_subfour_interval512(
            UINT64_C(0x3e46a00000000000), &value, scratch,
            MALBOLGE_GUEST_MATH_SUBFOUR_Q512_SCRATCH_LIMBS) ||
        value.sin.lower.limbs[0] != UINT32_C(0x12345678) ||
        malbolge_guest_math_sincos_subfour_interval512(
            UINT64_C(0x4010000000000000), &value, scratch,
            MALBOLGE_GUEST_MATH_SUBFOUR_Q512_SCRATCH_LIMBS) ||
        malbolge_guest_math_sincos_subfour_interval512(
            UINT64_C(0x3ff0000000000000), &value, scratch,
            MALBOLGE_GUEST_MATH_SUBFOUR_Q512_SCRATCH_LIMBS - UINT32_C(1)) ||
        malbolge_guest_math_sincos_subfour_unique_binary64_q512(
            (MalbolgeGuestMathUnaryOperation)UINT32_C(9),
            UINT64_C(0x3ff0000000000000), &result, scratch,
            MALBOLGE_GUEST_MATH_SUBFOUR_Q512_SCRATCH_LIMBS) ||
        result != UINT64_C(0xdeadbeef)) return 81;
  }}
  return 0;
}}
'''


def _signed(magnitude: str, negative: str) -> int:
    value = int(magnitude, 16)
    return -value if int(negative) else value


def test_subfour_q512_contains_fraction_and_rounds_uniquely(
    tmp_path: Path,
) -> None:
    """Enclose exact Taylor authority and publish the same binary64 word."""
    harness = tmp_path / "subfour-q512.c"
    binary = tmp_path / "subfour-q512"
    _ = harness.write_text(_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG), "-std=c23", "-O2", "-ffreestanding", "-fno-builtin",
            "-Wall", "-Wextra", "-Wpedantic", "-Werror", f"-I{CONTRACT}",
            str(SOURCE), str(harness), "-o", str(binary),
        ],
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    executed = _run([str(binary)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr
    lines = executed.stdout.splitlines()
    assert lines[0] == "terms=64 scratch=187 widthbits=52"
    records = tuple(tuple(line.split()) for line in lines[1:])
    assert len(records) == len(CASES)
    for (operation, bits), row in zip(CASES, records, strict=True):
        lower, upper, expected_bits = _oracle(operation, bits)
        assert int(row[0]) == operation
        assert int(row[1], 16) == bits
        assert int(row[2], 16) == expected_bits
        offset = 3 if operation == SIN else 7
        c_lower = Fraction(_signed(row[offset + 1], row[offset]), Q512)
        c_upper = Fraction(_signed(row[offset + 3], row[offset + 2]), Q512)
        assert c_lower <= lower <= upper <= c_upper
        assert (c_upper - c_lower) < Fraction(1, 1 << 460)
