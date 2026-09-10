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
#   - Reduced atan2 denominator factorization after exact special handling.
# - Must-Not:
#   - Treat an arbitrary 106-bit integer as the only denominator structure.
#   - Use host floating division or transcendental functions as authority.
# - Allows:
#   - Inputs: exact branch cutoffs and fixed kernel-required binary64 witnesses.
#   - Outputs: odd-factor and power-of-two denominator ceilings by branch.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - A finite bivariate TMD search consumes denominator factors directly.
# - Merge-When:
#   - Full atan2 resource proof owns exact ratio realizability itself.
# - Summary:
#   - Factors every surviving ratio denominator into odd and dyadic parts.
# - Description:
#   - Fraction proves factorization; C pins branch-surviving tight witnesses.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - These are search-space bounds, not a midpoint-separation theorem.
#

"""Structural denominator factors for adaptive binary64 atan2 ratios."""

from __future__ import annotations

from fractions import Fraction
from itertools import starmap
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
SIGN = 1 << 63
MAGNITUDE = SIGN - 1
EXPONENT_MASK = 0x7FF
FRACTION_MASK = (1 << 52) - 1
HIDDEN = 1 << 52
SIGNIFICAND_BITS = 53
SIGNIFICAND_TRAILING_ZERO_MAX = 52
POSITIVE_DIRECT_DYADIC_MAX = 79
NEGATIVE_DIRECT_DYADIC_MAX = 104
SWAPPED_DYADIC_MAX = 52
ODD_FACTOR_BITS_MAX = 53
KERNEL_REQUIRED = 2

# Branch witnesses: positive-direct v2=79, negative-direct v2=104,
# swapped v2=52, and an existing hard pair with a 53-bit odd denominator.
CASES = (
    (0x3E4E2CF51ED74C7B, 0x3FF0000000000000),
    (0x3CB0000000000001, 0xBFF0000000000000),
    (0x3FF0000000000001, 0x3FF0000000000000),
    (0x3FE97B1DB9A2A48C, 0x3FF781CE6A6EE8EF),
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


def _magnitude(bits: int) -> Fraction:
    raw = bits & MAGNITUDE
    exponent = (raw >> 52) & EXPONENT_MASK
    fraction = raw & FRACTION_MASK
    assert raw != 0
    assert exponent != EXPONENT_MASK
    if exponent == 0:
        return Fraction(fraction, 1 << 1074)
    significand = HIDDEN | fraction
    power = exponent - 1023 - 52
    if power >= 0:
        return Fraction(significand << power, 1)
    return Fraction(significand, 1 << -power)


def _denominator_shape(y_bits: int, x_bits: int) -> tuple[int, int]:
    denominator = (_magnitude(y_bits) / _magnitude(x_bits)).denominator
    dyadic_exponent = (denominator & -denominator).bit_length() - 1
    odd = denominator >> dyadic_exponent
    return odd.bit_length(), dyadic_exponent


def test_branch_cutoffs_bound_denominator_factorization() -> None:
    """Derive branch ceilings from 53-bit significands and special cutoffs."""
    # Reduction by gcd can only shrink the odd part inherited from one
    # normalized binary64 significand.
    assert ODD_FACTOR_BITS_MAX == SIGNIFICAND_BITS

    # A swapped ratio is inverted, so its nonnegative power-of-two exponent
    # can only cancel denominator factors. The denominator therefore divides
    # one 53-bit significand and has at most 52 factors of two.
    assert SWAPPED_DYADIC_MAX == SIGNIFICAND_TRAILING_ZERO_MAX

    # On the negative-x, non-swapped branch, ratios at or below 2^-52 are
    # resolved at the axis. A survivor therefore has exponent delta >= -52.
    assert (
        SIGNIFICAND_TRAILING_ZERO_MAX + 52 == NEGATIVE_DIRECT_DYADIC_MAX
    )

    # On positive x, ratios outside the small-atan identity have exponent
    # delta >= -27, yielding at most 52+27 = 79 dyadic denominator bits.
    assert SIGNIFICAND_TRAILING_ZERO_MAX + 27 == POSITIVE_DIRECT_DYADIC_MAX

    # Inside the identity range, let E be the normalized binary64 quotient
    # exponent. For E=-53..-28, the spacing shortcut resolves whenever the odd
    # denominator d <= 3*2^(m-1), m=-(2E+55). A survivor has bit_length(d)
    # >= m+1, leaving at most 52-m trailing zeroes in its significand. Adding
    # the input exponent shift gives v2(q) <= 107+E <= 79. If normalization
    # decremented E, the input shift is one smaller and only improves the bound.
    for exponent in range(-53, -27):
        margin_shift = -(2 * exponent + 55)
        significand_twos = 52 - margin_shift
        denominator_twos = significand_twos - exponent
        assert denominator_twos <= POSITIVE_DIRECT_DYADIC_MAX


def _source() -> str:
    rows = ",\n".join(
        f"  {{UINT64_C(0x{y:016x}), UINT64_C(0x{x:016x})}}" for y, x in CASES
    )
    return f"""#include "math_transcendental_bits.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
typedef struct Pair {{ uint64_t y, x; }} Pair;
static const Pair pairs[] = {{
{rows}
}};
int main(void) {{
  uint32_t index = UINT32_C(0);
  while (index < (uint32_t)(sizeof(pairs) / sizeof(pairs[0]))) {{
    const MalbolgeGuestMathSpecialResult special =
        malbolge_guest_math_atan2_special(pairs[index].y, pairs[index].x);
    MalbolgeGuestMathAtan2KernelInput input;
    if (!malbolge_guest_math_atan2_kernel_input(
            pairs[index].y, pairs[index].x, &input)) return 81;
    (void)printf("%u %u %u %d\\n", (unsigned)special.status,
                 input.swapped, input.x_negative, input.exponent_delta);
    ++index;
  }}
  return 0;
}}
"""


def test_factorization_witnesses_survive_special_path(tmp_path: Path) -> None:
    """Pin tight odd/dyadic factors on the branches that reach the kernel."""
    harness = tmp_path / "atan2-denominator-shape.c"
    executable = tmp_path / "atan2-denominator-shape"
    _ = harness.write_text(_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
            "-O2",
            "-ffreestanding",
            "-fno-builtin",
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
    rows = tuple(
        tuple(map(int, line.split())) for line in executed.stdout.splitlines()
    )
    assert len(rows) == len(CASES)
    assert all(row[0] == KERNEL_REQUIRED for row in rows)

    shapes = tuple(starmap(_denominator_shape, CASES))
    assert shapes[0] == (1, POSITIVE_DIRECT_DYADIC_MAX)
    assert rows[0][1:3] == (0, 0)
    assert shapes[1] == (1, NEGATIVE_DIRECT_DYADIC_MAX)
    assert rows[1][1:3] == (0, 1)
    assert shapes[2] == (1, SWAPPED_DYADIC_MAX)
    assert rows[2][1] == 1
    assert shapes[3][0] == ODD_FACTOR_BITS_MAX

    for odd_bits, dyadic_exponent in shapes:
        assert odd_bits <= ODD_FACTOR_BITS_MAX
        assert dyadic_exponent <= NEGATIVE_DIRECT_DYADIC_MAX
