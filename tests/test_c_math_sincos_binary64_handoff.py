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
#   - Sub-four SIN/COS adaptive handoff through unique binary64 publication.
# - Must-Not:
#   - Use host trigonometric functions or floating expected-value authority.
# - Allows:
#   - Inputs: raw binary64 words handled by special or sub-four refinement.
#   - Outputs: fast result, exact retry plan, or certified binary64 result.
#   - Side effects: temporary C harness compilation and execution only.
# - Split-When:
#   - Periodic reduction admits finite magnitudes at least four.
# - Merge-When:
#   - Public sin/cos consumes this handoff with a proved resource policy.
# - Summary:
#   - Composes preproof, normalized refinement, and exact final rounding.
# - Description:
#   - Fraction Taylor bounds independently certify retained final result bits.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Capacity exhaustion reports retry; out-of-domain inputs fail atomically.
#

"""Sub-four binary64 sin/cos handoff evidence."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
SIN = 1
COS = 2
SIGN = 1 << 63
EXPONENT_MASK = 0x7FF
FRACTION_MASK = (1 << 52) - 1
HIDDEN = 1 << 52
MAX_EXPONENT = 1023
TERMS = 40
CASES = (
    (SIN, 0x3FE0000000000000, 0),
    (COS, 0x3FE0000000000000, 0),
    (SIN, 0x3FF0000000000000, 0),
    (COS, 0x3FF0000000000000, 0),
    (SIN, 0x4000000000000000, 0),
    (COS, 0x4000000000000000, 1),
    (SIN, 0x4008000000000000, 1),
    (COS, 0x4008000000000000, 0),
    (SIN, 0x400FFFFFFFFFFFFF, 2),
    (COS, 0x400FFFFFFFFFFFFF, 2),
    (SIN, 0xBFF0000000000000, 0),
    (COS, 0xBFF0000000000000, 0),
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
    assert raw_exponent != EXPONENT_MASK
    if raw_exponent == 0:
        value = Fraction(fraction, 1 << 1074)
    else:
        significand = HIDDEN | fraction
        exponent = raw_exponent - MAX_EXPONENT - 52
        value = Fraction(significand, 1) * _pow2(exponent)
    return -value if negative else value


def _round_integer(value: Fraction) -> int:
    quotient, remainder = divmod(value.numerator, value.denominator)
    twice = remainder * 2
    if twice > value.denominator or (
        twice == value.denominator and quotient & 1
    ):
        quotient += 1
    return quotient


def _floor_log2(value: Fraction) -> int:
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    return exponent - 1 if value < _pow2(exponent) else exponent


def _binary64_bits(value: Fraction) -> int:
    negative = value < 0
    magnitude = abs(value)
    if not magnitude:
        return 0
    if magnitude < _pow2(-1022):
        quantized = _round_integer(magnitude / _pow2(-1074))
        bits = HIDDEN if quantized == HIDDEN else quantized
    else:
        exponent = _floor_log2(magnitude)
        quantized = _round_integer(magnitude / _pow2(exponent - 52))
        if quantized == 1 << 53:
            quantized >>= 1
            exponent += 1
        bits = ((exponent + MAX_EXPONENT) << 52) | (
            quantized & FRACTION_MASK
        )
    return bits | (SIGN if negative else 0)


def _sin_bounds(value: Fraction) -> tuple[Fraction, Fraction]:
    square = value * value
    term = value
    total = term
    for index in range(TERMS - 1):
        term *= square
        term /= ((2 * index) + 2) * ((2 * index) + 3)
        total = total - term if (index + 1) & 1 else total + term
    omitted = term * square / ((2 * TERMS) * ((2 * TERMS) + 1))
    if TERMS % 2 == 0:
        return total, total + omitted
    return total - omitted, total


def _cos_bounds(value: Fraction) -> tuple[Fraction, Fraction]:
    square = value * value
    term = Fraction(1)
    total = term
    for index in range(TERMS - 1):
        term *= square
        term /= ((2 * index) + 1) * ((2 * index) + 2)
        total = total - term if (index + 1) & 1 else total + term
    omitted = term * square / (((2 * TERMS) - 1) * (2 * TERMS))
    if TERMS % 2 == 0:
        return total, total + omitted
    return total - omitted, total


def _expected_bits(operation: int, bits: int) -> int:
    value = _binary64_fraction(bits)
    bounds = _sin_bounds(value) if operation == SIN else _cos_bounds(value)
    lower, upper = bounds
    lower_bits = _binary64_bits(lower)
    upper_bits = _binary64_bits(upper)
    assert lower_bits == upper_bits
    return lower_bits


def _source() -> str:
    rows = ",\n".join(
        f"  {{UINT32_C({op}), UINT64_C(0x{bits:016x})}}"
        for op, bits, _ in CASES
    )
    return f"""#include "math_transcendental_bits.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

typedef struct Case {{ uint32_t operation; uint64_t bits; }} Case;
static const Case cases[] = {{
{rows}
}};

static int lifecycle(void) {{
  uint32_t workspace[120];
  MalbolgeGuestMathSincosBinary64Progress progress;
  const uint64_t near_four = UINT64_C(0x400fffffffffffff);
  progress.status = MALBOLGE_GUEST_MATH_SINCOS_BINARY64_FAST_RESOLVED;
  progress.input_bits = UINT64_C(11);
  progress.bits = UINT64_C(12);
  progress.plan.stage = UINT32_C(13);
  if (!malbolge_guest_math_unary_sincos_binary64_available(
          MALBOLGE_GUEST_MATH_SIN, near_four, UINT32_C(0), 0, UINT32_C(0),
          &progress) ||
      progress.status != MALBOLGE_GUEST_MATH_SINCOS_BINARY64_RETRY ||
      progress.plan.stage != UINT32_C(0) ||
      progress.plan.required_workspace_limbs != UINT32_C(72)) return 0;
  if (!malbolge_guest_math_unary_sincos_binary64_available(
          MALBOLGE_GUEST_MATH_SIN, near_four, UINT32_C(0), workspace,
          UINT32_C(96), &progress) ||
      progress.status != MALBOLGE_GUEST_MATH_SINCOS_BINARY64_RETRY ||
      progress.plan.stage != UINT32_C(2) ||
      progress.plan.required_workspace_limbs != UINT32_C(120)) return 0;
  if (!malbolge_guest_math_unary_sincos_binary64_available(
          MALBOLGE_GUEST_MATH_SIN, near_four, UINT32_C(0), workspace,
          UINT32_C(120), &progress) ||
      progress.status != MALBOLGE_GUEST_MATH_SINCOS_BINARY64_REFINED_RESOLVED ||
      progress.plan.stage != UINT32_C(2)) return 0;
  if (!malbolge_guest_math_unary_sincos_binary64_available(
          MALBOLGE_GUEST_MATH_SIN, UINT64_C(0), UINT32_C(0), 0, UINT32_C(0),
          &progress) ||
      progress.status != MALBOLGE_GUEST_MATH_SINCOS_BINARY64_FAST_RESOLVED ||
      progress.bits != UINT64_C(0)) return 0;
  progress.status = MALBOLGE_GUEST_MATH_SINCOS_BINARY64_FAST_RESOLVED;
  progress.input_bits = UINT64_C(21);
  progress.bits = UINT64_C(22);
  progress.plan.stage = UINT32_C(23);
  if (malbolge_guest_math_unary_sincos_binary64_available(
          MALBOLGE_GUEST_MATH_SIN, UINT64_C(0x4010000000000000), UINT32_C(0),
          workspace, UINT32_C(120), &progress) ||
      progress.input_bits != UINT64_C(21) || progress.bits != UINT64_C(22) ||
      progress.plan.stage != UINT32_C(23)) return 0;
  return 1;
}}

int main(void) {{
  uint32_t workspace[240];
  uint32_t index = UINT32_C(0);
  if (!lifecycle()) return 70;
  while (index < (uint32_t)(sizeof(cases) / sizeof(cases[0]))) {{
    MalbolgeGuestMathSincosBinary64Progress progress;
    if (!malbolge_guest_math_unary_sincos_binary64_available(
            (MalbolgeGuestMathUnaryOperation)cases[index].operation,
            cases[index].bits, UINT32_C(0), workspace, UINT32_C(240),
            &progress) ||
        progress.status !=
            MALBOLGE_GUEST_MATH_SINCOS_BINARY64_REFINED_RESOLVED) return 71;
    (void)printf("%" PRIu32 " %016" PRIx64 " %" PRIu32 " %016" PRIx64 "\\n",
                 cases[index].operation, cases[index].bits, progress.plan.stage,
                 progress.bits);
    ++index;
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


def test_sub_four_handoff_matches_fraction_authority(tmp_path: Path) -> None:
    """Certify retained final bits and exact retry stages without host trig."""
    harness = tmp_path / "sincos-binary64-handoff.c"
    executable = tmp_path / "sincos-binary64-handoff"
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
    rows = tuple(line.split() for line in executed.stdout.splitlines())
    assert len(rows) == len(CASES)
    for (operation, bits, stage), row in zip(CASES, rows, strict=True):
        assert int(row[0]) == operation
        assert int(row[1], 16) == bits
        assert int(row[2]) == stage
        assert int(row[3], 16) == _expected_bits(operation, bits)
