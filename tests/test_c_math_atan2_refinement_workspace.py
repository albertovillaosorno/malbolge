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
