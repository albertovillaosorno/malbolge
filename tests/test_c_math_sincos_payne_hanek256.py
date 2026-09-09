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
#   - Full-domain Payne-Hanek quotient-mod-4 and Q256 residual evidence.
# - Must-Not:
#   - Use host pi/libm or assume the bounded u64-multiple reducer covers it.
# - Allows:
#   - Inputs: finite raw binary64 words with magnitude at least four.
#   - Outputs: quadrant, original sign, and a directed signed Q256 residual.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Full-domain trig evaluation/rounding needs independent evidence.
# - Merge-When:
#   - One public full-domain sin/cos handoff subsumes both reduction paths.
# - Summary:
#   - Checks exact 53x2176 extraction through max-finite against Machin bounds.
# - Description:
#   - Fraction independently proves quotient mod four and residual containment.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Inputs below four remain outside periodic reduction.
#

"""Full-domain Q2176 Payne-Hanek reduction evidence."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
SIGN = 1 << 63
MAGNITUDE = SIGN - 1
FRACTION_MASK = (1 << 52) - 1
EXPONENT_MASK = 0x7FF
HIDDEN = 1 << 52
TWO64 = 0x43F0000000000000
MAX_FINITE = 0x7FEFFFFFFFFFFFFF
Q256 = 1 << 256
ATAN5_TERMS = 1400
ATAN239_TERMS = 400
CASE_COUNT = 320


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
    if terms % 2 == 0:
        return total, total + omitted
    return total - omitted, total


def _pi_bounds() -> tuple[Fraction, Fraction]:
    a5_lo, a5_hi = _atan_bounds(5, ATAN5_TERMS)
    a239_lo, a239_hi = _atan_bounds(239, ATAN239_TERMS)
    return 16 * a5_lo - 4 * a239_hi, 16 * a5_hi - 4 * a239_lo


def _components(bits: int) -> tuple[int, int]:
    magnitude = bits & MAGNITUDE
    exponent = (magnitude >> 52) & EXPONENT_MASK
    fraction = magnitude & FRACTION_MASK
    assert 0 < exponent < EXPONENT_MASK
    return HIDDEN | fraction, exponent - 1023 - 52


def _binary64_magnitude(bits: int) -> Fraction:
    significand, power = _components(bits)
    if power >= 0:
        return Fraction(significand << power, 1)
    return Fraction(significand, 1 << -power)


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
    scaled = abs(value) * Q256
    magnitude, remainder = divmod(scaled.numerator, scaled.denominator)
    if negative and lower and remainder:
        magnitude += 1
    if not negative and not lower and remainder:
        magnitude += 1
    return magnitude, int(negative and magnitude != 0)


def _quotient(
    value: Fraction,
    pi_lower: Fraction,
    pi_upper: Fraction,
) -> int:
    quotient_lower = _nearest_even(2 * value / pi_upper)
    quotient_upper = _nearest_even(2 * value / pi_lower)
    assert quotient_lower == quotient_upper
    return quotient_lower


def _oracle(bits: int) -> tuple[int, int, int, int, int, int]:
    pi_lower, pi_upper = _pi_bounds()
    value = _binary64_magnitude(bits)
    multiple = _quotient(value, pi_lower, pi_upper)
    residuals = (
        value - Fraction(multiple, 2) * pi_upper,
        value - Fraction(multiple, 2) * pi_lower,
    )
    lower_mag, lower_neg = _quantize_signed(residuals[0], lower=True)
    upper_mag, upper_neg = _quantize_signed(residuals[1], lower=False)
    return (
        multiple & 3,
        int(bool(bits & SIGN)),
        lower_mag,
        lower_neg,
        upper_mag,
        upper_neg,
    )


def _cases() -> tuple[int, ...]:
    rows = [
        TWO64,
        TWO64 + 1,
        (1087 << 52) | FRACTION_MASK,
        (1500 << 52) | 0x123456789ABCD,
        (2000 << 52) | ((1 << 51) - 1),
        MAX_FINITE,
    ]
    state = 0x5041594E4548414E
    while len(rows) < CASE_COUNT:
        state = (state * 6364136223846793005 + 1442695040888963407) & (
            (1 << 64) - 1
        )
        exponent = 1087 + ((state >> 57) % 960)
        fraction = (state >> 5) & FRACTION_MASK
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
static void print_fixed(const MalbolgeGuestMathFixed256 *value) {{
  uint32_t index = MALBOLGE_GUEST_MATH_FIXED_256_LIMBS;
  while (index != UINT32_C(0)) {{
    --index;
    (void)printf("%08" PRIx32, value->limbs[index]);
  }}
}}
int main(void) {{
  uint32_t index = UINT32_C(0);
  while (index < (uint32_t)(sizeof(cases) / sizeof(cases[0]))) {{
    MalbolgeGuestMathSincosPayneHanek256 value;
    if (!malbolge_guest_math_sincos_payne_hanek_reduce256(
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
    MalbolgeGuestMathSincosPayneHanek256 value = {{
        UINT32_C(9), UINT32_C(8), {{UINT32_C(7)}}, UINT32_C(6),
        {{UINT32_C(5)}}, UINT32_C(4)}};
    const uint64_t bad[] = {{
        UINT64_C(0x400fffffffffffff), UINT64_C(0x7ff0000000000000),
        UINT64_C(0x7ff8000000000001)}};
    index = UINT32_C(0);
    while (index < UINT32_C(3)) {{
      if (malbolge_guest_math_sincos_payne_hanek_reduce256(
              bad[index], &value) || value.quadrant != UINT32_C(9) ||
          value.residual_lower.limbs[0] != UINT32_C(7) ||
          value.residual_upper.limbs[0] != UINT32_C(5)) return 81;
      ++index;
    }}
    if (malbolge_guest_math_sincos_payne_hanek_reduce256(
            UINT64_C(0x4010000000000000), 0)) return 82;
  }}
  return 0;
}}
"""


def _compile_and_run(tmp_path: Path) -> tuple[tuple[str, ...], ...]:
    source = tmp_path / "payne-hanek256.c"
    binary = tmp_path / "payne-hanek256"
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


def test_full_domain_payne_hanek_matches_fraction_machin(
    tmp_path: Path,
) -> None:
    """Match quadrant and directed residual through max-finite."""
    records = _compile_and_run(tmp_path)
    assert len(records) == len(CASES)
    for bits, record in zip(CASES, records, strict=True):
        expected = _oracle(bits)
        assert int(record[0], 16) == bits
        assert int(record[1]) == expected[0]
        assert int(record[2]) == expected[1]
        c_lower = _signed(int(record[5], 16), int(record[3]))
        c_upper = _signed(int(record[6], 16), int(record[4]))
        oracle_lower = _signed(expected[2], expected[3])
        oracle_upper = _signed(expected[4], expected[5])
        assert c_lower <= oracle_lower
        assert oracle_lower <= oracle_upper
        assert oracle_upper <= c_upper
