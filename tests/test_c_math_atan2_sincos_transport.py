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
#   - Multi-step caller-owned transport through directed sin/cos doublings.
# - Must-Not:
#   - Claim that Lambert normalization itself proves tangent separation.
# - Allows:
#   - Inputs: proven-sign signed sin/cos intervals and doubling counts <= 56.
#   - Outputs: final interval after all steps, or proven=0 without publication.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Normalized Lambert evaluation and transport become one proof pipeline.
# - Merge-When:
#   - Full-domain midpoint separation owns the complete transport scheduler.
# - Summary:
#   - Pins atomic multi-step double-angle transport and its 56-step ceiling.
# - Description:
#   - Exercises exact dyadic identities and unresolved-after-progress behavior.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Any unresolved intermediate sign preserves all external outputs.
#

"""Exact fixed-point authority for multi-step sin/cos angle transport."""

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
#include <stdint.h>

#define LIMBS UINT32_C(8)
#define FRACTION_LIMBS UINT32_C(7)
#define SCRATCH_LIMBS (UINT32_C(16) * LIMBS)

static void zero_words(uint32_t *value) {
  uint32_t i = UINT32_C(0);
  while (i < LIMBS) value[i++] = UINT32_C(0);
}

static void fill_words(uint32_t *value, uint32_t word) {
  uint32_t i = UINT32_C(0);
  while (i < LIMBS) value[i++] = word;
}

static void set_dyadic(uint32_t *value, uint32_t numerator, uint32_t shift) {
  const uint32_t position = FRACTION_LIMBS * UINT32_C(32) - shift;
  zero_words(value);
  value[position >> UINT32_C(5)] = numerator << (position & UINT32_C(31));
}

static int same_words(const uint32_t *left, const uint32_t *right) {
  uint32_t i = UINT32_C(0);
  while (i < LIMBS) {
    if (left[i] != right[i]) return 0;
    ++i;
  }
  return 1;
}

static int run_exact_three(uint32_t sin_negative) {
  uint32_t sin_lower[LIMBS], sin_upper[LIMBS];
  uint32_t cos_lower[LIMBS], cos_upper[LIMBS];
  uint32_t out_sin_lower[LIMBS], out_sin_upper[LIMBS];
  uint32_t out_cos_lower[LIMBS], out_cos_upper[LIMBS];
  uint32_t expected_sin[LIMBS], expected_cos[LIMBS];
  uint32_t scratch[SCRATCH_LIMBS];
  uint32_t sln = UINT32_C(9), sun = UINT32_C(9);
  uint32_t cln = UINT32_C(9), cun = UINT32_C(9);
  uint32_t proven = UINT32_C(9);

  set_dyadic(sin_lower, UINT32_C(1), UINT32_C(1));
  set_dyadic(sin_upper, UINT32_C(1), UINT32_C(1));
  set_dyadic(cos_lower, UINT32_C(3), UINT32_C(2));
  set_dyadic(cos_upper, UINT32_C(3), UINT32_C(2));
  set_dyadic(expected_sin, UINT32_C(1785), UINT32_C(12));
  set_dyadic(expected_cos, UINT32_C(239), UINT32_C(16));
  if (!malbolge_guest_math_fixed_sincos_double_transport(
          sin_lower, sin_negative, sin_upper, sin_negative,
          cos_lower, UINT32_C(0), cos_upper, UINT32_C(0), LIMBS,
          FRACTION_LIMBS, UINT32_C(3), out_sin_lower, &sln, out_sin_upper,
          &sun, out_cos_lower, &cln, out_cos_upper, &cun, &proven, scratch,
          SCRATCH_LIMBS) ||
      proven != UINT32_C(1) || !same_words(out_sin_lower, expected_sin) ||
      !same_words(out_sin_upper, expected_sin) ||
      !same_words(out_cos_lower, expected_cos) ||
      !same_words(out_cos_upper, expected_cos) || cln != UINT32_C(1) ||
      cun != UINT32_C(1) || sln != (sin_negative != UINT32_C(0) ?
                                    UINT32_C(0) : UINT32_C(1)) ||
      sun != sln) return 1;
  return 0;
}

static int run_copy_zero(void) {
  uint32_t sin_value[LIMBS], cos_value[LIMBS];
  uint32_t outputs[4][LIMBS];
  uint32_t scratch[SCRATCH_LIMBS];
  uint32_t sln = UINT32_C(9), sun = UINT32_C(9);
  uint32_t cln = UINT32_C(9), cun = UINT32_C(9);
  uint32_t proven = UINT32_C(9);

  set_dyadic(sin_value, UINT32_C(5), UINT32_C(3));
  set_dyadic(cos_value, UINT32_C(7), UINT32_C(3));
  if (!malbolge_guest_math_fixed_sincos_double_transport(
          sin_value, UINT32_C(1), sin_value, UINT32_C(1),
          cos_value, UINT32_C(0), cos_value, UINT32_C(0), LIMBS,
          FRACTION_LIMBS, UINT32_C(0), outputs[0], &sln, outputs[1], &sun,
          outputs[2], &cln, outputs[3], &cun, &proven, scratch,
          SCRATCH_LIMBS) || proven != UINT32_C(1) || sln != UINT32_C(1) ||
      sun != UINT32_C(1) || cln != UINT32_C(0) || cun != UINT32_C(0) ||
      !same_words(outputs[0], sin_value) ||
      !same_words(outputs[1], sin_value) ||
      !same_words(outputs[2], cos_value) || !same_words(outputs[3], cos_value))
    return 1;
  return 0;
}

static int run_unresolved_after_progress(void) {
  uint32_t half[LIMBS], outputs[4][LIMBS];
  uint32_t scratch[SCRATCH_LIMBS];
  uint32_t sln = UINT32_C(41), sun = UINT32_C(42);
  uint32_t cln = UINT32_C(43), cun = UINT32_C(44);
  uint32_t proven = UINT32_C(45);

  set_dyadic(half, UINT32_C(1), UINT32_C(1));
  fill_words(&outputs[0][0], UINT32_C(0xdeadbeef));
  if (!malbolge_guest_math_fixed_sincos_double_transport(
          half, UINT32_C(0), half, UINT32_C(0),
          half, UINT32_C(0), half, UINT32_C(0), LIMBS,
          FRACTION_LIMBS, UINT32_C(56), outputs[0], &sln, outputs[1], &sun,
          outputs[2], &cln, outputs[3], &cun, &proven, scratch,
          SCRATCH_LIMBS) || proven != UINT32_C(0) ||
      outputs[0][0] != UINT32_C(0xdeadbeef) || sln != UINT32_C(41) ||
      sun != UINT32_C(42) || cln != UINT32_C(43) || cun != UINT32_C(44))
    return 1;
  return 0;
}

static int run_fail_closed(void) {
  uint32_t half[LIMBS], outputs[4][LIMBS];
  uint32_t scratch[SCRATCH_LIMBS];
  uint32_t sln = UINT32_C(51), sun = UINT32_C(52);
  uint32_t cln = UINT32_C(53), cun = UINT32_C(54);
  uint32_t proven = UINT32_C(55);

  set_dyadic(half, UINT32_C(1), UINT32_C(1));
  fill_words(&outputs[0][0], UINT32_C(0xcafebabe));
  if (malbolge_guest_math_fixed_sincos_double_transport(
          half, UINT32_C(0), half, UINT32_C(0),
          half, UINT32_C(0), half, UINT32_C(0), LIMBS,
          FRACTION_LIMBS, UINT32_C(57), outputs[0], &sln, outputs[1], &sun,
          outputs[2], &cln, outputs[3], &cun, &proven, scratch,
          SCRATCH_LIMBS) || proven != UINT32_C(55) ||
      outputs[0][0] != UINT32_C(0xcafebabe)) return 1;
  if (malbolge_guest_math_fixed_sincos_double_transport(
          half, UINT32_C(0), half, UINT32_C(0),
          half, UINT32_C(0), half, UINT32_C(0), LIMBS,
          FRACTION_LIMBS, UINT32_C(1), outputs[0], &sln, outputs[1], &sun,
          outputs[2], &cln, outputs[3], &cun, &proven, scratch,
          SCRATCH_LIMBS - UINT32_C(1)) || proven != UINT32_C(55) ||
      outputs[0][0] != UINT32_C(0xcafebabe)) return 1;
  return 0;
}

int main(void) {
  if (run_copy_zero() || run_exact_three(UINT32_C(0)) ||
      run_exact_three(UINT32_C(1)) || run_unresolved_after_progress() ||
      run_fail_closed()) return 70;
  return 0;
}
"""


def test_multi_step_sincos_transport_is_atomic_and_exact(
    tmp_path: Path,
) -> None:
    """Transport exact dyadics atomically across multiple doublings."""
    harness = tmp_path / "atan2-sincos-transport.c"
    executable = tmp_path / "atan2-sincos-transport"
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
