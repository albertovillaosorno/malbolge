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
#   - Composition of non-special sub-four binary64 input with dyadic sincos.
# - Must-Not:
#   - Implement periodic reduction or publish a rounded binary64 result.
# - Allows:
#   - Inputs: SIN/COS raw words accepted by the exact reduced-dyadic bridge.
#   - Outputs: the same proven/retry intervals as manual dyadic refinement.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - General binary64 range reduction supplies a reduced principal argument.
# - Merge-When:
#   - Public sin/cos handoff owns special, reduction, refinement, and rounding.
# - Summary:
#   - Joins raw sub-four inputs to the normalized caller-owned sincos scheduler.
# - Description:
#   - Differential C evidence compares wrapper and manual composition exactly.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Special and magnitude-at-least-four inputs remain outside this wrapper.
#

"""Raw binary64 sub-four sincos refinement composition evidence."""

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


def test_binary64_driver_matches_manual_dyadic_composition(
    tmp_path: Path,
) -> None:
    """Match manual results and preserve retry or hard-failure outputs."""
    source = r"""#include "math_transcendental_bits.h"
#include <stdint.h>

#define CAP UINT32_C(5)
#define SCR UINT32_C(100)

typedef struct Case { MalbolgeGuestMathUnaryOperation op; uint64_t bits; } Case;
static const Case cases[] = {
  {MALBOLGE_GUEST_MATH_SIN, UINT64_C(0x3fe8000000000000)},
  {MALBOLGE_GUEST_MATH_COS, UINT64_C(0xbfe8000000000000)},
  {MALBOLGE_GUEST_MATH_COS, UINT64_C(0x3e46a00000000001)},
  {MALBOLGE_GUEST_MATH_SIN, UINT64_C(0x400fffffffffffff)}
};

static void fill(uint32_t *value, uint32_t count, uint32_t word) {
  uint32_t index = UINT32_C(0);
  while (index < count) value[index++] = word;
}

static int same(const uint32_t a[4][CAP], const uint32_t as[4],
                const uint32_t b[4][CAP], const uint32_t bs[4],
                uint32_t count) {
  uint32_t row = UINT32_C(0);
  while (row < UINT32_C(4)) {
    uint32_t index = UINT32_C(0);
    if (as[row] != bs[row]) return 0;
    while (index < count) {
      if (a[row][index] != b[row][index]) return 0;
      ++index;
    }
    ++row;
  }
  return 1;
}

static int compare_case(Case item) {
  MalbolgeGuestMathDyadic dyadic;
  MalbolgeGuestMathSincosRefinementProgress manual_progress;
  MalbolgeGuestMathSincosRefinementProgress wrapper_progress;
  uint32_t manual[4][CAP], wrapper[4][CAP];
  uint32_t manual_sign[4] = {UINT32_C(0)};
  uint32_t wrapper_sign[4] = {UINT32_C(0)};
  uint32_t manual_scratch[SCR], wrapper_scratch[SCR];
  if (!malbolge_guest_math_unary_reduced_dyadic(item.op, item.bits, &dyadic) ||
      !malbolge_guest_math_dyadic_sincos_refine_available(
          &dyadic, UINT32_C(0), manual[0], &manual_sign[0], manual[1],
          &manual_sign[1], manual[2], &manual_sign[2], manual[3],
          &manual_sign[3], CAP, manual_scratch, SCR, &manual_progress) ||
      !malbolge_guest_math_unary_sincos_refine_available(
          item.op, item.bits, UINT32_C(0), wrapper[0], &wrapper_sign[0],
          wrapper[1], &wrapper_sign[1], wrapper[2], &wrapper_sign[2],
          wrapper[3], &wrapper_sign[3], CAP, wrapper_scratch, SCR,
          &wrapper_progress) || manual_progress.proven != UINT32_C(1) ||
      wrapper_progress.proven != UINT32_C(1) ||
      manual_progress.plan.stage != wrapper_progress.plan.stage ||
      manual_progress.plan.required_output_limbs !=
          wrapper_progress.plan.required_output_limbs ||
      !same(manual, manual_sign, wrapper, wrapper_sign,
            manual_progress.plan.required_output_limbs)) return 0;
  return 1;
}

static int retry_contract(void) {
  uint32_t output[4][CAP];
  uint32_t signs[4] = {UINT32_C(41), UINT32_C(42), UINT32_C(43), UINT32_C(44)};
  uint32_t scratch[SCR];
  MalbolgeGuestMathSincosRefinementProgress progress;
  fill(&output[0][0], UINT32_C(4) * CAP, UINT32_C(0xdeadbeef));
  if (!malbolge_guest_math_unary_sincos_refine_available(
          MALBOLGE_GUEST_MATH_SIN, UINT64_C(0x400fffffffffffff), UINT32_C(0),
          output[0], &signs[0], output[1], &signs[1], output[2], &signs[2],
          output[3], &signs[3], UINT32_C(4), scratch, UINT32_C(80),
          &progress) || progress.proven != UINT32_C(0) ||
      progress.plan.stage != UINT32_C(2) ||
      progress.plan.required_output_limbs != UINT32_C(5) ||
      progress.plan.required_scratch_limbs != UINT32_C(100) ||
      output[0][0] != UINT32_C(0xdeadbeef) ||
      output[3][0] != UINT32_C(0xdeadbeef) || signs[0] != UINT32_C(41) ||
      signs[3] != UINT32_C(44)) return 0;
  return 1;
}

static int special_failure_contract(void) {
  uint32_t output[4][CAP];
  uint32_t signs[4] = {UINT32_C(51), UINT32_C(52), UINT32_C(53), UINT32_C(54)};
  uint32_t scratch[SCR];
  MalbolgeGuestMathSincosRefinementProgress progress;
  fill(&output[0][0], UINT32_C(4) * CAP, UINT32_C(0xcafebabe));
  progress.proven = UINT32_C(61);
  progress.plan.stage = UINT32_C(62);
  if (malbolge_guest_math_unary_sincos_refine_available(
          MALBOLGE_GUEST_MATH_COS, UINT64_C(0x3e46a00000000000), UINT32_C(0),
          output[0], &signs[0], output[1], &signs[1], output[2], &signs[2],
          output[3], &signs[3], CAP, scratch, SCR, &progress) ||
      progress.proven != UINT32_C(61) || progress.plan.stage != UINT32_C(62) ||
      output[0][0] != UINT32_C(0xcafebabe) ||
      signs[0] != UINT32_C(51)) return 0;
  return 1;
}

int main(void) {
  uint32_t index = UINT32_C(0);
  while (index < (uint32_t)(sizeof(cases) / sizeof(cases[0]))) {
    if (!compare_case(cases[index])) return 81;
    ++index;
  }
  return retry_contract() && special_failure_contract() ? 0 : 82;
}
"""
    harness = tmp_path / "binary64-sincos-driver.c"
    executable = tmp_path / "binary64-sincos-driver"
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
