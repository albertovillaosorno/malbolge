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
#   - Q256/32 post-Taylor interval-width evidence for periodic sin/cos.
# - Must-Not:
#   - Treat the width ceiling as a binary64 midpoint-separation theorem.
# - Allows:
#   - Inputs: finite periodic binary64 values with magnitude at least four.
#   - Outputs: analytical Taylor-width bounds plus exact Q256 width checks.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Final table-maker separation obtains an independent quantitative proof.
# - Merge-When:
#   - A complete correctly-rounded sin/cos proof owns all error budgets.
# - Summary:
#   - Proves a 74-ulp Q256/32 computational interval ceiling.
# - Description:
#   - Integer width recurrence bounds every directed Taylor operation.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Retained corpus reaches 40 ulps while production rejects above 74.
#

"""Periodic Q256/32 sin/cos computational-width authority."""

from __future__ import annotations

from fractions import Fraction
from math import ceil
from math import factorial
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
SIGN = 1 << 63
FRACTION_MASK = (1 << 52) - 1
MASK64 = (1 << 64) - 1
INPUT_ULPS = 6
SQUARE_ULPS = 11
POLICY_TERMS = 32
CONTRACT_ULPS = 74
COS_ULPS = 71
OBSERVED_ULPS = 40
CASE_COUNT = 2048
SIN_WITNESS = 0x79410EF56AB915AC
COS_WITNESS = 0xC10999E0C64A54A1


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


def _divide_width(width: int, divisor: int) -> int:
    return ceil(Fraction(width, divisor) + 2) - 1


def _term_widths(*, cosine: bool) -> tuple[int, ...]:
    widths = [0 if cosine else INPUT_ULPS]
    for index in range(1, POLICY_TERMS + 1):
        product = widths[-1] + SQUARE_ULPS + 1
        left = 2 * index - 1 if cosine else 2 * index
        right = 2 * index if cosine else 2 * index + 1
        widths.append(_divide_width(_divide_width(product, left), right))
    return tuple(widths)


def _cases() -> tuple[int, ...]:
    state = 0x9E3779B97F4A7C15
    rows: list[int] = [
        0x4010000000000000,
        0x7FEFFFFFFFFFFFFF,
        SIN_WITNESS,
        COS_WITNESS,
    ]
    while len(rows) < CASE_COUNT + 4:
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
  uint32_t scratch[90];
  uint32_t index = UINT32_C(0);
  (void)printf("terms=%u limit=%u\\n",
               MALBOLGE_GUEST_MATH_PERIODIC_TAYLOR_TERMS,
               MALBOLGE_GUEST_MATH_PERIODIC_INTERVAL_ULPS_MAX);
  while (index < (uint32_t)(sizeof(cases) / sizeof(cases[0]))) {{
    MalbolgeGuestMathSincosInterval256 value;
    if (!malbolge_guest_math_sincos_range_interval256(
            cases[index], MALBOLGE_GUEST_MATH_PERIODIC_TAYLOR_TERMS,
            &value, scratch, UINT32_C(90))) return 80;
    (void)printf("%016" PRIx64 " %u ", cases[index], value.sin.lower_negative);
    print_fixed(&value.sin.lower);
    (void)printf(" %u ", value.sin.upper_negative);
    print_fixed(&value.sin.upper);
    (void)printf(" %u ", value.cos.lower_negative);
    print_fixed(&value.cos.lower);
    (void)printf(" %u ", value.cos.upper_negative);
    print_fixed(&value.cos.upper); (void)printf("\\n");
    ++index;
  }}
  return 0;
}}
"""


def _records(
    tmp_path: Path,
) -> tuple[tuple[int, int], tuple[tuple[str, ...], ...]]:
    source = tmp_path / "periodic-width.c"
    binary = tmp_path / "periodic-width"
    _ = source.write_text(_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG), "-std=c23", "-O2", "-ffreestanding", "-fno-builtin",
            "-Wall", "-Wextra", "-Wpedantic", "-Werror", f"-I{CONTRACT}",
            str(SOURCE), str(source), "-o", str(binary),
        ],
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    executed = _run([str(binary)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr
    lines = executed.stdout.splitlines()
    policy = tuple(int(field.split("=")[1]) for field in lines[0].split())
    rows = tuple(tuple(line.split()) for line in lines[1:])
    return (policy[0], policy[1]), rows


def _signed(magnitude: str, negative: str) -> int:
    value = int(magnitude, 16)
    return -value if int(negative) else value


def test_q256_32_width_recurrence_proves_contract() -> None:
    """Bound all directed term widths and the first omitted Taylor term."""
    # x < pi/4 < 4/5 and input width <= 6 ulps. Thus x^2 has exact width
    # below 48/5 ulps; directed product quantization makes that at most 11.
    assert Fraction(2 * 4 * INPUT_ULPS, 5) < SQUARE_ULPS - 1

    sin_widths = _term_widths(cosine=False)
    cos_widths = _term_widths(cosine=True)
    assert sum(sin_widths) == CONTRACT_ULPS
    assert sum(cos_widths) == COS_ULPS

    unit = Fraction(1, 1 << 256)
    sin_tail = Fraction(4, 5) ** 65 / factorial(65)
    cos_tail = Fraction(4, 5) ** 64 / factorial(64)
    assert sin_tail < unit
    assert cos_tail < unit


def test_q256_32_outputs_respect_computational_width_contract(
    tmp_path: Path,
) -> None:
    """Measure exact signed Q256 widths over all binary64 exponent bands."""
    policy, records = _records(tmp_path)
    assert policy == (POLICY_TERMS, CONTRACT_ULPS)
    assert len(records) == len(CASES)
    maximum = 0
    sin_witness = -1
    cos_witness = -1
    for bits, row in zip(CASES, records, strict=True):
        assert int(row[0], 16) == bits
        sin_width = _signed(row[4], row[3]) - _signed(row[2], row[1])
        cos_width = _signed(row[8], row[7]) - _signed(row[6], row[5])
        assert 0 <= sin_width <= CONTRACT_ULPS
        assert 0 <= cos_width <= CONTRACT_ULPS
        maximum = max(maximum, sin_width, cos_width)
        if bits == SIN_WITNESS:
            sin_witness = sin_width
        if bits == COS_WITNESS:
            cos_witness = cos_width
    assert sin_witness == OBSERVED_ULPS
    assert cos_witness == OBSERVED_ULPS
    assert maximum == OBSERVED_ULPS
