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
#   - Fixed periodic Q256-to-Q512 handoff and scratch-driven retry evidence.
# - Must-Not:
#   - Claim the injected wide Q256 interval is a naturally occurring hard case.
# - Allows:
#   - Inputs: finite periodic binary64 words and a staged Q256 interval.
#   - Outputs: retry, Q256 resolution, Q512 resolution, or Q512 unresolved
#     state.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - A precision layer beyond Q512 gains its own retry planner.
# - Merge-When:
#   - A general periodic refinement scheduler subsumes fixed Q256/Q512 policy.
# - Summary:
#   - Pins 90-limb Q256 and 170-limb Q512 lifecycle boundaries.
# - Description:
#   - A synthetic ambiguous Q256 interval exercises the Q512 transition.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Q512 unresolved is valid nonpublication, not a hard error.
#

"""Periodic Q256-to-Q512 handoff lifecycle evidence."""

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
    return """#include "math_transcendental_bits.h"
#include <stdint.h>

static int sentinel(const MalbolgeGuestMathSincosPeriodicProgress *value) {
  return value->status == (MalbolgeGuestMathSincosPeriodicStatus)9 &&
         value->bits == UINT64_C(0xaaaaaaaaaaaaaaaa);
}

int main(void) {
  const uint64_t input = UINT64_C(0x4010000000000000);
  uint32_t scratch[MALBOLGE_GUEST_MATH_PERIODIC_Q512_SCRATCH_LIMBS];
  MalbolgeGuestMathSincosPeriodicProgress progress;
  MalbolgeGuestMathSincosInterval256 injected = {0};
  uint64_t expected = UINT64_C(0);

  if (!malbolge_guest_math_sincos_range_unique_binary64_q512(
          MALBOLGE_GUEST_MATH_SIN, input, &expected, scratch,
          MALBOLGE_GUEST_MATH_PERIODIC_Q512_SCRATCH_LIMBS)) return 80;
  if (!malbolge_guest_math_sincos_periodic_handoff_available(
          MALBOLGE_GUEST_MATH_SIN, input, (uint32_t *)0, UINT32_C(0),
          &progress) ||
      progress.status != MALBOLGE_GUEST_MATH_SINCOS_PERIODIC_RETRY ||
      progress.input_bits != input || progress.bits != UINT64_C(0) ||
      progress.required_scratch_limbs !=
          MALBOLGE_GUEST_MATH_PERIODIC_Q256_SCRATCH_LIMBS) return 81;
  if (!malbolge_guest_math_sincos_periodic_handoff_available(
          MALBOLGE_GUEST_MATH_SIN, input, scratch,
          MALBOLGE_GUEST_MATH_PERIODIC_Q256_SCRATCH_LIMBS, &progress) ||
      progress.status != MALBOLGE_GUEST_MATH_SINCOS_PERIODIC_Q256_RESOLVED ||
      progress.bits != expected) return 82;

  injected.sin.upper.limbs[8] = UINT32_C(1);
  if (!malbolge_guest_math_sincos_refine_q256_interval512_available(
          MALBOLGE_GUEST_MATH_SIN, input, &injected, scratch,
          MALBOLGE_GUEST_MATH_PERIODIC_Q512_SCRATCH_LIMBS - UINT32_C(1),
          &progress) ||
      progress.status != MALBOLGE_GUEST_MATH_SINCOS_PERIODIC_RETRY ||
      progress.required_scratch_limbs !=
          MALBOLGE_GUEST_MATH_PERIODIC_Q512_SCRATCH_LIMBS) return 83;
  if (!malbolge_guest_math_sincos_refine_q256_interval512_available(
          MALBOLGE_GUEST_MATH_SIN, input, &injected, scratch,
          MALBOLGE_GUEST_MATH_PERIODIC_Q512_SCRATCH_LIMBS, &progress) ||
      progress.status != MALBOLGE_GUEST_MATH_SINCOS_PERIODIC_Q512_RESOLVED ||
      progress.bits != expected || progress.input_bits != input) return 84;

  progress.status = (MalbolgeGuestMathSincosPeriodicStatus)9;
  progress.bits = UINT64_C(0xaaaaaaaaaaaaaaaa);
  injected.sin.lower_negative = UINT32_C(2);
  if (malbolge_guest_math_sincos_refine_q256_interval512_available(
          MALBOLGE_GUEST_MATH_SIN, input, &injected, scratch,
          MALBOLGE_GUEST_MATH_PERIODIC_Q512_SCRATCH_LIMBS, &progress) ||
      !sentinel(&progress)) return 85;
  return 0;
}
"""


def test_periodic_handoff_retries_q256_then_resolves_q512(
    tmp_path: Path,
) -> None:
    """Use a declared synthetic Q256 ambiguity to exercise Q512 resolution."""
    harness = tmp_path / "periodic-handoff.c"
    binary = tmp_path / "periodic-handoff"
    _ = harness.write_text(_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG), "-std=c23", "-O2", "-ffreestanding", "-fno-builtin",
            "-Wall", "-Wextra", "-Wpedantic", "-Werror", f"-I{CONTRACT}",
            str(SOURCE), str(harness), "-o", str(binary),
        ],
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    executed = _run([str(binary)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr
