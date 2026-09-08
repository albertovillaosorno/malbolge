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
#   - Independent dyadic-midpoint certificates for internal atan2 rounding.
# - Must-Not:
#   - Use host atan/atan2, pi constants, or Q192/Q224/Q256/Q1152 as authority.
# - Allows:
#   - Inputs: finite nonzero binary64 pairs and candidate bits emitted by C.
#   - Outputs: exact-rational proof that each candidate rounding cell contains
#     the principal atan2 angle strictly between both midpoint boundaries.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - A runtime tangent-midpoint comparator gains its own implementation.
# - Merge-When:
#   - Complete correctly-rounded atan2 proof subsumes this independent route.
# - Summary:
#   - Certifies atan2 cells through tan(midpoint), not through atan evaluation.
# - Description:
#   - Directed rational sin/cos Taylor bounds compare y/x to tangent on the
#     matching principal-angle branch; quadrant order handles pole crossings.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Forty Taylor terms leave ample headroom for the retained hard vectors.
#

"""Independent dyadic-midpoint rounding certificates for guest atan2."""

from __future__ import annotations

from fractions import Fraction
from itertools import product
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
SIGN_BIT = 1 << 63
MAGNITUDE_MASK = SIGN_BIT - 1
FRACTION_MASK = (1 << 52) - 1
EXPONENT_MASK = 0x7FF
HIDDEN_BIT = 1 << 52
TAYLOR_TERMS = 40
MAX_MIDPOINT_MAGNITUDE = Fraction(4)

BASE_HARD_PAIRS = (
    (0x3FEE19FA869EA9FC, 0x3FF197DD31B21770),
    (0x3FE74E55173F69A0, 0x3FF6943B1C1EE532),
    (0x3FEF179200C72129, 0x3FFBC1B4128CF396),
    (0x3FE97B1DB9A2A48C, 0x3FF781CE6A6EE8EF),
    (0x3FE9519856F5242F, 0x3FF06C408C434F0E),
    (0x3FEF7590E09E2ADD, 0x3FF629E5895F91A7),
    (0x3FE5139B1425C8A2, 0x3FF4FA0C073AF8F1),
    (0x3FE549E587E6D4CD, 0x3FF11E3639F76651),
    (0x3FD75B9A8D0A0447, 0x3FF069F1CC6166FC),
    (0x3FDF65E15A3E11FD, 0x3FF31E45227A22DE),
    (0x3FDEF69FB021F2DB, 0x3FF90CC971F74C07),
    (0x3FDABB28E6EEF14A, 0x3FF544C4908DDACE),
    (0x3FD94D130BF48845, 0x3FF2CCCC5A36B6E1),
    (0x3FD667E2DB48932E, 0x3FF41B5A664E9573),
    (0x3FDBA787A32EAF18, 0x3FF914A595604C36),
    (0x3FD88C55EA9394D5, 0x3FF6ABB1E310A1AC),
)
EDGE_PAIRS = (
    (0x3FF0000000000000, 0x0000000000000001),
    (0x3FF0000000000000, 0x8000000000000001),
    (0x0010000000000000, 0x7FEFFFFFFFFFFFFF),
    (0x8010000000000000, 0x7FEFFFFFFFFFFFFF),
)


def _signed_hard_pairs() -> tuple[tuple[int, int], ...]:
    return tuple(
        (y | y_sign, x | x_sign)
        for y, x in BASE_HARD_PAIRS
        for y_sign, x_sign in product((0, SIGN_BIT), repeat=2)
    )


CERTIFICATE_PAIRS = _signed_hard_pairs() + EDGE_PAIRS


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


def _binary64_fraction(bits: int) -> Fraction:
    negative = bool(bits & SIGN_BIT)
    magnitude = bits & MAGNITUDE_MASK
    raw_exponent = (magnitude >> 52) & EXPONENT_MASK
    fraction = magnitude & FRACTION_MASK
    assert raw_exponent != EXPONENT_MASK
    if raw_exponent == 0:
        value = Fraction(fraction, 1 << 1074)
    else:
        significand = HIDDEN_BIT | fraction
        shift = raw_exponent - 1023 - 52
        value = (
            Fraction(significand << shift, 1)
            if shift >= 0
            else Fraction(significand, 1 << -shift)
        )
    return -value if negative else value


def _next_up(bits: int) -> int:
    if bits == SIGN_BIT:
        return 1
    return bits - 1 if bits & SIGN_BIT else bits + 1


def _next_down(bits: int) -> int:
    if bits == 0:
        return SIGN_BIT | 1
    return bits + 1 if bits & SIGN_BIT else bits - 1


def _sin_interval(value: Fraction) -> tuple[Fraction, Fraction]:
    negative = value < 0
    magnitude = abs(value)
    square = magnitude * magnitude
    term = magnitude
    total = term
    for index in range(TAYLOR_TERMS - 1):
        term *= square
        term /= ((2 * index) + 2) * ((2 * index) + 3)
        total = total - term if (index + 1) & 1 else total + term
    last = TAYLOR_TERMS - 1
    omitted = term * square / (((2 * last) + 2) * ((2 * last) + 3))
    lower, upper = (total - omitted, total) if TAYLOR_TERMS & 1 else (
        total,
        total + omitted,
    )
    return (-upper, -lower) if negative else (lower, upper)


def _cos_interval(value: Fraction) -> tuple[Fraction, Fraction]:
    square = value * value
    term = Fraction(1)
    total = term
    for index in range(TAYLOR_TERMS - 1):
        term *= square
        term /= ((2 * index) + 1) * ((2 * index) + 2)
        total = total - term if (index + 1) & 1 else total + term
    last = TAYLOR_TERMS - 1
    omitted = term * square / (((2 * last) + 1) * ((2 * last) + 2))
    return (total - omitted, total) if TAYLOR_TERMS & 1 else (
        total,
        total + omitted,
    )


def _sincos_interval(
    value: Fraction,
) -> tuple[Fraction, Fraction, Fraction, Fraction]:
    assert abs(value) < MAX_MIDPOINT_MAGNITUDE
    sin_lower, sin_upper = _sin_interval(value)
    cos_lower, cos_upper = _cos_interval(value)
    return sin_lower, sin_upper, cos_lower, cos_upper


def _tangent_interval(
    midpoint: Fraction,
) -> tuple[Fraction, Fraction, tuple[Fraction, Fraction, Fraction, Fraction]]:
    sin_lower, sin_upper, cos_lower, cos_upper = _sincos_interval(midpoint)
    assert cos_lower > 0 or cos_upper < 0
    if cos_lower > 0:
        return (
            sin_lower / cos_upper,
            sin_upper / cos_lower,
            (sin_lower, sin_upper, cos_lower, cos_upper),
        )
    quotients = (
        sin_lower / cos_lower,
        sin_lower / cos_upper,
        sin_upper / cos_lower,
        sin_upper / cos_upper,
    )
    return min(quotients), max(quotients), (
        sin_lower,
        sin_upper,
        cos_lower,
        cos_upper,
    )


def _proven_sign(lower: Fraction, upper: Fraction) -> int:
    if lower > 0:
        return 1
    if upper < 0:
        return -1
    return 0


def _actual_branch_rank(y_bits: int, x_bits: int) -> int:
    signs = (-1 if y_bits & SIGN_BIT else 1, -1 if x_bits & SIGN_BIT else 1)
    return {(-1, -1): 0, (-1, 1): 1, (1, 1): 2, (1, -1): 3}[signs]


def _boundary_branch_rank(
    midpoint: Fraction,
    sincos: tuple[Fraction, Fraction, Fraction, Fraction],
) -> int:
    sin_sign = _proven_sign(sincos[0], sincos[1])
    cos_sign = _proven_sign(sincos[2], sincos[3])
    assert sin_sign != 0
    assert cos_sign != 0
    if midpoint > 0 and sin_sign < 0 and cos_sign < 0:
        return 4
    if midpoint < 0 and sin_sign > 0 and cos_sign < 0:
        return -1
    return {
        (-1, -1): 0,
        (-1, 1): 1,
        (1, 1): 2,
        (1, -1): 3,
    }[sin_sign, cos_sign]


def _compare_angle_to_midpoint(
    y_bits: int, x_bits: int, midpoint: Fraction
) -> int:
    tan_lower, tan_upper, sincos = _tangent_interval(midpoint)
    actual_rank = _actual_branch_rank(y_bits, x_bits)
    boundary_rank = _boundary_branch_rank(midpoint, sincos)
    result = 0
    if actual_rank < boundary_rank:
        result = -1
    elif actual_rank > boundary_rank:
        result = 1
    else:
        ratio = _binary64_fraction(y_bits) / _binary64_fraction(x_bits)
        if ratio > tan_upper:
            result = 1
        elif ratio < tan_lower:
            result = -1
    return result


def _candidate_harness_source() -> str:
    rows = ",\n".join(
        f"  {{UINT64_C(0x{y:016x}), UINT64_C(0x{x:016x})}}"
        for y, x in CERTIFICATE_PAIRS
    )
    return f"""#include \"math_transcendental_bits.h\"
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
    uint64_t output = UINT64_C(0);
    if (!malbolge_guest_math_atan2_unique_binary64(
            pairs[index].y, pairs[index].x, &output)) {{
      return 93;
    }}
    (void)printf("%016" PRIx64 "\\n", output);
    ++index;
  }}
  return index == UINT32_C({len(CERTIFICATE_PAIRS)}) ? 0 : 94;
}}
"""


def _certify_rounding_cell(y_bits: int, x_bits: int, output_bits: int) -> None:
    output = _binary64_fraction(output_bits)
    lower_midpoint = (_binary64_fraction(_next_down(output_bits)) + output) / 2
    upper_midpoint = (output + _binary64_fraction(_next_up(output_bits))) / 2
    assert _compare_angle_to_midpoint(y_bits, x_bits, lower_midpoint) == 1
    assert _compare_angle_to_midpoint(y_bits, x_bits, upper_midpoint) == -1


def test_forty_terms_enter_the_monotone_alternating_tail() -> None:
    """Bound every omitted sin/cos term ratio for abs(midpoint) below four."""
    assert Fraction(16, 82 * 83) < 1
    assert Fraction(16, 81 * 82) < 1


def test_atan2_candidate_cells_have_independent_midpoint_certificates(
    tmp_path: Path,
) -> None:
    """Certify 68 C candidates without an atan-based rounding oracle."""
    harness = tmp_path / "atan2-midpoint-candidates.c"
    executable = tmp_path / "atan2-midpoint-candidates"
    _ = harness.write_text(_candidate_harness_source(), encoding="utf-8")
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
    outputs = tuple(int(line, 16) for line in executed.stdout.splitlines())
    assert len(outputs) == len(CERTIFICATE_PAIRS)
    rows = zip(CERTIFICATE_PAIRS, outputs, strict=True)
    for (y_bits, x_bits), output_bits in rows:
        _certify_rounding_cell(y_bits, x_bits, output_bits)
