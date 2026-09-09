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
#   - Retry distribution for the parallel normalized atan2 refinement scheduler.
# - Must-Not:
#   - Replace the production direct scheduler or claim a full-domain ceiling.
# - Allows:
#   - Inputs: retained hard pairs plus the deterministic 4096-pair LCG corpus.
#   - Outputs: exact normalized first-stage counts and caller scratch plans.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Production path selection acquires independent policy.
# - Merge-When:
#   - A single proven scheduler subsumes direct and normalized refinement.
# - Summary:
#   - Pins Q128/Q192 normalized retries and their 24*N scratch policy.
# - Description:
#   - Uses the same candidate cell as the direct retained atan2 evidence.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Earlier inconclusive stages remain retries rather than failures.
#

"""Deterministic retry evidence for normalized atan2 refinement."""

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


def _source() -> str:
    return r"""#include "math_transcendental_bits.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

#define SIGN UINT64_C(0x8000000000000000)
#define MAG UINT64_C(0x7fffffffffffffff)
#define EXP UINT64_C(0x7ff0000000000000)
#define LCGM UINT64_C(6364136223846793005)
#define LCGI UINT64_C(1442695040888963407)
#define ADAPTIVE_COUNT UINT32_C(4096)
#define SCRATCH_LIMBS UINT32_C(168)

typedef struct Pair { uint64_t y; uint64_t x; } Pair;
static const Pair hard[] = {
  {UINT64_C(0x3fee19fa869ea9fc), UINT64_C(0x3ff197dd31b21770)},
  {UINT64_C(0x3fe74e55173f69a0), UINT64_C(0x3ff6943b1c1ee532)},
  {UINT64_C(0x3fef179200c72129), UINT64_C(0x3ffbc1b4128cf396)},
  {UINT64_C(0x3fe97b1db9a2a48c), UINT64_C(0x3ff781ce6a6ee8ef)},
  {UINT64_C(0x3fe9519856f5242f), UINT64_C(0x3ff06c408c434f0e)},
  {UINT64_C(0x3fef7590e09e2add), UINT64_C(0x3ff629e5895f91a7)},
  {UINT64_C(0x3fe5139b1425c8a2), UINT64_C(0x3ff4fa0c073af8f1)},
  {UINT64_C(0x3fe549e587e6d4cd), UINT64_C(0x3ff11e3639f76651)},
  {UINT64_C(0x3fd75b9a8d0a0447), UINT64_C(0x3ff069f1cc6166fc)},
  {UINT64_C(0x3fdf65e15a3e11fd), UINT64_C(0x3ff31e45227a22de)},
  {UINT64_C(0x3fdef69fb021f2db), UINT64_C(0x3ff90cc971f74c07)},
  {UINT64_C(0x3fdabb28e6eef14a), UINT64_C(0x3ff544c4908ddace)},
  {UINT64_C(0x3fd94d130bf48845), UINT64_C(0x3ff2cccc5a36b6e1)},
  {UINT64_C(0x3fd667e2db48932e), UINT64_C(0x3ff41b5a664e9573)},
  {UINT64_C(0x3fdba787a32eaf18), UINT64_C(0x3ff914a595604c36)},
  {UINT64_C(0x3fd88c55ea9394d5), UINT64_C(0x3ff6abb1e310a1ac)}
};
static const Pair edges[] = {
  {UINT64_C(0x3ff0000000000000), UINT64_C(0x0000000000000001)},
  {UINT64_C(0x3ff0000000000000), UINT64_C(0x8000000000000001)},
  {UINT64_C(0x0010000000000000), UINT64_C(0x7fefffffffffffff)},
  {UINT64_C(0x8010000000000000), UINT64_C(0x7fefffffffffffff)}
};

static uint32_t special_count = UINT32_C(0);
static uint32_t kernel_count = UINT32_C(0);
static uint32_t stages[5] = {UINT32_C(0)};

static int finite_nonzero(uint64_t bits) {
  const uint64_t magnitude = bits & MAG;
  return magnitude != UINT64_C(0) && (magnitude & EXP) != EXP;
}

static int check_pair(uint64_t y, uint64_t x) {
  const MalbolgeGuestMathSpecialResult special =
      malbolge_guest_math_atan2_special(y, x);
  uint64_t candidate = UINT64_C(0);
  uint32_t scratch[SCRATCH_LIMBS];
  uint32_t stage = UINT32_C(0);
  if (special.status != MALBOLGE_GUEST_MATH_SPECIAL_KERNEL_REQUIRED) {
    ++special_count;
    return 1;
  }
  ++kernel_count;
  if (!malbolge_guest_math_atan2_unique_binary64(y, x, &candidate)) return 0;
  while (stage < UINT32_C(5)) {
    uint32_t certified = UINT32_C(0);
    const uint32_t fraction_limbs = stage + UINT32_C(2);
    const uint32_t terms = stage * UINT32_C(4) + UINT32_C(8);
    if (!malbolge_guest_math_atan2_normalized_refinement_attempt(
            y, x, candidate, fraction_limbs, terms, &certified, scratch,
            SCRATCH_LIMBS)) return 0;
    if (certified != UINT32_C(0)) {
      ++stages[stage];
      return 1;
    }
    ++stage;
  }
  return 0;
}

static int check_driver(void) {
  const uint64_t y = UINT64_C(0x3fee19fa869ea9fc);
  const uint64_t x = UINT64_C(0x3ff197dd31b21770);
  uint64_t candidate = UINT64_C(0);
  uint32_t scratch[SCRATCH_LIMBS];
  MalbolgeGuestMathAtan2RefinementProgress progress;
  static const uint32_t required[5] = {
      UINT32_C(72), UINT32_C(96), UINT32_C(120),
      UINT32_C(144), UINT32_C(168)};
  uint32_t stage = UINT32_C(0);
  if (!malbolge_guest_math_atan2_unique_binary64(y, x, &candidate)) return 0;
  while (stage < UINT32_C(5)) {
    MalbolgeGuestMathAtan2RefinementPlan plan;
    if (!malbolge_guest_math_atan2_normalized_refinement_plan(stage, &plan) ||
        plan.stage != stage || plan.fraction_limbs != stage + UINT32_C(2) ||
        plan.terms != stage * UINT32_C(4) + UINT32_C(8) ||
        plan.required_scratch_limbs != required[stage]) return 0;
    ++stage;
  }
  if (!malbolge_guest_math_atan2_normalized_refine_available(
          y, x, candidate, UINT32_C(0), scratch, UINT32_C(119), &progress) ||
      progress.certified != UINT32_C(0) || progress.plan.stage != UINT32_C(2) ||
      progress.plan.required_scratch_limbs != UINT32_C(120)) return 0;
  if (!malbolge_guest_math_atan2_normalized_refine_available(
          y, x, candidate, UINT32_C(0), scratch, UINT32_C(167), &progress) ||
      progress.certified != UINT32_C(0) || progress.plan.stage != UINT32_C(4) ||
      progress.plan.required_scratch_limbs != UINT32_C(168)) return 0;
  if (!malbolge_guest_math_atan2_normalized_refine_available(
          y, x, candidate, UINT32_C(0), scratch, UINT32_C(168), &progress) ||
      progress.certified != UINT32_C(1) || progress.plan.stage != UINT32_C(4))
    return 0;
  return 1;
}

int main(void) {
  uint32_t index = UINT32_C(0);
  uint32_t y_sign = UINT32_C(0);
  uint32_t x_sign = UINT32_C(0);
  uint32_t accepted = UINT32_C(0);
  uint64_t state = UINT64_C(0x4d4944504f494e54);
  while (index < (uint32_t)(sizeof(hard) / sizeof(hard[0]))) {
    y_sign = UINT32_C(0);
    while (y_sign < UINT32_C(2)) {
      x_sign = UINT32_C(0);
      while (x_sign < UINT32_C(2)) {
        if (!check_pair(hard[index].y | (y_sign ? SIGN : UINT64_C(0)),
                        hard[index].x | (x_sign ? SIGN : UINT64_C(0))))
          return 81;
        ++x_sign;
      }
      ++y_sign;
    }
    ++index;
  }
  index = UINT32_C(0);
  while (index < (uint32_t)(sizeof(edges) / sizeof(edges[0]))) {
    if (!check_pair(edges[index].y, edges[index].x)) return 82;
    ++index;
  }
  while (accepted < ADAPTIVE_COUNT) {
    uint64_t y = UINT64_C(0);
    uint64_t x = UINT64_C(0);
    state = state * LCGM + LCGI;
    y = state;
    state = state * LCGM + LCGI;
    x = state;
    if (!finite_nonzero(y) || !finite_nonzero(x)) continue;
    if (!check_pair(y, x)) return 83;
    ++accepted;
  }
  if (!check_driver()) return 84;
  (void)printf("%" PRIu32 " %" PRIu32, special_count, kernel_count);
  index = UINT32_C(0);
  while (index < UINT32_C(5)) {
    (void)printf(" %" PRIu32, stages[index]);
    ++index;
  }
  (void)printf("\n");
  return 0;
}
"""


def test_normalized_refinement_retry_distribution_is_deterministic(
    tmp_path: Path,
) -> None:
    """Pin normalized first-certification stages and caller scratch plans."""
    harness = tmp_path / "atan2-normalized-refinement-schedule.c"
    executable = tmp_path / "atan2-normalized-refinement-schedule"
    _ = harness.write_text(_source(), encoding="utf-8")
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
    assert tuple(map(int, executed.stdout.split())) == (
        3921,
        243,
        0,
        0,
        211,
        0,
        32,
    )
