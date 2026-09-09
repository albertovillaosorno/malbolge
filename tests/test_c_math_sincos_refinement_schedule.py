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
#   - Caller-owned scheduling and storage requirements for reduced dyadic
#     sincos.
# - Must-Not:
#   - Claim binary64 range reduction, final rounding, or public sin/cos support.
# - Allows:
#   - Inputs: reduced nonzero dyadics admitted by the normalized sincos
#     boundary.
#   - Outputs: open-ended refinement plans, storage extents, and proven/retry.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Binary64 sin/cos range reduction owns a separate argument-reduction
#     policy.
# - Merge-When:
#   - Public correctly-rounded sin/cos owns the complete refinement lifecycle.
# - Summary:
#   - Makes normalized dyadic sincos independently schedulable outside atan2.
# - Description:
#   - Exercises stage progression, storage overflow, retry, and atomic failure.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Q128/16 remains bounded evidence, never a full-domain precision ceiling.
#

"""Dyadic sincos refinement scheduling and caller-owned storage evidence."""

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


def test_dyadic_sincos_schedule_and_storage_are_fail_closed(
    tmp_path: Path,
) -> None:
    """Drive easy and deep dyadics while preserving retry output atomically."""
    source = r"""#include "math_transcendental_bits.h"
#include "guest_runtime.h"
#include <stdint.h>

#define OUT_CAP UINT32_C(7)
#define SCR_CAP UINT32_C(140)

static void fill(uint32_t *value, uint32_t count, uint32_t word) {
  uint32_t index = UINT32_C(0);
  while (index < count) value[index++] = word;
}

static int unchanged(const uint32_t out[4][OUT_CAP], const uint32_t signs[4]) {
  return out[0][0] == UINT32_C(0xdeadbeef) &&
         out[1][0] == UINT32_C(0xdeadbeef) &&
         out[2][0] == UINT32_C(0xdeadbeef) &&
         out[3][0] == UINT32_C(0xdeadbeef) &&
         signs[0] == UINT32_C(41) && signs[1] == UINT32_C(42) &&
         signs[2] == UINT32_C(43) && signs[3] == UINT32_C(44);
}

static void reset(uint32_t out[4][OUT_CAP], uint32_t signs[4]) {
  fill(&out[0][0], UINT32_C(4) * OUT_CAP, UINT32_C(0xdeadbeef));
  signs[0] = UINT32_C(41);
  signs[1] = UINT32_C(42);
  signs[2] = UINT32_C(43);
  signs[3] = UINT32_C(44);
}

static int check_plans(void) {
  static const uint32_t output_limbs[5] = {
      UINT32_C(3), UINT32_C(4), UINT32_C(5), UINT32_C(6), UINT32_C(7)};
  static const uint32_t scratch_limbs[5] = {
      UINT32_C(60), UINT32_C(80), UINT32_C(100),
      UINT32_C(120), UINT32_C(140)};
  MalbolgeGuestMathSincosRefinementPlan plan;
  MalbolgeGuestMathSincosStorageRequirement storage;
  uint32_t stage = UINT32_C(0);
  if ((MALBOLGE_GUEST_HEAP_ALIGNMENT % UINT32_C(4)) != UINT32_C(0)) return 0;
  while (stage < UINT32_C(5)) {
    if (!malbolge_guest_math_dyadic_sincos_refinement_plan(stage, &plan) ||
        plan.stage != stage || plan.fraction_limbs != stage + UINT32_C(2) ||
        plan.terms != stage * UINT32_C(4) + UINT32_C(8) ||
        plan.required_output_limbs != output_limbs[stage] ||
        plan.required_scratch_limbs != scratch_limbs[stage] ||
        !malbolge_guest_math_dyadic_sincos_refinement_storage_requirement(
            &plan, &storage) || storage.output_limbs != output_limbs[stage] ||
        storage.output_bytes_each != output_limbs[stage] * UINT32_C(4) ||
        storage.scratch_limbs != scratch_limbs[stage] ||
        storage.scratch_bytes != scratch_limbs[stage] * UINT32_C(4) ||
        storage.alignment != UINT32_C(4)) return 0;
    ++stage;
  }
  if (!malbolge_guest_math_dyadic_sincos_refinement_plan(
          UINT32_C(53687088), &plan) ||
      !malbolge_guest_math_dyadic_sincos_refinement_storage_requirement(
          &plan, &storage) ||
      storage.output_limbs != UINT32_C(53687091) ||
      storage.output_bytes_each != UINT32_C(214748364) ||
      storage.scratch_limbs != UINT32_C(1073741820) ||
      storage.scratch_bytes != UINT32_C(4294967280)) return 0;
  storage.output_limbs = UINT32_C(11);
  storage.output_bytes_each = UINT32_C(22);
  storage.scratch_limbs = UINT32_C(33);
  storage.scratch_bytes = UINT32_C(44);
  storage.alignment = UINT32_C(55);
  if (!malbolge_guest_math_dyadic_sincos_refinement_plan(
          UINT32_C(53687089), &plan) ||
      malbolge_guest_math_dyadic_sincos_refinement_storage_requirement(
          &plan, &storage) || storage.output_limbs != UINT32_C(11) ||
      storage.scratch_bytes != UINT32_C(44)) return 0;
  if (!malbolge_guest_math_dyadic_sincos_refinement_plan(
          UINT32_C(2), &plan)) return 0;
  plan.terms += UINT32_C(1);
  if (malbolge_guest_math_dyadic_sincos_refinement_storage_requirement(
          &plan, &storage) || storage.output_limbs != UINT32_C(11)) return 0;
  return 1;
}

static int check_driver(void) {
  const MalbolgeGuestMathDyadic easy = {
      UINT64_C(3), UINT32_C(2), UINT32_C(0)};
  const MalbolgeGuestMathDyadic near_four = {
      UINT64_C(0x003fffffffffffff), UINT32_C(52), UINT32_C(0)};
  const MalbolgeGuestMathDyadic deep_negative = {
      UINT64_C(0x0020000000000001), UINT32_C(107), UINT32_C(1)};
  const MalbolgeGuestMathDyadic malformed = {
      UINT64_C(2), UINT32_C(107), UINT32_C(0)};
  uint32_t out[4][OUT_CAP];
  uint32_t signs[4];
  uint32_t scratch[SCR_CAP];
  MalbolgeGuestMathSincosRefinementProgress progress;

  reset(out, signs);
  if (!malbolge_guest_math_dyadic_sincos_refine_available(
          &easy, UINT32_C(0), out[0], &signs[0], out[1], &signs[1], out[2],
          &signs[2], out[3], &signs[3], OUT_CAP, scratch, SCR_CAP,
          &progress) || progress.proven != UINT32_C(1) ||
      progress.plan.stage != UINT32_C(0) || unchanged(out, signs)) return 0;

  reset(out, signs);
  if (!malbolge_guest_math_dyadic_sincos_refine_available(
          &near_four, UINT32_C(0), out[0], &signs[0], out[1], &signs[1],
          out[2], &signs[2], out[3], &signs[3], UINT32_C(4), scratch,
          UINT32_C(80), &progress) || progress.proven != UINT32_C(0) ||
      progress.plan.stage != UINT32_C(2) ||
      progress.plan.required_output_limbs != UINT32_C(5) ||
      progress.plan.required_scratch_limbs != UINT32_C(100) ||
      !unchanged(out, signs)) return 0;

  reset(out, signs);
  if (!malbolge_guest_math_dyadic_sincos_refine_available(
          &near_four, UINT32_C(0), out[0], &signs[0], out[1], &signs[1],
          out[2], &signs[2], out[3], &signs[3], UINT32_C(5), scratch,
          UINT32_C(100), &progress) || progress.proven != UINT32_C(1) ||
      progress.plan.stage != UINT32_C(2) || unchanged(out, signs)) return 0;

  reset(out, signs);
  if (!malbolge_guest_math_dyadic_sincos_refine_available(
          &deep_negative, UINT32_C(0), out[0], &signs[0], out[1], &signs[1],
          out[2], &signs[2], out[3], &signs[3], UINT32_C(5), scratch,
          UINT32_C(100), &progress) || progress.proven != UINT32_C(1) ||
      progress.plan.stage != UINT32_C(2) || signs[0] != UINT32_C(1) ||
      signs[1] != UINT32_C(1) || signs[2] != UINT32_C(0) ||
      signs[3] != UINT32_C(0)) return 0;

  reset(out, signs);
  progress.proven = UINT32_C(77);
  progress.plan.stage = UINT32_C(78);
  if (malbolge_guest_math_dyadic_sincos_refine_available(
          &malformed, UINT32_C(0), out[0], &signs[0], out[1], &signs[1],
          out[2], &signs[2], out[3], &signs[3], OUT_CAP, scratch, SCR_CAP,
          &progress) || progress.proven != UINT32_C(77) ||
      progress.plan.stage != UINT32_C(78) || !unchanged(out, signs)) return 0;
  return 1;
}

int main(void) {
  return check_plans() && check_driver() ? 0 : 80;
}
"""
    harness = tmp_path / "dyadic-sincos-refinement-schedule.c"
    executable = tmp_path / "dyadic-sincos-refinement-schedule"
    _ = harness.write_text(source, encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
            "-O2",
            "-ffreestanding",
            "-fno-builtin",
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
