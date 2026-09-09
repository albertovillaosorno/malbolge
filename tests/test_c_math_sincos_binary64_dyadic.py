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
#   - Exact binary64-to-dyadic input bridge below four after unary preproofs.
# - Must-Not:
#   - Perform periodic range reduction or claim final sin/cos rounding.
# - Allows:
#   - Inputs: raw binary64 words and SIN/COS operation selectors.
#   - Outputs: exact reduced signed dyadics with denominator shift at most 79.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Full binary64 range reduction introduces quotient/remainder state.
# - Merge-When:
#   - Public sin/cos input reduction subsumes this exact sub-four boundary.
# - Summary:
#   - Connects real binary64 inputs to normalized dyadic sincos refinement.
# - Description:
#   - Fraction independently reconstructs every accepted raw input exactly.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Preproof-resolved inputs and magnitudes at least four remain rejected.
#

"""Exact binary64-to-dyadic sincos input bridge evidence."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
SIGN = 1 << 63
MAG = SIGN - 1
EXPONENT_MASK = 0x7FF
FRACTION_MASK = (1 << 52) - 1
HIDDEN = 1 << 52
SIN = 1
COS = 2
SIN_CUTOFF = 0x3E57000000000000
COS_CUTOFF = 0x3E46A00000000000
FOUR = 0x4010000000000000
MAX_SHIFT = 79
CASE_COUNT = 520


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
    magnitude = bits & MAG
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


def _expected(bits: int) -> tuple[int, int, int]:
    value = _binary64(bits)
    magnitude = abs(value)
    shift = magnitude.denominator.bit_length() - 1
    return magnitude.numerator, shift, int(value < 0)


def _cases() -> tuple[tuple[int, int], ...]:
    fixed = [
        (SIN, SIN_CUTOFF + 1),
        (SIN, SIGN | (SIN_CUTOFF + 1)),
        (COS, COS_CUTOFF + 1),
        (COS, SIGN | (COS_CUTOFF + 1)),
        (SIN, 0x3FE8000000000000),
        (COS, 0x3FF0000000000000),
        (SIN, FOUR - 1),
        (COS, SIGN | (FOUR - 1)),
    ]
    state = 0x53494E434F534459
    rows = list(fixed)
    while len(rows) < CASE_COUNT:
        state = (state * 6364136223846793005 + 1442695040888963407) & (
            (1 << 64) - 1
        )
        magnitude = state & MAG
        if magnitude == 0 or magnitude >= FOUR:
            continue
        operation = SIN if state & 1 else COS
        cutoff = SIN_CUTOFF if operation == SIN else COS_CUTOFF
        if magnitude <= cutoff:
            continue
        rows.append((operation, magnitude | (state & SIGN)))
    return tuple(rows)


CASES = _cases()


def _source() -> str:
    rows = ",\n".join(
        f"  {{UINT32_C({operation}), UINT64_C(0x{bits:016x})}}"
        for operation, bits in CASES
    )
    return f"""#include "math_transcendental_bits.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
typedef struct Case {{ uint32_t operation; uint64_t bits; }} Case;
static const Case cases[] = {{
{rows}
}};
int main(void) {{
  uint32_t index = UINT32_C(0);
  while (index < (uint32_t)(sizeof(cases) / sizeof(cases[0]))) {{
    MalbolgeGuestMathDyadic value;
    if (!malbolge_guest_math_unary_reduced_dyadic(
            (MalbolgeGuestMathUnaryOperation)cases[index].operation,
            cases[index].bits, &value)) return 81;
    (void)printf("%" PRIu64 " %" PRIu32 " %" PRIu32 "\\n",
                 value.numerator, value.denominator_shift, value.negative);
    ++index;
  }}
  {{
    MalbolgeGuestMathDyadic value = {{UINT64_C(11), UINT32_C(22), UINT32_C(1)}};
    static const Case bad[] = {{
      {{UINT32_C({SIN}), UINT64_C(0x{SIN_CUTOFF:016x})}},
      {{UINT32_C({COS}), UINT64_C(0x{COS_CUTOFF:016x})}},
      {{UINT32_C({SIN}), UINT64_C(0)}},
      {{UINT32_C({COS}), UINT64_C(0x7ff0000000000000)}},
      {{UINT32_C({SIN}), UINT64_C(0x7ff8000000000001)}},
      {{UINT32_C({COS}), UINT64_C(0x{FOUR:016x})}},
      {{UINT32_C(99), UINT64_C(0x3ff0000000000000)}}
    }};
    index = UINT32_C(0);
    while (index < (uint32_t)(sizeof(bad) / sizeof(bad[0]))) {{
      if (malbolge_guest_math_unary_reduced_dyadic(
              (MalbolgeGuestMathUnaryOperation)bad[index].operation,
              bad[index].bits, &value) || value.numerator != UINT64_C(11) ||
          value.denominator_shift != UINT32_C(22) ||
          value.negative != UINT32_C(1)) return 82;
      ++index;
    }}
  }}
  return 0;
}}
"""


def test_binary64_reduced_dyadic_matches_fraction(tmp_path: Path) -> None:
    """Match every accepted raw value and pin the tight shift-79 cosine edge."""
    harness = tmp_path / "binary64-sincos-dyadic.c"
    executable = tmp_path / "binary64-sincos-dyadic"
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
    records = tuple(
        tuple(map(int, line.split())) for line in executed.stdout.splitlines()
    )
    assert len(records) == len(CASES)
    for (_, bits), record in zip(CASES, records, strict=True):
        assert record == _expected(bits)
        assert record[1] <= MAX_SHIFT
    cosine_edge = records[2]
    assert CASES[2] == (COS, COS_CUTOFF + 1)
    assert cosine_edge[1] == MAX_SHIFT
