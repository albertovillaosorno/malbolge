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
#   - Signed branch and principal-range midpoint comparison evidence for atan2.
# - Must-Not:
#   - Use host trig, pi constants, or atan-family fixed-Q oracles as authority.
# - Allows:
#   - Inputs: finite nonzero binary64 ratios and exact signed dyadic midpoints.
#   - Outputs: strict angular order or unresolved directed refinement.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Adaptive precision/term scheduling gains independently testable policy.
# - Merge-When:
#   - Complete adaptive atan2 cell certification subsumes branch comparison.
# - Summary:
#   - Proves all four quadrant ranks, signed tangent order, and principal wraps.
# - Description:
#   - Signed hard cells exercise same-branch products; synthetic dyadics pin
#     rank order.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Unproven sin/cos signs remain unresolved instead of guessing a branch.
#

"""Signed branch/pole midpoint comparison evidence for adaptive atan2."""

from __future__ import annotations

from itertools import product
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
SIGN_BIT = 1 << 63
FRACTION_LIMBS = 8
LIMB_COUNT = FRACTION_LIMBS + 1
SCRATCH_LIMBS = LIMB_COUNT * 15
TERMS = 16
RANK_ROW_COUNT = 16

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


def _signed_hard_pairs() -> tuple[tuple[int, int], ...]:
    return tuple(
        (y | y_sign, x | x_sign)
        for y, x in BASE_HARD_PAIRS
        for y_sign, x_sign in product((0, SIGN_BIT), repeat=2)
    )


def _hard_rows() -> str:
    return ",\n".join(
        f"  {{UINT64_C(0x{y:016x}), UINT64_C(0x{x:016x})}}"
        for y, x in _signed_hard_pairs()
    )


def _hard_harness_source() -> str:
    return f"""#include "math_transcendental_bits.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

typedef struct Pair {{ uint64_t y; uint64_t x; }} Pair;
static const Pair pairs[] = {{
{_hard_rows()}
}};

int main(void) {{
  uint32_t scratch[{SCRATCH_LIMBS}];
  uint32_t index = UINT32_C(0);
  while (index < (uint32_t)(sizeof(pairs) / sizeof(pairs[0]))) {{
    MalbolgeGuestMathAtan2KernelInput ratio;
    MalbolgeGuestMathAtan2CellMidpoints cell;
    uint64_t output_bits = UINT64_C(0);
    int32_t lower = INT32_C(99);
    int32_t upper = INT32_C(99);
    if (!malbolge_guest_math_atan2_kernel_input(
            pairs[index].y, pairs[index].x, &ratio) ||
        !malbolge_guest_math_atan2_unique_binary64(
            pairs[index].y, pairs[index].x, &output_bits) ||
        !malbolge_guest_math_atan2_cell_midpoints(output_bits, &cell))
      return 81;
    if (!malbolge_guest_math_midpoint_compare(
            &ratio, &cell.lower, UINT32_C({FRACTION_LIMBS}), UINT32_C({TERMS}),
            &lower, scratch, UINT32_C({SCRATCH_LIMBS})) ||
        !malbolge_guest_math_midpoint_compare(
            &ratio, &cell.upper, UINT32_C({FRACTION_LIMBS}), UINT32_C({TERMS}),
            &upper, scratch, UINT32_C({SCRATCH_LIMBS}))) return 82;
    (void)printf("%" PRIu32 " %" PRId32 " %" PRId32 "\\n",
                 index, lower, upper);
    ++index;
  }}
  return 0;
}}
"""


def test_signed_hard_cells_certify_all_quadrants(tmp_path: Path) -> None:
    """Certify both cell midpoints for 16 hard ratios in all four quadrants."""
    harness = tmp_path / "midpoint-branches-hard.c"
    executable = tmp_path / "midpoint-branches-hard"
    _ = harness.write_text(_hard_harness_source(), encoding="utf-8")
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
    rows = tuple(line.split() for line in executed.stdout.splitlines())
    assert len(rows) == len(_signed_hard_pairs())
    assert all((int(row[1]), int(row[2])) == (1, -1) for row in rows)


def _rank_harness_source() -> str:
    return f"""#include "math_transcendental_bits.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

typedef struct SignedPair {{ uint64_t y; uint64_t x; }} SignedPair;
static const SignedPair pairs[] = {{
  {{UINT64_C(0xbff0000000000000), UINT64_C(0xbff0000000000000)}},
  {{UINT64_C(0xbff0000000000000), UINT64_C(0x3ff0000000000000)}},
  {{UINT64_C(0x3ff0000000000000), UINT64_C(0x3ff0000000000000)}},
  {{UINT64_C(0x3ff0000000000000), UINT64_C(0xbff0000000000000)}}
}};

static int compare_all(MalbolgeGuestMathDyadic midpoint) {{
  uint32_t scratch[{SCRATCH_LIMBS}];
  uint32_t index = UINT32_C(0);
  while (index < UINT32_C(4)) {{
    MalbolgeGuestMathAtan2KernelInput ratio;
    int32_t comparison = INT32_C(99);
    if (!malbolge_guest_math_atan2_kernel_input(
            pairs[index].y, pairs[index].x, &ratio) ||
        !malbolge_guest_math_midpoint_compare(
            &ratio, &midpoint, UINT32_C({FRACTION_LIMBS}), UINT32_C({TERMS}),
            &comparison, scratch, UINT32_C({SCRATCH_LIMBS}))) return 0;
    (void)printf("%" PRIu32 " %" PRIu32 " %" PRId32 "\\n",
                 midpoint.negative, index, comparison);
    ++index;
  }}
  return 1;
}}

int main(void) {{
  MalbolgeGuestMathDyadic positive_one =
      {{UINT64_C(1), UINT32_C(0), UINT32_C(0)}};
  MalbolgeGuestMathDyadic negative_one =
      {{UINT64_C(1), UINT32_C(0), UINT32_C(1)}};
  MalbolgeGuestMathDyadic positive_wrap =
      {{UINT64_C(7), UINT32_C(1), UINT32_C(0)}};
  MalbolgeGuestMathDyadic negative_wrap =
      {{UINT64_C(7), UINT32_C(1), UINT32_C(1)}};
  if (!compare_all(positive_one) || !compare_all(negative_one) ||
      !compare_all(positive_wrap) || !compare_all(negative_wrap)) return 91;
  return 0;
}}
"""


def test_branch_rank_and_principal_wrap_order(tmp_path: Path) -> None:
    """Pin rank order at signed one and principal wraps at plus/minus 3.5."""
    harness = tmp_path / "midpoint-branches-rank.c"
    executable = tmp_path / "midpoint-branches-rank"
    _ = harness.write_text(_rank_harness_source(), encoding="utf-8")
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
    rows = tuple(line.split() for line in executed.stdout.splitlines())
    assert len(rows) == RANK_ROW_COUNT
    comparisons = tuple(int(row[2]) for row in rows)
    assert comparisons[0:4] == (-1, -1, -1, 1)
    assert comparisons[4:8] == (-1, 1, 1, 1)
    assert comparisons[8:12] == (-1, -1, -1, -1)
    assert comparisons[12:16] == (1, 1, 1, 1)
