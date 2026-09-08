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
#   - Variable-width directed Taylor-term recurrence evidence for atan2.
# - Must-Not:
#   - Allocate memory, evaluate transcendental host functions, or use Q oracles.
# - Allows:
#   - Inputs: nonnegative term/x-squared intervals and one positive divisor.
#   - Outputs: directed enclosure of term*x^2/divisor or fail-closed rejection.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Full sin/cos summation gains independent adaptive policy.
# - Merge-When:
#   - Complete tangent-midpoint refinement owns the Taylor recurrence directly.
# - Summary:
#   - Proves the shared directed recurrence used by sine and cosine terms.
# - Description:
#   - Product and divide reuse one caller-owned four-limb-per-value workspace.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Malformed intervals, zero divisors, or short scratch reject atomically.
#

"""Directed Taylor-term recurrence evidence for adaptive atan2."""

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
class TaylorCase:
    """One directed fixed-point Taylor recurrence fixture."""

    limb_count: int
    term_lower: int
    term_upper: int
    square_lower: int
    square_upper: int
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
        limbs.append((state >> 17) & UINT32_MAX)
    limbs[-1] &= 1
    return sum(limb << (32 * index) for index, limb in enumerate(limbs))


def _cases() -> tuple[TaylorCase, ...]:
    rows: list[TaylorCase] = []
    for width, divisor in zip((4, 8, 16, 128), (6, 20, 42, 72), strict=True):
        term = _pattern_integer(width, 0x5445524D0000 + width)
        square = _pattern_integer(width, 0x535155410000 + width)
        rows.append(
            TaylorCase(width, term, term + 9, square, square + 13, divisor)
        )
    return tuple(rows)


def _c_limbs(integer: int, count: int) -> str:
    return ", ".join(
        f"UINT32_C(0x{((integer >> (32 * index)) & UINT32_MAX):08x})"
        for index in range(count)
    )


def _case_block(case: TaylorCase) -> str:
    count = case.limb_count
    return f"""  {{
    uint32_t tl[{count}] = {{{_c_limbs(case.term_lower, count)}}};
    uint32_t tu[{count}] = {{{_c_limbs(case.term_upper, count)}}};
    uint32_t sl[{count}] = {{{_c_limbs(case.square_lower, count)}}};
    uint32_t su[{count}] = {{{_c_limbs(case.square_upper, count)}}};
    uint32_t lower[{count}];
    uint32_t upper[{count}];
    uint32_t scratch[{count * 4}];
    if (!malbolge_guest_math_fixed_taylor_term_interval(
            tl, tu, sl, su, UINT32_C({count}), UINT32_C({count - 1}),
            UINT32_C({case.divisor}), lower, upper, scratch,
            UINT32_C({count * 4}))) return 81;
    print_limbs("L", lower, UINT32_C({count}));
    print_limbs("U", upper, UINT32_C({count}));
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


def _expected(case: TaylorCase) -> tuple[int, int]:
    scale = 1 << (32 * (case.limb_count - 1))
    lower_product = (case.term_lower * case.square_lower) // scale
    upper_product = _ceil_div(case.term_upper * case.square_upper, scale)
    return lower_product // case.divisor, _ceil_div(upper_product, case.divisor)


def test_taylor_recurrence_matches_directed_integer_authority(
    tmp_path: Path,
) -> None:
    """Match the shared sin/cos term recurrence through 128 limbs."""
    harness = tmp_path / "taylor-recurrence.c"
    executable = tmp_path / "taylor-recurrence"
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
    assert len(records) == 2 * len(_cases())
    for position, case in enumerate(_cases()):
        lower, upper = _expected(case)
        lower_row, upper_row = records[position * 2 : position * 2 + 2]
        assert lower_row[:2] == ["L", str(case.limb_count)]
        assert upper_row[:2] == ["U", str(case.limb_count)]
        assert _limbs_to_integer(lower_row[2:]) == lower
        assert _limbs_to_integer(upper_row[2:]) == upper


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
  uint32_t one[2] = {UINT32_C(1), UINT32_C(0)};
  uint32_t two[2] = {UINT32_C(2), UINT32_C(0)};
  uint32_t ceil_left[2] = {UINT32_C(3), UINT32_C(0xfffffffe)};
  uint32_t ceil_right[2] = {UINT32_C(2), UINT32_C(1)};
  uint32_t lower[2] = {UINT32_C(0x11111111), UINT32_C(0x22222222)};
  uint32_t upper[2] = {UINT32_C(0x33333333), UINT32_C(0x44444444)};
  uint32_t scratch[8];

  if (malbolge_guest_math_fixed_taylor_term_interval(
          two, one, one, one, UINT32_C(2), UINT32_C(1), UINT32_C(6),
          lower, upper, scratch, UINT32_C(8)) || !unchanged(lower, upper))
    return 91;
  if (malbolge_guest_math_fixed_taylor_term_interval(
          one, one, one, one, UINT32_C(2), UINT32_C(1), UINT32_C(0),
          lower, upper, scratch, UINT32_C(8)) || !unchanged(lower, upper))
    return 92;
  if (malbolge_guest_math_fixed_taylor_term_interval(
          one, one, one, one, UINT32_C(2), UINT32_C(1), UINT32_C(6),
          lower, upper, scratch, UINT32_C(7)) || !unchanged(lower, upper))
    return 93;
  if (malbolge_guest_math_fixed_taylor_term_interval(
          ceil_left, ceil_left, ceil_right, ceil_right, UINT32_C(2),
          UINT32_C(1), UINT32_C(1), lower, upper, scratch, UINT32_C(8)) ||
      !unchanged(lower, upper))
    return 94;
  return 0;
}
"""


def test_taylor_recurrence_failures_do_not_publish(tmp_path: Path) -> None:
    """Reject malformed terms and invalid recurrence resources."""
    harness = tmp_path / "taylor-recurrence-failure.c"
    executable = tmp_path / "taylor-recurrence-failure"
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
