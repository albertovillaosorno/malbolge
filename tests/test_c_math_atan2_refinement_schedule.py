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
#   - Bounded precision/depth retry evidence for atan2 refinement scheduling.
# - Must-Not:
#   - Treat corpus completion as a full-domain precision or termination bound.
# - Allows:
#   - Inputs: signed hard cases, edge cases, and a fixed 4096-pair binary64 LCG.
#   - Outputs: exact certification counts at selected precision/depth requests.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Product retry scheduling gains its own executable policy.
# - Merge-When:
#   - Complete adaptive fallback subsumes bounded scheduler evidence.
# - Summary:
#   - Pins that both fixed-point precision and Taylor depth can cause retries.
# - Description:
#   - Q128/16 closes this corpus; lower precision or depth deliberately does
#     not.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Counts are coverage evidence only and never a global correctness bound.
#

"""Bounded retry-distribution evidence for adaptive atan2 scheduling."""

from __future__ import annotations

from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
EXPECTED_COUNTS = (997, 3167, 3112, 3135, 21, 26, 2107, 3167)


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


def _harness_source() -> str:
    return r"""#include "math_transcendental_bits.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

#define SIGN_BIT UINT64_C(0x8000000000000000)
#define MAGNITUDE_MASK UINT64_C(0x7fffffffffffffff)
#define EXPONENT_MASK UINT64_C(0x7ff0000000000000)
#define LCG_MULTIPLIER UINT64_C(6364136223846793005)
#define LCG_INCREMENT UINT64_C(1442695040888963407)
#define ADAPTIVE_COUNT UINT32_C(4096)

typedef struct Pair { uint64_t y; uint64_t x; } Pair;
static const Pair base_hard[] = {
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

static uint32_t counts[8];

static int finite_nonzero(uint64_t bits) {
  const uint64_t magnitude = bits & MAGNITUDE_MASK;
  return magnitude != UINT64_C(0) &&
         (magnitude & EXPONENT_MASK) != EXPONENT_MASK;
}

static int attempt(uint64_t y, uint64_t x, uint64_t candidate,
                   uint32_t fraction_limbs, uint32_t terms,
                   uint32_t *certified) {
  uint32_t scratch[75];
  return malbolge_guest_math_atan2_refinement_attempt(
      y, x, candidate, fraction_limbs, terms, certified, scratch, UINT32_C(75));
}

static int check_pair(uint64_t y, uint64_t x) {
  const MalbolgeGuestMathSpecialResult special =
      malbolge_guest_math_atan2_special(y, x);
  uint64_t candidate = UINT64_C(0);
  uint32_t certified = UINT32_C(0);
  if (special.status != MALBOLGE_GUEST_MATH_SPECIAL_KERNEL_REQUIRED) {
    ++counts[0];
    return 1;
  }
  ++counts[1];
  if (!malbolge_guest_math_atan2_unique_binary64(y, x, &candidate)) return 0;
  if (!attempt(y, x, candidate, UINT32_C(2), UINT32_C(16), &certified))
    return 0;
  counts[2] += certified;
  if (!attempt(y, x, candidate, UINT32_C(3), UINT32_C(16), &certified))
    return 0;
  counts[3] += certified;
  if (!attempt(y, x, candidate, UINT32_C(4), UINT32_C(4), &certified))
    return 0;
  counts[4] += certified;
  if (!attempt(y, x, candidate, UINT32_C(4), UINT32_C(8), &certified))
    return 0;
  counts[5] += certified;
  if (!attempt(y, x, candidate, UINT32_C(4), UINT32_C(12), &certified))
    return 0;
  counts[6] += certified;
  if (!attempt(y, x, candidate, UINT32_C(4), UINT32_C(16), &certified))
    return 0;
  counts[7] += certified;
  return 1;
}

int main(void) {
  uint32_t index = UINT32_C(0);
  uint32_t y_sign = UINT32_C(0);
  uint32_t x_sign = UINT32_C(0);
  uint32_t accepted = UINT32_C(0);
  uint64_t state = UINT64_C(0x4d4944504f494e54);

  while (index < (uint32_t)(sizeof(base_hard) / sizeof(base_hard[0]))) {
    y_sign = UINT32_C(0);
    while (y_sign < UINT32_C(2)) {
      x_sign = UINT32_C(0);
      while (x_sign < UINT32_C(2)) {
        if (!check_pair(base_hard[index].y | (y_sign ? SIGN_BIT : UINT64_C(0)),
                        base_hard[index].x | (x_sign ? SIGN_BIT : UINT64_C(0))))
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
    state = state * LCG_MULTIPLIER + LCG_INCREMENT;
    y = state;
    state = state * LCG_MULTIPLIER + LCG_INCREMENT;
    x = state;
    if (!finite_nonzero(y) || !finite_nonzero(x)) continue;
    if (!check_pair(y, x)) return 83;
    ++accepted;
  }
  index = UINT32_C(0);
  while (index < UINT32_C(8)) {
    (void)printf("%" PRIu32 "%c", counts[index],
                 index + UINT32_C(1) == UINT32_C(8) ? '\n' : ' ');
    ++index;
  }
  return 0;
}
"""


def test_refinement_retry_distribution_is_deterministic(
    tmp_path: Path,
) -> None:
    """Pin retry counts while keeping the full-domain obligation open."""
    harness = tmp_path / "refinement-schedule.c"
    executable = tmp_path / "refinement-schedule"
    _ = harness.write_text(_harness_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
            "-O2",
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
    assert tuple(map(int, executed.stdout.split())) == EXPECTED_COUNTS
