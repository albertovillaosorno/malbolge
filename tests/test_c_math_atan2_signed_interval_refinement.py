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
#   - Atomic signed-magnitude interval accumulation evidence for atan2
#     refinement.
# - Must-Not:
#   - Allocate memory, use two's-complement fixed width, or publish negative
#     zero.
# - Allows:
#   - Inputs: ordered signed-magnitude intervals plus caller-owned staging
#     scratch.
#   - Outputs: exact interval sum or nonpublishing rejection.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Full alternating Taylor summation gains independently testable policy.
# - Merge-When:
#   - Adaptive sine/cosine refinement owns signed interval accumulation
#     directly.
# - Summary:
#   - Proves monotone signed interval addition with atomic endpoint publication.
# - Description:
#   - Lower/lower and upper/upper sums stage in two magnitude buffers.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Malformed intervals, invalid signs, short scratch, or carry reject
#     atomically.
#

"""Atomic signed interval accumulation evidence for adaptive atan2."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
UINT32_MAX = (1 << 32) - 1
WIDTHS = (4, 8, 16, 128)


@dataclass(frozen=True)
class SignedIntervalCase:
    """One pair of ordered signed fixed-point intervals."""

    limb_count: int
    left_lower: int
    left_upper: int
    right_lower: int
    right_upper: int


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
        limbs.append((state >> 18) & UINT32_MAX)
    limbs[-1] &= 0x0FFFFFFF
    return sum(limb << (32 * index) for index, limb in enumerate(limbs))


def _cases() -> tuple[SignedIntervalCase, ...]:
    rows: list[SignedIntervalCase] = []
    for width in WIDTHS:
        left = _pattern_integer(width, 0x53494C4C0000 + width) + 1000
        right = _pattern_integer(width, 0x53494C520000 + width) + 500
        rows.append(
            SignedIntervalCase(
                width,
                -(left + 71),
                left + 113,
                -(right + 37),
                right + 59,
            )
        )
    return tuple(rows)


def _c_limbs(integer: int, count: int) -> str:
    magnitude = abs(integer)
    return ", ".join(
        f"UINT32_C(0x{((magnitude >> (32 * index)) & UINT32_MAX):08x})"
        for index in range(count)
    )


def _negative(integer: int) -> int:
    return int(integer < 0)


def _case_block(case: SignedIntervalCase) -> str:
    count = case.limb_count
    return f"""  {{
    uint32_t ll[{count}] = {{{_c_limbs(case.left_lower, count)}}};
    uint32_t lu[{count}] = {{{_c_limbs(case.left_upper, count)}}};
    uint32_t rl[{count}] = {{{_c_limbs(case.right_lower, count)}}};
    uint32_t ru[{count}] = {{{_c_limbs(case.right_upper, count)}}};
    uint32_t lower[{count}];
    uint32_t upper[{count}];
    uint32_t scratch[{count * 2}];
    uint32_t lower_negative = UINT32_C(9);
    uint32_t upper_negative = UINT32_C(9);
    if (!malbolge_guest_math_fixed_signed_interval_add(
            ll, UINT32_C({_negative(case.left_lower)}),
            lu, UINT32_C({_negative(case.left_upper)}),
            rl, UINT32_C({_negative(case.right_lower)}),
            ru, UINT32_C({_negative(case.right_upper)}), UINT32_C({count}),
            lower, &lower_negative, upper, &upper_negative, scratch,
            UINT32_C({count * 2}))) return 81;
    print_value("L", lower, UINT32_C({count}), lower_negative);
    print_value("U", upper, UINT32_C({count}), upper_negative);
  }}"""


def _harness_source() -> str:
    body = "\n".join(_case_block(case) for case in _cases())
    return f"""#include "math_transcendental_bits.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

static void print_value(const char *tag, const uint32_t *value,
                        uint32_t count, uint32_t negative) {{
  uint32_t index = UINT32_C(0);
  (void)printf("%s %" PRIu32 " %" PRIu32, tag, count, negative);
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


def _signed_record(record: list[str]) -> int:
    magnitude = _limbs_to_integer(record[3:])
    return -magnitude if int(record[2]) else magnitude


def test_signed_interval_add_matches_integer_authority(tmp_path: Path) -> None:
    """Match cross-zero interval sums through 128 limbs."""
    harness = tmp_path / "signed-interval.c"
    executable = tmp_path / "signed-interval"
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
        lower_row, upper_row = records[position * 2 : position * 2 + 2]
        assert lower_row[:2] == ["L", str(case.limb_count)]
        assert upper_row[:2] == ["U", str(case.limb_count)]
        assert _signed_record(lower_row) == case.left_lower + case.right_lower
        assert _signed_record(upper_row) == case.left_upper + case.right_upper


def _failure_harness_source() -> str:
    return r"""#include "math_transcendental_bits.h"
#include <stdint.h>

static int unchanged(const uint32_t *lower, uint32_t lower_negative,
                     const uint32_t *upper, uint32_t upper_negative) {
  return lower[0] == UINT32_C(0x11111111) &&
         lower[1] == UINT32_C(0x22222222) &&
         lower_negative == UINT32_C(7) &&
         upper[0] == UINT32_C(0x33333333) &&
         upper[1] == UINT32_C(0x44444444) &&
         upper_negative == UINT32_C(8);
}

int main(void) {
  uint32_t zero[2] = {UINT32_C(0), UINT32_C(0)};
  uint32_t one[2] = {UINT32_C(1), UINT32_C(0)};
  uint32_t ten[2] = {UINT32_C(10), UINT32_C(0)};
  uint32_t twenty[2] = {UINT32_C(20), UINT32_C(0)};
  uint32_t maximum[2] = {UINT32_MAX, UINT32_MAX};
  uint32_t lower[2] = {UINT32_C(0x11111111), UINT32_C(0x22222222)};
  uint32_t upper[2] = {UINT32_C(0x33333333), UINT32_C(0x44444444)};
  uint32_t scratch[4];
  uint32_t lower_negative = UINT32_C(7);
  uint32_t upper_negative = UINT32_C(8);

  if (malbolge_guest_math_fixed_signed_interval_add(
          twenty, UINT32_C(0), ten, UINT32_C(0), zero, UINT32_C(0),
          zero, UINT32_C(0), UINT32_C(2), lower, &lower_negative, upper,
          &upper_negative, scratch, UINT32_C(4)) ||
      !unchanged(lower, lower_negative, upper, upper_negative)) return 91;
  if (malbolge_guest_math_fixed_signed_interval_add(
          zero, UINT32_C(0), maximum, UINT32_C(0), zero, UINT32_C(0),
          one, UINT32_C(0), UINT32_C(2), lower, &lower_negative, upper,
          &upper_negative, scratch, UINT32_C(4)) ||
      !unchanged(lower, lower_negative, upper, upper_negative)) return 92;
  if (malbolge_guest_math_fixed_signed_interval_add(
          zero, UINT32_C(0), one, UINT32_C(0), zero, UINT32_C(0),
          one, UINT32_C(0), UINT32_C(2), lower, &lower_negative, upper,
          &upper_negative, scratch, UINT32_C(3)) ||
      !unchanged(lower, lower_negative, upper, upper_negative)) return 93;
  if (malbolge_guest_math_fixed_signed_interval_add(
          zero, UINT32_C(2), one, UINT32_C(0), zero, UINT32_C(0),
          one, UINT32_C(0), UINT32_C(2), lower, &lower_negative, upper,
          &upper_negative, scratch, UINT32_C(4)) ||
      !unchanged(lower, lower_negative, upper, upper_negative)) return 94;
  return 0;
}
"""


def test_signed_interval_failures_do_not_publish(tmp_path: Path) -> None:
    """Reject malformed, upper-carry, short-scratch, and invalid-sign inputs."""
    harness = tmp_path / "signed-interval-failure.c"
    executable = tmp_path / "signed-interval-failure"
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
