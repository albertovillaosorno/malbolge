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
#   - Ordered candidate-range extraction and adaptive binary-search evidence.
# - Must-Not:
#   - Require Q256 to span only one or two binary64 rounding cells.
# - Allows:
#   - Inputs: Q256 intervals or same-sign finite atan2 candidate ranges below 4.
#   - Outputs: narrowed retry ranges or one certified binary64 cell.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Product handoff consumes adaptive range search directly.
# - Merge-When:
#   - Complete atan2 fallback owns candidate range and certification together.
# - Summary:
#   - Binary-search arbitrary same-sign candidate spans with directed midpoints.
# - Description:
#   - Skewed positive and negative ranges prove coarse-stage narrowing.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Invalid ranges and contradictory search states fail without publication.
#

"""Ordered candidate-range and adaptive binary-search evidence for atan2."""

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


def test_fixed256_range_covers_spans_rejected_by_two_candidates(
    tmp_path: Path,
) -> None:
    """Represent a three-cell Q256 span without enumerating its middle cell."""
    source = r"""#include "math_transcendental_bits.h"
#include <stdint.h>
static void clear_interval(MalbolgeGuestMathFixed256Interval *interval) {
  uint32_t index = UINT32_C(0);
  while (index < MALBOLGE_GUEST_MATH_FIXED_256_LIMBS) {
    interval->lower.limbs[index] = UINT32_C(0);
    interval->upper.limbs[index] = UINT32_C(0);
    ++index;
  }
}
int main(void) {
  MalbolgeGuestMathFixed256Interval interval;
  MalbolgeGuestMathAtan2CandidateRange range = {
      UINT64_C(0xaaaaaaaaaaaaaaaa), UINT64_C(0xbbbbbbbbbbbbbbbb)};
  MalbolgeGuestMathAtan2Candidates candidates = {
      UINT32_C(7), {UINT64_C(0), UINT64_C(0)}};
  clear_interval(&interval);
  interval.lower.limbs[8] = UINT32_C(1);
  interval.upper.limbs[6] = UINT32_C(0x00002000);
  interval.upper.limbs[8] = UINT32_C(1);
  if (!malbolge_guest_math_fixed256_candidate_range(&interval, &range) ||
      range.lower_bits != UINT64_C(0x3ff0000000000000) ||
      range.upper_bits != UINT64_C(0x3ff0000000000002)) return 81;
  if (malbolge_guest_math_fixed256_candidates(&interval, &candidates) ||
      candidates.count != UINT32_C(7)) return 82;
  return 0;
}
"""
    _compile_and_run(source, tmp_path, "fixed256-candidate-range")


def test_range_search_narrows_and_certifies_broad_signed_ranges(
    tmp_path: Path,
) -> None:
    """Shrink 12289-cell signed ranges and certify the hard cell at Q128."""
    source = r"""#include "math_transcendental_bits.h"
#include <stdint.h>

#define SIGN UINT64_C(0x8000000000000000)

static int run(uint64_t y, uint64_t x, uint32_t negative) {
  MalbolgeGuestMathAtan2CandidateRange range;
  MalbolgeGuestMathAtan2RangeProgress progress;
  uint32_t scratch[75];
  uint64_t correct = UINT64_C(0);
  uint64_t remaining_span = UINT64_C(0);
  if (!malbolge_guest_math_atan2_unique_binary64(y, x, &correct)) return 0;
  if (negative == UINT32_C(0)) {
    range.lower_bits = correct - UINT64_C(4096);
    range.upper_bits = correct + UINT64_C(8192);
  } else {
    range.lower_bits = correct + UINT64_C(8192);
    range.upper_bits = correct - UINT64_C(4096);
  }
  if (!malbolge_guest_math_atan2_refine_range_available(
          y, x, &range, UINT32_C(0), scratch, UINT32_C(45), &progress) ||
      progress.certified != UINT32_C(0) ||
      progress.plan.stage != UINT32_C(1)) return 0;
  remaining_span = negative == UINT32_C(0)
                       ? progress.remaining.upper_bits -
                             progress.remaining.lower_bits
                       : progress.remaining.lower_bits -
                             progress.remaining.upper_bits;
  if (remaining_span > UINT64_C(4)) return 0;
  if (!malbolge_guest_math_atan2_refine_range_available(
          y, x, &range, UINT32_C(0), scratch, UINT32_C(75), &progress) ||
      progress.certified != UINT32_C(1) || progress.bits != correct ||
      progress.plan.stage != UINT32_C(2) ||
      progress.remaining.lower_bits != correct ||
      progress.remaining.upper_bits != correct) return 0;
  return 1;
}

int main(void) {
  if (!run(UINT64_C(0x3fee19fa869ea9fc),
           UINT64_C(0x3ff197dd31b21770), UINT32_C(0))) return 91;
  if (!run(UINT64_C(0xbfee19fa869ea9fc),
           UINT64_C(0x3ff197dd31b21770), UINT32_C(1))) return 92;
  return 0;
}
"""
    _compile_and_run(source, tmp_path, "candidate-range-search")


def test_q256_range_wrapper_matches_current_hard_result(tmp_path: Path) -> None:
    """Compose Q256 endpoint range extraction with binary-search refinement."""
    source = r"""#include "math_transcendental_bits.h"
#include <stdint.h>
int main(void) {
  const uint64_t y = UINT64_C(0x3fee19fa869ea9fc);
  const uint64_t x = UINT64_C(0x3ff197dd31b21770);
  MalbolgeGuestMathAtan2CandidateRange range;
  MalbolgeGuestMathAtan2RangeProgress progress;
  uint32_t scratch[75];
  uint64_t expected = UINT64_C(0);
  if (!malbolge_guest_math_atan2_unique_binary64(y, x, &expected) ||
      !malbolge_guest_math_atan2_q256_candidate_range(y, x, &range) ||
      range.lower_bits != expected || range.upper_bits != expected ||
      !malbolge_guest_math_atan2_q256_refine_range_available(
          y, x, UINT32_C(0), scratch, UINT32_C(75), &progress) ||
      progress.certified != UINT32_C(1) || progress.bits != expected)
    return 101;
  return 0;
}
"""
    _compile_and_run(source, tmp_path, "q256-candidate-range")


def test_range_search_rejects_invalid_order_without_publication(
    tmp_path: Path,
) -> None:
    """Reject mixed-sign or reversed ranges without mutating progress."""
    source = r"""#include "math_transcendental_bits.h"
#include <stdint.h>
int main(void) {
  const uint64_t y = UINT64_C(0x3fee19fa869ea9fc);
  const uint64_t x = UINT64_C(0x3ff197dd31b21770);
  MalbolgeGuestMathAtan2CandidateRange range = {
      UINT64_C(0x3fe0000000000001), UINT64_C(0x3fe0000000000000)};
  MalbolgeGuestMathAtan2RangeProgress progress;
  uint32_t scratch[75];
  progress.certified = UINT32_C(7);
  progress.bits = UINT64_C(0xaaaaaaaaaaaaaaaa);
  if (malbolge_guest_math_atan2_refine_range_available(
          y, x, &range, UINT32_C(0), scratch, UINT32_C(75), &progress) ||
      progress.certified != UINT32_C(7) ||
      progress.bits != UINT64_C(0xaaaaaaaaaaaaaaaa)) return 111;
  range.lower_bits = UINT64_C(0x3fe0000000000000);
  range.upper_bits = UINT64_C(0xbfe0000000000000);
  if (malbolge_guest_math_atan2_refine_range_available(
          y, x, &range, UINT32_C(0), scratch, UINT32_C(75), &progress) ||
      progress.certified != UINT32_C(7)) return 112;
  return 0;
}
"""
    _compile_and_run(source, tmp_path, "candidate-range-invalid")
