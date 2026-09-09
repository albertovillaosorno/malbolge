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
#   - Evidence for the caller-owned atan2 fast/adaptive handoff integration.
# - Must-Not:
#   - Claim a natural Q256-ambiguous atan2 input from a synthetic interval.
#   - Require scratch before special or fixed-Q uniqueness has been exhausted.
# - Allows:
#   - Inputs: raw binary64 pairs and injected enclosing Q256 intervals.
#   - Outputs: fast resolved, adaptive retry, or refined resolved progress.
#   - Side effects: temporary C harness compilation and execution only.
# - Split-When:
#   - Public libc exposure or allocator-owned retry gains a separate contract.
# - Merge-When:
#   - Correctly-rounded public atan2 subsumes the internal handoff evidence.
# - Summary:
#   - Joins the fixed-Q ladder and caller-owned candidate-range refinement.
# - Description:
#   - Exercises no-scratch fast resolution and synthetic ambiguous refinement.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Retry reports exact required scratch and never invents a result.
#

"""Caller-owned atan2 fixed-Q to adaptive-range handoff evidence."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
SIGN = 1 << 63
FRACTION_MASK = (1 << 52) - 1
EXPONENT_MASK = 0x7FF
HIDDEN = 1 << 52
FIXED_BITS = 256
LIMBS = 9
HARD_Y = 0x3FEE19FA869EA9FC
HARD_X = 0x3FF197DD31B21770
HARD_EXPECTED = 0x3FE6A53B6B0B8E47
LCG_MULTIPLIER = 6364136223846793005
LCG_INCREMENT = 1442695040888963407
LCG_SEED = 0x48414E444F464635
ALL_BITS = (1 << 64) - 1
PAIR_COUNT = 512


def _run(command: list[str], cwd: Path) -> sp.CompletedProcess[str]:
    return sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        shell=False,
        text=True,
        timeout=60,
    )


def _finite_nonzero(bits: int) -> bool:
    magnitude = bits & ~SIGN
    exponent = (magnitude >> 52) & EXPONENT_MASK
    return magnitude != 0 and exponent != EXPONENT_MASK


def _pairs() -> tuple[tuple[int, int], ...]:
    state = LCG_SEED
    pairs: list[tuple[int, int]] = []
    while len(pairs) < PAIR_COUNT:
        state = (state * LCG_MULTIPLIER + LCG_INCREMENT) & ALL_BITS
        y_bits = state
        state = (state * LCG_MULTIPLIER + LCG_INCREMENT) & ALL_BITS
        x_bits = state
        if _finite_nonzero(y_bits) and _finite_nonzero(x_bits):
            pairs.append((y_bits, x_bits))
    return tuple(pairs)


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


def _compile(tmp_path: Path, source: str, name: str) -> Path:
    harness = tmp_path / f"{name}.c"
    executable = tmp_path / name
    _ = harness.write_text(source, encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
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
    return executable


def _fast_source() -> str:
    rows = ",\n".join(
        f"  {{UINT64_C(0x{y:016x}), UINT64_C(0x{x:016x})}}"
        for y, x in _pairs()
    )
    return f"""#include "math_transcendental_bits.h"
#include <stdint.h>
typedef struct Pair {{ uint64_t y, x; }} Pair;
static const Pair pairs[] = {{
{rows}
}};
int main(void) {{
  MalbolgeGuestMathAtan2HandoffProgress out;
  uint64_t expected = UINT64_C(0);
  uint32_t index = UINT32_C(0);
  if (!malbolge_guest_math_atan2_handoff_available(
          UINT64_C(0), UINT64_C(0x3ff0000000000000), UINT32_C(0),
          (uint32_t *)0, UINT32_C(0), &out) ||
      out.status != MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_FAST_RESOLVED ||
      out.bits != UINT64_C(0) || out.plan.required_scratch_limbs != UINT32_C(0))
    return 81;
  while (index < (uint32_t)(sizeof(pairs) / sizeof(pairs[0]))) {{
    if (!malbolge_guest_math_atan2_unique_binary64(
            pairs[index].y, pairs[index].x, &expected) ||
        !malbolge_guest_math_atan2_handoff_available(
            pairs[index].y, pairs[index].x, UINT32_C(0), (uint32_t *)0,
            UINT32_C(0), &out) ||
        out.status != MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_FAST_RESOLVED ||
        out.bits != expected || out.remaining.lower_bits != expected ||
        out.remaining.upper_bits != expected ||
        out.plan.required_scratch_limbs != UINT32_C(0))
      return 82;
    ++index;
  }}
  return index == UINT32_C({PAIR_COUNT}) ? 0 : 83;
}}
"""


def test_handoff_fast_path_requires_no_scratch(tmp_path: Path) -> None:
    """Resolve special and retained fixed-Q work before scratch is required."""
    executable = _compile(tmp_path, _fast_source(), "atan2-handoff-fast")
    executed = _run([str(executable)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr


def _adaptive_source() -> str:
    lower_bits = HARD_EXPECTED - 4096
    upper_bits = HARD_EXPECTED + 8192
    lower = _fixed_integer(lower_bits)
    upper = _fixed_integer(upper_bits)
    return f"""#include "math_transcendental_bits.h"
#include <stdint.h>
static int unchanged(const MalbolgeGuestMathAtan2HandoffProgress *out) {{
  return out->status == (MalbolgeGuestMathAtan2HandoffStatus)9 &&
         out->bits == UINT64_C(0xaaaaaaaaaaaaaaaa);
}}
int main(void) {{
  MalbolgeGuestMathAtan2Interval256 interval = {{
    {{{{{_limbs(lower)}}}, {{{_limbs(upper)}}}}}, UINT32_C(0)}};
  MalbolgeGuestMathAtan2HandoffProgress out;
  uint32_t scratch[75];
  out.status = (MalbolgeGuestMathAtan2HandoffStatus)9;
  out.bits = UINT64_C(0xaaaaaaaaaaaaaaaa);
  if (!malbolge_guest_math_atan2_refine_q256_interval_available(
          UINT64_C(0x{HARD_Y:016x}), UINT64_C(0x{HARD_X:016x}), &interval,
          UINT32_C(0), (uint32_t *)0, UINT32_C(0), &out) ||
      out.status != MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_RETRY ||
      out.plan.stage != UINT32_C(0) ||
      out.plan.required_scratch_limbs != UINT32_C(45) ||
      out.remaining.lower_bits != UINT64_C(0x{lower_bits:016x}) ||
      out.remaining.upper_bits != UINT64_C(0x{upper_bits:016x}))
    return 91;
  if (!malbolge_guest_math_atan2_refine_q256_interval_available(
          UINT64_C(0x{HARD_Y:016x}), UINT64_C(0x{HARD_X:016x}), &interval,
          UINT32_C(0), scratch, UINT32_C(60), &out) ||
      out.status != MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_RETRY ||
      out.plan.stage != UINT32_C(2) ||
      out.plan.required_scratch_limbs != UINT32_C(75) ||
      out.remaining.lower_bits > UINT64_C(0x{HARD_EXPECTED:016x}) ||
      out.remaining.upper_bits < UINT64_C(0x{HARD_EXPECTED:016x}))
    return 92;
  if (!malbolge_guest_math_atan2_refine_q256_interval_available(
          UINT64_C(0x{HARD_Y:016x}), UINT64_C(0x{HARD_X:016x}), &interval,
          UINT32_C(0), scratch, UINT32_C(75), &out) ||
      out.status != MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_REFINED_RESOLVED ||
      out.bits != UINT64_C(0x{HARD_EXPECTED:016x}) ||
      out.remaining.lower_bits != UINT64_C(0x{HARD_EXPECTED:016x}) ||
      out.remaining.upper_bits != UINT64_C(0x{HARD_EXPECTED:016x}) ||
      out.plan.stage != UINT32_C(2))
    return 93;
  interval.negative = UINT32_C(1);
  out.status = (MalbolgeGuestMathAtan2HandoffStatus)9;
  out.bits = UINT64_C(0xaaaaaaaaaaaaaaaa);
  if (malbolge_guest_math_atan2_refine_q256_interval_available(
          UINT64_C(0x{HARD_Y:016x}), UINT64_C(0x{HARD_X:016x}), &interval,
          UINT32_C(0), scratch, UINT32_C(75), &out) || !unchanged(&out))
    return 94;
  return 0;
}}
"""


def test_handoff_refines_injected_q256_range(tmp_path: Path) -> None:
    """Retry, narrow, and certify an injected Q256-ambiguous hard interval."""
    executable = _compile(tmp_path, _adaptive_source(), "atan2-handoff-adapt")
    executed = _run([str(executable)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr


def _resume_source() -> str:
    lower_bits = HARD_EXPECTED - 4096
    upper_bits = HARD_EXPECTED + 8192
    lower = _fixed_integer(lower_bits)
    upper = _fixed_integer(upper_bits)
    return f"""#include "math_transcendental_bits.h"
#include <stdint.h>
static int sentinel(const MalbolgeGuestMathAtan2HandoffProgress *out) {{
  return out->status == (MalbolgeGuestMathAtan2HandoffStatus)9 &&
         out->bits == UINT64_C(0xcccccccccccccccc);
}}
int main(void) {{
  MalbolgeGuestMathAtan2Interval256 interval = {{
    {{{{{_limbs(lower)}}}, {{{_limbs(upper)}}}}}, UINT32_C(0)}};
  MalbolgeGuestMathAtan2HandoffProgress first;
  MalbolgeGuestMathAtan2HandoffProgress second;
  MalbolgeGuestMathAtan2HandoffProgress final;
  MalbolgeGuestMathAtan2HandoffProgress bad;
  uint32_t scratch[75];
  if (!malbolge_guest_math_atan2_refine_q256_interval_available(
          UINT64_C(0x{HARD_Y:016x}), UINT64_C(0x{HARD_X:016x}), &interval,
          UINT32_C(0), (uint32_t *)0, UINT32_C(0), &first) ||
      first.status != MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_RETRY ||
      first.y_bits != UINT64_C(0x{HARD_Y:016x}) ||
      first.x_bits != UINT64_C(0x{HARD_X:016x}) ||
      first.plan.stage != UINT32_C(0))
    return 101;
  if (!malbolge_guest_math_atan2_resume_handoff_available(
          UINT64_C(0x{HARD_Y:016x}), UINT64_C(0x{HARD_X:016x}), &first,
          scratch, UINT32_C(60), &second) ||
      second.status != MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_RETRY ||
      second.plan.stage != UINT32_C(2) ||
      second.plan.required_scratch_limbs != UINT32_C(75) ||
      second.remaining.lower_bits > UINT64_C(0x{HARD_EXPECTED:016x}) ||
      second.remaining.upper_bits < UINT64_C(0x{HARD_EXPECTED:016x}))
    return 102;
  if (!malbolge_guest_math_atan2_resume_handoff_available(
          UINT64_C(0x{HARD_Y:016x}), UINT64_C(0x{HARD_X:016x}), &second,
          scratch, UINT32_C(75), &final) ||
      final.status != MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_REFINED_RESOLVED ||
      final.bits != UINT64_C(0x{HARD_EXPECTED:016x}) ||
      final.remaining.lower_bits != UINT64_C(0x{HARD_EXPECTED:016x}) ||
      final.remaining.upper_bits != UINT64_C(0x{HARD_EXPECTED:016x}) ||
      final.plan.stage != UINT32_C(2))
    return 103;
  bad.status = (MalbolgeGuestMathAtan2HandoffStatus)9;
  bad.bits = UINT64_C(0xcccccccccccccccc);
  first.plan.terms += UINT32_C(1);
  if (malbolge_guest_math_atan2_resume_handoff_available(
          UINT64_C(0x{HARD_Y:016x}), UINT64_C(0x{HARD_X:016x}), &first,
          scratch, UINT32_C(75), &bad) || !sentinel(&bad))
    return 104;
  first.plan.terms -= UINT32_C(1);
  first.y_bits ^= UINT64_C(1);
  if (malbolge_guest_math_atan2_resume_handoff_available(
          UINT64_C(0x{HARD_Y:016x}), UINT64_C(0x{HARD_X:016x}), &first,
          scratch, UINT32_C(75), &bad) || !sentinel(&bad))
    return 105;
  return 0;
}}
"""


def test_handoff_resume_preserves_narrowed_range(tmp_path: Path) -> None:
    """Resume the saved range and first unattempted plan with more scratch."""
    executable = _compile(tmp_path, _resume_source(), "atan2-handoff-resume")
    executed = _run([str(executable)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr
