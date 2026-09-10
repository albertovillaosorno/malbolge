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
#   - Byte/alignment evidence for caller-owned atan2 refinement scratch.
# - Must-Not:
#   - Allocate memory or make math depend on startup-bound heap state.
# - Allows:
#   - Inputs: validated refinement plans.
#   - Outputs: exact u32 byte extent, limb count, and alignment requirements.
#   - Side effects: temporary C harness compilation and execution only.
# - Split-When:
#   - Math starts owning allocation rather than reporting storage requirements.
# - Merge-When:
#   - Public atan2 owns its complete scratch allocation policy.
# - Summary:
#   - Bridges limb plans to the guest heap's u32 allocation extent safely.
# - Description:
#   - Checks byte overflow and compatibility with guest heap alignment.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Unrepresentable byte extents reject before output publication.
#

"""Atan2 refinement scratch byte/alignment requirement evidence."""

from __future__ import annotations

from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
MATH_CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
RUNTIME_CONTRACT = ROOT / "src/runtime/guest-runtime/contract"
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


def test_scratch_requirement_matches_guest_u32_extent(tmp_path: Path) -> None:
    """Translate valid limb plans to byte extents without overflow."""
    source = r"""#include "math_transcendental_bits.h"
#include "guest_runtime.h"
#include <stdint.h>
static int unchanged(const MalbolgeGuestMathAtan2ScratchRequirement *value) {
  return value->limbs == UINT32_C(11) && value->bytes == UINT32_C(22) &&
         value->alignment == UINT32_C(33);
}
int main(void) {
  static const uint32_t stages[3] = {
      UINT32_C(0), UINT32_C(1), UINT32_C(2)};
  static const uint32_t limbs[3] = {
      UINT32_C(45), UINT32_C(60), UINT32_C(75)};
  static const uint32_t bytes[3] = {
      UINT32_C(180), UINT32_C(240), UINT32_C(300)};
  MalbolgeGuestMathAtan2RefinementPlan plan;
  MalbolgeGuestMathAtan2ScratchRequirement requirement;
  uint32_t index = UINT32_C(0);
  if ((MALBOLGE_GUEST_HEAP_ALIGNMENT % UINT32_C(4)) != UINT32_C(0)) return 80;
  while (index < UINT32_C(3)) {
    if (!malbolge_guest_math_atan2_refinement_plan(stages[index], &plan) ||
        !malbolge_guest_math_atan2_refinement_scratch_requirement(
            &plan, &requirement) || requirement.limbs != limbs[index] ||
        requirement.bytes != bytes[index] ||
        requirement.alignment != UINT32_C(4)) return 81;
    ++index;
  }
  if (!malbolge_guest_math_atan2_refinement_plan(
          MALBOLGE_GUEST_MATH_ATAN2_PROVED_REFINEMENT_STAGE, &plan) ||
      plan.fraction_limbs * UINT32_C(32) !=
          MALBOLGE_GUEST_MATH_ATAN2_PROVED_FRACTION_BITS ||
      plan.terms != MALBOLGE_GUEST_MATH_ATAN2_PROVED_TERMS ||
      plan.required_scratch_limbs !=
          MALBOLGE_GUEST_MATH_ATAN2_PROVED_SCRATCH_LIMBS ||
      !malbolge_guest_math_atan2_refinement_scratch_requirement(
          &plan, &requirement) ||
      requirement.limbs != MALBOLGE_GUEST_MATH_ATAN2_PROVED_SCRATCH_LIMBS ||
      requirement.bytes != MALBOLGE_GUEST_MATH_ATAN2_PROVED_SCRATCH_BYTES ||
      requirement.alignment != UINT32_C(4)) return 82;
  if (!malbolge_guest_math_atan2_refinement_plan(
          UINT32_C(71582785), &plan) ||
      !malbolge_guest_math_atan2_refinement_scratch_requirement(
          &plan, &requirement) ||
      requirement.limbs != UINT32_C(1073741820) ||
      requirement.bytes != UINT32_C(4294967280) ||
      requirement.alignment != UINT32_C(4)) return 83;
  requirement.limbs = UINT32_C(11);
  requirement.bytes = UINT32_C(22);
  requirement.alignment = UINT32_C(33);
  if (!malbolge_guest_math_atan2_refinement_plan(
          UINT32_C(71582786), &plan) ||
      malbolge_guest_math_atan2_refinement_scratch_requirement(
          &plan, &requirement) || !unchanged(&requirement)) return 84;
  if (!malbolge_guest_math_atan2_refinement_plan(UINT32_C(2), &plan)) return 85;
  plan.terms += UINT32_C(1);
  if (malbolge_guest_math_atan2_refinement_scratch_requirement(
          &plan, &requirement) || !unchanged(&requirement)) return 86;
  return 0;
}
"""
    harness = tmp_path / "atan2-scratch-requirement.c"
    executable = tmp_path / "atan2-scratch-requirement"
    _ = harness.write_text(source, encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
            "-Wall",
            "-Wextra",
            "-Wpedantic",
            "-Werror",
            f"-I{MATH_CONTRACT}",
            f"-I{RUNTIME_CONTRACT}",
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


def test_normalized_scratch_requirement_matches_guest_u32_extent(
    tmp_path: Path,
) -> None:
    """Translate only normalized 24*N plans to byte extents atomically."""
    source = r"""#include "math_transcendental_bits.h"
#include "guest_runtime.h"
#include <stdint.h>

static int unchanged(const MalbolgeGuestMathAtan2ScratchRequirement *value) {
  return value->limbs == UINT32_C(11) && value->bytes == UINT32_C(22) &&
         value->alignment == UINT32_C(33);
}

int main(void) {
  static const uint32_t stages[5] = {
      UINT32_C(0), UINT32_C(1), UINT32_C(2), UINT32_C(3), UINT32_C(4)};
  static const uint32_t limbs[5] = {
      UINT32_C(72), UINT32_C(96), UINT32_C(120),
      UINT32_C(144), UINT32_C(168)};
  static const uint32_t bytes[5] = {
      UINT32_C(288), UINT32_C(384), UINT32_C(480),
      UINT32_C(576), UINT32_C(672)};
  MalbolgeGuestMathAtan2RefinementPlan plan;
  MalbolgeGuestMathAtan2ScratchRequirement requirement;
  uint32_t index = UINT32_C(0);
  if ((MALBOLGE_GUEST_HEAP_ALIGNMENT % UINT32_C(4)) != UINT32_C(0)) return 90;
  while (index < UINT32_C(5)) {
    if (!malbolge_guest_math_atan2_normalized_refinement_plan(
            stages[index], &plan) ||
        !malbolge_guest_math_atan2_normalized_refinement_scratch_requirement(
            &plan, &requirement) || requirement.limbs != limbs[index] ||
        requirement.bytes != bytes[index] ||
        requirement.alignment != UINT32_C(4)) return 91;
    ++index;
  }
  if (!malbolge_guest_math_atan2_normalized_refinement_plan(
          UINT32_C(44739239), &plan) ||
      plan.fraction_limbs != UINT32_C(44739241) ||
      plan.terms != UINT32_C(178956964) ||
      !malbolge_guest_math_atan2_normalized_refinement_scratch_requirement(
          &plan, &requirement) ||
      requirement.limbs != UINT32_C(1073741808) ||
      requirement.bytes != UINT32_C(4294967232) ||
      requirement.alignment != UINT32_C(4)) return 92;
  requirement.limbs = UINT32_C(11);
  requirement.bytes = UINT32_C(22);
  requirement.alignment = UINT32_C(33);
  if (!malbolge_guest_math_atan2_normalized_refinement_plan(
          UINT32_C(44739240), &plan) ||
      malbolge_guest_math_atan2_normalized_refinement_scratch_requirement(
          &plan, &requirement) || !unchanged(&requirement)) return 93;
  if (!malbolge_guest_math_atan2_refinement_plan(UINT32_C(2), &plan) ||
      malbolge_guest_math_atan2_normalized_refinement_scratch_requirement(
          &plan, &requirement) || !unchanged(&requirement)) return 94;
  if (!malbolge_guest_math_atan2_normalized_refinement_plan(
          UINT32_C(2), &plan) ||
      malbolge_guest_math_atan2_refinement_scratch_requirement(
          &plan, &requirement) || !unchanged(&requirement)) return 95;
  plan.terms += UINT32_C(1);
  if (malbolge_guest_math_atan2_normalized_refinement_scratch_requirement(
          &plan, &requirement) || !unchanged(&requirement)) return 96;
  return 0;
}
"""
    harness = tmp_path / "atan2-normalized-scratch-requirement.c"
    executable = tmp_path / "atan2-normalized-scratch-requirement"
    _ = harness.write_text(source, encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
            "-Wall",
            "-Wextra",
            "-Wpedantic",
            "-Werror",
            f"-I{MATH_CONTRACT}",
            f"-I{RUNTIME_CONTRACT}",
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
