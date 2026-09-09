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
#   - Exact dyadic size evidence for Lambert tangent-GCF arguments.
# - Must-Not:
#   - Claim a finite irrationality-measure constant or atan2 completion.
# - Allows:
#   - Inputs: reduced dyadics and exact binary64 candidate-cell boundaries.
#   - Outputs: numerator bits, denominator shift, and a strict power-of-two
#     ceiling for u^2/v.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - An explicit GCF growth/error proof consumes this scale directly.
# - Merge-When:
#   - Full-domain atan2 resource proof owns the same Lambert argument geometry.
# - Summary:
#   - Proves u^2/v < 2^56 for candidate-cell dyadics below four.
# - Description:
#   - Checks exact integer geometry without evaluating tangent or host trig.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - The ceiling is structural evidence, not a separation constant.
#

"""Exact structural bounds for Lambert tangent-GCF dyadic arguments."""

from __future__ import annotations

from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
MAX_SCALE_EXPONENT = 56


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

static int emit(const MalbolgeGuestMathDyadic *value) {
  MalbolgeGuestMathLambertArgumentBounds bounds;
  if (!malbolge_guest_math_dyadic_lambert_argument_bounds(value, &bounds))
    return 0;
  (void)printf("%" PRIu32 " %" PRIu32 " %" PRId32 " %" PRIu32
               " %" PRIu32 " %" PRId32 "\n",
               bounds.numerator_bits, bounds.denominator_shift,
               bounds.square_over_denominator_pow2_exponent_upper,
               bounds.normalizing_halvings,
               bounds.normalized_denominator_shift,
               bounds.normalized_scale_pow2_exponent_upper);
  return 1;
}

int main(void) {
  const MalbolgeGuestMathDyadic near_four = {
      UINT64_C(0x003fffffffffffff), UINT32_C(52), UINT32_C(0)};
  const MalbolgeGuestMathDyadic deep = {
      UINT64_C(0x0020000000000001), UINT32_C(107), UINT32_C(1)};
  MalbolgeGuestMathDyadic invalid_even = {
      UINT64_C(6), UINT32_C(4), UINT32_C(0)};
  MalbolgeGuestMathDyadic invalid_wide = {
      UINT64_C(0x0040000000000001), UINT32_C(52), UINT32_C(0)};
  MalbolgeGuestMathDyadic invalid_shift = {
      UINT64_C(3), UINT32_C(108), UINT32_C(0)};
  MalbolgeGuestMathLambertArgumentBounds sentinel = {
      UINT32_C(91), UINT32_C(92), INT32_C(93), UINT32_C(94),
      UINT32_C(95), INT32_C(96)};

  if (!emit(&near_four) || !emit(&deep)) return 81;
  if (malbolge_guest_math_dyadic_lambert_argument_bounds(
          &invalid_even, &sentinel) ||
      sentinel.numerator_bits != UINT32_C(91) ||
      malbolge_guest_math_dyadic_lambert_argument_bounds(
          &invalid_wide, &sentinel) ||
      sentinel.denominator_shift != UINT32_C(92) ||
      malbolge_guest_math_dyadic_lambert_argument_bounds(
          &invalid_shift, &sentinel) ||
      sentinel.square_over_denominator_pow2_exponent_upper != INT32_C(93) ||
      sentinel.normalizing_halvings != UINT32_C(94) ||
      sentinel.normalized_denominator_shift != UINT32_C(95) ||
      sentinel.normalized_scale_pow2_exponent_upper != INT32_C(96))
    return 82;
  return 0;
}
"""


def test_lambert_argument_scale_matches_exact_bit_geometry(
    tmp_path: Path,
) -> None:
    """Pin the tight structural exponent and deep-denominator reduction."""
    harness = tmp_path / "atan2-lambert-argument.c"
    executable = tmp_path / "atan2-lambert-argument"
    _ = harness.write_text(_source(), encoding="utf-8")
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
    rows = [
        tuple(map(int, line.split())) for line in executed.stdout.splitlines()
    ]
    assert rows == [
        (54, 52, MAX_SCALE_EXPONENT, 56, 108, 0),
        (54, 107, 1, 1, 108, 0),
    ]
