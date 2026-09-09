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
#   - Test-only compatibility evidence between atan2 scratch and bound guest
#     heap.
# - Must-Not:
#   - Make production math call allocation or claim compiler startup binds the
#     heap.
#   - Use host allocation as guest-runtime authority.
# - Allows:
#   - Inputs: an explicitly bound test arena and synthetic Q256 ambiguity.
#   - Outputs: retry-driven allocate/resize/release compatibility evidence.
#   - Side effects: one process-local guest heap arena owned by the test
#     harness.
# - Split-When:
#   - Product atan2 gains allocator-owned scratch after startup binding is
#     proven.
# - Merge-When:
#   - Public correctly-rounded atan2 owns the final scratch lifecycle.
# - Summary:
#   - Grows guest-heap scratch through the current adaptive retry sequence.
# - Description:
#   - Proves direct 180/240/300 and normalized 288..672 byte growth.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Pre-bind allocation remains NOT_INITIALIZED and production math stays
#     pure.
#

"""Guest-heap compatibility evidence for caller-owned atan2 scratch."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
MATH_CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
RUNTIME_CONTRACT = ROOT / "src/runtime/guest-runtime/contract"
MATH_SOURCE = (
    ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
)
HEAP_SOURCE = ROOT / "src/runtime/guest-runtime/domain/heap.c"
STARTUP_SOURCE = ROOT / "src/runtime/guest-runtime/domain/startup.c"
SIGN = 1 << 63
FRACTION_MASK = (1 << 52) - 1
EXPONENT_MASK = 0x7FF
HIDDEN = 1 << 52
FIXED_BITS = 256
LIMBS = 9
HARD_Y = 0x3FEE19FA869EA9FC
HARD_X = 0x3FF197DD31B21770
HARD_EXPECTED = 0x3FE6A53B6B0B8E47


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


def _positive_fraction(bits: int) -> Fraction:
    assert bits & SIGN == 0
    raw_exponent = (bits >> 52) & EXPONENT_MASK
    fraction = bits & FRACTION_MASK
    assert raw_exponent not in {0, EXPONENT_MASK}
    significand = HIDDEN | fraction
    power = raw_exponent - 1023 - 52
    if power >= 0:
        return Fraction(significand << power, 1)
    return Fraction(significand, 1 << -power)


def _fixed_integer(bits: int) -> int:
    scaled = _positive_fraction(bits) * (1 << FIXED_BITS)
    assert scaled.denominator == 1
    return scaled.numerator


def _limbs(value: int) -> str:
    return ", ".join(
        f"UINT32_C(0x{((value >> (32 * index)) & 0xFFFFFFFF):08x})"
        for index in range(LIMBS)
    )


def _source() -> str:
    lower = _fixed_integer(HARD_EXPECTED - 4096)
    upper = _fixed_integer(HARD_EXPECTED + 8192)
    return f"""#include "math_transcendental_bits.h"
#include "guest_runtime.h"
#include <stddef.h>
#include <stdint.h>

int main(void) {{
  alignas(16) uint8_t arena[1024] = {{0}};
  MalbolgeGuestMathAtan2Interval256 interval = {{
    {{{{{_limbs(lower)}}}, {{{_limbs(upper)}}}}}, UINT32_C(0)}};
  MalbolgeGuestMathAtan2HandoffProgress progress;
  MalbolgeGuestMathAtan2HandoffProgress next;
  MalbolgeGuestMathAtan2ScratchRequirement requirement;
  void *buffer = (void *)(uintptr_t)1U;
  void *resized = NULL;

  if (malbolge_guest_runtime_allocate(UINT32_C(300), &buffer) !=
          MALBOLGE_GUEST_RUNTIME_NOT_INITIALIZED ||
      buffer != NULL) return 81;
  if (malbolge_guest_runtime_bind_heap(arena, (uint32_t)sizeof(arena)) !=
      MALBOLGE_GUEST_RUNTIME_VALID) return 82;

  if (!malbolge_guest_math_atan2_refine_q256_interval_available(
          UINT64_C(0x{HARD_Y:016x}), UINT64_C(0x{HARD_X:016x}), &interval,
          UINT32_C(0), (uint32_t *)0, UINT32_C(0), &progress) ||
      progress.status != MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_RETRY ||
      !malbolge_guest_math_atan2_refinement_scratch_requirement(
          &progress.plan, &requirement) || requirement.bytes != UINT32_C(180) ||
      requirement.limbs != UINT32_C(45)) return 83;

  if (malbolge_guest_runtime_allocate(requirement.bytes, &buffer) !=
          MALBOLGE_GUEST_RUNTIME_VALID || buffer == NULL ||
      ((uintptr_t)buffer % (uintptr_t)requirement.alignment) != (uintptr_t)0U)
    return 84;
  if (!malbolge_guest_math_atan2_resume_handoff_available(
          UINT64_C(0x{HARD_Y:016x}), UINT64_C(0x{HARD_X:016x}), &progress,
          (uint32_t *)buffer, requirement.limbs, &next) ||
      next.status != MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_RETRY ||
      !malbolge_guest_math_atan2_refinement_scratch_requirement(
          &next.plan, &requirement) || requirement.bytes != UINT32_C(240) ||
      requirement.limbs != UINT32_C(60)) return 85;
  progress = next;

  if (malbolge_guest_runtime_resize(buffer, requirement.bytes, &resized) !=
          MALBOLGE_GUEST_RUNTIME_VALID || resized == NULL ||
      ((uintptr_t)resized % (uintptr_t)requirement.alignment) != (uintptr_t)0U)
    return 86;
  buffer = resized;
  if (!malbolge_guest_math_atan2_resume_handoff_available(
          UINT64_C(0x{HARD_Y:016x}), UINT64_C(0x{HARD_X:016x}), &progress,
          (uint32_t *)buffer, requirement.limbs, &next) ||
      next.status != MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_RETRY ||
      !malbolge_guest_math_atan2_refinement_scratch_requirement(
          &next.plan, &requirement) || requirement.bytes != UINT32_C(300) ||
      requirement.limbs != UINT32_C(75)) return 87;
  progress = next;

  if (malbolge_guest_runtime_resize(buffer, requirement.bytes, &resized) !=
          MALBOLGE_GUEST_RUNTIME_VALID || resized == NULL ||
      ((uintptr_t)resized % (uintptr_t)requirement.alignment) != (uintptr_t)0U)
    return 88;
  buffer = resized;
  if (!malbolge_guest_math_atan2_resume_handoff_available(
          UINT64_C(0x{HARD_Y:016x}), UINT64_C(0x{HARD_X:016x}), &progress,
          (uint32_t *)buffer, requirement.limbs, &next) ||
      next.status != MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_REFINED_RESOLVED ||
      next.bits != UINT64_C(0x{HARD_EXPECTED:016x})) return 89;

  if (malbolge_guest_runtime_release(buffer) != MALBOLGE_GUEST_RUNTIME_VALID)
    return 90;
  buffer = NULL;
  if (malbolge_guest_runtime_allocate(UINT32_C(300), &buffer) !=
          MALBOLGE_GUEST_RUNTIME_VALID || buffer == NULL) return 91;
  if (malbolge_guest_runtime_release(buffer) != MALBOLGE_GUEST_RUNTIME_VALID)
    return 92;
  return 0;
}}
"""


def test_guest_heap_can_grow_atan_refinement_scratch(tmp_path: Path) -> None:
    """Bind explicitly, grow 180/240/300-byte scratch, certify, and release."""
    harness = tmp_path / "atan2-guest-heap-scratch.c"
    executable = tmp_path / "atan2-guest-heap-scratch"
    _ = harness.write_text(_source(), encoding="utf-8")
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
            str(MATH_SOURCE),
            str(HEAP_SOURCE),
            str(STARTUP_SOURCE),
            str(harness),
            "-o",
            str(executable),
        ],
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    executed = _run([str(executable)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr


def _normalized_source() -> str:
    return f"""#include \"math_transcendental_bits.h\"
#include \"guest_runtime.h\"
#include <stddef.h>
#include <stdint.h>

static int next_requirement(
    const MalbolgeGuestMathAtan2RefinementProgress *progress,
    MalbolgeGuestMathAtan2ScratchRequirement *requirement) {{
  return malbolge_guest_math_atan2_normalized_refinement_scratch_requirement(
      &progress->plan, requirement);
}}

int main(void) {{
  alignas(16) uint8_t arena[2048] = {{0}};
  const uint64_t y = UINT64_C(0x{HARD_Y:016x});
  const uint64_t x = UINT64_C(0x{HARD_X:016x});
  uint64_t candidate = UINT64_C(0);
  MalbolgeGuestMathAtan2RefinementPlan plan;
  MalbolgeGuestMathAtan2RefinementProgress progress;
  MalbolgeGuestMathAtan2ScratchRequirement requirement;
  void *buffer = (void *)(uintptr_t)1U;
  void *resized = NULL;

  if (malbolge_guest_runtime_allocate(UINT32_C(672), &buffer) !=
          MALBOLGE_GUEST_RUNTIME_NOT_INITIALIZED ||
      buffer != NULL) return 101;
  if (malbolge_guest_runtime_bind_heap(arena, (uint32_t)sizeof(arena)) !=
      MALBOLGE_GUEST_RUNTIME_VALID) return 102;
  if (!malbolge_guest_math_atan2_unique_binary64(y, x, &candidate) ||
      candidate != UINT64_C(0x{HARD_EXPECTED:016x}) ||
      !malbolge_guest_math_atan2_normalized_refinement_plan(
          UINT32_C(0), &plan) ||
      !malbolge_guest_math_atan2_normalized_refinement_scratch_requirement(
          &plan, &requirement) || requirement.bytes != UINT32_C(288) ||
      requirement.limbs != UINT32_C(72)) return 103;
  if (malbolge_guest_runtime_allocate(requirement.bytes, &buffer) !=
          MALBOLGE_GUEST_RUNTIME_VALID || buffer == NULL) return 104;

  if (!malbolge_guest_math_atan2_normalized_refine_available(
          y, x, candidate, UINT32_C(0), (uint32_t *)buffer,
          requirement.limbs, &progress) || progress.certified != UINT32_C(0) ||
      progress.plan.stage != UINT32_C(1) || !next_requirement(
          &progress, &requirement) || requirement.bytes != UINT32_C(384) ||
      requirement.limbs != UINT32_C(96)) return 105;
  if (malbolge_guest_runtime_resize(buffer, requirement.bytes, &resized) !=
          MALBOLGE_GUEST_RUNTIME_VALID || resized == NULL) return 106;
  buffer = resized;

  if (!malbolge_guest_math_atan2_normalized_refine_available(
          y, x, candidate, progress.plan.stage, (uint32_t *)buffer,
          requirement.limbs, &progress) || progress.certified != UINT32_C(0) ||
      progress.plan.stage != UINT32_C(2) || !next_requirement(
          &progress, &requirement) || requirement.bytes != UINT32_C(480) ||
      requirement.limbs != UINT32_C(120)) return 107;
  if (malbolge_guest_runtime_resize(buffer, requirement.bytes, &resized) !=
          MALBOLGE_GUEST_RUNTIME_VALID || resized == NULL) return 108;
  buffer = resized;

  if (!malbolge_guest_math_atan2_normalized_refine_available(
          y, x, candidate, progress.plan.stage, (uint32_t *)buffer,
          requirement.limbs, &progress) || progress.certified != UINT32_C(0) ||
      progress.plan.stage != UINT32_C(3) || !next_requirement(
          &progress, &requirement) || requirement.bytes != UINT32_C(576) ||
      requirement.limbs != UINT32_C(144)) return 109;
  if (malbolge_guest_runtime_resize(buffer, requirement.bytes, &resized) !=
          MALBOLGE_GUEST_RUNTIME_VALID || resized == NULL) return 110;
  buffer = resized;

  if (!malbolge_guest_math_atan2_normalized_refine_available(
          y, x, candidate, progress.plan.stage, (uint32_t *)buffer,
          requirement.limbs, &progress) || progress.certified != UINT32_C(0) ||
      progress.plan.stage != UINT32_C(4) || !next_requirement(
          &progress, &requirement) || requirement.bytes != UINT32_C(672) ||
      requirement.limbs != UINT32_C(168)) return 111;
  if (malbolge_guest_runtime_resize(buffer, requirement.bytes, &resized) !=
          MALBOLGE_GUEST_RUNTIME_VALID || resized == NULL) return 112;
  buffer = resized;

  if (!malbolge_guest_math_atan2_normalized_refine_available(
          y, x, candidate, progress.plan.stage, (uint32_t *)buffer,
          requirement.limbs, &progress) || progress.certified != UINT32_C(1) ||
      progress.plan.stage != UINT32_C(4)) return 113;
  if (malbolge_guest_runtime_release(buffer) != MALBOLGE_GUEST_RUNTIME_VALID)
    return 114;
  buffer = NULL;
  if (malbolge_guest_runtime_allocate(UINT32_C(672), &buffer) !=
          MALBOLGE_GUEST_RUNTIME_VALID || buffer == NULL) return 115;
  if (malbolge_guest_runtime_release(buffer) != MALBOLGE_GUEST_RUNTIME_VALID)
    return 116;
  return 0;
}}
"""


def test_guest_heap_can_grow_normalized_atan_scratch(tmp_path: Path) -> None:
    """Grow 288/384/480/576/672-byte normalized scratch and certify."""
    harness = tmp_path / "atan2-normalized-guest-heap-scratch.c"
    executable = tmp_path / "atan2-normalized-guest-heap-scratch"
    _ = harness.write_text(_normalized_source(), encoding="utf-8")
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
            str(MATH_SOURCE),
            str(HEAP_SOURCE),
            str(STARTUP_SOURCE),
            str(harness),
            "-o",
            str(executable),
        ],
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    executed = _run([str(executable)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr
