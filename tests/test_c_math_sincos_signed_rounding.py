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
#   - Exact signed fixed-point to binary64 rounding evidence for sincos.
# - Must-Not:
#   - Use host floating arithmetic, libm, or approximate expected values.
# - Allows:
#   - Inputs: ordered signed-magnitude fixed-point intervals at whole-limb
#     scale.
#   - Outputs: a binary64 word only when both exact endpoints round identically.
#   - Side effects: temporary C harness compilation and execution only.
# - Split-When:
#   - Public sin/cos publication gains operation-specific range reduction.
# - Merge-When:
#   - The final transcendental handoff owns this rounding gate directly.
# - Summary:
#   - Locks normal, subnormal, underflow, sign, and nearest-even interval gates.
# - Description:
#   - Fraction authority independently quantizes exact dyadics to binary64.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Ambiguous or malformed intervals reject without output publication.
#

"""Signed fixed-point interval nearest-even binary64 rounding evidence."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
SIGN = 1 << 63
FRACTION_MASK = (1 << 52) - 1
HIDDEN = 1 << 52
MAX_LIMBS = 35
MAX_BINARY64_EXPONENT = 1023


@dataclass(frozen=True)
class Case:
    """One exact signed interval in common fixed-point scale."""

    lower: int
    upper: int
    fraction_bits: int
    expected_ok: bool | None = None


def _pow2(exponent: int) -> Fraction:
    return (
        Fraction(1 << exponent, 1)
        if exponent >= 0
        else Fraction(1, 1 << -exponent)
    )


def _round_ratio_nearest_even(value: Fraction) -> int:
    quotient, remainder = divmod(value.numerator, value.denominator)
    doubled = remainder * 2
    if doubled > value.denominator or (
        doubled == value.denominator and quotient & 1
    ):
        quotient += 1
    return quotient


def _floor_log2(value: Fraction) -> int:
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    if value < _pow2(exponent):
        exponent -= 1
    return exponent


def _binary64_bits(value: Fraction) -> int:
    negative = value < 0
    magnitude = abs(value)
    if not magnitude:
        return 0
    minimum_normal = _pow2(-1022)
    if magnitude < minimum_normal:
        quantized = _round_ratio_nearest_even(magnitude / _pow2(-1074))
        bits = HIDDEN if quantized == HIDDEN else quantized
    else:
        exponent = _floor_log2(magnitude)
        quantized = _round_ratio_nearest_even(magnitude / _pow2(exponent - 52))
        if quantized == 1 << 53:
            quantized >>= 1
            exponent += 1
        assert exponent <= MAX_BINARY64_EXPONENT
        bits = ((exponent + MAX_BINARY64_EXPONENT) << 52) | (
            quantized & FRACTION_MASK
        )
    return bits | (SIGN if negative else 0)


def _fixed_value(integer: int, fraction_bits: int) -> Fraction:
    return Fraction(integer, 1 << fraction_bits)


def _cases() -> tuple[Case, ...]:
    f64 = 64
    one = 1 << f64
    one_midpoint = one + (1 << (f64 - 53))
    f1088 = 1088
    half_min_subnormal = 1 << (f1088 - 1075)
    min_subnormal = 1 << (f1088 - 1074)
    min_normal = 1 << (f1088 - 1022)
    max_subnormal_midpoint = ((1 << 53) - 1) << (f1088 - 1075)
    min_normal_next_midpoint = min_normal + half_min_subnormal
    return (
        Case(one, one, f64),
        Case(-one, -one, f64),
        Case(one_midpoint - 1, one_midpoint - 1, f64),
        Case(one_midpoint, one_midpoint, f64),
        Case(one_midpoint + 1, one_midpoint + 1, f64),
        Case(-(one_midpoint + 1), -(one_midpoint + 1), f64),
        Case(half_min_subnormal - 1, half_min_subnormal - 1, f1088),
        Case(half_min_subnormal, half_min_subnormal, f1088),
        Case(half_min_subnormal + 1, half_min_subnormal + 1, f1088),
        Case(-(half_min_subnormal - 1), -(half_min_subnormal - 1), f1088),
        Case(-half_min_subnormal, -half_min_subnormal, f1088),
        Case(-(half_min_subnormal + 1), -(half_min_subnormal + 1), f1088),
        Case(min_subnormal, min_subnormal, f1088),
        Case(3 * half_min_subnormal, 3 * half_min_subnormal, f1088),
        Case(5 * half_min_subnormal, 5 * half_min_subnormal, f1088),
        Case(max_subnormal_midpoint - 1, max_subnormal_midpoint - 1, f1088),
        Case(max_subnormal_midpoint, max_subnormal_midpoint, f1088),
        Case(max_subnormal_midpoint + 1, max_subnormal_midpoint + 1, f1088),
        Case(min_normal, min_normal, f1088),
        Case(min_normal_next_midpoint, min_normal_next_midpoint, f1088),
        Case(min_normal_next_midpoint + 1, min_normal_next_midpoint + 1, f1088),
        Case(0, half_min_subnormal - 1, f1088),
        Case(-(half_min_subnormal - 1), -1, f1088),
        Case(
            -(half_min_subnormal - 1),
            half_min_subnormal - 1,
            f1088,
            expected_ok=False,
        ),
        Case(one, one_midpoint, f64),
        Case(one_midpoint + 1, one_midpoint + 2, f64),
        Case(-one_midpoint, -one, f64),
    )


def _limbs(magnitude: int, count: int) -> str:
    return ", ".join(
        f"UINT32_C(0x{((magnitude >> (32 * index)) & 0xffffffff):08x})"
        for index in range(count)
    )


def _case_row(case: Case) -> str:
    fraction_limbs = case.fraction_bits // 32
    limb_count = fraction_limbs + 1
    lower = _fixed_value(case.lower, case.fraction_bits)
    upper = _fixed_value(case.upper, case.fraction_bits)
    lower_bits = _binary64_bits(lower)
    upper_bits = _binary64_bits(upper)
    expected_ok = (
        lower_bits == upper_bits
        if case.expected_ok is None
        else case.expected_ok
    )
    expected_bits = lower_bits if expected_ok else 0
    return f"""  {{
    {{{_limbs(abs(case.lower), limb_count)}}},
    {{{_limbs(abs(case.upper), limb_count)}}},
    UINT32_C({int(case.lower < 0)}), UINT32_C({int(case.upper < 0)}),
    UINT32_C({limb_count}), UINT32_C({fraction_limbs}),
    UINT32_C({int(expected_ok)}), UINT64_C(0x{expected_bits:016x})
  }}"""


def _source() -> str:
    rows = ",\n".join(_case_row(case) for case in _cases())
    return f"""#include "math_transcendental_bits.h"
#include <stdint.h>

typedef struct Case {{
  uint32_t lower[{MAX_LIMBS}];
  uint32_t upper[{MAX_LIMBS}];
  uint32_t lower_negative;
  uint32_t upper_negative;
  uint32_t limb_count;
  uint32_t fraction_limbs;
  uint32_t expected_ok;
  uint64_t expected_bits;
}} Case;

static const Case cases[] = {{
{rows}
}};

int main(void) {{
  uint32_t index = UINT32_C(0);
  while (index < (uint32_t)(sizeof(cases) / sizeof(cases[0]))) {{
    const Case *item = &cases[index];
    uint64_t output = UINT64_C(0xfeedfacecafebeef);
    const int ok = malbolge_guest_math_fixed_signed_interval_unique_binary64(
        item->lower, item->lower_negative, item->upper, item->upper_negative,
        item->limb_count, item->fraction_limbs, &output);
    if ((uint32_t)ok != item->expected_ok) return 80 + (int)index;
    if (ok != 0 && output != item->expected_bits) return 120 + (int)index;
    if (ok == 0 && output != UINT64_C(0xfeedfacecafebeef))
      return 160 + (int)index;
    ++index;
  }}
  {{
    uint32_t one[3] = {{UINT32_C(0), UINT32_C(0), UINT32_C(1)}};
    uint32_t two[3] = {{UINT32_C(0), UINT32_C(0), UINT32_C(2)}};
    uint64_t output = UINT64_C(0xfeedfacecafebeef);
    if (malbolge_guest_math_fixed_signed_interval_unique_binary64(
            two, UINT32_C(0), one, UINT32_C(0), UINT32_C(3), UINT32_C(2),
            &output) || output != UINT64_C(0xfeedfacecafebeef)) return 220;
    if (malbolge_guest_math_fixed_signed_interval_unique_binary64(
            one, UINT32_C(2), one, UINT32_C(0), UINT32_C(3), UINT32_C(2),
            &output) || output != UINT64_C(0xfeedfacecafebeef)) return 221;
    if (malbolge_guest_math_fixed_signed_interval_unique_binary64(
            one, UINT32_C(0), one, UINT32_C(0), UINT32_C(3), UINT32_C(4),
            &output) || output != UINT64_C(0xfeedfacecafebeef)) return 222;
  }}
  return 0;
}}
"""


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


def test_signed_fixed_interval_rounding_matches_fraction(
    tmp_path: Path,
) -> None:
    """Match exact nearest-even through normals, subnormals, and signed zero."""
    harness = tmp_path / "sincos-signed-rounding.c"
    executable = tmp_path / "sincos-signed-rounding"
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
