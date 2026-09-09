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
#   - Differential evidence for normalized and direct atan midpoint comparison.
# - Must-Not:
#   - Promote Q128/16 to a full-domain precision or resource ceiling.
# - Allows:
#   - Inputs: kernel-required binary64 ratios and reduced dyadic midpoints.
#   - Outputs: exact agreement of comparison signs, plus retry/error contracts.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - The production refinement scheduler switches to normalized comparison.
# - Merge-When:
#   - Full-domain separation proof subsumes both comparison implementations.
# - Summary:
#   - Pins normalized comparison on signed hard cells and 56-step transport.
# - Description:
#   - The direct comparator is differential evidence, not rounding authority.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Insufficient normalized precision returns comparison zero.
#

"""Differential coverage for normalized atan midpoint comparison."""

from __future__ import annotations

from itertools import product
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
SIGN_BIT = 1 << 63
BASE_HARD_PAIRS = (
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
SIGNED_HARD_PAIRS = tuple(
    (y | y_sign, x | x_sign)
    for y, x in BASE_HARD_PAIRS
    for y_sign, x_sign in product((0, SIGN_BIT), repeat=2)
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


def _source() -> str:
    rows = ",\n".join(
        f"  {{UINT64_C(0x{y:016x}), UINT64_C(0x{x:016x})}}"
        for y, x in SIGNED_HARD_PAIRS
    )
    return f"""#include \"math_transcendental_bits.h\"
#include <stdint.h>

typedef struct Pair {{ uint64_t y, x; }} Pair;
static const Pair pairs[] = {{
{rows}
}};
#define F UINT32_C(6)
#define N (F + UINT32_C(1))
#define LOW_F UINT32_C(4)
#define LOW_N (LOW_F + UINT32_C(1))
#define LOW_SCRATCH (UINT32_C(24) * LOW_N)
#define DIRECT_SCRATCH (UINT32_C(15) * N)
#define NORMALIZED_SCRATCH (UINT32_C(24) * N)

static int compare_one(const Pair pair) {{
  MalbolgeGuestMathAtan2KernelInput ratio;
  MalbolgeGuestMathAtan2CellMidpoints cell;
  uint64_t output = UINT64_C(0);
  uint32_t direct_scratch[DIRECT_SCRATCH];
  uint32_t normalized_scratch[NORMALIZED_SCRATCH];
  int32_t direct_lower = INT32_C(0), direct_upper = INT32_C(0);
  int32_t normalized_lower = INT32_C(0), normalized_upper = INT32_C(0);
  if (malbolge_guest_math_atan2_special(pair.y, pair.x).status !=
          MALBOLGE_GUEST_MATH_SPECIAL_KERNEL_REQUIRED ||
      !malbolge_guest_math_atan2_kernel_input(pair.y, pair.x, &ratio) ||
      !malbolge_guest_math_atan2_unique_binary64(pair.y, pair.x, &output) ||
      !malbolge_guest_math_atan2_cell_midpoints(output, &cell) ||
      !malbolge_guest_math_midpoint_compare(
          &ratio, &cell.lower, F, UINT32_C(16), &direct_lower, direct_scratch,
          DIRECT_SCRATCH) ||
      !malbolge_guest_math_midpoint_compare(
          &ratio, &cell.upper, F, UINT32_C(16), &direct_upper, direct_scratch,
          DIRECT_SCRATCH) ||
      !malbolge_guest_math_normalized_midpoint_compare(
          &ratio, &cell.lower, F, UINT32_C(16), &normalized_lower,
          normalized_scratch, NORMALIZED_SCRATCH) ||
      !malbolge_guest_math_normalized_midpoint_compare(
          &ratio, &cell.upper, F, UINT32_C(16), &normalized_upper,
          normalized_scratch, NORMALIZED_SCRATCH)) return 0;
  return direct_lower == INT32_C(1) && direct_upper == INT32_C(-1) &&
         normalized_lower == direct_lower && normalized_upper == direct_upper;
}}

static int q128_retry_contract(void) {{
  MalbolgeGuestMathAtan2KernelInput ratio;
  MalbolgeGuestMathAtan2CellMidpoints cell;
  uint64_t output = UINT64_C(0);
  uint32_t scratch[LOW_SCRATCH];
  int32_t comparison = INT32_C(88);
  if (!malbolge_guest_math_atan2_kernel_input(pairs[0].y, pairs[0].x, &ratio) ||
      !malbolge_guest_math_atan2_unique_binary64(
          pairs[0].y, pairs[0].x, &output) ||
      !malbolge_guest_math_atan2_cell_midpoints(output, &cell) ||
      !malbolge_guest_math_normalized_midpoint_compare(
          &ratio, &cell.lower, LOW_F, UINT32_C(16), &comparison, scratch,
          LOW_SCRATCH) || comparison != INT32_C(0)) return 0;
  return 1;
}}

static int near_four_contract(void) {{
  const uint64_t one = UINT64_C(0x3ff0000000000000);
  const MalbolgeGuestMathDyadic near_four =
      {{UINT64_C(0x003fffffffffffff), UINT32_C(52), UINT32_C(0)}};
  MalbolgeGuestMathAtan2KernelInput ratio;
  uint32_t direct_scratch[DIRECT_SCRATCH];
  uint32_t normalized_scratch[NORMALIZED_SCRATCH];
  int32_t direct = INT32_C(77), normalized = INT32_C(78);
  if (!malbolge_guest_math_atan2_kernel_input(one, one, &ratio) ||
      !malbolge_guest_math_midpoint_compare(
          &ratio, &near_four, F, UINT32_C(16), &direct, direct_scratch,
          DIRECT_SCRATCH) ||
      !malbolge_guest_math_normalized_midpoint_compare(
          &ratio, &near_four, F, UINT32_C(16), &normalized,
          normalized_scratch, NORMALIZED_SCRATCH) ||
      direct != INT32_C(-1) || normalized != direct) return 0;
  normalized = INT32_C(78);
  if (!malbolge_guest_math_normalized_midpoint_compare(
          &ratio, &near_four, UINT32_C(3), UINT32_C(16), &normalized,
          normalized_scratch, NORMALIZED_SCRATCH) || normalized != INT32_C(0))
    return 0;
  normalized = INT32_C(78);
  if (malbolge_guest_math_normalized_midpoint_compare(
          &ratio, &near_four, F, UINT32_C(16), &normalized,
          normalized_scratch, NORMALIZED_SCRATCH - UINT32_C(1)) ||
      normalized != INT32_C(78)) return 0;
  return 1;
}}

int main(void) {{
  uint32_t index = UINT32_C(0);
  while (index < (uint32_t)(sizeof(pairs) / sizeof(pairs[0]))) {{
    if (!compare_one(pairs[index])) return 70;
    ++index;
  }}
  return q128_retry_contract() && near_four_contract() ? 0 : 71;
}}
"""


def test_normalized_midpoint_compare_matches_direct_signed_hard_cells(
    tmp_path: Path,
) -> None:
    """Match direct comparison across signed hard cells and full transport."""
    harness = tmp_path / "atan2-normalized-midpoint-compare.c"
    executable = tmp_path / "atan2-normalized-midpoint-compare"
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
