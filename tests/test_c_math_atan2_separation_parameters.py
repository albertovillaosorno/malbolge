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
#   - Exact finite parameters consumed by future atan2 separation bounds.
# - Must-Not:
#   - Treat these parameters as a quantitative irrationality measure.
# - Allows:
#   - Inputs: kernel-required pairs and their current candidate cells.
#   - Outputs: reduced ratio height plus exact lower/upper midpoint shifts.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - A quantitative tangent separation theorem gains its own implementation.
# - Merge-When:
#   - Full-domain atan2 resource proof consumes these exact parameters directly.
# - Summary:
#   - Joins ratio height and candidate-cell dyadic geometry atomically.
# - Description:
#   - Fraction independently reconstructs all reported structural parameters.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Sign-mismatched candidate cells fail without publication.
#

"""Exact structural parameters for future quantitative atan2 separation."""

from __future__ import annotations

from fractions import Fraction
from itertools import starmap
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
SIGN = 1 << 63
MAGNITUDE_MASK = SIGN - 1
EXPONENT_MASK = 0x7FF
FRACTION_MASK = (1 << 52) - 1
HIDDEN = 1 << 52
MAX_FALLBACK_MIDPOINT_SHIFT = 107
MAX_ADAPTIVE_NUMERATOR_BITS = 108
MAX_ADAPTIVE_DENOMINATOR_BITS = 106
CASES = (
    (0x3FEE19FA869EA9FC, 0x3FF197DD31B21770),
    (0xBFEE19FA869EA9FC, 0x3FF197DD31B21770),
    (0x3FF0000000000000, 0xBC80000000000001),
    (0x3CA8000000000001, 0x3FF0000000000001),
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


def _binary64(bits: int) -> Fraction:
    negative = bool(bits & SIGN)
    magnitude = bits & MAGNITUDE_MASK
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


def _next_up(bits: int) -> int:
    return bits - 1 if bits & SIGN else bits + 1


def _next_down(bits: int) -> int:
    return bits + 1 if bits & SIGN else bits - 1


def _shift(value: Fraction) -> int:
    denominator = value.denominator
    assert denominator & (denominator - 1) == 0
    return denominator.bit_length() - 1


def _height(y_bits: int, x_bits: int) -> tuple[int, int, int]:
    ratio = abs(_binary64(y_bits) / _binary64(x_bits))
    numerator_bits = ratio.numerator.bit_length()
    denominator_bits = ratio.denominator.bit_length()
    height_bits = max(numerator_bits, denominator_bits)
    return numerator_bits, denominator_bits, height_bits


def _midpoint_shifts(candidate: int) -> tuple[int, int, int]:
    value = _binary64(candidate)
    lower = (_binary64(_next_down(candidate)) + value) / 2
    upper = (value + _binary64(_next_up(candidate))) / 2
    lower_shift = _shift(lower)
    upper_shift = _shift(upper)
    return lower_shift, upper_shift, max(lower_shift, upper_shift)


def _source() -> str:
    rows = ",\n".join(
        f"  {{UINT64_C(0x{y:016x}), UINT64_C(0x{x:016x})}}" for y, x in CASES
    )
    return f"""#include "math_transcendental_bits.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
typedef struct Pair {{ uint64_t y, x; }} Pair;
static const Pair pairs[] = {{
{rows}
}};
int main(void) {{
  uint32_t index = UINT32_C(0);
  while (index < (uint32_t)(sizeof(pairs) / sizeof(pairs[0]))) {{
    uint64_t candidate = UINT64_C(0);
    MalbolgeGuestMathAtan2SeparationParameters parameters;
    if (!malbolge_guest_math_atan2_unique_binary64(
            pairs[index].y, pairs[index].x, &candidate) ||
        !malbolge_guest_math_atan2_separation_parameters(
            pairs[index].y, pairs[index].x, candidate, &parameters))
      return 81;
    (void)printf("%016" PRIx64 " %" PRIu32 " %" PRIu32 " %" PRIu32
                 " %" PRIu32 " %" PRIu32 " %" PRIu32 "\\n",
                 candidate, parameters.ratio_height.numerator_bits,
                 parameters.ratio_height.denominator_bits,
                 parameters.ratio_height.height_bits,
                 parameters.lower_midpoint_shift,
                 parameters.upper_midpoint_shift,
                 parameters.midpoint_shift_max);
    ++index;
  }}
  {{
    MalbolgeGuestMathAtan2SeparationParameters sentinel = {{
      {{UINT32_C(11), UINT32_C(12), UINT32_C(13)}},
      UINT32_C(14), UINT32_C(15), UINT32_C(16)}};
    if (malbolge_guest_math_atan2_separation_parameters(
            pairs[0].y, pairs[0].x, UINT64_C(0xbfe6a53b6b0b8e47),
            &sentinel) ||
        sentinel.ratio_height.numerator_bits != UINT32_C(11) ||
        sentinel.midpoint_shift_max != UINT32_C(16)) return 82;
  }}
  return 0;
}}
"""


def test_separation_parameters_match_exact_fraction(tmp_path: Path) -> None:
    """Match ratio height and midpoint shifts without a quantitative claim."""
    harness = tmp_path / "atan2-separation-parameters.c"
    executable = tmp_path / "atan2-separation-parameters"
    _ = harness.write_text(_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
            "-O2",
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
    rows = tuple(line.split() for line in executed.stdout.splitlines())
    assert len(rows) == len(CASES)
    for pair, row in zip(CASES, rows, strict=True):
        candidate = int(row[0], 16)
        actual_height = tuple(map(int, row[1:4]))
        actual_shifts = tuple(map(int, row[4:7]))
        assert actual_height == _height(*pair)
        assert actual_height[0] <= MAX_ADAPTIVE_NUMERATOR_BITS
        assert actual_height[1] <= MAX_ADAPTIVE_DENOMINATOR_BITS
        assert actual_shifts == _midpoint_shifts(candidate)
        assert actual_shifts[2] <= MAX_FALLBACK_MIDPOINT_SHIFT

    heights = tuple(starmap(_height, CASES))
    assert max(height[0] for height in heights) == MAX_ADAPTIVE_NUMERATOR_BITS
    assert max(height[1] for height in heights) == MAX_ADAPTIVE_DENOMINATOR_BITS
