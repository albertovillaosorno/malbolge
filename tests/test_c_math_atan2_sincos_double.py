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
#   - Directed fixed-point evidence for one signed sin/cos angle doubling.
# - Must-Not:
#   - Claim a full halving/doubling transport proof or atan2 completion.
# - Allows:
#   - Inputs: proven-sign signed sin/cos intervals at caller-selected widths.
#   - Outputs: atomic enclosures for sin(2x), cos(2x), or proven=0.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - A multi-step doubling scheduler acquires independent policy.
# - Merge-When:
#   - Full-domain midpoint transport owns the same one-step primitive.
# - Summary:
#   - Pins exact dyadic doubling across signs and variable limb widths.
# - Description:
#   - Exercises algebraic identities only; no host trigonometry is authority.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Sign-crossing inputs are inconclusive rather than guessed.
#

"""Exact fixed-point authority for one directed sin/cos angle doubling."""

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

#define MAX_LIMBS UINT32_C(128)
#define MAX_SCRATCH (UINT32_C(12) * MAX_LIMBS)

static void zero_words(uint32_t *value, uint32_t limbs) {
  uint32_t i = UINT32_C(0);
  while (i < limbs) value[i++] = UINT32_C(0);
}

static void fill_words(uint32_t *value, uint32_t limbs, uint32_t word) {
  uint32_t i = UINT32_C(0);
  while (i < limbs) value[i++] = word;
}

static void set_fraction(uint32_t *value, uint32_t limbs,
                         uint32_t fraction_limbs, uint32_t top_word) {
  zero_words(value, limbs);
  value[fraction_limbs - UINT32_C(1)] = top_word;
}

static int equal_words(const uint32_t *left, const uint32_t *right,
                       uint32_t limbs) {
  uint32_t i = UINT32_C(0);
  while (i < limbs) {
    if (left[i] != right[i]) return 0;
    ++i;
  }
  return 1;
}

static int run_case(uint32_t limbs, uint32_t sin_word,
                    uint32_t sin_negative, uint32_t cos_word,
                    uint32_t cos_negative, uint32_t expected_sin_word,
                    uint32_t expected_sin_negative,
                    uint32_t expected_cos_word,
                    uint32_t expected_cos_negative) {
  const uint32_t fraction_limbs = limbs - UINT32_C(1);
  uint32_t sin_lower[MAX_LIMBS], sin_upper[MAX_LIMBS];
  uint32_t cos_lower[MAX_LIMBS], cos_upper[MAX_LIMBS];
  uint32_t out_sin_lower[MAX_LIMBS], out_sin_upper[MAX_LIMBS];
  uint32_t out_cos_lower[MAX_LIMBS], out_cos_upper[MAX_LIMBS];
  uint32_t expected_sin[MAX_LIMBS], expected_cos[MAX_LIMBS];
  uint32_t scratch[MAX_SCRATCH];
  uint32_t sln = UINT32_C(9), sun = UINT32_C(9);
  uint32_t cln = UINT32_C(9), cun = UINT32_C(9);
  uint32_t proven = UINT32_C(9);

  set_fraction(sin_lower, limbs, fraction_limbs, sin_word);
  set_fraction(sin_upper, limbs, fraction_limbs, sin_word);
  set_fraction(cos_lower, limbs, fraction_limbs, cos_word);
  set_fraction(cos_upper, limbs, fraction_limbs, cos_word);
  set_fraction(expected_sin, limbs, fraction_limbs, expected_sin_word);
  set_fraction(expected_cos, limbs, fraction_limbs, expected_cos_word);
  if (!malbolge_guest_math_fixed_sincos_double_interval(
          sin_lower, sin_negative, sin_upper, sin_negative,
          cos_lower, cos_negative, cos_upper, cos_negative,
          limbs, fraction_limbs, out_sin_lower, &sln, out_sin_upper, &sun,
          out_cos_lower, &cln, out_cos_upper, &cun, &proven, scratch,
          UINT32_C(12) * limbs) ||
      proven != UINT32_C(1) || sln != expected_sin_negative ||
      sun != expected_sin_negative || cln != expected_cos_negative ||
      cun != expected_cos_negative ||
      !equal_words(out_sin_lower, expected_sin, limbs) ||
      !equal_words(out_sin_upper, expected_sin, limbs) ||
      !equal_words(out_cos_lower, expected_cos, limbs) ||
      !equal_words(out_cos_upper, expected_cos, limbs)) return 1;
  return 0;
}

static int run_wide_interval(uint32_t limbs) {
  const uint32_t fraction_limbs = limbs - UINT32_C(1);
  uint32_t sin_lower[MAX_LIMBS], sin_upper[MAX_LIMBS];
  uint32_t cos_lower[MAX_LIMBS], cos_upper[MAX_LIMBS];
  uint32_t out_sin_lower[MAX_LIMBS], out_sin_upper[MAX_LIMBS];
  uint32_t out_cos_lower[MAX_LIMBS], out_cos_upper[MAX_LIMBS];
  uint32_t expected_sin_lower[MAX_LIMBS], expected_sin_upper[MAX_LIMBS];
  uint32_t expected_cos_lower[MAX_LIMBS], expected_cos_upper[MAX_LIMBS];
  uint32_t scratch[MAX_SCRATCH];
  uint32_t sln = UINT32_C(9), sun = UINT32_C(9);
  uint32_t cln = UINT32_C(9), cun = UINT32_C(9);
  uint32_t proven = UINT32_C(9);

  set_fraction(sin_lower, limbs, fraction_limbs, UINT32_C(0x40000000));
  set_fraction(sin_upper, limbs, fraction_limbs, UINT32_C(0x80000000));
  set_fraction(cos_lower, limbs, fraction_limbs, UINT32_C(0x80000000));
  set_fraction(cos_upper, limbs, fraction_limbs, UINT32_C(0xc0000000));
  set_fraction(expected_sin_lower, limbs, fraction_limbs,
               UINT32_C(0x40000000));
  set_fraction(expected_sin_upper, limbs, fraction_limbs,
               UINT32_C(0xc0000000));
  zero_words(expected_cos_lower, limbs);
  set_fraction(expected_cos_upper, limbs, fraction_limbs,
               UINT32_C(0x80000000));
  if (!malbolge_guest_math_fixed_sincos_double_interval(
          sin_lower, UINT32_C(0), sin_upper, UINT32_C(0),
          cos_lower, UINT32_C(0), cos_upper, UINT32_C(0),
          limbs, fraction_limbs, out_sin_lower, &sln, out_sin_upper, &sun,
          out_cos_lower, &cln, out_cos_upper, &cun, &proven, scratch,
          UINT32_C(12) * limbs) ||
      proven != UINT32_C(1) || sln != UINT32_C(0) || sun != UINT32_C(0) ||
      cln != UINT32_C(0) || cun != UINT32_C(0) ||
      !equal_words(out_sin_lower, expected_sin_lower, limbs) ||
      !equal_words(out_sin_upper, expected_sin_upper, limbs) ||
      !equal_words(out_cos_lower, expected_cos_lower, limbs) ||
      !equal_words(out_cos_upper, expected_cos_upper, limbs)) return 1;
  return 0;
}

static int run_fail_closed(uint32_t limbs) {
  const uint32_t fraction_limbs = limbs - UINT32_C(1);
  uint32_t quarter[MAX_LIMBS], half[MAX_LIMBS], three_quarters[MAX_LIMBS];
  uint32_t output[4][MAX_LIMBS];
  uint32_t scratch[MAX_SCRATCH];
  uint32_t sln = UINT32_C(41), sun = UINT32_C(42);
  uint32_t cln = UINT32_C(43), cun = UINT32_C(44);
  uint32_t proven = UINT32_C(45);

  set_fraction(quarter, limbs, fraction_limbs, UINT32_C(0x40000000));
  set_fraction(half, limbs, fraction_limbs, UINT32_C(0x80000000));
  set_fraction(three_quarters, limbs, fraction_limbs, UINT32_C(0xc0000000));
  fill_words(&output[0][0], UINT32_C(4) * MAX_LIMBS,
             UINT32_C(0xdeadbeef));
  if (!malbolge_guest_math_fixed_sincos_double_interval(
          quarter, UINT32_C(1), quarter, UINT32_C(0),
          half, UINT32_C(0), three_quarters, UINT32_C(0),
          limbs, fraction_limbs, output[0], &sln, output[1], &sun,
          output[2], &cln, output[3], &cun, &proven, scratch,
          UINT32_C(12) * limbs) || proven != UINT32_C(0) ||
      output[0][0] != UINT32_C(0xdeadbeef) || sln != UINT32_C(41)) return 1;
  proven = UINT32_C(45);
  if (malbolge_guest_math_fixed_sincos_double_interval(
          half, UINT32_C(0), half, UINT32_C(0),
          three_quarters, UINT32_C(0), three_quarters, UINT32_C(0),
          limbs, fraction_limbs, output[0], &sln, output[1], &sun,
          output[2], &cln, output[3], &cun, &proven, scratch,
          UINT32_C(12) * limbs - UINT32_C(1)) ||
      proven != UINT32_C(45) || output[0][0] != UINT32_C(0xdeadbeef)) return 1;
  return 0;
}

int main(void) {
  const uint32_t widths[] = {UINT32_C(4), UINT32_C(8), UINT32_C(16),
                             UINT32_C(128)};
  uint32_t i = UINT32_C(0);
  while (i < (uint32_t)(sizeof(widths) / sizeof(widths[0]))) {
    const uint32_t limbs = widths[i];
    if (run_case(limbs, UINT32_C(0x80000000), UINT32_C(0),
                 UINT32_C(0xc0000000), UINT32_C(0),
                 UINT32_C(0xc0000000), UINT32_C(0),
                 UINT32_C(0x50000000), UINT32_C(0)) ||
        run_case(limbs, UINT32_C(0x80000000), UINT32_C(1),
                 UINT32_C(0xc0000000), UINT32_C(0),
                 UINT32_C(0xc0000000), UINT32_C(1),
                 UINT32_C(0x50000000), UINT32_C(0)) ||
        run_case(limbs, UINT32_C(0xc0000000), UINT32_C(0),
                 UINT32_C(0x80000000), UINT32_C(1),
                 UINT32_C(0xc0000000), UINT32_C(1),
                 UINT32_C(0x50000000), UINT32_C(1)) ||
        run_wide_interval(limbs) || run_fail_closed(limbs)) return 70;
    ++i;
  }
  return 0;
}
"""


def test_signed_sincos_double_matches_exact_dyadic_identities(
    tmp_path: Path,
) -> None:
    """Enclose one doubling exactly across signs and variable widths."""
    harness = tmp_path / "atan2-sincos-double.c"
    executable = tmp_path / "atan2-sincos-double"
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
