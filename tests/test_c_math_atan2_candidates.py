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
#   - Conservative Q256 binary64 candidate-cell extraction evidence for atan2.
# - Must-Not:
#   - Treat the retained corpus as proof that Q256 always spans at most two
#     cells.
# - Allows:
#   - Inputs: synthetic Q256 intervals and retained finite atan2 kernel pairs.
#   - Outputs: one/two adjacent candidates or fail-closed rejection.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Candidate certification policy gains independent retry state.
# - Merge-When:
#   - Complete adaptive fallback owns proposal and certification together.
# - Summary:
#   - Extract endpoint-rounded cells only when they are equal or adjacent.
# - Description:
#   - Synthetic midpoint straddles exercise the two-cell path exactly.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Wider spans and malformed intervals fail without mutating output.
#

"""Conservative Q256 candidate-cell extraction evidence for atan2."""

from __future__ import annotations

from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"


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


def _compile_and_run(source: str, tmp_path: Path, name: str) -> None:
    harness = tmp_path / f"{name}.c"
    executable = tmp_path / name
    _ = harness.write_text(source, encoding="utf-8")
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


def test_fixed256_candidates_pin_one_two_and_wide_spans(tmp_path: Path) -> None:
    """Extract one/two cells and reject wider or malformed Q256 spans."""
    source = r"""#include "math_transcendental_bits.h"
#include <stdint.h>

static void zero_interval(MalbolgeGuestMathFixed256Interval *value) {
  uint32_t index = UINT32_C(0);
  while (index < MALBOLGE_GUEST_MATH_FIXED_256_LIMBS) {
    value->lower.limbs[index] = UINT32_C(0);
    value->upper.limbs[index] = UINT32_C(0);
    ++index;
  }
}

int main(void) {
  MalbolgeGuestMathFixed256Interval interval;
  MalbolgeGuestMathAtan2Candidates out = {
      UINT32_C(7), {UINT64_C(0xaaaaaaaaaaaaaaaa),
                    UINT64_C(0xbbbbbbbbbbbbbbbb)}};
  zero_interval(&interval);
  interval.lower.limbs[8] = UINT32_C(1);
  interval.upper.limbs[8] = UINT32_C(1);
  if (!malbolge_guest_math_fixed256_candidates(&interval, &out) ||
      out.count != UINT32_C(1) ||
      out.bits[0] != UINT64_C(0x3ff0000000000000) ||
      out.bits[1] != UINT64_C(0x3ff0000000000000)) return 81;

  zero_interval(&interval);
  interval.lower.limbs[0] = UINT32_C(0xffffffff);
  interval.lower.limbs[1] = UINT32_C(0xffffffff);
  interval.lower.limbs[2] = UINT32_C(0xffffffff);
  interval.lower.limbs[3] = UINT32_C(0xffffffff);
  interval.lower.limbs[4] = UINT32_C(0xffffffff);
  interval.lower.limbs[5] = UINT32_C(0xffffffff);
  interval.lower.limbs[6] = UINT32_C(0x000007ff);
  interval.lower.limbs[8] = UINT32_C(1);
  interval.upper.limbs[0] = UINT32_C(1);
  interval.upper.limbs[6] = UINT32_C(0x00000800);
  interval.upper.limbs[8] = UINT32_C(1);
  if (!malbolge_guest_math_fixed256_candidates(&interval, &out) ||
      out.count != UINT32_C(2) ||
      out.bits[0] != UINT64_C(0x3ff0000000000000) ||
      out.bits[1] != UINT64_C(0x3ff0000000000001)) return 82;

  zero_interval(&interval);
  interval.lower.limbs[8] = UINT32_C(1);
  interval.upper.limbs[6] = UINT32_C(0x00002000);
  interval.upper.limbs[8] = UINT32_C(1);
  out.count = UINT32_C(7);
  out.bits[0] = UINT64_C(0xaaaaaaaaaaaaaaaa);
  if (malbolge_guest_math_fixed256_candidates(&interval, &out) ||
      out.count != UINT32_C(7) ||
      out.bits[0] != UINT64_C(0xaaaaaaaaaaaaaaaa)) return 83;

  interval.lower.limbs[6] = UINT32_C(0x00003000);
  out.count = UINT32_C(7);
  if (malbolge_guest_math_fixed256_candidates(&interval, &out) ||
      out.count != UINT32_C(7)) return 84;
  return 0;
}
"""
    _compile_and_run(source, tmp_path, "fixed256-candidates")


def test_q256_candidates_match_unique_handoff_on_retained_pairs(
    tmp_path: Path,
) -> None:
    """Keep the bounded retained corpus on the one-candidate path."""
    source = r"""#include "math_transcendental_bits.h"
#include <stdint.h>

#define SIGN UINT64_C(0x8000000000000000)
#define MASK UINT64_C(0x7fffffffffffffff)
#define EXP UINT64_C(0x7ff0000000000000)
#define MUL UINT64_C(6364136223846793005)
#define INC UINT64_C(1442695040888963407)

typedef struct Pair { uint64_t y; uint64_t x; } Pair;
static const Pair hard[] = {
  {UINT64_C(0x3fee19fa869ea9fc), UINT64_C(0x3ff197dd31b21770)},
  {UINT64_C(0x3fd75b9a8d0a0447), UINT64_C(0x3ff069f1cc6166fc)}
};
static int finite_nonzero(uint64_t bits) {
  const uint64_t magnitude = bits & MASK;
  return magnitude != UINT64_C(0) && (magnitude & EXP) != EXP;
}
static int check(uint64_t y, uint64_t x) {
  const MalbolgeGuestMathSpecialResult special =
      malbolge_guest_math_atan2_special(y, x);
  MalbolgeGuestMathAtan2Candidates candidates;
  uint64_t unique = UINT64_C(0);
  if (special.status != MALBOLGE_GUEST_MATH_SPECIAL_KERNEL_REQUIRED) return 1;
  if (!malbolge_guest_math_atan2_q256_candidates(y, x, &candidates) ||
      !malbolge_guest_math_atan2_unique_binary64(y, x, &unique) ||
      candidates.count != UINT32_C(1) || candidates.bits[0] != unique)
    return 0;
  return 1;
}
int main(void) {
  uint32_t i = UINT32_C(0);
  uint32_t sy = UINT32_C(0);
  uint32_t sx = UINT32_C(0);
  uint32_t accepted = UINT32_C(0);
  uint64_t state = UINT64_C(0x4d4944504f494e54);
  while (i < (uint32_t)(sizeof(hard) / sizeof(hard[0]))) {
    sy = UINT32_C(0);
    while (sy < UINT32_C(2)) {
      sx = UINT32_C(0);
      while (sx < UINT32_C(2)) {
        if (!check(hard[i].y | (sy ? SIGN : UINT64_C(0)),
                   hard[i].x | (sx ? SIGN : UINT64_C(0)))) return 91;
        ++sx;
      }
      ++sy;
    }
    ++i;
  }
  while (accepted < UINT32_C(4096)) {
    uint64_t y = UINT64_C(0);
    uint64_t x = UINT64_C(0);
    state = state * MUL + INC;
    y = state;
    state = state * MUL + INC;
    x = state;
    if (!finite_nonzero(y) || !finite_nonzero(x)) continue;
    if (!check(y, x)) return 92;
    ++accepted;
  }
  return 0;
}
"""
    _compile_and_run(source, tmp_path, "q256-candidates-retained")


def test_q256_candidates_reject_special_without_publication(
    tmp_path: Path,
) -> None:
    """Reject pre-resolved work without mutating candidate output."""
    source = r"""#include "math_transcendental_bits.h"
#include <stdint.h>
int main(void) {
  MalbolgeGuestMathAtan2Candidates out = {
      UINT32_C(7), {UINT64_C(0xaaaaaaaaaaaaaaaa),
                    UINT64_C(0xbbbbbbbbbbbbbbbb)}};
  if (malbolge_guest_math_atan2_q256_candidates(
          UINT64_C(0x3ff0000000000000), UINT64_C(0x3ff0000000000000),
          &out) || out.count != UINT32_C(7) ||
      out.bits[0] != UINT64_C(0xaaaaaaaaaaaaaaaa)) return 101;
  return 0;
}
"""
    _compile_and_run(source, tmp_path, "q256-candidates-special")
