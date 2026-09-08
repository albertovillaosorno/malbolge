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
#   - Caller-owned binary-limb workspace evidence for atan2 midpoint refinement.
# - Must-Not:
#   - Allocate memory, consume the guest heap, or use host floating arithmetic.
# - Allows:
#   - Inputs: exact signed dyadics and requested binary fractional precision.
#   - Outputs: exact little-endian u32 magnitude limbs or capacity rejection.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Tangent interval arithmetic gains an independently testable
#     implementation.
# - Merge-When:
#   - Complete adaptive atan2 refinement owns this workspace contract directly.
# - Summary:
#   - Proves dyadic inputs enter caller-owned variable-precision binary limbs.
# - Description:
#   - Required capacity is planned without allocation; short buffers fail
#     closed.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Limb order is little-endian and sign remains in the source dyadic.
#

"""Caller-owned binary-limb workspace evidence for adaptive atan2."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
UINT32_MAX = (1 << 32) - 1


@dataclass(frozen=True)
class DyadicCase:
    """One exact dyadic and target fixed-point precision."""

    numerator: int
    denominator_shift: int
    negative: int
    fraction_bits: int


CASES = (
    DyadicCase(0, 0, 0, 107),
    DyadicCase(1, 107, 0, 107),
    DyadicCase(1, 107, 1, 128),
    DyadicCase(0x1F_FFFF_FFFF_FFFF, 107, 0, 128),
    DyadicCase(0x10_0000_0000_0001, 82, 1, 129),
    DyadicCase(0x1A_2B3C_4D5E_6F71, 64, 0, 256),
    DyadicCase(0x7FFF_FFFF_FFFF_FFFF, 53, 1, 4096),
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


def _row_literal(case: DyadicCase) -> str:
    return (
        f"  {{UINT64_C(0x{case.numerator:016x}), "
        f"UINT32_C({case.denominator_shift}), "
        f"UINT32_C({case.negative}), UINT32_C({case.fraction_bits})}}"
    )


def _harness_source() -> str:
    rows = ",\n".join(_row_literal(case) for case in CASES)
    return f"""#include "math_transcendental_bits.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

typedef struct Row {{
  uint64_t numerator;
  uint32_t denominator_shift;
  uint32_t negative;
  uint32_t fraction_bits;
}} Row;

static const Row rows[] = {{
{rows}
}};

int main(void) {{
  uint32_t index = UINT32_C(0);
  while (index < (uint32_t)(sizeof(rows) / sizeof(rows[0]))) {{
    MalbolgeGuestMathDyadic input;
    uint32_t limbs[130];
    uint32_t required = UINT32_C(0);
    uint32_t limb = UINT32_C(0);
    input.numerator = rows[index].numerator;
    input.denominator_shift = rows[index].denominator_shift;
    input.negative = rows[index].negative;
    if (!malbolge_guest_math_dyadic_fixed_limb_count(
            &input, rows[index].fraction_bits, &required) ||
        required > UINT32_C(130) ||
        !malbolge_guest_math_dyadic_write_fixed(
            &input, rows[index].fraction_bits, limbs, required)) {{
      return 91;
    }}
    (void)printf("%" PRIu32, required);
    while (limb < required) {{
      (void)printf(" %08" PRIx32, limbs[limb]);
      ++limb;
    }}
    (void)printf("\\n");
    ++index;
  }}
  return 0;
}}
"""


def _expected(case: DyadicCase) -> tuple[int, tuple[int, ...]]:
    assert case.fraction_bits >= case.denominator_shift
    integer = case.numerator << (case.fraction_bits - case.denominator_shift)
    required = max(1, (integer.bit_length() + 31) // 32)
    limbs = tuple(
        (integer >> (32 * index)) & UINT32_MAX for index in range(required)
    )
    return required, limbs


def test_dyadic_workspace_matches_exact_integer_authority(
    tmp_path: Path,
) -> None:
    """Write exact dyadics through 4,096 fractional bits without allocation."""
    harness = tmp_path / "dyadic-workspace.c"
    executable = tmp_path / "dyadic-workspace"
    _ = harness.write_text(_harness_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
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
    records = tuple(line.split() for line in executed.stdout.splitlines())
    assert len(records) == len(CASES)
    for case, record in zip(CASES, records, strict=True):
        required, limbs = _expected(case)
        assert int(record[0]) == required
        assert tuple(int(item, 16) for item in record[1:]) == limbs


def _failure_harness_source() -> str:
    return r"""#include "math_transcendental_bits.h"
#include <stdint.h>

int main(void) {
  MalbolgeGuestMathDyadic input = {
      UINT64_C(0x1fffffffffffff), UINT32_C(107), UINT32_C(0)};
  MalbolgeGuestMathDyadic invalid_sign = input;
  uint32_t limbs[4] = {
      UINT32_C(0xaaaaaaaa), UINT32_C(0xbbbbbbbb),
      UINT32_C(0xcccccccc), UINT32_C(0xdddddddd)};
  uint32_t required = UINT32_C(0x13579bdf);
  uint32_t huge_required = UINT32_C(0);

  if (!malbolge_guest_math_dyadic_fixed_limb_count(
          &input, UINT32_C(256), &required) || required != UINT32_C(7)) {
    return 81;
  }
  if (malbolge_guest_math_dyadic_write_fixed(
          &input, UINT32_C(256), limbs, UINT32_C(4)) ||
      limbs[0] != UINT32_C(0xaaaaaaaa) ||
      limbs[1] != UINT32_C(0xbbbbbbbb) ||
      limbs[2] != UINT32_C(0xcccccccc) ||
      limbs[3] != UINT32_C(0xdddddddd)) {
    return 82;
  }
  required = UINT32_C(0x13579bdf);
  if (malbolge_guest_math_dyadic_fixed_limb_count(
          &input, UINT32_C(106), &required) ||
      required != UINT32_C(0x13579bdf)) {
    return 83;
  }
  invalid_sign.negative = UINT32_C(2);
  if (malbolge_guest_math_dyadic_fixed_limb_count(
          &invalid_sign, UINT32_C(256), &required)) {
    return 84;
  }
  if (!malbolge_guest_math_dyadic_fixed_limb_count(
          &input, UINT32_MAX, &huge_required) ||
      huge_required != UINT32_C(134217727)) {
    return 85;
  }
  if (malbolge_guest_math_dyadic_fixed_limb_count(
          0, UINT32_C(256), &required) ||
      malbolge_guest_math_dyadic_fixed_limb_count(
          &input, UINT32_C(256), 0) ||
      malbolge_guest_math_dyadic_write_fixed(
          &input, UINT32_C(256), 0, UINT32_C(8))) {
    return 86;
  }
  return 0;
}
"""


def test_dyadic_workspace_plans_before_nonmutating_capacity_failure(
    tmp_path: Path,
) -> None:
    """Plan huge precision and reject short buffers without mutation."""
    harness = tmp_path / "dyadic-workspace-failure.c"
    executable = tmp_path / "dyadic-workspace-failure"
    _ = harness.write_text(_failure_harness_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
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


@dataclass(frozen=True)
class ArithmeticCase:
    """One variable-width fixed-point product and small-division fixture."""

    limb_count: int
    left: int
    right: int
    divisor: int


def _pattern_integer(limb_count: int, seed: int) -> int:
    state = seed
    limbs: list[int] = []
    for _ in range(limb_count):
        state = (state * 6364136223846793005 + 1442695040888963407) & (
            (1 << 64) - 1
        )
        limbs.append((state >> 16) & UINT32_MAX)
    limbs[-1] &= 3
    return sum(limb << (32 * index) for index, limb in enumerate(limbs))


def _arithmetic_cases() -> tuple[ArithmeticCase, ...]:
    widths = (4, 8, 16, 128)
    divisors = (3, 239, 0x80000001, UINT32_MAX)
    return tuple(
        ArithmeticCase(
            width,
            _pattern_integer(width, 0x4154414E0000 + width),
            _pattern_integer(width, 0x54414E470000 + width),
            divisor,
        )
        for width, divisor in zip(widths, divisors, strict=True)
    )


def _c_limbs(integer: int, count: int) -> str:
    values = tuple(
        (integer >> (32 * index)) & UINT32_MAX for index in range(count)
    )
    return ", ".join(f"UINT32_C(0x{value:08x})" for value in values)


def _arithmetic_harness_source() -> str:
    blocks: list[str] = []
    for case in _arithmetic_cases():
        count = case.limb_count
        blocks.append(
            f"""  {{
    uint32_t left[{count}] = {{{_c_limbs(case.left, count)}}};
    uint32_t right[{count}] = {{{_c_limbs(case.right, count)}}};
    uint32_t output[{count}];
    uint32_t divide[{count}] = {{{_c_limbs(case.left, count)}}};
    uint32_t scratch[{count * 2}];
    uint32_t discarded = UINT32_C(0);
    uint32_t remainder = UINT32_C(0);
    uint32_t index = UINT32_C(0);
    if (!malbolge_guest_math_fixed_multiply_floor(
            left, right, UINT32_C({count}), UINT32_C({count - 1}), output,
            scratch, UINT32_C({count * 2}), &discarded)) {{
      return 91;
    }}
    (void)printf("M {count} %" PRIu32, discarded);
    while (index < UINT32_C({count})) {{
      (void)printf(" %08" PRIx32, output[index]);
      ++index;
    }}
    (void)printf("\\n");
    if (!malbolge_guest_math_fixed_divide_small_floor(
            divide, UINT32_C({count}), UINT32_C({case.divisor}), divide,
            &remainder)) {{
      return 92;
    }}
    (void)printf("D {count} %" PRIu32, remainder);
    index = UINT32_C(0);
    while (index < UINT32_C({count})) {{
      (void)printf(" %08" PRIx32, divide[index]);
      ++index;
    }}
    (void)printf("\\n");
  }}"""
        )
    body = "\n".join(blocks)
    return f"""#include "math_transcendental_bits.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

int main(void) {{
{body}
  return 0;
}}
"""


def _limbs_to_integer(items: list[str]) -> int:
    return sum(
        int(item, 16) << (32 * index) for index, item in enumerate(items)
    )


def _assert_arithmetic_records(records: tuple[list[str], ...]) -> None:
    assert len(records) == 2 * len(_arithmetic_cases())
    for case, product_row, divide_row in zip(
        _arithmetic_cases(), records[::2], records[1::2], strict=True
    ):
        shift = 32 * (case.limb_count - 1)
        full_product = case.left * case.right
        expected_product = full_product >> shift
        expected_discarded = int(full_product != expected_product << shift)
        assert product_row[:3] == [
            "M",
            str(case.limb_count),
            str(expected_discarded),
        ]
        assert _limbs_to_integer(product_row[3:]) == expected_product
        expected_quotient, expected_remainder = divmod(case.left, case.divisor)
        assert divide_row[:3] == [
            "D",
            str(case.limb_count),
            str(expected_remainder),
        ]
        assert _limbs_to_integer(divide_row[3:]) == expected_quotient


def test_variable_fixed_product_and_division_match_integer_authority(
    tmp_path: Path,
) -> None:
    """Match Python integers through 128 caller-owned limbs."""
    harness = tmp_path / "variable-fixed-arithmetic.c"
    executable = tmp_path / "variable-fixed-arithmetic"
    _ = harness.write_text(_arithmetic_harness_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
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
    records = tuple(line.split() for line in executed.stdout.splitlines())
    _assert_arithmetic_records(records)


def _arithmetic_failure_harness_source() -> str:
    return r"""#include "math_transcendental_bits.h"
#include <stdint.h>

int main(void) {
  uint32_t maximum[4] = {
      UINT32_MAX, UINT32_MAX, UINT32_MAX, UINT32_MAX};
  uint32_t one[4] = {UINT32_C(1), UINT32_C(0), UINT32_C(0), UINT32_C(0)};
  uint32_t output[4] = {
      UINT32_C(0x11111111), UINT32_C(0x22222222),
      UINT32_C(0x33333333), UINT32_C(0x44444444)};
  uint32_t scratch[8] = {
      UINT32_C(9), UINT32_C(9), UINT32_C(9), UINT32_C(9),
      UINT32_C(9), UINT32_C(9), UINT32_C(9), UINT32_C(9)};
  uint32_t discarded = UINT32_C(0xabcdef01);
  uint32_t remainder = UINT32_C(0x76543210);

  if (malbolge_guest_math_fixed_multiply_floor(
          maximum, maximum, UINT32_C(4), UINT32_C(0), output, scratch,
          UINT32_C(8), &discarded) ||
      output[0] != UINT32_C(0x11111111) ||
      discarded != UINT32_C(0xabcdef01)) {
    return 81;
  }
  if (malbolge_guest_math_fixed_multiply_floor(
          one, one, UINT32_C(4), UINT32_C(3), output, scratch,
          UINT32_C(7), &discarded) ||
      output[0] != UINT32_C(0x11111111) ||
      discarded != UINT32_C(0xabcdef01)) {
    return 82;
  }
  if (malbolge_guest_math_fixed_divide_small_floor(
          one, UINT32_C(4), UINT32_C(0), output, &remainder) ||
      output[0] != UINT32_C(0x11111111) ||
      remainder != UINT32_C(0x76543210)) {
    return 83;
  }
  return 0;
}
"""


def test_variable_fixed_arithmetic_fails_before_result_publication(
    tmp_path: Path,
) -> None:
    """Reject product overflow, short scratch, and zero divisor fail closed."""
    harness = tmp_path / "variable-fixed-failure.c"
    executable = tmp_path / "variable-fixed-failure"
    _ = harness.write_text(
        _arithmetic_failure_harness_source(), encoding="utf-8"
    )
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
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
