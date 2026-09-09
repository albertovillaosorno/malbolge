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
#   - Stateless refinement-plan and caller-capacity driver evidence for atan2.
# - Must-Not:
#   - Hide invalid inputs as memory retries or claim a finite stage is
#     exhaustive.
# - Allows:
#   - Inputs: valid kernel cells, start stage, and caller-owned scratch
#     capacity.
#   - Outputs: certifying plan or the next plan that needs more scratch.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Taylor divisor growth or product candidate generation gains separate
#     policy.
# - Merge-When:
#   - Complete adaptive atan2 fallback owns planning and candidate generation.
# - Summary:
#   - Grows precision and Taylor depth together without a chosen Q ceiling.
# - Description:
#   - Stages start Q64/8, then add one limb and four terms per retry.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Insufficient capacity reports the first unattempted plan, not hard
#     failure.
#

"""Stateless refinement-plan and caller-capacity driver evidence for atan2."""

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


def _compile(source: str, tmp_path: Path, stem: str) -> Path:
    harness = tmp_path / f"{stem}.c"
    executable = tmp_path / stem
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
    return executable


def test_refinement_plan_grows_both_dimensions_and_checks_limit(
    tmp_path: Path,
) -> None:
    """Pin early plans and the current u32 Taylor-divisor planning boundary."""
    source = r"""#include "math_transcendental_bits.h"
#include <stdint.h>
int main(void) {
  MalbolgeGuestMathAtan2RefinementPlan plan;
  MalbolgeGuestMathAtan2RefinementPlan sentinel = {
      UINT32_C(99), UINT32_C(98), UINT32_C(97), UINT32_C(96)};
  const uint32_t expected[4][4] = {
      {UINT32_C(0), UINT32_C(2), UINT32_C(8), UINT32_C(45)},
      {UINT32_C(1), UINT32_C(3), UINT32_C(12), UINT32_C(60)},
      {UINT32_C(2), UINT32_C(4), UINT32_C(16), UINT32_C(75)},
      {UINT32_C(3), UINT32_C(5), UINT32_C(20), UINT32_C(90)}};
  uint32_t index = UINT32_C(0);
  while (index < UINT32_C(4)) {
    if (!malbolge_guest_math_atan2_refinement_plan(index, &plan) ||
        plan.stage != expected[index][0] ||
        plan.fraction_limbs != expected[index][1] ||
        plan.terms != expected[index][2] ||
        plan.required_scratch_limbs != expected[index][3]) return 81;
    ++index;
  }
  if (!malbolge_guest_math_atan2_refinement_plan(UINT32_C(8189), &plan) ||
      plan.fraction_limbs != UINT32_C(8191) ||
      plan.terms != UINT32_C(32764) ||
      plan.required_scratch_limbs != UINT32_C(122880)) return 82;
  plan = sentinel;
  if (malbolge_guest_math_atan2_refinement_plan(UINT32_C(8190), &plan) ||
      plan.stage != sentinel.stage ||
      plan.fraction_limbs != sentinel.fraction_limbs ||
      plan.terms != sentinel.terms ||
      plan.required_scratch_limbs != sentinel.required_scratch_limbs) return 83;
  return 0;
}
"""
    executable = _compile(source, tmp_path, "refinement-plan")
    executed = _run([str(executable)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr


def test_refinement_driver_reports_retry_capacity_and_certification(
    tmp_path: Path,
) -> None:
    """Require a hard seed to progress Q64/8 through Q128/16 before certify."""
    source = r"""#include "math_transcendental_bits.h"
#include <stdint.h>
int main(void) {
  const uint64_t y = UINT64_C(0x3fee19fa869ea9fc);
  const uint64_t x = UINT64_C(0x3ff197dd31b21770);
  uint64_t candidate = UINT64_C(0);
  uint32_t scratch[75];
  MalbolgeGuestMathAtan2RefinementProgress progress;
  if (!malbolge_guest_math_atan2_unique_binary64(y, x, &candidate)) return 91;
  if (!malbolge_guest_math_atan2_refine_available(
          y, x, candidate, UINT32_C(0), scratch, UINT32_C(44), &progress) ||
      progress.certified != UINT32_C(0) || progress.plan.stage != UINT32_C(0) ||
      progress.plan.required_scratch_limbs != UINT32_C(45)) return 92;
  if (!malbolge_guest_math_atan2_refine_available(
          y, x, candidate, UINT32_C(0), scratch, UINT32_C(45), &progress) ||
      progress.certified != UINT32_C(0) || progress.plan.stage != UINT32_C(1) ||
      progress.plan.required_scratch_limbs != UINT32_C(60)) return 93;
  if (!malbolge_guest_math_atan2_refine_available(
          y, x, candidate, UINT32_C(0), scratch, UINT32_C(60), &progress) ||
      progress.certified != UINT32_C(0) || progress.plan.stage != UINT32_C(2) ||
      progress.plan.required_scratch_limbs != UINT32_C(75)) return 94;
  if (!malbolge_guest_math_atan2_refine_available(
          y, x, candidate, UINT32_C(0), scratch, UINT32_C(75), &progress) ||
      progress.certified != UINT32_C(1) || progress.plan.stage != UINT32_C(2) ||
      progress.plan.fraction_limbs != UINT32_C(4) ||
      progress.plan.terms != UINT32_C(16)) return 95;
  if (!malbolge_guest_math_atan2_refine_available(
          y, x, candidate + UINT64_C(1), UINT32_C(0), scratch, UINT32_C(75),
          &progress) || progress.certified != UINT32_C(0) ||
      progress.plan.stage != UINT32_C(3) ||
      progress.plan.required_scratch_limbs != UINT32_C(90)) return 96;
  return 0;
}
"""
    executable = _compile(source, tmp_path, "refinement-driver")
    executed = _run([str(executable)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr


def test_refinement_driver_validates_before_capacity_reporting(
    tmp_path: Path,
) -> None:
    """Keep special failures nonpublishing even with too little scratch."""
    source = r"""#include "math_transcendental_bits.h"
#include <stdint.h>
int main(void) {
  uint32_t scratch[1] = {UINT32_C(0)};
  const MalbolgeGuestMathAtan2RefinementProgress sentinel = {
      UINT32_C(9), {UINT32_C(8), UINT32_C(7), UINT32_C(6), UINT32_C(5)}};
  MalbolgeGuestMathAtan2RefinementProgress progress = sentinel;
  if (malbolge_guest_math_atan2_refine_available(
          UINT64_C(0x3ff0000000000000), UINT64_C(0x3ff0000000000000),
          UINT64_C(0x3fe921fb54442d18), UINT32_C(0), scratch, UINT32_C(1),
          &progress)) return 101;
  if (progress.certified != sentinel.certified ||
      progress.plan.stage != sentinel.plan.stage ||
      progress.plan.fraction_limbs != sentinel.plan.fraction_limbs ||
      progress.plan.terms != sentinel.plan.terms ||
      progress.plan.required_scratch_limbs !=
          sentinel.plan.required_scratch_limbs) return 102;
  return 0;
}
"""
    executable = _compile(source, tmp_path, "refinement-driver-invalid")
    executed = _run([str(executable)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr
