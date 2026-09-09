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
#   - Cell-margin evidence for atan2 ratios close to pi/2 and pi axes.
# - Must-Not:
#   - Treat bounded corpus observations as the full-domain height proof.
# - Allows:
#   - Inputs: exact binary64 axis-neighborhood vectors and Q256 pi bounds.
#   - Outputs: exact cutoff inequalities and special-path status checks.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - A stronger non-axis preproof gains independent mathematics.
# - Merge-When:
#   - The owning special-value contract absorbs all axis-neighborhood proofs.
# - Summary:
#   - Proves safe atan2 axis cells before the adaptive tangent comparator.
# - Description:
#   - Uses atan(r)<r and already-certified directed Q256 pi/4 constants.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Ratios above each certified cutoff remain kernel-required.
#

"""Exact axis-neighborhood atan2 preproofs."""

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
HIDDEN = 1 << 52
EXPONENT_MASK = 0x7FF
MIN_NORMAL_EXPONENT = -1022
MAX_NORMAL_EXPONENT = 1023
MAX_DIRECT_KERNEL_HEIGHT_BITS = 106
PI_OVER_TWO_BITS = 0x3FF921FB54442D18
PI_BITS = 0x400921FB54442D18
ONE_BITS = 0x3FF0000000000000
Q256_SCALE = 1 << 256
Q256_QUARTER_LOWER = int(
    "0c90fdaa22168c234c4c6628b80dc1cd129024e088a67cc74020bbea63b139b22", 16
)
Q256_QUARTER_UPPER = Q256_QUARTER_LOWER + 1
RESOLVED = 1
KERNEL_REQUIRED = 2
MAX_KERNEL_HEIGHT_BITS = 108


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


def _binary64(bits: int) -> Fraction:
    negative = bool(bits & SIGN)
    magnitude = bits & (SIGN - 1)
    exponent = (magnitude >> 52) & EXPONENT_MASK
    fraction = magnitude & FRACTION_MASK
    assert exponent != EXPONENT_MASK
    if exponent == 0:
        value = Fraction(fraction, 1 << 1074)
    else:
        significand = HIDDEN | fraction
        power = exponent - 1023 - 52
        value = (
            Fraction(significand << power, 1)
            if power >= 0
            else Fraction(significand, 1 << -power)
        )
    return -value if negative else value


def _cell(bits: int) -> tuple[Fraction, Fraction]:
    value = _binary64(bits)
    lower = (_binary64(bits - 1) + value) / 2
    upper = (value + _binary64(bits + 1)) / 2
    return lower, upper


def _power_bits(exponent: int) -> int:
    assert MIN_NORMAL_EXPONENT <= exponent <= MAX_NORMAL_EXPONENT
    return (exponent + 1023) << 52


def test_axis_cutoffs_fit_directed_pi_cells() -> None:
    """Fit atan(r)<r inside directed Q256 pi/2 and pi cell margins."""
    quarter_lower = Fraction(Q256_QUARTER_LOWER, Q256_SCALE)
    quarter_upper = Fraction(Q256_QUARTER_UPPER, Q256_SCALE)
    half_lower = quarter_lower * 2
    half_upper = quarter_upper * 2
    pi_lower = quarter_lower * 4
    half_cell_lower, half_cell_upper = _cell(PI_OVER_TWO_BITS)
    pi_cell_lower, _ = _cell(PI_BITS)
    assert half_lower - Fraction(1, 1 << 53) > half_cell_lower
    assert half_upper + Fraction(1, 1 << 55) < half_cell_upper
    assert pi_lower - Fraction(1, 1 << 52) > pi_cell_lower


def _vectors() -> tuple[tuple[int, int, int, int], ...]:
    p52 = _power_bits(-52)
    p53 = _power_bits(-53)
    p55 = _power_bits(-55)
    return (
        (p52, SIGN | ONE_BITS, RESOLVED, PI_BITS),
        (SIGN | p52, SIGN | ONE_BITS, RESOLVED, SIGN | PI_BITS),
        (p52 + 1, SIGN | ONE_BITS, KERNEL_REQUIRED, 0),
        (ONE_BITS, p53, RESOLVED, PI_OVER_TWO_BITS),
        (SIGN | ONE_BITS, p53, RESOLVED, SIGN | PI_OVER_TWO_BITS),
        (ONE_BITS, p53 + 1, KERNEL_REQUIRED, 0),
        (ONE_BITS, SIGN | p55, RESOLVED, PI_OVER_TWO_BITS),
        (SIGN | ONE_BITS, SIGN | p55, RESOLVED, SIGN | PI_OVER_TWO_BITS),
        (ONE_BITS, SIGN | (p55 + 1), KERNEL_REQUIRED, 0),
    )


def _source() -> str:
    rows = ",\n".join(
        "".join(
            (
                f"  {{UINT64_C(0x{y:016x}), UINT64_C(0x{x:016x}), ",
                f"UINT32_C({status}), UINT64_C(0x{bits:016x})}}",
            )
        )
        for y, x, status, bits in _vectors()
    )
    return f"""#include \"math_transcendental_bits.h\"
#include <stdint.h>
typedef struct Vector {{
  uint64_t y_bits, x_bits;
  uint32_t status;
  uint64_t bits;
}} Vector;
static const Vector vectors[] = {{
{rows}
}};
int main(void) {{
  uint32_t index = UINT32_C(0);
  while (index < (uint32_t)(sizeof(vectors) / sizeof(vectors[0]))) {{
    const Vector *v = &vectors[index];
    const MalbolgeGuestMathSpecialResult result =
        malbolge_guest_math_atan2_special(v->y_bits, v->x_bits);
    if ((uint32_t)result.status != v->status || result.bits != v->bits) {{
      return 81;
    }}
    ++index;
  }}
  return 0;
}}
"""


def test_axis_cutoffs_match_c_special_path(tmp_path: Path) -> None:
    """Resolve each certified boundary and reject its next larger ratio."""
    harness = tmp_path / "atan2-axis-preproof.c"
    executable = tmp_path / "atan2-axis-preproof"
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


def test_axis_preproof_caps_kernel_ratio_height() -> None:
    """Derive the 108-bit post-special height ceiling from branch cutoffs."""
    significand_bits = 53
    # x>0, not swapped: existing zero-axis proof resolves exponent <= -54.
    zero_axis_delta_min = -53
    # x<0, not swapped: r < 2^-52 whenever exponent_delta <= -53.
    pi_axis_delta_min = -52
    # x>0, swapped: r < 2^-53 whenever exponent_delta <= -54.
    half_subtract_delta_min = -53
    # x<0, swapped: r < 2^-55 whenever exponent_delta <= -56.
    half_add_delta_min = -55
    direct_height = max(
        significand_bits - zero_axis_delta_min,
        significand_bits - pi_axis_delta_min,
    )
    reciprocal_height = max(
        significand_bits - half_subtract_delta_min,
        significand_bits - half_add_delta_min,
    )
    assert direct_height == MAX_DIRECT_KERNEL_HEIGHT_BITS
    assert reciprocal_height == MAX_KERNEL_HEIGHT_BITS
    assert max(direct_height, reciprocal_height) == MAX_KERNEL_HEIGHT_BITS
    tight_x = SIGN | (_power_bits(-55) + 1)
    tight_ratio = abs(_binary64(ONE_BITS) / _binary64(tight_x))
    tight_height = max(
        tight_ratio.numerator.bit_length(),
        tight_ratio.denominator.bit_length(),
    )
    assert tight_height == MAX_KERNEL_HEIGHT_BITS
