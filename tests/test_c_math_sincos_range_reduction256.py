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
#   - Q32.256 periodic sin/cos reduction for finite 4 <= |x| < 2^31.
# - Must-Not:
#   - Use host pi/libm as quotient or residual authority.
#   - Claim this bounded Q256 reducer covers the full binary64 domain.
# - Allows:
#   - Inputs: raw binary64 words in the bounded reduction domain.
#   - Outputs: exact u32 multiple/quadrant plus a directed signed Q256 residual.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Full Payne-Hanek-style reduction needs wider quotient/constant geometry.
# - Merge-When:
#   - A full-domain periodic reducer subsumes this bounded Q256 path.
# - Summary:
#   - Certifies bounded periodic reduction from Machin Fraction authority.
# - Description:
#   - Re-derives quarter-pi and 2/pi Q256 cells independently.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - 512 fixed-seed cases plus exact neighbors of selected pi/2 multiples.
#

"""Exact Q256 periodic sin/cos range-reduction evidence."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import struct
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
SCALE = 1 << 256
SIGN = 1 << 63
MAGNITUDE = SIGN - 1
EXPONENT_MASK = 0x7FF
FRACTION_MASK = (1 << 52) - 1
HIDDEN = 1 << 52
FOUR = 0x4010000000000000
TWO31 = 0x41E0000000000000
MAX_FINITE = 0x7FEFFFFFFFFFFFFF
MASK64 = (1 << 64) - 1
MULTIPLE_LIMIT = 1_367_130_552
CASE_COUNT = 512


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


def _atan_reciprocal_bounds(
    denominator: int,
    terms: int,
) -> tuple[Fraction, Fraction]:
    total = Fraction(0)
    x = Fraction(1, denominator)
    square = x * x
    term = x
    for index in range(terms):
        contribution = term / (2 * index + 1)
        total = total + contribution if index % 2 == 0 else total - contribution
        term *= square
    omitted = term / (2 * terms + 1)
    if terms % 2 == 0:
        return total, total + omitted
    return total - omitted, total


def _quarter_pi_bounds() -> tuple[Fraction, Fraction]:
    a5_lo, a5_hi = _atan_reciprocal_bounds(5, 90)
    a239_lo, a239_hi = _atan_reciprocal_bounds(239, 30)
    return 4 * a5_lo - a239_hi, 4 * a5_hi - a239_lo


def _floor(value: Fraction) -> int:
    return value.numerator // value.denominator


def _ceil(value: Fraction) -> int:
    return -((-value.numerator) // value.denominator)


def _q256_authority() -> tuple[int, int, int, int]:
    quarter_lo, quarter_hi = _quarter_pi_bounds()
    qlo = _floor(quarter_lo * SCALE)
    qhi = _ceil(quarter_hi * SCALE)
    recip_lo = (SCALE * SCALE) // (2 * qhi)
    recip_hi = _ceil(Fraction(SCALE * SCALE, 2 * qlo))
    assert qhi == qlo + 1
    assert recip_hi == recip_lo + 1
    return qlo, qhi, recip_lo, recip_hi


def _binary64(bits: int) -> Fraction:
    negative = bool(bits & SIGN)
    magnitude = bits & MAGNITUDE
    exponent = (magnitude >> 52) & EXPONENT_MASK
    fraction = magnitude & FRACTION_MASK
    assert exponent != EXPONENT_MASK
    if exponent == 0:
        value = Fraction(fraction, 1 << 1074)
    else:
        significand = HIDDEN | fraction
        power = exponent - 1023 - 52
        value = (
            Fraction(significand << power, 1)
            if power >= 0
            else Fraction(significand, 1 << -power)
        )
    return -value if negative else value


def _nearest_binary64_bits(value: Fraction) -> int:
    proposal = int.from_bytes(struct.pack(">d", float(value)), "big")
    choices = [proposal]
    if proposal > 0:
        choices.append(proposal - 1)
    if proposal < MAX_FINITE:
        choices.append(proposal + 1)
    ranked = tuple((abs(_binary64(bits) - value), bits) for bits in choices)
    distance = min(item[0] for item in ranked)
    tied = tuple(bits for delta, bits in ranked if delta == distance)
    return min(tied, key=lambda bits: bits & 1)


def _nearest_integer(value: Fraction) -> int:
    quotient, remainder = divmod(value.numerator, value.denominator)
    twice = remainder * 2
    round_up = twice > value.denominator or (
        twice == value.denominator and bool(quotient & 1)
    )
    return quotient + int(round_up)


def _q_from_interval(x_scaled: int, recip_lo: int, recip_hi: int) -> int:
    product_lo = (x_scaled * recip_lo) // SCALE
    product_hi = _ceil(Fraction(x_scaled * recip_hi, SCALE))
    lower = _nearest_integer(Fraction(product_lo, SCALE))
    upper = _nearest_integer(Fraction(product_hi, SCALE))
    assert lower == upper
    return lower


def _residual(
    x_scaled: int,
    *,
    multiple: int,
    quarter_lo: int,
    quarter_hi: int,
) -> tuple[int, int, int, int]:
    half_lo = 2 * quarter_lo * multiple
    half_hi = 2 * quarter_hi * multiple
    if x_scaled >= half_hi:
        return x_scaled - half_hi, 0, x_scaled - half_lo, 0
    if x_scaled <= half_lo:
        lower = half_hi - x_scaled
        upper = half_lo - x_scaled
        return lower, int(lower != 0), upper, int(upper != 0)
    lower = half_hi - x_scaled
    upper = x_scaled - half_lo
    return lower, int(lower != 0), upper, 0


def _expected(bits: int) -> tuple[int, int, int, int, int, int]:
    qlo, qhi, recip_lo, recip_hi = _q256_authority()
    value = abs(_binary64(bits))
    x_scaled = int(value * SCALE)
    assert Fraction(x_scaled, SCALE) == value
    multiple = _q_from_interval(x_scaled, recip_lo, recip_hi)
    residual = _residual(
        x_scaled,
        multiple=multiple,
        quarter_lo=qlo,
        quarter_hi=qhi,
    )
    return (
        multiple,
        residual[1],
        residual[3],
        residual[0],
        residual[2],
        multiple & 3,
    )


def _manual_bits() -> tuple[int, ...]:
    quarter_lo, quarter_hi = _quarter_pi_bounds()
    half_mid = quarter_lo + quarter_hi
    words: set[int] = {FOUR, FOUR + 1, TWO31 - 1}
    for multiple in (3, 4, 5, 7, 17, 1000, 1_000_000, 1_000_000_000):
        center = _nearest_binary64_bits(multiple * half_mid)
        for delta in (-2, -1, 0, 1, 2):
            magnitude = center + delta
            if FOUR <= magnitude < TWO31:
                words.add(magnitude)
                words.add(magnitude | SIGN)
    return tuple(sorted(words))


def _cases() -> tuple[int, ...]:
    state = 0xC0FFEE123456789A
    rows = list(_manual_bits())
    span = TWO31 - FOUR
    while len(rows) < len(_manual_bits()) + CASE_COUNT:
        state = (state * 6364136223846793005 + 1442695040888963407) & MASK64
        magnitude = FOUR + state % span
        rows.append(magnitude | (SIGN if state & 1 else 0))
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
int main(void) {{
  uint32_t index = UINT32_C(0);
  while (index < (uint32_t)(sizeof(cases) / sizeof(cases[0]))) {{
    MalbolgeGuestMathSincosRangeReduction256 r;
    uint32_t limb = UINT32_C(0);
    if (!malbolge_guest_math_sincos_range_reduce256(cases[index], &r))
      return 80;
    (void)printf("%016" PRIx64 " %u %u %u %u ", cases[index], r.multiple,
                 r.quadrant, r.residual_lower_negative,
                 r.residual_upper_negative);
    limb = MALBOLGE_GUEST_MATH_FIXED_256_LIMBS;
    while (limb != UINT32_C(0)) {{
      --limb;
      (void)printf("%08x", r.residual_lower.limbs[limb]);
    }}
    (void)printf(" ");
    limb = MALBOLGE_GUEST_MATH_FIXED_256_LIMBS;
    while (limb != UINT32_C(0)) {{
      --limb;
      (void)printf("%08x", r.residual_upper.limbs[limb]);
    }}
    (void)printf("\\n");
    ++index;
  }}
  return 0;
}}
"""


def _compile_and_execute(tmp_path: Path) -> tuple[str, ...]:
    harness = tmp_path / "range-reduction.c"
    executable = tmp_path / "range-reduction"
    _ = harness.write_text(_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
            "-O2",
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
    return tuple(executed.stdout.splitlines())


def _assert_record(bits: int, line: str) -> None:
    fields = line.split()
    expected = _expected(bits)
    assert int(fields[0], 16) == bits
    assert int(fields[1]) == expected[0]
    assert int(fields[2]) == expected[5]
    assert int(fields[3]) == expected[1]
    assert int(fields[4]) == expected[2]
    assert int(fields[5], 16) == expected[3]
    assert int(fields[6], 16) == expected[4]
    assert expected[0] < MULTIPLE_LIMIT
    _, qhi, _, _ = _q256_authority()
    assert expected[3] <= qhi
    assert expected[4] <= qhi


def test_q256_range_reduction_matches_fraction_machin(tmp_path: Path) -> None:
    """Match quotient/quadrant and both signed Q256 residual endpoints."""
    lines = _compile_and_execute(tmp_path)
    assert len(lines) == len(CASES)
    for bits, line in zip(CASES, lines, strict=True):
        _assert_record(bits, line)


def test_q256_range_reduction_rejects_outside_domain(tmp_path: Path) -> None:
    """Keep sub-four, 2^31, infinity, and null-output cases nonpublishing."""
    harness = tmp_path / "range-reduction-reject.c"
    executable = tmp_path / "range-reduction-reject"
    _ = harness.write_text(
        r"""#include "math_transcendental_bits.h"
#include <stdint.h>
int main(void) {
  MalbolgeGuestMathSincosRangeReduction256 out = {
      UINT32_C(99), UINT32_C(98), UINT32_C(97), {{UINT32_C(96)}},
      UINT32_C(95), {{UINT32_C(94)}}, UINT32_C(93)};
  const uint64_t bad[] = {
      UINT64_C(0x400fffffffffffff), UINT64_C(0x41e0000000000000),
      UINT64_C(0x7ff0000000000000)};
  uint32_t i = UINT32_C(0);
  while (i < UINT32_C(3)) {
    if (malbolge_guest_math_sincos_range_reduce256(bad[i], &out) ||
        out.multiple != UINT32_C(99) || out.quadrant != UINT32_C(98) ||
        out.residual_lower.limbs[0] != UINT32_C(96) ||
        out.residual_upper.limbs[0] != UINT32_C(94)) return 80;
    ++i;
  }
  if (malbolge_guest_math_sincos_range_reduce256(
          UINT64_C(0x4010000000000000), 0)) return 81;
  return 0;
}
""",
        encoding="utf-8",
    )
    compiled = _run(
        [
            str(CLANG), "-std=c23", "-O2", "-ffreestanding", "-fno-builtin",
            "-Wall", "-Wextra", "-Wpedantic", "-Werror", f"-I{CONTRACT}",
            str(SOURCE), str(harness), "-o", str(executable),
        ],
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    executed = _run([str(executable)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr
