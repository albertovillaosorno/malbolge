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
#   - Signed-magnitude variable-width accumulation evidence for atan2
#     refinement.
# - Must-Not:
#   - Allocate memory, use host floating arithmetic, or publish negative zero.
# - Allows:
#   - Inputs: two magnitude-limb values plus canonical one-bit sign selectors.
#   - Outputs: exact signed-magnitude sum or nonpublishing rejection.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Signed interval accumulation gains independently testable policy.
# - Merge-When:
#   - Full adaptive sine/cosine summation owns signed accumulation directly.
# - Summary:
#   - Proves sign-aware add/subtract and canonical zero over caller-owned limbs.
# - Description:
#   - Equal signs add; opposite signs subtract the smaller magnitude from
#     larger.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Carry overflow or invalid sign selectors reject before publication.
#

"""Signed-magnitude accumulation evidence for adaptive atan2."""

from __future__ import annotations

from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
UINT32_MAX = (1 << 32) - 1
WIDTHS = (4, 8, 16, 128)
RECORDS_PER_WIDTH = 6


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
    limbs[-1] &= 1
    return sum(limb << (32 * index) for index, limb in enumerate(limbs))


def _c_limbs(integer: int, count: int) -> str:
    return ", ".join(
        f"UINT32_C(0x{((integer >> (32 * index)) & UINT32_MAX):08x})"
        for index in range(count)
    )


def _case_block(count: int) -> str:
    left = _pattern_integer(count, 0x5349474C0000 + count) + 1000
    right = _pattern_integer(count, 0x534947520000 + count) + 500
    larger = max(left, right)
    smaller = min(left, right)
    return f"""  {{
    uint32_t left[{count}] = {{{_c_limbs(left, count)}}};
    uint32_t right[{count}] = {{{_c_limbs(right, count)}}};
    uint32_t larger[{count}] = {{{_c_limbs(larger, count)}}};
    uint32_t smaller[{count}] = {{{_c_limbs(smaller, count)}}};
    uint32_t zero[{count}] = {{UINT32_C(0)}};
    uint32_t output[{count}];
    uint32_t negative = UINT32_C(9);
    if (!malbolge_guest_math_fixed_signed_add(
            left, UINT32_C(0), right, UINT32_C(0), UINT32_C({count}),
            output, &negative)) return 81;
    print_value("PP", output, UINT32_C({count}), negative);
    if (!malbolge_guest_math_fixed_signed_add(
            left, UINT32_C(1), right, UINT32_C(1), UINT32_C({count}),
            output, &negative)) return 82;
    print_value("NN", output, UINT32_C({count}), negative);
    if (!malbolge_guest_math_fixed_signed_add(
            larger, UINT32_C(0), smaller, UINT32_C(1), UINT32_C({count}),
            output, &negative)) return 83;
    print_value("PN", output, UINT32_C({count}), negative);
    if (!malbolge_guest_math_fixed_signed_add(
            smaller, UINT32_C(0), larger, UINT32_C(1), UINT32_C({count}),
            output, &negative)) return 84;
    print_value("NP", output, UINT32_C({count}), negative);
    if (!malbolge_guest_math_fixed_signed_add(
            left, UINT32_C(0), left, UINT32_C(1), UINT32_C({count}),
            output, &negative)) return 85;
    print_value("CZ", output, UINT32_C({count}), negative);
    if (!malbolge_guest_math_fixed_signed_add(
            zero, UINT32_C(1), zero, UINT32_C(1), UINT32_C({count}),
            output, &negative)) return 86;
    print_value("NZ", output, UINT32_C({count}), negative);
  }}"""


def _harness_source() -> str:
    body = "\n".join(_case_block(count) for count in WIDTHS)
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


def test_signed_accumulation_matches_integer_authority(tmp_path: Path) -> None:
    """Match sign-aware accumulation through 128 limbs and canonicalize zero."""
    harness = tmp_path / "signed-accumulation.c"
    executable = tmp_path / "signed-accumulation"
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
    assert len(records) == RECORDS_PER_WIDTH * len(WIDTHS)
    offset = 0
    for count in WIDTHS:
        left = _pattern_integer(count, 0x5349474C0000 + count) + 1000
        right = _pattern_integer(count, 0x534947520000 + count) + 500
        expected = (
            ("PP", 0, left + right),
            ("NN", 1, left + right),
            ("PN", 0, abs(left - right)),
            ("NP", 1, abs(left - right)),
            ("CZ", 0, 0),
            ("NZ", 0, 0),
        )
        for (tag, negative, magnitude), record in zip(
            expected, records[offset : offset + 6], strict=True
        ):
            assert record[:3] == [tag, str(count), str(negative)]
            assert _limbs_to_integer(record[3:]) == magnitude
        offset += 6


def _failure_harness_source() -> str:
    return r"""#include "math_transcendental_bits.h"
#include <stdint.h>

int main(void) {
  uint32_t maximum[2] = {UINT32_MAX, UINT32_MAX};
  uint32_t one[2] = {UINT32_C(1), UINT32_C(0)};
  uint32_t output[2] = {UINT32_C(0x11111111), UINT32_C(0x22222222)};
  uint32_t negative = UINT32_C(0x76543210);

  if (malbolge_guest_math_fixed_signed_add(
          maximum, UINT32_C(0), one, UINT32_C(0), UINT32_C(2), output,
          &negative) || output[0] != UINT32_C(0x11111111) ||
      output[1] != UINT32_C(0x22222222) ||
      negative != UINT32_C(0x76543210)) return 91;
  if (malbolge_guest_math_fixed_signed_add(
          one, UINT32_C(2), one, UINT32_C(0), UINT32_C(2), output,
          &negative) || output[0] != UINT32_C(0x11111111) ||
      output[1] != UINT32_C(0x22222222) ||
      negative != UINT32_C(0x76543210)) return 92;
  if (malbolge_guest_math_fixed_signed_add(
          one, UINT32_C(0), one, UINT32_C(0), UINT32_C(2), output, 0) ||
      output[0] != UINT32_C(0x11111111)) return 93;
  return 0;
}
"""


def test_signed_accumulation_failures_do_not_publish(tmp_path: Path) -> None:
    """Reject carry overflow, invalid signs, and null sign output atomically."""
    harness = tmp_path / "signed-accumulation-failure.c"
    executable = tmp_path / "signed-accumulation-failure"
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
