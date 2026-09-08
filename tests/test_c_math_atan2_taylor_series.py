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
#   - Variable-width sine/cosine Taylor enclosure evidence for atan2 refinement.
# - Must-Not:
#   - Use host sin/cos, pi constants, or fixed-Q transcendental oracles.
# - Allows:
#   - Inputs: exact nonnegative dyadics below four and an explicit term count.
#   - Outputs: signed fixed-point enclosures including the first omitted term.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Midpoint tangent comparison gains independently testable product policy.
# - Merge-When:
#   - Complete adaptive tangent refinement subsumes these series enclosures.
# - Summary:
#   - Certifies complete directed sine/cosine alternating Taylor summation.
# - Description:
#   - Exact Fraction partials and first omitted terms are independent authority.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Inputs outside [0,4), fewer than two terms, or short scratch fail closed.
#

"""Variable-width sine/cosine Taylor enclosure evidence for adaptive atan2."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import starmap
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
LIMB_COUNT = 8
FRACTION_LIMBS = 7
FRACTION_BITS = 32 * FRACTION_LIMBS
SCALE = 1 << FRACTION_BITS
TERM_COUNTS = (4, 8, 12, 16)
COSINE_TAG = "C"
VALUES = (
    Fraction(1, 8),
    Fraction(1),
    Fraction(5, 2),
    Fraction((4 * SCALE) - 1, SCALE),
)


@dataclass(frozen=True)
class SeriesCase:
    """One exact dyadic and Taylor depth fixture."""

    value: Fraction
    terms: int


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


def _cases() -> tuple[SeriesCase, ...]:
    return tuple(
        SeriesCase(value, terms) for value in VALUES for terms in TERM_COUNTS
    )


def _scaled_integer(value: Fraction) -> int:
    scaled = value * SCALE
    assert scaled.denominator == 1
    return scaled.numerator


def _c_limbs(integer: int) -> str:
    return ", ".join(
        f"UINT32_C(0x{((integer >> (32 * index)) & 0xFFFFFFFF):08x})"
        for index in range(LIMB_COUNT)
    )


def _case_block(position: int, case: SeriesCase) -> str:
    fixed = _scaled_integer(case.value)
    return f"""  {{
    uint32_t input[{LIMB_COUNT}] = {{{_c_limbs(fixed)}}};
    uint32_t lower[{LIMB_COUNT}];
    uint32_t upper[{LIMB_COUNT}];
    uint32_t scratch[{LIMB_COUNT * 10}];
    uint32_t lower_negative = UINT32_C(9);
    uint32_t upper_negative = UINT32_C(9);
    if (!malbolge_guest_math_fixed_sin_taylor_interval(
            input, input, UINT32_C({LIMB_COUNT}), UINT32_C({FRACTION_LIMBS}),
            UINT32_C({case.terms}), lower, &lower_negative, upper,
            &upper_negative, scratch, UINT32_C({LIMB_COUNT * 10}))) return 81;
    print_value("S", UINT32_C({position}), lower, lower_negative,
                upper, upper_negative);
    if (!malbolge_guest_math_fixed_cos_taylor_interval(
            input, input, UINT32_C({LIMB_COUNT}), UINT32_C({FRACTION_LIMBS}),
            UINT32_C({case.terms}), lower, &lower_negative, upper,
            &upper_negative, scratch, UINT32_C({LIMB_COUNT * 10}))) return 82;
    print_value("C", UINT32_C({position}), lower, lower_negative,
                upper, upper_negative);
  }}"""


def _harness_source() -> str:
    body = "\n".join(starmap(_case_block, enumerate(_cases())))
    return f"""#include "math_transcendental_bits.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

static void print_value(const char *tag, uint32_t position,
                        const uint32_t *lower, uint32_t lower_negative,
                        const uint32_t *upper, uint32_t upper_negative) {{
  uint32_t index = UINT32_C(0);
  (void)printf("%s %" PRIu32 " %" PRIu32, tag, position, lower_negative);
  while (index < UINT32_C({LIMB_COUNT})) {{
    (void)printf(" %08" PRIx32, lower[index]);
    ++index;
  }}
  (void)printf(" %" PRIu32, upper_negative);
  index = UINT32_C(0);
  while (index < UINT32_C({LIMB_COUNT})) {{
    (void)printf(" %08" PRIx32, upper[index]);
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


def _record_interval(record: list[str]) -> tuple[Fraction, Fraction]:
    lower_magnitude = _limbs_to_integer(record[3 : 3 + LIMB_COUNT])
    upper_sign_index = 3 + LIMB_COUNT
    upper_magnitude = _limbs_to_integer(record[upper_sign_index + 1 :])
    lower = Fraction(lower_magnitude, SCALE)
    upper = Fraction(upper_magnitude, SCALE)
    if int(record[2]):
        lower = -lower
    if int(record[upper_sign_index]):
        upper = -upper
    return lower, upper


def _series_bounds(
    value: Fraction, terms: int, *, cosine: bool
) -> tuple[Fraction, Fraction]:
    square = value * value
    term = Fraction(1) if cosine else value
    total = term
    for index in range(1, terms):
        divisor = (
            ((2 * index) - 1) * (2 * index)
            if cosine
            else (2 * index) * ((2 * index) + 1)
        )
        term = term * square / divisor
        total = total - term if index & 1 else total + term
    omitted_index = terms
    divisor = (
        ((2 * omitted_index) - 1) * (2 * omitted_index)
        if cosine
        else (2 * omitted_index) * ((2 * omitted_index) + 1)
    )
    omitted = term * square / divisor
    if terms & 1:
        return total - omitted, total
    return total, total + omitted


def _assert_series_record(record: list[str]) -> None:
    case = _cases()[int(record[1])]
    c_lower, c_upper = _record_interval(record)
    exact_lower, exact_upper = _series_bounds(
        case.value, case.terms, cosine=record[0] == COSINE_TAG
    )
    assert c_lower <= exact_lower <= exact_upper <= c_upper


def test_taylor_series_enclose_fraction_alternating_bounds(
    tmp_path: Path,
) -> None:
    """Enclose exact partial plus first-omitted bounds below four."""
    harness = tmp_path / "taylor-series.c"
    executable = tmp_path / "taylor-series"
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
    for record in records:
        _assert_series_record(record)


def _failure_harness_source() -> str:
    return r"""#include "math_transcendental_bits.h"
#include <stdint.h>

static int unchanged(const uint32_t *lower, uint32_t lower_negative,
                     const uint32_t *upper, uint32_t upper_negative) {
  return lower[0] == UINT32_C(0x11111111) &&
         lower_negative == UINT32_C(7) &&
         upper[0] == UINT32_C(0x22222222) &&
         upper_negative == UINT32_C(8);
}

int main(void) {
  uint32_t one[2] = {UINT32_C(0), UINT32_C(1)};
  uint32_t four[2] = {UINT32_C(0), UINT32_C(4)};
  uint32_t lower[2] = {UINT32_C(0x11111111), UINT32_C(0)};
  uint32_t upper[2] = {UINT32_C(0x22222222), UINT32_C(0)};
  uint32_t scratch[20];
  uint32_t lower_negative = UINT32_C(7);
  uint32_t upper_negative = UINT32_C(8);

  if (malbolge_guest_math_fixed_sin_taylor_interval(
          one, one, UINT32_C(2), UINT32_C(1), UINT32_C(1), lower,
          &lower_negative, upper, &upper_negative, scratch, UINT32_C(20)) ||
      !unchanged(lower, lower_negative, upper, upper_negative)) return 91;
  if (malbolge_guest_math_fixed_cos_taylor_interval(
          four, four, UINT32_C(2), UINT32_C(1), UINT32_C(4), lower,
          &lower_negative, upper, &upper_negative, scratch, UINT32_C(20)) ||
      !unchanged(lower, lower_negative, upper, upper_negative)) return 92;
  if (malbolge_guest_math_fixed_sin_taylor_interval(
          one, one, UINT32_C(2), UINT32_C(1), UINT32_C(4), lower,
          &lower_negative, upper, &upper_negative, scratch, UINT32_C(19)) ||
      !unchanged(lower, lower_negative, upper, upper_negative)) return 93;
  if (malbolge_guest_math_fixed_cos_taylor_interval(
          four, one, UINT32_C(2), UINT32_C(1), UINT32_C(4), lower,
          &lower_negative, upper, &upper_negative, scratch, UINT32_C(20)) ||
      !unchanged(lower, lower_negative, upper, upper_negative)) return 94;
  return 0;
}
"""


def test_taylor_series_invalid_inputs_do_not_publish(tmp_path: Path) -> None:
    """Reject shallow, out-of-range, undersized, and inverted requests."""
    harness = tmp_path / "taylor-series-failure.c"
    executable = tmp_path / "taylor-series-failure"
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
