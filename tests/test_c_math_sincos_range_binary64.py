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
#   - Final unique binary64 gate over bounded Q256 periodic sin/cos intervals.
# - Must-Not:
#   - Treat Q256 success on retained cases as full-domain sufficiency.
# - Allows:
#   - Inputs: retained 4 <= |x| < 2^31 cases already covered by rational
#     authority.
#   - Outputs: raw SIN/COS bits when both Q256 endpoints round identically.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Wider periodic precision becomes an adaptive retry surface.
# - Merge-When:
#   - A full-domain sin/cos handoff subsumes the bounded Q256 gate.
# - Summary:
#   - Proves retained periodic intervals publish unique binary64 results.
# - Description:
#   - Differentially matches the explicit interval-plus-rounding composition.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Uses the same pi/2-neighbor corpus as independent interval authority.
#

"""Bounded Q256 periodic sin/cos final-rounding evidence."""

from __future__ import annotations

from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
SIN = 1
COS = 2


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


CASES: tuple[int, ...] = (
    0x4010000000000000,
    0x4010000000000001,
    0x4012D97C7F3321D0,
    0x4012D97C7F3321D1,
    0x4012D97C7F3321D2,
    0x4012D97C7F3321D3,
    0x4012D97C7F3321D4,
    0x401921FB54442D16,
    0x401921FB54442D17,
    0x401921FB54442D18,
    0x401921FB54442D19,
    0x401921FB54442D1A,
    0x401F6A7A2955385C,
    0x401F6A7A2955385D,
    0x401F6A7A2955385E,
    0x401F6A7A2955385F,
    0x401F6A7A29553860,
    0x4025FDBBE9BBA773,
    0x4025FDBBE9BBA774,
    0x4025FDBBE9BBA775,
    0x4025FDBBE9BBA776,
    0x4025FDBBE9BBA777,
    0x403AB41B09886FE8,
    0x403AB41B09886FE9,
    0x403AB41B09886FEA,
    0x403AB41B09886FEB,
    0x403AB41B09886FEC,
    0x40988B2F704A9408,
    0x40988B2F704A9409,
    0x40988B2F704A940A,
    0x40988B2F704A940B,
    0x40988B2F704A940C,
    0x4137F7EC53A8D48F,
    0x4137F7EC53A8D490,
    0x4137F7EC53A8D491,
    0x4137F7EC53A8D492,
    0x4137F7EC53A8D493,
    0x41D7681CC9B2DF94,
    0x41D7681CC9B2DF95,
    0x41D7681CC9B2DF96,
    0x41D7681CC9B2DF97,
    0x41D7681CC9B2DF98,
    0x41DFFFFFFFFFFFFF,
    0xC012D97C7F3321D0,
    0xC012D97C7F3321D1,
    0xC012D97C7F3321D2,
    0xC012D97C7F3321D3,
    0xC012D97C7F3321D4,
    0xC01921FB54442D16,
    0xC01921FB54442D17,
    0xC01921FB54442D18,
    0xC01921FB54442D19,
    0xC01921FB54442D1A,
    0xC01F6A7A2955385C,
    0xC01F6A7A2955385D,
    0xC01F6A7A2955385E,
    0xC01F6A7A2955385F,
    0xC01F6A7A29553860,
    0xC025FDBBE9BBA773,
    0xC025FDBBE9BBA774,
    0xC025FDBBE9BBA775,
    0xC025FDBBE9BBA776,
    0xC025FDBBE9BBA777,
    0xC03AB41B09886FE8,
    0xC03AB41B09886FE9,
    0xC03AB41B09886FEA,
    0xC03AB41B09886FEB,
    0xC03AB41B09886FEC,
    0xC0988B2F704A9408,
    0xC0988B2F704A9409,
    0xC0988B2F704A940A,
    0xC0988B2F704A940B,
    0xC0988B2F704A940C,
    0xC137F7EC53A8D48F,
    0xC137F7EC53A8D490,
    0xC137F7EC53A8D491,
    0xC137F7EC53A8D492,
    0xC137F7EC53A8D493,
    0xC1D7681CC9B2DF94,
    0xC1D7681CC9B2DF95,
    0xC1D7681CC9B2DF96,
    0xC1D7681CC9B2DF97,
    0xC1D7681CC9B2DF98
)


def _source() -> str:
    rows = ",\n".join(f"  UINT64_C(0x{bits:016x})" for bits in CASES)
    return f"""#include "math_transcendental_bits.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
static const uint64_t cases[] = {{
{rows}
}};
int main(void) {{
  uint32_t scratch[90];
  uint32_t index = UINT32_C(0);
  while (index < (uint32_t)(sizeof(cases) / sizeof(cases[0]))) {{
    uint64_t direct_sin = UINT64_C(0), direct_cos = UINT64_C(0);
    uint64_t manual_sin = UINT64_C(0), manual_cos = UINT64_C(0);
    MalbolgeGuestMathSincosInterval256 interval;
    if (!malbolge_guest_math_sincos_range_interval256(
            cases[index], MALBOLGE_GUEST_MATH_PERIODIC_TAYLOR_TERMS,
            &interval, scratch, UINT32_C(90)))
      return 80;
    if (!malbolge_guest_math_fixed_signed_interval_unique_binary64(
            interval.sin.lower.limbs, interval.sin.lower_negative,
            interval.sin.upper.limbs, interval.sin.upper_negative,
            UINT32_C(9), UINT32_C(8), &manual_sin) ||
        !malbolge_guest_math_fixed_signed_interval_unique_binary64(
            interval.cos.lower.limbs, interval.cos.lower_negative,
            interval.cos.upper.limbs, interval.cos.upper_negative,
            UINT32_C(9), UINT32_C(8), &manual_cos)) return 81;
    if (!malbolge_guest_math_sincos_range_unique_binary64(
            MALBOLGE_GUEST_MATH_SIN, cases[index], &direct_sin,
            scratch, UINT32_C(90)) ||
        !malbolge_guest_math_sincos_range_unique_binary64(
            MALBOLGE_GUEST_MATH_COS, cases[index], &direct_cos,
            scratch, UINT32_C(90))) return 82;
    if (direct_sin != manual_sin || direct_cos != manual_cos) return 83;
    (void)printf("%016" PRIx64 " %016" PRIx64 " %016" PRIx64 "\\n",
                 cases[index], direct_sin, direct_cos);
    ++index;
  }}
  return 0;
}}
"""


def test_range_binary64_matches_unique_interval_composition(
    tmp_path: Path,
) -> None:
    """Publish both operations for every independently enclosed case."""
    harness = tmp_path / "range-binary64.c"
    executable = tmp_path / "range-binary64"
    _ = harness.write_text(_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG), "-std=c23", "-O2", "-ffreestanding", "-fno-builtin",
            "-Wall", "-Wextra", "-Wpedantic", "-Werror", f"-I{CONTRACT}",
            str(SOURCE), str(harness), "-o", str(executable),
        ],
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    executed = _run([str(executable)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr
    rows = tuple(executed.stdout.splitlines())
    assert len(rows) == len(CASES)
