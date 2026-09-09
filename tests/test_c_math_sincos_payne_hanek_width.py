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
#   - Uniform Q256 residual-width evidence for the active Payne-Hanek reducer.
# - Must-Not:
#   - Treat retained maximum width as a global final-rounding separation proof.
# - Allows:
#   - Inputs: finite raw binary64 words with magnitude at least four.
#   - Outputs: exact signed endpoint-width checks measured in Q256 ulps.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Post-Taylor interval-width propagation gains an independent theorem.
# - Merge-When:
#   - A complete sin/cos resource proof subsumes reduction-width evidence.
# - Summary:
#   - Proves a six-ulp reducer bound and checks a broad deterministic corpus.
# - Description:
#   - Q2176 and Q256 directed-rounding geometry give the analytical ceiling.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Retained corpus reaches four ulps; product rejects anything above six.
#

"""Uniform Payne-Hanek Q256 residual-width authority."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
SIGN = 1 << 63
EXPONENT_MASK = 0x7FF
FRACTION_MASK = (1 << 52) - 1
Q256_ULP = Fraction(1, 1 << 256)
Q2176_ULP = Fraction(1, 1 << 2176)
CONTRACT_ULPS = 6
OBSERVED_ULPS = 4
CASE_COUNT = 4096
MASK64 = (1 << 64) - 1
WIDTH_WITNESS = 0xCD22EEBE00FC8935
MANUAL = (
    0x4010000000000000,
    0x4010000000000001,
    0x43F0000000000000,
    0x7FEFFFFFFFFFFFFF,
    0xC010000000000000,
    0xFFEFFFFFFFFFFFFF,
    WIDTH_WITNESS,
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


def _cases() -> tuple[int, ...]:
    state = 0xD1B54A32D192ED03
    rows: list[int] = list(MANUAL)
    while len(rows) < len(MANUAL) + CASE_COUNT:
        state = (state * 6364136223846793005 + 1442695040888963407) & MASK64
        exponent = 1025 + ((state >> 52) % 1022)
        magnitude = (exponent << 52) | (state & FRACTION_MASK)
        rows.append(magnitude | (SIGN if state & 1 else 0))
    return tuple(rows)


CASES = _cases()


def _source() -> str:
    rows = ",\n".join(f"  UINT64_C(0x{bits:016x})" for bits in CASES)
    return f"""#include "math_transcendental_bits.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
static const uint64_t cases[] = {{
{rows}
}};
static void print_fixed(const MalbolgeGuestMathFixed256 *value) {{
  uint32_t limb = MALBOLGE_GUEST_MATH_FIXED_256_LIMBS;
  while (limb != UINT32_C(0)) {{
    --limb;
    (void)printf("%08" PRIx32, value->limbs[limb]);
  }}
}}
int main(void) {{
  uint32_t index = UINT32_C(0);
  (void)printf("limit=%u\\n",
               MALBOLGE_GUEST_MATH_PAYNE_HANEK_RESIDUAL_ULPS_MAX);
  while (index < (uint32_t)(sizeof(cases) / sizeof(cases[0]))) {{
    MalbolgeGuestMathSincosPayneHanek256 value;
    if (!malbolge_guest_math_sincos_payne_hanek_reduce256(
            cases[index], &value)) return 80;
    (void)printf("%016" PRIx64 " %u ", cases[index],
                 value.residual_lower_negative);
    print_fixed(&value.residual_lower);
    (void)printf(" %u ", value.residual_upper_negative);
    print_fixed(&value.residual_upper);
    (void)printf("\\n");
    ++index;
  }}
  return 0;
}}
"""


def _records(tmp_path: Path) -> tuple[int, tuple[tuple[str, ...], ...]]:
    source = tmp_path / "payne-width.c"
    binary = tmp_path / "payne-width"
    _ = source.write_text(_source(), encoding="utf-8")
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
            str(source),
            "-o",
            str(binary),
        ],
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    executed = _run([str(binary)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr
    lines = executed.stdout.splitlines()
    limit = int(lines[0].removeprefix("limit="))
    records = tuple(tuple(line.split()) for line in lines[1:])
    return limit, records


def _signed(magnitude: str, negative: str) -> int:
    value = int(magnitude, 16)
    return -value if int(negative) else value


def test_six_ulp_bound_follows_from_directed_geometry() -> None:
    """Derive the integer ceiling independently of retained reducer outputs."""
    # The active reciprocal table is one Q2176 ulp wide. Every finite binary64
    # magnitude is strictly below 2^1024, so its induced quotient interval is
    # strictly narrower than 2^-1152 and therefore far below one Q256 ulp.
    quotient_width = Fraction(1 << 1024, 1) * Q2176_ULP
    assert quotient_width < Q256_ULP

    # Floor(lower)/ceil(upper) of an interval narrower than one grid cell can
    # span at most two Q256 ulps. The certified pi/2 cell is two ulps wide,
    # pi/2 < 2, and nearest reduction keeps |fraction| <= 1/2.
    fraction_width = 2 * Q256_ULP
    half_pi_width = 2 * Q256_ULP
    exact_product_width = 2 * fraction_width + Fraction(1, 2) * half_pi_width
    assert exact_product_width == 5 * Q256_ULP

    # Exact width is strictly below that expression because pi/2 < 2. Directed
    # floor/ceil to the Q256 product grid can therefore span at most six cells.
    strict_grid_ceiling = exact_product_width + 2 * Q256_ULP
    assert strict_grid_ceiling == (CONTRACT_ULPS + 1) * Q256_ULP


def test_payne_hanek_residual_width_never_exceeds_contract(
    tmp_path: Path,
) -> None:
    """Check exact signed widths across edges and all exponent bands."""
    contract, records = _records(tmp_path)
    assert contract == CONTRACT_ULPS
    assert len(records) == len(CASES)
    maximum = 0
    witness_width = -1
    for bits, row in zip(CASES, records, strict=True):
        assert int(row[0], 16) == bits
        lower = _signed(row[2], row[1])
        upper = _signed(row[4], row[3])
        assert lower <= upper
        width = upper - lower
        assert width <= contract
        maximum = max(maximum, width)
        if bits == WIDTH_WITNESS:
            witness_width = width
    assert witness_width == OBSERVED_ULPS
    assert maximum == OBSERVED_ULPS
