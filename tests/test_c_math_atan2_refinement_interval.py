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
#   - Variable-width directed interval arithmetic evidence for atan2 refinement.
# - Must-Not:
#   - Allocate memory, use host floating arithmetic, or trust fixed-Q oracles.
# - Allows:
#   - Inputs: nonnegative fixed-point endpoint limbs and caller-owned scratch.
#   - Outputs: exact enclosing endpoint limbs or nonpublishing rejection.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - A Taylor sin/cos evaluator gains independently testable orchestration.
# - Merge-When:
#   - Complete adaptive tangent refinement subsumes these interval primitives.
# - Summary:
#   - Proves directed add/subtract/product/division over caller-owned limbs.
# - Description:
#   - Both endpoints publish only after the complete interval operation
#     succeeds.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Malformed intervals, overflow, or short scratch remain fail closed.
#

"""Directed variable-width interval arithmetic evidence for adaptive atan2."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
UINT32_MAX = (1 << 32) - 1


@dataclass(frozen=True)
class IntervalCase:
    """One exact nonnegative fixed-point interval fixture."""

    limb_count: int
    left_lower: int
    left_upper: int
    right_lower: int
    right_upper: int
    divisor: int


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


def _pattern_integer(limb_count: int, seed: int) -> int:
    state = seed
    limbs: list[int] = []
    for _ in range(limb_count):
        state = (state * 6364136223846793005 + 1442695040888963407) & (
            (1 << 64) - 1
        )
        limbs.append((state >> 16) & UINT32_MAX)
    limbs[-1] &= 1
    return sum(limb << (32 * index) for index, limb in enumerate(limbs))


def _cases() -> tuple[IntervalCase, ...]:
    widths = (4, 8, 16, 128)
    divisors = (3, 239, 0x80000001, UINT32_MAX)
    rows: list[IntervalCase] = []
    for width, divisor in zip(widths, divisors, strict=True):
        left = _pattern_integer(width, 0x494E544C0000 + width)
        right = _pattern_integer(width, 0x494E54520000 + width)
        rows.append(
            IntervalCase(width, left, left + 17, right, right + 31, divisor)
        )
    return tuple(rows)


def _c_limbs(integer: int, count: int) -> str:
    values = tuple(
        (integer >> (32 * index)) & UINT32_MAX for index in range(count)
    )
    return ", ".join(f"UINT32_C(0x{value:08x})" for value in values)


def _case_block(case: IntervalCase) -> str:
    count = case.limb_count
    sub_lower = case.left_lower + case.right_upper + 1000
    sub_upper = case.left_upper + case.right_upper + 2000
    return f"""  {{
    uint32_t ll[{count}] = {{{_c_limbs(case.left_lower, count)}}};
    uint32_t lu[{count}] = {{{_c_limbs(case.left_upper, count)}}};
    uint32_t rl[{count}] = {{{_c_limbs(case.right_lower, count)}}};
    uint32_t ru[{count}] = {{{_c_limbs(case.right_upper, count)}}};
    uint32_t sl[{count}] = {{{_c_limbs(sub_lower, count)}}};
    uint32_t su[{count}] = {{{_c_limbs(sub_upper, count)}}};
    uint32_t lower[{count}];
    uint32_t upper[{count}];
    uint32_t scratch[{count * 4}];
    if (!malbolge_guest_math_fixed_interval_add(
            ll, lu, rl, ru, UINT32_C({count}), lower, upper)) return 81;
    print_limbs("AL", lower, UINT32_C({count}));
    print_limbs("AU", upper, UINT32_C({count}));
    if (!malbolge_guest_math_fixed_interval_subtract(
            sl, su, rl, ru, UINT32_C({count}), lower, upper)) return 82;
    print_limbs("SL", lower, UINT32_C({count}));
    print_limbs("SU", upper, UINT32_C({count}));
    if (!malbolge_guest_math_fixed_interval_multiply(
            ll, lu, rl, ru, UINT32_C({count}), UINT32_C({count - 1}),
            lower, upper, scratch, UINT32_C({count * 4}))) return 83;
    print_limbs("ML", lower, UINT32_C({count}));
    print_limbs("MU", upper, UINT32_C({count}));
    if (!malbolge_guest_math_fixed_interval_divide_small(
            ll, lu, UINT32_C({count}), UINT32_C({case.divisor}), lower, upper,
            scratch, UINT32_C({count * 4}))) return 84;
    print_limbs("DL", lower, UINT32_C({count}));
    print_limbs("DU", upper, UINT32_C({count}));
  }}"""


def _harness_source() -> str:
    body = "\n".join(_case_block(case) for case in _cases())
    return f"""#include "math_transcendental_bits.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

static void print_limbs(const char *tag, const uint32_t *value,
                        uint32_t count) {{
  uint32_t index = UINT32_C(0);
  (void)printf("%s %" PRIu32, tag, count);
  while (index < count) {{
    (void)printf(" %08" PRIx32, value[index]);
    ++index;
  }}
  (void)printf("\\n");
}}

int main(void) {{
{body}
  return 0;
}}
"""


def _limbs_to_integer(items: list[str]) -> int:
    return sum(
        int(item, 16) << (32 * index) for index, item in enumerate(items)
    )


def _ceil_div(numerator: int, denominator: int) -> int:
    quotient, remainder = divmod(numerator, denominator)
    return quotient + int(remainder != 0)


def _expected(case: IntervalCase) -> tuple[tuple[str, int], ...]:
    scale = 1 << (32 * (case.limb_count - 1))
    sub_lower = case.left_lower + case.right_upper + 1000
    sub_upper = case.left_upper + case.right_upper + 2000
    return (
        ("AL", case.left_lower + case.right_lower),
        ("AU", case.left_upper + case.right_upper),
        ("SL", sub_lower - case.right_upper),
        ("SU", sub_upper - case.right_lower),
        ("ML", (case.left_lower * case.right_lower) // scale),
        ("MU", _ceil_div(case.left_upper * case.right_upper, scale)),
        ("DL", case.left_lower // case.divisor),
        ("DU", _ceil_div(case.left_upper, case.divisor)),
    )


def test_variable_interval_operations_match_integer_authority(
    tmp_path: Path,
) -> None:
    """Match directed interval endpoints through 128 caller-owned limbs."""
    harness = tmp_path / "variable-interval.c"
    executable = tmp_path / "variable-interval"
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
    records = tuple(line.split() for line in executed.stdout.splitlines())
    assert len(records) == 8 * len(_cases())
    offset = 0
    for case in _cases():
        for (tag, expected), record in zip(
            _expected(case), records[offset : offset + 8], strict=True
        ):
            assert record[:2] == [tag, str(case.limb_count)]
            assert _limbs_to_integer(record[2:]) == expected
        offset += 8


def _failure_harness_source() -> str:
    return r"""#include "math_transcendental_bits.h"
#include <stdint.h>

static int unchanged(const uint32_t *lower, const uint32_t *upper) {
  return lower[0] == UINT32_C(0x11111111) &&
         lower[1] == UINT32_C(0x22222222) &&
         upper[0] == UINT32_C(0x33333333) &&
         upper[1] == UINT32_C(0x44444444);
}

int main(void) {
  uint32_t maximum[2] = {UINT32_MAX, UINT32_MAX};
  uint32_t almost[2] = {UINT32_C(0xfffffffe), UINT32_MAX};
  uint32_t one[2] = {UINT32_C(1), UINT32_C(0)};
  uint32_t ten[2] = {UINT32_C(10), UINT32_C(0)};
  uint32_t twenty[2] = {UINT32_C(20), UINT32_C(0)};
  uint32_t fifteen[2] = {UINT32_C(15), UINT32_C(0)};
  uint32_t sixteen[2] = {UINT32_C(16), UINT32_C(0)};
  uint32_t ceil_left[2] = {UINT32_C(3), UINT32_C(0xfffffffe)};
  uint32_t ceil_right[2] = {UINT32_C(2), UINT32_C(1)};
  uint32_t lower[2] = {UINT32_C(0x11111111), UINT32_C(0x22222222)};
  uint32_t upper[2] = {UINT32_C(0x33333333), UINT32_C(0x44444444)};
  uint32_t scratch[8];

  if (malbolge_guest_math_fixed_interval_add(
          almost, maximum, one, one, UINT32_C(2), lower, upper) ||
      !unchanged(lower, upper)) return 91;
  if (malbolge_guest_math_fixed_interval_subtract(
          ten, twenty, fifteen, sixteen, UINT32_C(2), lower, upper) ||
      !unchanged(lower, upper)) return 92;
  if (malbolge_guest_math_fixed_interval_add(
          twenty, ten, one, one, UINT32_C(2), lower, upper) ||
      !unchanged(lower, upper)) return 93;
  if (malbolge_guest_math_fixed_interval_multiply(
          ceil_left, ceil_left, ceil_right, ceil_right, UINT32_C(2),
          UINT32_C(1), lower, upper, scratch, UINT32_C(8)) ||
      !unchanged(lower, upper)) return 94;
  if (malbolge_guest_math_fixed_interval_divide_small(
          one, one, UINT32_C(2), UINT32_C(3), lower, upper, scratch,
          UINT32_C(3)) || !unchanged(lower, upper)) return 95;
  if (malbolge_guest_math_fixed_interval_divide_small(
          one, one, UINT32_C(2), UINT32_C(0), lower, upper, scratch,
          UINT32_C(8)) || !unchanged(lower, upper)) return 96;
  return 0;
}
"""


def test_variable_interval_failures_do_not_publish(tmp_path: Path) -> None:
    """Reject malformed, overflowing, underflowing, or undersized operations."""
    harness = tmp_path / "variable-interval-failure.c"
    executable = tmp_path / "variable-interval-failure"
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
