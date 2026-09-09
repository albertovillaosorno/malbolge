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
#   - Multi-candidate adaptive atan2 certification evidence.
# - Must-Not:
#   - Invent nonadjacent candidate sets or treat one corpus as exhaustive.
# - Allows:
#   - Inputs: one/two ordered adjacent binary64 cells for kernel-required work.
#   - Outputs: exactly one certified cell or the next retry plan.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Candidate production no longer depends on Q256 interval endpoints.
# - Merge-When:
#   - Complete atan2 fallback owns generation and certification together.
# - Summary:
#   - Retry all plausible cells and publish only one uniquely certified result.
# - Description:
#   - Positive and negative hard seeds pin ordered adjacent-cell handling.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Malformed candidate lists fail without mutating progress output.
#

"""Multi-candidate adaptive atan2 certification evidence."""

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


def test_candidate_driver_selects_one_adjacent_hard_cell(
    tmp_path: Path,
) -> None:
    """Certify exactly one cell from positive and negative adjacent pairs."""
    source = r"""#include "math_transcendental_bits.h"
#include <stdint.h>

#define SIGN UINT64_C(0x8000000000000000)

static int positive_case(void) {
  const uint64_t y = UINT64_C(0x3fee19fa869ea9fc);
  const uint64_t x = UINT64_C(0x3ff197dd31b21770);
  MalbolgeGuestMathAtan2Candidates candidates;
  MalbolgeGuestMathAtan2CandidateProgress progress;
  uint32_t scratch[90];
  uint64_t correct = UINT64_C(0);
  if (!malbolge_guest_math_atan2_unique_binary64(y, x, &correct)) return 0;
  candidates.count = UINT32_C(2);
  candidates.bits[0] = correct;
  candidates.bits[1] = correct + UINT64_C(1);
  if (!malbolge_guest_math_atan2_refine_candidates_available(
          y, x, &candidates, UINT32_C(0), scratch, UINT32_C(60), &progress) ||
      progress.certified != UINT32_C(0) || progress.plan.stage != UINT32_C(2) ||
      progress.plan.required_scratch_limbs != UINT32_C(75)) return 0;
  if (!malbolge_guest_math_atan2_refine_candidates_available(
          y, x, &candidates, UINT32_C(0), scratch, UINT32_C(75), &progress) ||
      progress.certified != UINT32_C(1) || progress.bits != correct ||
      progress.plan.stage != UINT32_C(2)) return 0;
  return 1;
}

static int negative_case(void) {
  const uint64_t y = UINT64_C(0xbfee19fa869ea9fc);
  const uint64_t x = UINT64_C(0x3ff197dd31b21770);
  MalbolgeGuestMathAtan2Candidates candidates;
  MalbolgeGuestMathAtan2CandidateProgress progress;
  uint32_t scratch[75];
  uint64_t correct = UINT64_C(0);
  if (!malbolge_guest_math_atan2_unique_binary64(y, x, &correct) ||
      (correct & SIGN) == UINT64_C(0)) return 0;
  candidates.count = UINT32_C(2);
  candidates.bits[0] = correct + UINT64_C(1);
  candidates.bits[1] = correct;
  if (!malbolge_guest_math_atan2_refine_candidates_available(
          y, x, &candidates, UINT32_C(0), scratch, UINT32_C(75), &progress) ||
      progress.certified != UINT32_C(1) || progress.bits != correct ||
      progress.plan.stage != UINT32_C(2)) return 0;
  return 1;
}

int main(void) {
  return positive_case() && negative_case() ? 0 : 81;
}
"""
    _compile_and_run(source, tmp_path, "candidate-driver-adjacent")


def test_q256_candidate_wrapper_certifies_retained_hard_seed(
    tmp_path: Path,
) -> None:
    """Compose Q256 candidate extraction with the adaptive scheduler."""
    source = r"""#include "math_transcendental_bits.h"
#include <stdint.h>
int main(void) {
  const uint64_t y = UINT64_C(0x3fee19fa869ea9fc);
  const uint64_t x = UINT64_C(0x3ff197dd31b21770);
  MalbolgeGuestMathAtan2CandidateProgress progress;
  uint32_t scratch[75];
  uint64_t expected = UINT64_C(0);
  if (!malbolge_guest_math_atan2_unique_binary64(y, x, &expected) ||
      !malbolge_guest_math_atan2_q256_refine_available(
          y, x, UINT32_C(0), scratch, UINT32_C(75), &progress) ||
      progress.certified != UINT32_C(1) || progress.bits != expected ||
      progress.plan.stage != UINT32_C(2)) return 91;
  return 0;
}
"""
    _compile_and_run(source, tmp_path, "candidate-driver-q256")


def test_candidate_driver_rejects_malformed_list_without_publication(
    tmp_path: Path,
) -> None:
    """Reject duplicate/nonordered two-cell input atomically."""
    source = r"""#include "math_transcendental_bits.h"
#include <stdint.h>
int main(void) {
  const uint64_t y = UINT64_C(0x3fee19fa869ea9fc);
  const uint64_t x = UINT64_C(0x3ff197dd31b21770);
  MalbolgeGuestMathAtan2Candidates candidates = {
      UINT32_C(2), {UINT64_C(0x3fe0000000000000),
                    UINT64_C(0x3fe0000000000000)}};
  MalbolgeGuestMathAtan2CandidateProgress progress = {
      UINT32_C(7), UINT64_C(0xaaaaaaaaaaaaaaaa),
      {UINT32_C(9), UINT32_C(9), UINT32_C(9), UINT32_C(9)}};
  uint32_t scratch[75];
  if (malbolge_guest_math_atan2_refine_candidates_available(
          y, x, &candidates, UINT32_C(0), scratch, UINT32_C(75), &progress) ||
      progress.certified != UINT32_C(7) ||
      progress.bits != UINT64_C(0xaaaaaaaaaaaaaaaa) ||
      progress.plan.stage != UINT32_C(9)) return 101;
  return 0;
}
"""
    _compile_and_run(source, tmp_path, "candidate-driver-malformed")
