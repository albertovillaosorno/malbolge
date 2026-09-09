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
#   - End-to-end dyadic normalization, Taylor sin/cos, and doubling transport.
# - Must-Not:
#   - Use host sin/cos or claim tangent separation from these enclosures alone.
# - Allows:
#   - Inputs: reduced nonzero atan midpoint dyadics and selected precision.
#   - Outputs: signed sin/cos enclosures for the original midpoint, or proven=0.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - A Lambert GCF separation evaluator consumes the normalized route directly.
# - Merge-When:
#   - Full-domain midpoint proof owns both trigonometric and GCF normalization.
# - Summary:
#   - Certifies normalized Taylor plus up to 56 directed angle doublings.
# - Description:
#   - Fraction Taylor bounds enclose the original angle, not C internals.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Q128/16 is evidence coverage, never a full-domain precision ceiling.
#

"""Authority for normalized dyadic sin/cos transport in guest C."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
FRACTION_LIMBS = 4
FRACTION_BITS = FRACTION_LIMBS * 32
LIMB_COUNT = FRACTION_LIMBS + 1
AUTHORITY_TERMS = 40

CASES = (
    (3, 2, 0),
    (3, 2, 1),
    (0x003FFFFFFFFFFFFF, 52, 0),
    (0x0020000000000001, 107, 1),
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


def _sin_interval(value: Fraction, terms: int) -> tuple[Fraction, Fraction]:
    negative = value < 0
    magnitude = abs(value)
    square = magnitude * magnitude
    term = magnitude
    total = term
    for index in range(terms - 1):
        term *= square
        term /= ((2 * index) + 2) * ((2 * index) + 3)
        total = total - term if (index + 1) & 1 else total + term
    last = terms - 1
    omitted = term * square / (((2 * last) + 2) * ((2 * last) + 3))
    lower, upper = (
        (total - omitted, total) if terms & 1 else (total, total + omitted)
    )
    return (-upper, -lower) if negative else (lower, upper)


def _cos_interval(value: Fraction, terms: int) -> tuple[Fraction, Fraction]:
    square = value * value
    term = Fraction(1)
    total = term
    for index in range(terms - 1):
        term *= square
        term /= ((2 * index) + 1) * ((2 * index) + 2)
        total = total - term if (index + 1) & 1 else total + term
    last = terms - 1
    omitted = term * square / (((2 * last) + 1) * ((2 * last) + 2))
    return (
        (total - omitted, total) if terms & 1 else (total, total + omitted)
    )


def _fixed_value(words: list[int], negative: int) -> Fraction:
    integer = sum(word << (32 * index) for index, word in enumerate(words))
    value = Fraction(integer, 1 << FRACTION_BITS)
    return -value if negative and integer else value


def _row_literal(case: tuple[int, int, int]) -> str:
    numerator, shift, negative = case
    return (
        f"  {{UINT64_C(0x{numerator:016x}), UINT32_C({shift}), "
        f"UINT32_C({negative})}}"
    )


def _source() -> str:
    rows = ",\n".join(_row_literal(case) for case in CASES)
    return f"""#include \"math_transcendental_bits.h\"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

#define F UINT32_C({FRACTION_LIMBS})
#define N (F + UINT32_C(1))
#define S (UINT32_C(20) * N)

static const MalbolgeGuestMathDyadic cases[] = {{
{rows}
}};

static void fill(uint32_t *value, uint32_t count, uint32_t word) {{
  uint32_t i = UINT32_C(0);
  while (i < count) value[i++] = word;
}}

static void emit_words(const uint32_t *value) {{
  uint32_t i = UINT32_C(0);
  while (i < N) {{
    (void)printf(" %" PRIu32, value[i]);
    ++i;
  }}
}}

int main(void) {{
  uint32_t index = UINT32_C(0);
  while (index < (uint32_t)(sizeof(cases) / sizeof(cases[0]))) {{
    uint32_t out[4][N];
    uint32_t scratch[S];
    uint32_t signs[4] = {{UINT32_C(9), UINT32_C(9), UINT32_C(9), UINT32_C(9)}};
    uint32_t proven = UINT32_C(9);
    if (!malbolge_guest_math_dyadic_normalized_sincos_interval(
            &cases[index], F, UINT32_C(16), out[0], &signs[0], out[1],
            &signs[1], out[2], &signs[2], out[3], &signs[3], &proven,
            scratch, S) || proven != UINT32_C(1)) return 80;
    (void)printf("%" PRIu32 " %" PRIu32 " %" PRIu32 " %" PRIu32,
                 signs[0], signs[1], signs[2], signs[3]);
    emit_words(out[0]);
    emit_words(out[1]);
    emit_words(out[2]);
    emit_words(out[3]);
    (void)printf("\\n");
    ++index;
  }}
  {{
    const MalbolgeGuestMathDyadic near_four =
        {{UINT64_C(0x003fffffffffffff), UINT32_C(52), UINT32_C(0)}};
    uint32_t out[4][N];
    uint32_t scratch[S];
    uint32_t signs[4] = {{UINT32_C(41), UINT32_C(42),
                          UINT32_C(43), UINT32_C(44)}};
    uint32_t proven = UINT32_C(45);
    fill(&out[0][0], UINT32_C(4) * N, UINT32_C(0xdeadbeef));
    if (!malbolge_guest_math_dyadic_normalized_sincos_interval(
            &near_four, UINT32_C(3), UINT32_C(16), out[0], &signs[0], out[1],
            &signs[1], out[2], &signs[2], out[3], &signs[3], &proven,
            scratch, S) || proven != UINT32_C(0) ||
        out[0][0] != UINT32_C(0xdeadbeef) ||
        signs[0] != UINT32_C(41)) return 81;
    proven = UINT32_C(45);
    if (malbolge_guest_math_dyadic_normalized_sincos_interval(
            &near_four, F, UINT32_C(1), out[0], &signs[0], out[1], &signs[1],
            out[2], &signs[2], out[3], &signs[3], &proven, scratch, S) ||
        proven != UINT32_C(45) || out[0][0] != UINT32_C(0xdeadbeef)) return 82;
    if (malbolge_guest_math_dyadic_normalized_sincos_interval(
            &near_four, F, UINT32_C(16), out[0], &signs[0], out[1], &signs[1],
            out[2], &signs[2], out[3], &signs[3], &proven, scratch,
            UINT32_C(20) * N - UINT32_C(1)) || proven != UINT32_C(45) ||
        out[0][0] != UINT32_C(0xdeadbeef)) return 83;
  }}
  return 0;
}}
"""


def _assert_case_enclosed(case: tuple[int, int, int], row: list[int]) -> None:
    numerator, shift, negative = case
    signs = row[:4]
    words = [
        row[4 + index * LIMB_COUNT : 4 + (index + 1) * LIMB_COUNT]
        for index in range(4)
    ]
    c_bounds = (
        _fixed_value(words[0], signs[0]),
        _fixed_value(words[1], signs[1]),
        _fixed_value(words[2], signs[2]),
        _fixed_value(words[3], signs[3]),
    )
    value = Fraction(numerator, 1 << shift)
    if negative:
        value = -value
    sin_bounds = _sin_interval(value, AUTHORITY_TERMS)
    cos_bounds = _cos_interval(value, AUTHORITY_TERMS)
    assert c_bounds[0] <= sin_bounds[0] <= sin_bounds[1] <= c_bounds[1]
    assert c_bounds[2] <= cos_bounds[0] <= cos_bounds[1] <= c_bounds[3]


def test_normalized_sincos_contains_independent_original_angle_bounds(
    tmp_path: Path,
) -> None:
    """Enclose original-angle sin/cos after normalized Taylor and transport."""
    harness = tmp_path / "atan2-normalized-sincos.c"
    executable = tmp_path / "atan2-normalized-sincos"
    _ = harness.write_text(_source(), encoding="utf-8")
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
    rows = [
        list(map(int, line.split())) for line in executed.stdout.splitlines()
    ]
    assert len(rows) == len(CASES)
    for case, row in zip(CASES, rows, strict=True):
        _assert_case_enclosed(case, row)
