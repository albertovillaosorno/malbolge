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
#   - Atomic full-cell refinement-attempt evidence for adaptive atan2.
# - Must-Not:
#   - Treat unresolved boundaries as certification or mutate status on hard
#     failure.
# - Allows:
#   - Inputs: kernel-required binary64 pairs, one candidate cell,
#     precision/depth.
#   - Outputs: certified one, unresolved zero, or nonpublishing hard failure.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Retry scheduling and capacity planning gain independent policy.
# - Merge-When:
#   - Complete adaptive atan2 fallback owns cell attempts directly.
# - Summary:
#   - Requires strict lower-positive and upper-negative ordering before certify.
# - Description:
#   - Wrong candidates and coarse precision remain cleanly uncertified.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Special inputs and undersized scratch are hard, nonpublishing failures.
#

"""Atomic full-cell refinement-attempt evidence for adaptive atan2."""

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


def _rows() -> str:
    return ",\n".join(
        f"  {{UINT64_C(0x{y:016x}), UINT64_C(0x{x:016x})}}"
        for y, x in _signed_hard_pairs()
    )


def _success_harness_source() -> str:
    return f"""#include "math_transcendental_bits.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

typedef struct Pair {{ uint64_t y; uint64_t x; }} Pair;
static const Pair pairs[] = {{
{_rows()}
}};

int main(void) {{
  uint32_t scratch[{SCRATCH_LIMBS}];
  uint32_t index = UINT32_C(0);
  while (index < (uint32_t)(sizeof(pairs) / sizeof(pairs[0]))) {{
    uint64_t candidate = UINT64_C(0);
    uint32_t certified = UINT32_C(9);
    if (!malbolge_guest_math_atan2_unique_binary64(
            pairs[index].y, pairs[index].x, &candidate) ||
        !malbolge_guest_math_atan2_refinement_attempt(
            pairs[index].y, pairs[index].x, candidate,
            UINT32_C({FRACTION_LIMBS}), UINT32_C({TERMS}), &certified, scratch,
            UINT32_C({SCRATCH_LIMBS})) || certified != UINT32_C(1)) return 81;
    ++index;
  }}
  (void)printf("%" PRIu32 "\\n", index);
  return 0;
}}
"""


def test_refinement_attempt_certifies_all_signed_hard_cells(
    tmp_path: Path,
) -> None:
    """Certify the current candidate for all 64 signed hard cells."""
    harness = tmp_path / "refinement-attempt.c"
    executable = tmp_path / "refinement-attempt"
    _ = harness.write_text(_success_harness_source(), encoding="utf-8")
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
    assert int(executed.stdout.strip()) == len(_signed_hard_pairs())


def _failure_harness_source() -> str:
    return f"""#include "math_transcendental_bits.h"
#include <stdint.h>

int main(void) {{
  const uint64_t y = UINT64_C(0x3fee19fa869ea9fc);
  const uint64_t x = UINT64_C(0x3ff197dd31b21770);
  uint32_t scratch[{SCRATCH_LIMBS}];
  uint64_t candidate = UINT64_C(0);
  uint32_t certified = UINT32_C(9);
  if (!malbolge_guest_math_atan2_unique_binary64(y, x, &candidate)) return 91;
  if (!malbolge_guest_math_atan2_refinement_attempt(
          y, x, candidate, UINT32_C(1), UINT32_C({TERMS}), &certified, scratch,
          UINT32_C({SCRATCH_LIMBS})) || certified != UINT32_C(0)) return 92;
  certified = UINT32_C(9);
  if (!malbolge_guest_math_atan2_refinement_attempt(
          y, x, candidate + UINT64_C(1), UINT32_C({FRACTION_LIMBS}),
          UINT32_C({TERMS}), &certified, scratch, UINT32_C({SCRATCH_LIMBS})) ||
      certified != UINT32_C(0)) return 93;
  certified = UINT32_C(9);
  if (malbolge_guest_math_atan2_refinement_attempt(
          y, x, candidate, UINT32_C({FRACTION_LIMBS}), UINT32_C({TERMS}),
          &certified, scratch, UINT32_C({SCRATCH_LIMBS - 1})) ||
      certified != UINT32_C(9)) return 94;
  certified = UINT32_C(9);
  if (malbolge_guest_math_atan2_refinement_attempt(
          UINT64_C(0x3ff0000000000000), UINT64_C(0x3ff0000000000000),
          UINT64_C(0x3fe921fb54442d18), UINT32_C({FRACTION_LIMBS}),
          UINT32_C({TERMS}), &certified, scratch, UINT32_C({SCRATCH_LIMBS})) ||
      certified != UINT32_C(9)) return 95;
  return 0;
}}
"""


def test_refinement_attempt_distinguishes_retry_from_hard_failure(
    tmp_path: Path,
) -> None:
    """Keep coarse/wrong cells uncertified and hard failures nonpublishing."""
    harness = tmp_path / "refinement-attempt-failure.c"
    executable = tmp_path / "refinement-attempt-failure"
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
