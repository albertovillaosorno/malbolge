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
#   - Q512 Payne-Hanek residual refinement and half-pi provenance.
# - Must-Not:
#   - Use host pi/libm or claim Q512 is a full-domain precision ceiling.
# - Allows:
#   - Inputs: finite raw binary64 words with magnitude at least four.
#   - Outputs: quadrant, original sign, and directed signed Q512 residuals.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Adaptive periodic Taylor/rounding consumes Q512 residuals directly.
# - Merge-When:
#   - A generic variable-width periodic reducer subsumes fixed Q512.
# - Summary:
#   - Regenerates half-pi and checks 53x2176 extraction through max-finite.
# - Description:
#   - Fraction verifies every Q512 endpoint independently of guest C.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Q256 remains the first periodic attempt; Q512 is refinement evidence.
#

"""Q512 Payne-Hanek refinement evidence for periodic sin/cos."""

from __future__ import annotations

import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
SIGN = 1 << 63
MAGNITUDE = SIGN - 1
FRACTION_MASK = (1 << 52) - 1
EXPONENT_MASK = 0x7FF
HIDDEN = 1 << 52
FOUR = 0x4010000000000000
MAX_FINITE = 0x7FEFFFFFFFFFFFFF
Q512 = 1 << 512
ATAN5_TERMS = 400
ATAN239_TERMS = 120
CASE_COUNT = 96
RESIDUAL_ULPS_MAX = 6
OBSERVED_ULPS_MAX = 4


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


def _atan_bounds(denominator: int, terms: int) -> tuple[Fraction, Fraction]:
    x = Fraction(1, denominator)
    square = x * x
    term = x
    total = Fraction(0)
    for index in range(terms):
        contribution = term / (2 * index + 1)
        total = total + contribution if index % 2 == 0 else total - contribution
        term *= square
    omitted = term / (2 * terms + 1)
    return (
        (total, total + omitted)
        if terms % 2 == 0
        else (total - omitted, total)
    )


def _pi_bounds() -> tuple[Fraction, Fraction]:
    a5_lo, a5_hi = _atan_bounds(5, ATAN5_TERMS)
    a239_lo, a239_hi = _atan_bounds(239, ATAN239_TERMS)
    return 16 * a5_lo - 4 * a239_hi, 16 * a5_hi - 4 * a239_lo


PI_LOWER, PI_UPPER = _pi_bounds()
# Even the largest quotient must amplify the Machin enclosure by less than
# one Q512 cell; otherwise this oracle could not certify directed residuals.
assert (PI_UPPER - PI_LOWER) * (1 << 1025) * Q512 < 1


def _components(bits: int) -> tuple[int, int]:
    magnitude = bits & MAGNITUDE
    exponent = (magnitude >> 52) & EXPONENT_MASK
    fraction = magnitude & FRACTION_MASK
    assert 0 < exponent < EXPONENT_MASK
    return HIDDEN | fraction, exponent - 1023 - 52


def _binary64_magnitude(bits: int) -> Fraction:
    significand, power = _components(bits)
    return (
        Fraction(significand << power, 1)
        if power >= 0
        else Fraction(significand, 1 << -power)
    )


def _nearest_even(value: Fraction) -> int:
    quotient, remainder = divmod(value.numerator, value.denominator)
    twice = 2 * remainder
    if twice > value.denominator or (
        twice == value.denominator and bool(quotient & 1)
    ):
        quotient += 1
    return quotient


def _quantize_signed(value: Fraction, *, lower: bool) -> tuple[int, int]:
    negative = value < 0
    scaled = abs(value) * Q512
    magnitude, remainder = divmod(scaled.numerator, scaled.denominator)
    if negative and lower and remainder:
        magnitude += 1
    if not negative and not lower and remainder:
        magnitude += 1
    return magnitude, int(negative and magnitude != 0)


def _oracle(bits: int) -> tuple[int, int, int, int, int, int]:
    value = _binary64_magnitude(bits)
    q_lo = _nearest_even(2 * value / PI_UPPER)
    q_hi = _nearest_even(2 * value / PI_LOWER)
    assert q_lo == q_hi
    residual_lower = value - Fraction(q_lo, 2) * PI_UPPER
    residual_upper = value - Fraction(q_lo, 2) * PI_LOWER
    low_mag, low_neg = _quantize_signed(residual_lower, lower=True)
    high_mag, high_neg = _quantize_signed(residual_upper, lower=False)
    return (
        q_lo & 3,
        int(bool(bits & SIGN)),
        low_mag,
        low_neg,
        high_mag,
        high_neg,
    )


def _cases() -> tuple[int, ...]:
    rows = [FOUR, FOUR + 1, 0x43F0000000000000, MAX_FINITE]
    state = 0x513531325041594E
    while len(rows) < CASE_COUNT:
        state = (state * 6364136223846793005 + 1442695040888963407) & MAGNITUDE
        exponent = 1025 + ((state >> 55) % 1022)
        fraction = (state >> 3) & FRACTION_MASK
        bits = (exponent << 52) | fraction
        rows.append(bits | (SIGN if state & 1 else 0))
    return tuple(rows)


CASES = _cases()


def _source() -> str:
    rows = ",\n".join(f"  UINT64_C(0x{bits:016x})" for bits in CASES)
    return f"""#include "math_transcendental_bits.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
static const uint64_t cases[] = {{
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
  uint32_t index = UINT32_C(0);
  MalbolgeGuestMathFixed512Interval half_pi;
  if (!malbolge_guest_math_half_pi_interval512(&half_pi)) return 79;
  print_fixed(&half_pi.lower);
  (void)printf(" ");
  print_fixed(&half_pi.upper);
  (void)printf("\\n");
  while (index < (uint32_t)(sizeof(cases) / sizeof(cases[0]))) {{
    MalbolgeGuestMathSincosPayneHanek512 value;
    if (!malbolge_guest_math_sincos_payne_hanek_reduce512(
            cases[index], &value)) return 80;
    (void)printf("%016" PRIx64 " %u %u %u %u ", cases[index],
                 value.quadrant, value.input_negative,
                 value.residual_lower_negative, value.residual_upper_negative);
    print_fixed(&value.residual_lower);
    (void)printf(" ");
    print_fixed(&value.residual_upper);
    (void)printf("\\n");
    ++index;
  }}
  {{
    MalbolgeGuestMathSincosPayneHanek512 value = {{
        UINT32_C(9), UINT32_C(8), {{UINT32_C(7)}}, UINT32_C(6),
        {{UINT32_C(5)}}, UINT32_C(4)}};
    const uint64_t bad[] = {{
        UINT64_C(0x400fffffffffffff), UINT64_C(0x7ff0000000000000),
        UINT64_C(0x7ff8000000000001)}};
    index = UINT32_C(0);
    while (index < UINT32_C(3)) {{
      if (malbolge_guest_math_sincos_payne_hanek_reduce512(
              bad[index], &value) || value.quadrant != UINT32_C(9) ||
          value.residual_lower.limbs[0] != UINT32_C(7) ||
          value.residual_upper.limbs[0] != UINT32_C(5)) return 81;
      ++index;
    }}
  }}
  return 0;
}}
"""


def _compile_and_run(tmp_path: Path) -> tuple[tuple[str, ...], ...]:
    source = tmp_path / "payne-hanek512.c"
    binary = tmp_path / "payne-hanek512"
    _ = source.write_text(_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG), "-std=c23", "-O2", "-ffreestanding", "-fno-builtin",
            "-Wall", "-Wextra", "-Wpedantic", "-Werror", f"-I{CONTRACT}",
            str(SOURCE), str(source), "-o", str(binary),
        ],
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    executed = _run([str(binary)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr
    return tuple(tuple(line.split()) for line in executed.stdout.splitlines())


def _signed(magnitude: int, negative: int) -> int:
    return -magnitude if negative else magnitude


def test_q512_half_pi_and_payne_hanek_match_fraction_machin(
    tmp_path: Path,
) -> None:
    """Match the Q512 constant, quadrant, and residual through max-finite."""
    records = _compile_and_run(tmp_path)
    half_lo = (PI_LOWER * Q512 // 2)
    half_hi_value = PI_UPPER * Q512 / 2
    half_hi = (
        half_hi_value.numerator + half_hi_value.denominator - 1
    ) // half_hi_value.denominator
    assert int(records[0][0], 16) == half_lo
    assert int(records[0][1], 16) == half_hi
    assert half_hi - half_lo == 1
    assert len(records) == len(CASES) + 1
    observed_width = 0
    for bits, record in zip(CASES, records[1:], strict=True):
        expected = _oracle(bits)
        assert int(record[0], 16) == bits
        assert int(record[1]) == expected[0]
        assert int(record[2]) == expected[1]
        c_lower = _signed(int(record[5], 16), int(record[3]))
        c_upper = _signed(int(record[6], 16), int(record[4]))
        oracle_lower = _signed(expected[2], expected[3])
        oracle_upper = _signed(expected[4], expected[5])
        assert c_lower <= oracle_lower <= oracle_upper <= c_upper
        observed_width = max(observed_width, c_upper - c_lower)
        assert c_upper - c_lower <= RESIDUAL_ULPS_MAX
    assert observed_width == OBSERVED_ULPS_MAX
