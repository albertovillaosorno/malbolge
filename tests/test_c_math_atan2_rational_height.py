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
#   - Exact reduced-rational height evidence for the atan2 tangent comparator.
# - Must-Not:
#   - Treat retained-corpus height as a full-domain denominator bound.
#   - Approximate the ratio with host floating arithmetic.
# - Allows:
#   - Inputs: the durable signed-hard/edge/4096-pair refinement corpus.
#   - Outputs: numerator, denominator, and maximum reduced bit lengths.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - A quantitative transcendence bound consumes rational height directly.
# - Merge-When:
#   - Full-domain atan2 resource proof owns the same exact height arithmetic.
# - Summary:
#   - Cross-checks giant shifted ratios without materializing giant integers.
# - Description:
#   - Python Fraction independently reduces |y/x| for every kernel-required
#     case.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Height is structural evidence, not a correct-rounding completion claim.
#

"""Exact reduced rational-height evidence for adaptive atan2."""

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
MAGNITUDE_MASK = (1 << 63) - 1
EXPONENT_MASK = 0x7FF
FRACTION_MASK = (1 << 52) - 1
HIDDEN_BIT = 1 << 52
ALL_BITS = (1 << 64) - 1
LCG_MULTIPLIER = 6364136223846793005
LCG_INCREMENT = 1442695040888963407
LCG_SEED = 0x4D4944504F494E54
LCG_COUNT = 4096
KERNEL_REQUIRED = 2
EXPECTED_KERNEL_COUNT = 3167
EXTREME_PAIR_COUNT = 2
FULL_DOMAIN_HEIGHT_BITS = 2098
CORPUS_DENOMINATOR_MAX = 2089
CORPUS_NUMERATOR_MAX = 2069

BASE_HARD = (
    (0x3FEE19FA869EA9FC, 0x3FF197DD31B21770),
    (0x3FE74E55173F69A0, 0x3FF6943B1C1EE532),
    (0x3FEF179200C72129, 0x3FFBC1B4128CF396),
    (0x3FE97B1DB9A2A48C, 0x3FF781CE6A6EE8EF),
    (0x3FE9519856F5242F, 0x3FF06C408C434F0E),
    (0x3FEF7590E09E2ADD, 0x3FF629E5895F91A7),
    (0x3FE5139B1425C8A2, 0x3FF4FA0C073AF8F1),
    (0x3FE549E587E6D4CD, 0x3FF11E3639F76651),
    (0x3FD75B9A8D0A0447, 0x3FF069F1CC6166FC),
    (0x3FDF65E15A3E11FD, 0x3FF31E45227A22DE),
    (0x3FDEF69FB021F2DB, 0x3FF90CC971F74C07),
    (0x3FDABB28E6EEF14A, 0x3FF544C4908DDACE),
    (0x3FD94D130BF48845, 0x3FF2CCCC5A36B6E1),
    (0x3FD667E2DB48932E, 0x3FF41B5A664E9573),
    (0x3FDBA787A32EAF18, 0x3FF914A595604C36),
    (0x3FD88C55EA9394D5, 0x3FF6ABB1E310A1AC),
)
EDGES = (
    (0x3FF0000000000000, 0x0000000000000001),
    (0x3FF0000000000000, 0x8000000000000001),
    (0x0010000000000000, 0x7FEFFFFFFFFFFFFF),
    (0x8010000000000000, 0x7FEFFFFFFFFFFFFF),
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
    magnitude = bits & MAGNITUDE_MASK
    return magnitude != 0 and (magnitude >> 52) & EXPONENT_MASK != EXPONENT_MASK


def _signed_hard_pairs() -> list[tuple[int, int]]:
    return [
        (y | y_negative, x | x_negative)
        for y, x in BASE_HARD
        for y_negative in (0, SIGN_BIT)
        for x_negative in (0, SIGN_BIT)
    ]


def _lcg_pairs() -> list[tuple[int, int]]:
    pairs: list[tuple[int, int]] = []
    state = LCG_SEED
    while len(pairs) < LCG_COUNT:
        state = (state * LCG_MULTIPLIER + LCG_INCREMENT) & ALL_BITS
        y = state
        state = (state * LCG_MULTIPLIER + LCG_INCREMENT) & ALL_BITS
        x = state
        if _finite_nonzero(y) and _finite_nonzero(x):
            pairs.append((y, x))
    return pairs


def _pairs() -> tuple[tuple[int, int], ...]:
    return (*_signed_hard_pairs(), *EDGES, *_lcg_pairs())


def _raw_magnitude(bits: int) -> Fraction:
    magnitude = bits & MAGNITUDE_MASK
    raw_exponent = (magnitude >> 52) & EXPONENT_MASK
    fraction = magnitude & FRACTION_MASK
    assert magnitude != 0
    assert raw_exponent != EXPONENT_MASK
    if raw_exponent == 0:
        return Fraction(fraction, 1 << 1074)
    significand = HIDDEN_BIT | fraction
    exponent = raw_exponent - 1023 - 52
    if exponent >= 0:
        return Fraction(significand << exponent, 1)
    return Fraction(significand, 1 << -exponent)


def _expected_height(y: int, x: int) -> tuple[int, int, int]:
    ratio = _raw_magnitude(y) / _raw_magnitude(x)
    numerator_bits = ratio.numerator.bit_length()
    denominator_bits = ratio.denominator.bit_length()
    height_bits = max(numerator_bits, denominator_bits)
    return numerator_bits, denominator_bits, height_bits


def _harness_source(pairs: tuple[tuple[int, int], ...]) -> str:
    rows = ",\n".join(
        f"  {{UINT64_C(0x{y:016x}), UINT64_C(0x{x:016x})}}" for y, x in pairs
    )
    return f"""#include "math_transcendental_bits.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
typedef struct Pair {{ uint64_t y; uint64_t x; }} Pair;
static const Pair pairs[] = {{
{rows}
}};
int main(void) {{
  uint32_t index = UINT32_C(0);
  while (index < (uint32_t)(sizeof(pairs) / sizeof(pairs[0]))) {{
    const MalbolgeGuestMathSpecialResult special =
        malbolge_guest_math_atan2_special(pairs[index].y, pairs[index].x);
    if (special.status == MALBOLGE_GUEST_MATH_SPECIAL_KERNEL_REQUIRED) {{
      MalbolgeGuestMathAtan2KernelInput ratio;
      MalbolgeGuestMathRationalHeight height;
      if (!malbolge_guest_math_atan2_kernel_input(
              pairs[index].y, pairs[index].x, &ratio) ||
          !malbolge_guest_math_atan2_ratio_reduced_height(&ratio, &height))
        return 81;
      (void)printf("%" PRIu32 " %" PRIu32 " %" PRIu32 " %" PRIu32 "\\n",
                   index, height.numerator_bits, height.denominator_bits,
                   height.height_bits);
    }}
    ++index;
  }}
  return 0;
}}
"""


def test_reduced_ratio_height_matches_fraction(tmp_path: Path) -> None:
    """Match exact Fraction heights across the durable adaptive corpus."""
    pairs = _pairs()
    harness = tmp_path / "atan2-rational-height.c"
    executable = tmp_path / "atan2-rational-height"
    _ = harness.write_text(_harness_source(pairs), encoding="utf-8")
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
    rows = [
        tuple(map(int, line.split())) for line in executed.stdout.splitlines()
    ]
    assert len(rows) == EXPECTED_KERNEL_COUNT
    for index, numerator_bits, denominator_bits, height_bits in rows:
        expected = _expected_height(*pairs[index])
        assert numerator_bits == expected[0]
        assert denominator_bits == expected[1]
        assert height_bits == expected[2]

    assert max(row[1] for row in rows) == CORPUS_NUMERATOR_MAX
    assert max(row[2] for row in rows) == CORPUS_DENOMINATOR_MAX
    assert max(row[3] for row in rows) == CORPUS_DENOMINATOR_MAX


def test_binary64_ratio_height_bound_is_tight(tmp_path: Path) -> None:
    """Pin the exact 2098-bit finite-binary64 ratio height ceiling."""
    pairs = (
        (0x0000000000000001, 0xFFEFFFFFFFFFFFFF),
        (0x7FEFFFFFFFFFFFFF, 0x0000000000000001),
    )
    harness = tmp_path / "atan2-rational-height-extremes.c"
    executable = tmp_path / "atan2-rational-height-extremes"
    _ = harness.write_text(_harness_source(pairs), encoding="utf-8")
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
    rows = [
        tuple(map(int, line.split())) for line in executed.stdout.splitlines()
    ]
    assert len(rows) == EXTREME_PAIR_COUNT
    expected = tuple(starmap(_expected_height, pairs))
    assert expected[0] == (1, FULL_DOMAIN_HEIGHT_BITS, FULL_DOMAIN_HEIGHT_BITS)
    assert expected[1] == (FULL_DOMAIN_HEIGHT_BITS, 1, FULL_DOMAIN_HEIGHT_BITS)
    assert rows[0][1:] == expected[0]
    assert rows[1][1:] == expected[1]
