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
#   - Exact positive-ratio versus directed tangent cross-product evidence.
# - Must-Not:
#   - Divide fixed values, call host trig, or treat an overlapping interval as
#     proof.
# - Allows:
#   - Inputs: positive binary64 kernel ratios and nonnegative sin/cos limb
#     intervals.
#   - Outputs: -1, 0, or +1 for below, unresolved, or above tangent bounds.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Midpoint candidate orchestration gains branch/quadrant policy.
# - Merge-When:
#   - Complete adaptive tangent refinement owns cross-product comparison
#     directly.
# - Summary:
#   - Proves ratio/tangent ordering without fixed/fixed division.
# - Description:
#   - Exact u64 scalar products retain exponent shifts through plus/minus 53.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Zero lower trig bounds return unresolved; malformed requests reject.
#

"""Exact cross-product tangent comparison evidence for adaptive atan2."""

from __future__ import annotations

from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
LIMB_COUNT = 4
EXTENDED_LIMBS = LIMB_COUNT + 4
SCRATCH_LIMBS = EXTENDED_LIMBS * 2

CASES = (
    (0x3CA0000000000000, 0x3FF0000000000000, -1),  # 2^-53
    (0x3FD0000000000000, 0x3FF0000000000000, -1),  # 1/4
    (0x3FE0000000000000, 0x3FF0000000000000, 0),  # 1/2
    (0x3FF0000000000000, 0x3FF0000000000000, 1),  # 1
    (0x4000000000000000, 0x3FF0000000000000, 1),  # 2
    (0x3FF0000000000000, 0x3CA0000000000000, 1),  # 2^53
)


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


def _case_block(position: int, y_bits: int, x_bits: int) -> str:
    return f"""  {{
    MalbolgeGuestMathAtan2KernelInput ratio;
    int32_t comparison = INT32_C(99);
    if (!malbolge_guest_math_atan2_kernel_input(
            UINT64_C(0x{y_bits:016x}), UINT64_C(0x{x_bits:016x}), &ratio))
      return 81;
    if (!malbolge_guest_math_positive_ratio_tangent_compare(
            &ratio, sin_value, sin_value, cos_value, cos_value,
            UINT32_C({LIMB_COUNT}), &comparison, scratch,
            UINT32_C({SCRATCH_LIMBS}))) return 82;
    (void)printf("{position} %" PRId32 "\\n", comparison);
  }}"""


def _harness_source() -> str:
    body = "\n".join(
        _case_block(position, y_bits, x_bits)
        for position, (y_bits, x_bits, _) in enumerate(CASES)
    )
    return f"""#include "math_transcendental_bits.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

int main(void) {{
  uint32_t sin_value[{LIMB_COUNT}] = {{
      UINT32_C(0), UINT32_C(0), UINT32_C(0x80000000), UINT32_C(0)}};
  uint32_t cos_value[{LIMB_COUNT}] = {{
      UINT32_C(0), UINT32_C(0), UINT32_C(0), UINT32_C(1)}};
  uint32_t scratch[{SCRATCH_LIMBS}];
{body}
  return 0;
}}
"""


def test_positive_ratio_tangent_cross_products_cover_shift_extremes(
    tmp_path: Path,
) -> None:
    """Resolve all orderings through exponent shifts plus/minus 53."""
    harness = tmp_path / "tangent-compare.c"
    executable = tmp_path / "tangent-compare"
    _ = harness.write_text(_harness_source(), encoding="utf-8")
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
    executed = _run([str(executable)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr
    rows = tuple(line.split() for line in executed.stdout.splitlines())
    assert len(rows) == len(CASES)
    for row, (_, _, expected) in zip(rows, CASES, strict=True):
        assert int(row[1]) == expected


def _failure_harness_source() -> str:
    return f"""#include "math_transcendental_bits.h"
#include <stdint.h>

int main(void) {{
  MalbolgeGuestMathAtan2KernelInput ratio;
  uint32_t zero[{LIMB_COUNT}] = {{UINT32_C(0)}};
  uint32_t half[{LIMB_COUNT}] = {{
      UINT32_C(0), UINT32_C(0), UINT32_C(0x80000000), UINT32_C(0)}};
  uint32_t one[{LIMB_COUNT}] = {{
      UINT32_C(0), UINT32_C(0), UINT32_C(0), UINT32_C(1)}};
  uint32_t scratch[{SCRATCH_LIMBS}];
  int32_t comparison = INT32_C(77);

  if (!malbolge_guest_math_atan2_kernel_input(
          UINT64_C(0x3ff0000000000000), UINT64_C(0x3ff0000000000000),
          &ratio)) return 91;
  if (!malbolge_guest_math_positive_ratio_tangent_compare(
          &ratio, zero, half, one, one, UINT32_C({LIMB_COUNT}), &comparison,
          scratch, UINT32_C({SCRATCH_LIMBS})) || comparison != INT32_C(0))
    return 92;
  comparison = INT32_C(77);
  if (malbolge_guest_math_positive_ratio_tangent_compare(
          &ratio, one, half, one, one, UINT32_C({LIMB_COUNT}), &comparison,
          scratch, UINT32_C({SCRATCH_LIMBS})) || comparison != INT32_C(77))
    return 93;
  if (malbolge_guest_math_positive_ratio_tangent_compare(
          &ratio, half, half, one, one, UINT32_C({LIMB_COUNT}), &comparison,
          scratch, UINT32_C({SCRATCH_LIMBS - 1})) || comparison != INT32_C(77))
    return 94;
  ratio.y_negative = UINT32_C(1);
  if (malbolge_guest_math_positive_ratio_tangent_compare(
          &ratio, half, half, one, one, UINT32_C({LIMB_COUNT}), &comparison,
          scratch, UINT32_C({SCRATCH_LIMBS})) || comparison != INT32_C(77))
    return 95;
  return 0;
}}
"""


def test_positive_ratio_tangent_compare_invalid_inputs_fail_closed(
    tmp_path: Path,
) -> None:
    """Keep zero trig bounds unresolved and malformed requests nonpublishing."""
    harness = tmp_path / "tangent-compare-failure.c"
    executable = tmp_path / "tangent-compare-failure"
    _ = harness.write_text(_failure_harness_source(), encoding="utf-8")
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
    executed = _run([str(executable)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr
