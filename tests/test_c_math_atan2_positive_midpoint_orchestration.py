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
#   - Positive-branch midpoint orchestration evidence for adaptive atan2.
# - Must-Not:
#   - Use host trig, pi constants, or fixed-Q atan as midpoint comparison
#     authority.
# - Allows:
#   - Inputs: positive finite binary64 pairs and their candidate rounding cells.
#   - Outputs: strict lower/upper midpoint ordering or unresolved refinement.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Quadrant/pole classification gains complete signed midpoint policy.
# - Merge-When:
#   - Complete adaptive atan2 cell certification subsumes this positive branch.
# - Summary:
#   - Runs dyadic materialization, Taylor bounds, and tangent products end to
#     end.
# - Description:
#   - Q256 plus 16 terms certifies both boundaries of retained hard cells.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Insufficient dyadic precision returns unresolved rather than a false
#     proof.
#

"""Positive-branch midpoint orchestration evidence for adaptive atan2."""

from __future__ import annotations

from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
FRACTION_LIMBS = 8
LIMB_COUNT = FRACTION_LIMBS + 1
SCRATCH_LIMBS = LIMB_COUNT * 15
TERMS = 16

HARD_PAIRS = (
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


def _case_block(position: int, y_bits: int, x_bits: int) -> str:
    return f"""  {{
    MalbolgeGuestMathAtan2KernelInput ratio;
    MalbolgeGuestMathAtan2CellMidpoints cell;
    uint64_t output_bits = UINT64_C(0);
    int32_t lower = INT32_C(99);
    int32_t upper = INT32_C(99);
    int32_t coarse = INT32_C(99);
    if (!malbolge_guest_math_atan2_kernel_input(
            UINT64_C(0x{y_bits:016x}), UINT64_C(0x{x_bits:016x}), &ratio) ||
        !malbolge_guest_math_atan2_unique_binary64(
            UINT64_C(0x{y_bits:016x}), UINT64_C(0x{x_bits:016x}),
            &output_bits) ||
        !malbolge_guest_math_atan2_cell_midpoints(output_bits, &cell))
      return 81;
    if (!malbolge_guest_math_positive_midpoint_compare(
            &ratio, &cell.lower, UINT32_C({FRACTION_LIMBS}), UINT32_C({TERMS}),
            &lower, scratch, UINT32_C({SCRATCH_LIMBS})) ||
        !malbolge_guest_math_positive_midpoint_compare(
            &ratio, &cell.upper, UINT32_C({FRACTION_LIMBS}), UINT32_C({TERMS}),
            &upper, scratch, UINT32_C({SCRATCH_LIMBS}))) return 82;
    if (UINT32_C({position}) == UINT32_C(0) &&
        (!malbolge_guest_math_positive_midpoint_compare(
             &ratio, &cell.lower, UINT32_C(1), UINT32_C({TERMS}), &coarse,
             scratch, UINT32_C({SCRATCH_LIMBS})) || coarse != INT32_C(0)))
      return 83;
    (void)printf("{position} %" PRId32 " %" PRId32 "\\n", lower, upper);
  }}"""


def _harness_source() -> str:
    body = "\n".join(
        _case_block(position, y_bits, x_bits)
        for position, (y_bits, x_bits) in enumerate(HARD_PAIRS)
    )
    return f"""#include "math_transcendental_bits.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

int main(void) {{
  uint32_t scratch[{SCRATCH_LIMBS}];
{body}
  return 0;
}}
"""


def test_positive_hard_cells_certify_both_midpoints(tmp_path: Path) -> None:
    """Certify all retained positive hard cells through variable-width C."""
    harness = tmp_path / "positive-midpoint-orchestration.c"
    executable = tmp_path / "positive-midpoint-orchestration"
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
    rows = tuple(line.split() for line in executed.stdout.splitlines())
    assert len(rows) == len(HARD_PAIRS)
    assert all((int(row[1]), int(row[2])) == (1, -1) for row in rows)
