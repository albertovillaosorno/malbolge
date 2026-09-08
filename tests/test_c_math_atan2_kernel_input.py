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
#   - Differential evidence for exact atan2 reduction and fixed-point intervals.
# - Must-Not:
#   - Use host atan2, floating division, or approximate expected values.
# - Allows:
#   - Inputs: deterministic finite nonzero binary64 word pairs.
#   - Outputs: native C agreement with exact Fraction-derived kernel geometry.
#   - Side effects: temporary C harness compilation and execution only.
# - Split-When:
#   - Public rounding or wider-precision fallback needs independent evidence.
# - Merge-When:
#   - Complete atan2 differential evidence subsumes exact input reduction.
# - Summary:
#   - Cross-checks atan2 geometry and interval enclosure over binary64 inputs.
# - Description:
#   - Expected geometry and interval bounds are reconstructed with Fraction.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Public atan2 remains unavailable; interval enclosure does not finalize
#     rounding.
#

"""Differential exact-ratio evidence for future binary64 atan2 kernels."""

from __future__ import annotations

from fractions import Fraction
from functools import cache
from itertools import starmap
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
SIGN_BIT = 1 << 63
FRACTION_MASK = (1 << 52) - 1
HIDDEN_BIT = 1 << 52
SIGNIFICAND_BITS = 53
EXPONENT_MASK = 0x7FF
MIN_NORMAL_EXPONENT = -1022
ATAN_MARGIN_MAX_EXPONENT = -27
ATAN_TOP_MARGIN_THRESHOLD = Fraction(727, 768)
ATAN_SCALED_MARGIN_THRESHOLD = Fraction(2, 3)
ALL_BITS = (1 << 64) - 1
VECTOR_COUNT = 512
LCG_MULTIPLIER = 6364136223846793005
LCG_INCREMENT = 1442695040888963407
LCG_SEED = 0x4154414E325F5631
SMALL_RATIO_LCG_SEED = 0x4154414E325F5352
SMALL_RATIO_VECTOR_COUNT = 512
ATAN2_STRESS_SEED = 0x4154414E325F5631
ATAN2_STRESS_PAIR_COUNT = 1_000_000
ATAN2_STRESS_FINITE_COUNT = 999_006
ATAN_INTERVAL_SAMPLE_STRIDE = 9
EXPECTED_SMALL_RATIO_RESOLVED = 511
EXPECTED_SMALL_RATIO_UNRESOLVED = 1
RESOLVED_STATUS = 1
KERNEL_REQUIRED_STATUS = 2
ATAN2_BASE_ZERO = 0
ATAN2_BASE_HALF_PI = 1
ATAN2_BASE_PI = 2
ATAN2_QUARTER_BASE_ZERO = 0
ATAN2_QUARTER_BASE_ONE = 1
ATAN2_QUARTER_BASE_TWO = 2
ATAN2_QUARTER_BASE_THREE = 3
ATAN2_QUARTER_BASE_FOUR = 4
ATAN2_RATIO_ADD = 1
ATAN2_RATIO_SUBTRACT = 2
ATAN_BASE_ZERO = 0
ATAN_BASE_QUARTER_PI = 1
ATAN_QUARTER_CUT = Fraction(169, 408)
ATAN_QUARTER_TRANSFORMED_CUT = Fraction(239, 577)
ATAN_QUARTER_MAX_SHIFT = 2
ATAN_QUARTER_LOWER_PRODUCT = 239 * 408
ATAN_QUARTER_UPPER_PRODUCT = 169 * 577
ATAN_SERIES_TARGET_BITS = 160
ATAN_SERIES_TERMS = 60
ATAN_SERIES_PREVIOUS_TERMS = ATAN_SERIES_TERMS - 1
ATAN_INTERVAL_EVALUATION_BITS = 160
ATAN2_INTEGER_ORACLE_BITS = 1152
ATAN_CUT_UPPER_FIXED = int(
    "6a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0b", 16
)
FIXED_INTERVAL_BITS = 192
PI_MACHIN_FIFTH_TERMS = 42
PI_MACHIN_239_TERMS = 12
QUARTER_PI_LOWER_FIXED = int(
    "c90fdaa22168c234c4c6628b80dc1cd129024e088a67cc74", 16
)
QUARTER_PI_UPPER_FIXED = QUARTER_PI_LOWER_FIXED + 1
ATAN_IDENTITY_MAX_BITS = 0x3E4C000000000000
ATAN_IDENTITY_MAX = Fraction(7, 1 << 29)
ONE_BITS = 0x3FF0000000000000
THREE_BITS = 0x4008000000000000
ATAN_TOP_MARGIN_PAIRS = (
    (0x3E4DA8FC2D9C711E, 0x3FFB9F8AF4448B26),
    (0x3E4DA8FC2D97A47C, 0x3FFB9F8AF4448B26),
)
ATAN_SCALED_MARGIN_PAIRS = (
    (0x3E39B3D6292B29EF, 0x3FF8805F49619E6E),
    (0x3E34AB4E736E3956, 0x3FF3C38BCBCE8B80),
)
EDGE_PAIRS = (
    (0x0000000000000001, 0x3FF0000000000000),
    (0x000FFFFFFFFFFFFF, 0x0010000000000000),
    (0x0010000000000000, 0x7FEFFFFFFFFFFFFF),
    (0x3FF0000000000000, 0x3FF0000000000000),
    (0x4000000000000000, 0x3FF0000000000000),
    (0xBFF8000000000000, 0x4004000000000000),
    (0x7FEFFFFFFFFFFFFF, 0x0000000000000001),
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


def _finite_nonzero(bits: int) -> bool:
    magnitude = bits & ~SIGN_BIT
    return magnitude != 0 and (magnitude >> 52) & EXPONENT_MASK != EXPONENT_MASK


def _deterministic_pairs() -> tuple[tuple[int, int], ...]:
    state = LCG_SEED
    pairs = list(EDGE_PAIRS)
    while len(pairs) < VECTOR_COUNT + len(EDGE_PAIRS):
        state = (state * LCG_MULTIPLIER + LCG_INCREMENT) & ALL_BITS
        y_bits = state
        state = (state * LCG_MULTIPLIER + LCG_INCREMENT) & ALL_BITS
        x_bits = state
        if _finite_nonzero(y_bits) and _finite_nonzero(x_bits):
            pairs.append((y_bits, x_bits))
    return tuple(pairs)


def _raw_fraction(bits: int) -> Fraction:
    magnitude = bits & ~SIGN_BIT
    raw_exponent = (magnitude >> 52) & EXPONENT_MASK
    fraction = magnitude & FRACTION_MASK
    if raw_exponent == 0:
        return Fraction(fraction, 1 << 1074)
    significand = HIDDEN_BIT | fraction
    exponent = raw_exponent - 1023 - 52
    if exponent >= 0:
        return Fraction(significand << exponent, 1)
    return Fraction(significand, 1 << -exponent)


def _normalized(bits: int) -> tuple[int, int]:
    magnitude = bits & ~SIGN_BIT
    raw_exponent = (magnitude >> 52) & EXPONENT_MASK
    significand = magnitude & FRACTION_MASK
    if raw_exponent == 0:
        exponent = -1074
    else:
        significand |= HIDDEN_BIT
        exponent = raw_exponent - 1023 - 52
    while significand.bit_length() < SIGNIFICAND_BITS:
        significand <<= 1
        exponent -= 1
    return significand, exponent


def _ordered_bits(y_bits: int, x_bits: int) -> tuple[int, int, int]:
    y_magnitude = y_bits & ~SIGN_BIT
    x_magnitude = x_bits & ~SIGN_BIT
    if y_magnitude > x_magnitude:
        return x_bits, y_bits, 1
    return y_bits, x_bits, 0


def _geometry_ratio(geometry: tuple[int, int, int, int, int, int]) -> Fraction:
    ratio = Fraction(geometry[0], geometry[1])
    if geometry[2] >= 0:
        return ratio * (1 << geometry[2])
    return ratio / (1 << -geometry[2])


def _expected(y_bits: int, x_bits: int) -> tuple[int, int, int, int, int, int]:
    numerator_bits, denominator_bits, swapped = _ordered_bits(y_bits, x_bits)
    numerator = _normalized(numerator_bits)
    denominator = _normalized(denominator_bits)
    result = (
        numerator[0],
        denominator[0],
        numerator[1] - denominator[1],
        swapped,
        int(bool(y_bits & SIGN_BIT)),
        int(bool(x_bits & SIGN_BIT)),
    )
    exact_ratio = min(_raw_fraction(y_bits), _raw_fraction(x_bits)) / max(
        _raw_fraction(y_bits), _raw_fraction(x_bits)
    )
    assert _geometry_ratio(result) == exact_ratio
    assert exact_ratio <= 1
    return result


def _floor_log2(value: Fraction) -> int:
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    if exponent >= 0:
        power = Fraction(1 << exponent, 1)
    else:
        power = Fraction(1, 1 << -exponent)
    return exponent - 1 if value < power else exponent


def _round_quotient(numerator: int, denominator: int) -> int:
    quotient, remainder = divmod(numerator, denominator)
    doubled = remainder * 2
    if doubled > denominator or (doubled == denominator and quotient & 1):
        quotient += 1
    return quotient


def _ceil_quotient(numerator: int, denominator: int) -> int:
    quotient, remainder = divmod(numerator, denominator)
    return quotient + int(remainder != 0)


def _nearest_binary64_bits(value: Fraction) -> int:
    exponent = _floor_log2(value)
    if exponent < MIN_NORMAL_EXPONENT:
        return _round_quotient(value.numerator << 1074, value.denominator)
    shift = 52 - exponent
    if shift >= 0:
        significand = _round_quotient(
            value.numerator << shift, value.denominator
        )
    else:
        significand = _round_quotient(
            value.numerator, value.denominator << -shift
        )
    if significand == 1 << 53:
        significand >>= 1
        exponent += 1
    return ((exponent + 1023) << 52) | (significand - HIDDEN_BIT)


def _expected_atan_reduction(
    y_bits: int, x_bits: int
) -> tuple[int, int, int, int, int]:
    geometry = _expected(y_bits, x_bits)
    ratio = _geometry_ratio(geometry)
    if ratio < ATAN_QUARTER_CUT:
        return (
            geometry[0],
            geometry[1],
            geometry[2],
            ATAN_BASE_ZERO,
            ATAN2_RATIO_ADD,
        )
    shift = -geometry[2]
    assert 0 <= shift <= ATAN_QUARTER_MAX_SHIFT
    denominator = geometry[1] << shift
    result = (
        denominator - geometry[0],
        denominator + geometry[0],
        0,
        ATAN_BASE_QUARTER_PI,
        ATAN2_RATIO_SUBTRACT,
    )
    residual = Fraction(result[0], result[1])
    transformed = (1 - ratio) / (1 + ratio)
    assert (residual.numerator, residual.denominator) == (
        transformed.numerator,
        transformed.denominator,
    )
    assert residual <= ATAN_QUARTER_TRANSFORMED_CUT < ATAN_QUARTER_CUT
    return result


def _atan_reduction_row(y_bits: int, x_bits: int) -> str:
    expected = _expected_atan_reduction(y_bits, x_bits)
    return (
        "  {"
        f"UINT64_C(0x{y_bits:016x}), UINT64_C(0x{x_bits:016x}), "
        f"UINT64_C(0x{expected[0]:016x}), UINT64_C(0x{expected[1]:016x}), "
        f"INT32_C({expected[2]}), UINT32_C({expected[3]}), "
        f"UINT32_C({expected[4]})"
        "}"
    )


def _atan_reduction_harness_source() -> str:
    rows = ",\n".join(starmap(_atan_reduction_row, _deterministic_pairs()))
    return f"""#include "math_transcendental_bits.h"
#include <stdint.h>
typedef struct Vector {{
  uint64_t y_bits, x_bits, numerator, denominator;
  int32_t exponent_delta;
  uint32_t base, operation;
}} Vector;
static const Vector vectors[] = {{
{rows}
}};
int main(void) {{
  uint32_t i = 0;
  while (i < (uint32_t)(sizeof(vectors) / sizeof(vectors[0]))) {{
    MalbolgeGuestMathAtan2KernelInput input;
    MalbolgeGuestMathAtanKernelReduction reduction;
    const Vector *v = &vectors[i];
    if (!malbolge_guest_math_atan2_kernel_input(v->y_bits, v->x_bits, &input) ||
        !malbolge_guest_math_atan_kernel_reduction(&input, &reduction) ||
        reduction.residual.numerator != v->numerator ||
        reduction.residual.denominator != v->denominator ||
        reduction.residual.exponent_delta != v->exponent_delta ||
        (uint32_t)reduction.base != v->base ||
        (uint32_t)reduction.ratio_operation != v->operation) {{
      return 30;
    }}
    ++i;
  }}
  return 0;
}}
"""


def _base_quarters(base: int) -> int:
    if base == ATAN2_BASE_HALF_PI:
        return ATAN2_QUARTER_BASE_TWO
    if base == ATAN2_BASE_PI:
        return ATAN2_QUARTER_BASE_FOUR
    return ATAN2_QUARTER_BASE_ZERO


def _expected_atan2_kernel_plan(
    y_bits: int, x_bits: int
) -> tuple[int, int, int, int, int, int]:
    geometry = _expected(y_bits, x_bits)
    base, operation, negative = _reconstruction_fields(
        geometry[3], geometry[4], geometry[5]
    )
    reduction = _expected_atan_reduction(y_bits, x_bits)
    quarters = _base_quarters(base)
    if reduction[3] == ATAN_BASE_QUARTER_PI:
        if operation == ATAN2_RATIO_ADD:
            quarters += 1
            operation = ATAN2_RATIO_SUBTRACT
        else:
            quarters -= 1
            operation = ATAN2_RATIO_ADD
    assert ATAN2_QUARTER_BASE_ZERO <= quarters <= ATAN2_QUARTER_BASE_FOUR
    return (
        reduction[0],
        reduction[1],
        reduction[2],
        quarters,
        operation,
        negative,
    )


def _atan2_plan_row(y_bits: int, x_bits: int) -> str:
    expected = _expected_atan2_kernel_plan(y_bits, x_bits)
    return (
        "  {"
        f"UINT64_C(0x{y_bits:016x}), UINT64_C(0x{x_bits:016x}), "
        f"UINT64_C(0x{expected[0]:016x}), UINT64_C(0x{expected[1]:016x}), "
        f"INT32_C({expected[2]}), UINT32_C({expected[3]}), "
        f"UINT32_C({expected[4]}), UINT32_C({expected[5]})"
        "}"
    )


def _atan2_plan_harness_source() -> str:
    rows = ",\n".join(starmap(_atan2_plan_row, _deterministic_pairs()))
    return f"""#include "math_transcendental_bits.h"
#include <stdint.h>
typedef struct Vector {{
  uint64_t y_bits, x_bits, numerator, denominator;
  int32_t exponent_delta;
  uint32_t quarter_pi_base, operation, negative;
}} Vector;
static const Vector vectors[] = {{
{rows}
}};
int main(void) {{
  uint32_t i = 0;
  while (i < (uint32_t)(sizeof(vectors) / sizeof(vectors[0]))) {{
    MalbolgeGuestMathAtan2KernelPlan plan;
    const Vector *v = &vectors[i];
    if (!malbolge_guest_math_atan2_kernel_plan(v->y_bits, v->x_bits, &plan) ||
        plan.residual.numerator != v->numerator ||
        plan.residual.denominator != v->denominator ||
        plan.residual.exponent_delta != v->exponent_delta ||
        (uint32_t)plan.quarter_pi_base != v->quarter_pi_base ||
        (uint32_t)plan.ratio_operation != v->operation ||
        plan.negative != v->negative) {{
      return 40;
    }}
    ++i;
  }}
  return 0;
}}
"""


def _exact_ratio_fraction(
    numerator: int, denominator: int, exponent: int
) -> Fraction:
    value = Fraction(numerator, denominator)
    if exponent >= 0:
        return value * (1 << exponent)
    return value / (1 << -exponent)


def _fixed_192_interval(value: Fraction) -> tuple[int, int]:
    scaled = value * (1 << FIXED_INTERVAL_BITS)
    lower, remainder = divmod(scaled.numerator, scaled.denominator)
    return lower, lower if remainder == 0 else lower + 1


def _fixed_192_limbs(value: int) -> tuple[int, ...]:
    return tuple((value >> (32 * index)) & 0xFFFFFFFF for index in range(7))


def _fixed_ratio_row(y_bits: int, x_bits: int) -> str:
    plan = _expected_atan2_kernel_plan(y_bits, x_bits)
    residual = _exact_ratio_fraction(plan[0], plan[1], plan[2])
    lower, upper = _fixed_192_interval(residual)
    lower_limbs = ", ".join(
        f"UINT32_C(0x{limb:08x})" for limb in _fixed_192_limbs(lower)
    )
    upper_limbs = ", ".join(
        f"UINT32_C(0x{limb:08x})" for limb in _fixed_192_limbs(upper)
    )
    return (
        f"  {{UINT64_C(0x{y_bits:016x}), UINT64_C(0x{x_bits:016x}), "
        f"{{{lower_limbs}}}, {{{upper_limbs}}}}}"
    )


def _fixed_ratio_harness_source() -> str:
    rows = ",\n".join(starmap(_fixed_ratio_row, _deterministic_pairs()))
    return f"""#include "math_transcendental_bits.h"
#include <stdint.h>
typedef struct Vector {{
  uint64_t y_bits, x_bits;
  uint32_t lower[7], upper[7];
}} Vector;
static const Vector vectors[] = {{
{rows}
}};
static int equal_fixed(const MalbolgeGuestMathFixed192 *value,
                       const uint32_t expected[7]) {{
  uint32_t index = 0;
  while (index < MALBOLGE_GUEST_MATH_FIXED_192_LIMBS) {{
    if (value->limbs[index] != expected[index]) return 0;
    ++index;
  }}
  return 1;
}}
int main(void) {{
  uint32_t i = 0;
  while (i < (uint32_t)(sizeof(vectors) / sizeof(vectors[0]))) {{
    MalbolgeGuestMathAtan2KernelPlan plan;
    MalbolgeGuestMathFixed192Interval interval;
    const Vector *v = &vectors[i];
    if (!malbolge_guest_math_atan2_kernel_plan(v->y_bits, v->x_bits, &plan) ||
        !malbolge_guest_math_exact_ratio_interval(&plan.residual, &interval) ||
        !equal_fixed(&interval.lower, v->lower) ||
        !equal_fixed(&interval.upper, v->upper)) {{
      return 50;
    }}
    ++i;
  }}
  return 0;
}}
"""


@cache
def _atan_exact_series_interval(value: Fraction) -> tuple[Fraction, Fraction]:
    total = Fraction(0)
    power = value
    square = value * value
    for index in range(ATAN_SERIES_TERMS):
        term = power / ((2 * index) + 1)
        total = total + term if index % 2 == 0 else total - term
        power *= square
    return total, total + (power / ((2 * ATAN_SERIES_TERMS) + 1))


def _integer_bounds(value: Fraction) -> tuple[int, int]:
    scaled = value * (1 << FIXED_INTERVAL_BITS)
    floor, remainder = divmod(scaled.numerator, scaled.denominator)
    return floor, floor if remainder == 0 else floor + 1


def _atan_interval_pairs() -> tuple[tuple[int, int], ...]:
    pairs = _deterministic_pairs()
    edge_count = len(EDGE_PAIRS)
    return pairs[:edge_count] + pairs[edge_count::ATAN_INTERVAL_SAMPLE_STRIDE]


def _atan_interval_limits(
    y_bits: int, x_bits: int
) -> tuple[int, int, int, int]:
    plan = _expected_atan2_kernel_plan(y_bits, x_bits)
    residual = _exact_ratio_fraction(plan[0], plan[1], plan[2])
    exact_lower, exact_upper = _atan_exact_series_interval(residual)
    lower_floor = _integer_bounds(exact_lower)[0]
    upper_ceil = _integer_bounds(exact_upper)[1]
    slack = 1 << (FIXED_INTERVAL_BITS - ATAN_INTERVAL_EVALUATION_BITS)
    return (
        max(0, lower_floor - slack),
        lower_floor,
        upper_ceil,
        upper_ceil + slack,
    )


def _fixed_array_literal(value: int) -> str:
    limbs = _fixed_192_limbs(value)
    encoded = ", ".join(f"UINT32_C(0x{limb:08x})" for limb in limbs)
    return "{" + encoded + "}"


def _atan_interval_row(y_bits: int, x_bits: int) -> str:
    limits = _atan_interval_limits(y_bits, x_bits)
    encoded = [_fixed_array_literal(value) for value in limits]
    return (
        f"  {{UINT64_C(0x{y_bits:016x}), UINT64_C(0x{x_bits:016x}), "
        + ", ".join(encoded)
        + "}"
    )


def _atan_interval_harness_source() -> str:
    rows = ",\n".join(starmap(_atan_interval_row, _atan_interval_pairs()))
    return f"""#include "math_transcendental_bits.h"
#include <stdint.h>
typedef struct Vector {{
  uint64_t y_bits, x_bits;
  uint32_t lower_min[7], lower_floor[7], upper_ceil[7], upper_max[7];
}} Vector;
static const Vector vectors[] = {{
{rows}
}};
static int compare_fixed(const MalbolgeGuestMathFixed192 *value,
                         const uint32_t expected[7]) {{
  uint32_t index = MALBOLGE_GUEST_MATH_FIXED_192_LIMBS;
  while (index != 0) {{
    --index;
    if (value->limbs[index] < expected[index]) return -1;
    if (value->limbs[index] > expected[index]) return 1;
  }}
  return 0;
}}
int main(void) {{
  uint32_t i = 0;
  while (i < (uint32_t)(sizeof(vectors) / sizeof(vectors[0]))) {{
    MalbolgeGuestMathAtan2KernelPlan plan;
    MalbolgeGuestMathFixed192Interval interval;
    const Vector *v = &vectors[i];
    if (!malbolge_guest_math_atan2_kernel_plan(v->y_bits, v->x_bits, &plan) ||
        !malbolge_guest_math_atan_residual_interval(
            &plan.residual, &interval) ||
        compare_fixed(&interval.lower, v->lower_min) < 0 ||
        compare_fixed(&interval.lower, v->lower_floor) > 0 ||
        compare_fixed(&interval.upper, v->upper_ceil) < 0 ||
        compare_fixed(&interval.upper, v->upper_max) > 0) {{
      return 60;
    }}
    ++i;
  }}
  return 0;
}}
"""


def _atan2_exact_interval(
    y_bits: int, x_bits: int
) -> tuple[Fraction, Fraction, int]:
    plan = _expected_atan2_kernel_plan(y_bits, x_bits)
    quarter_lower, quarter_upper = _quarter_pi_machin_interval()
    atan_lower, atan_upper = _atan_exact_series_interval(
        _exact_ratio_fraction(plan[0], plan[1], plan[2])
    )
    base_lower = plan[3] * quarter_lower
    base_upper = plan[3] * quarter_upper
    if plan[4] == ATAN2_RATIO_ADD:
        return base_lower + atan_lower, base_upper + atan_upper, plan[5]
    return base_lower - atan_upper, base_upper - atan_lower, plan[5]


def _atan2_interval_limits(
    y_bits: int, x_bits: int
) -> tuple[int, int, int, int, int]:
    exact_lower, exact_upper, negative = _atan2_exact_interval(y_bits, x_bits)
    lower_floor = _integer_bounds(exact_lower)[0]
    upper_ceil = _integer_bounds(exact_upper)[1]
    evaluation_slack = 1 << (
        FIXED_INTERVAL_BITS - ATAN_INTERVAL_EVALUATION_BITS
    )
    total_slack = (
        (1 << (FIXED_INTERVAL_BITS - ATAN_SERIES_TARGET_BITS))
        + evaluation_slack
        + ATAN2_QUARTER_BASE_FOUR
    )
    return (
        max(0, lower_floor - total_slack),
        lower_floor,
        upper_ceil,
        upper_ceil + total_slack,
        negative,
    )


def _atan2_interval_row(y_bits: int, x_bits: int) -> str:
    limits = _atan2_interval_limits(y_bits, x_bits)
    encoded = [_fixed_array_literal(value) for value in limits[:4]]
    return (
        f"  {{UINT64_C(0x{y_bits:016x}), UINT64_C(0x{x_bits:016x}), "
        + ", ".join(encoded)
        + f", UINT32_C({limits[4]})}}"
    )


def _atan2_interval_harness_source() -> str:
    rows = ",\n".join(starmap(_atan2_interval_row, _atan_interval_pairs()))
    return f"""#include "math_transcendental_bits.h"
#include <stdint.h>
typedef struct Vector {{
  uint64_t y_bits, x_bits;
  uint32_t lower_min[7], lower_floor[7], upper_ceil[7], upper_max[7];
  uint32_t negative;
}} Vector;
static const Vector vectors[] = {{
{rows}
}};
static int compare_fixed(const MalbolgeGuestMathFixed192 *value,
                         const uint32_t expected[7]) {{
  uint32_t index = MALBOLGE_GUEST_MATH_FIXED_192_LIMBS;
  while (index != 0) {{
    --index;
    if (value->limbs[index] < expected[index]) return -1;
    if (value->limbs[index] > expected[index]) return 1;
  }}
  return 0;
}}
int main(void) {{
  uint32_t i = 0;
  while (i < (uint32_t)(sizeof(vectors) / sizeof(vectors[0]))) {{
    MalbolgeGuestMathAtan2Interval interval;
    const Vector *v = &vectors[i];
    if (!malbolge_guest_math_atan2_interval(v->y_bits, v->x_bits, &interval) ||
        compare_fixed(&interval.magnitude.lower, v->lower_min) < 0 ||
        compare_fixed(&interval.magnitude.lower, v->lower_floor) > 0 ||
        compare_fixed(&interval.magnitude.upper, v->upper_ceil) < 0 ||
        compare_fixed(&interval.magnitude.upper, v->upper_max) > 0 ||
        interval.negative != v->negative) {{
      return 70;
    }}
    ++i;
  }}
  return 0;
}}
"""


def _integer_oracle_scaled_bounds(value: Fraction) -> tuple[int, int]:
    numerator = value.numerator << ATAN2_INTEGER_ORACLE_BITS
    denominator = value.denominator
    return (
        numerator // denominator,
        _ceil_quotient(numerator, denominator),
    )


@cache
def _quarter_pi_integer_oracle_bounds() -> tuple[int, int]:
    lower, upper = _quarter_pi_machin_interval()
    lower_floor, _ = _integer_oracle_scaled_bounds(lower)
    _, upper_ceil = _integer_oracle_scaled_bounds(upper)
    return lower_floor, upper_ceil


def _integer_oracle_term_bounds(
    numerator: int, denominator: int, divisor: int
) -> tuple[int, int]:
    scaled_numerator = numerator << ATAN2_INTEGER_ORACLE_BITS
    divided_denominator = denominator * divisor
    return (
        scaled_numerator // divided_denominator,
        _ceil_quotient(scaled_numerator, divided_denominator),
    )


def _atan_integer_oracle_bounds(value: Fraction) -> tuple[int, int]:
    power_numerator = value.numerator
    power_denominator = value.denominator
    square_numerator = power_numerator * power_numerator
    square_denominator = power_denominator * power_denominator
    lower = 0
    upper = 0

    for index in range(ATAN_SERIES_TERMS):
        term_floor, term_ceil = _integer_oracle_term_bounds(
            power_numerator, power_denominator, (2 * index) + 1
        )
        if index & 1:
            lower -= term_ceil
            upper -= term_floor
        else:
            lower += term_floor
            upper += term_ceil
        power_numerator *= square_numerator
        power_denominator *= square_denominator

    upper += _integer_oracle_term_bounds(
        power_numerator,
        power_denominator,
        (2 * ATAN_SERIES_TERMS) + 1,
    )[1]
    return lower, upper


def _atan2_integer_oracle_interval(
    y_bits: int, x_bits: int
) -> tuple[int, int, int]:
    plan = _expected_atan2_kernel_plan(y_bits, x_bits)
    residual = _exact_ratio_fraction(plan[0], plan[1], plan[2])
    atan_lower, atan_upper = _atan_integer_oracle_bounds(residual)
    quarter_lower, quarter_upper = _quarter_pi_integer_oracle_bounds()
    base_lower = plan[3] * quarter_lower
    base_upper = plan[3] * quarter_upper
    if plan[4] == ATAN2_RATIO_ADD:
        return base_lower + atan_lower, base_upper + atan_upper, plan[5]
    return base_lower - atan_upper, base_upper - atan_lower, plan[5]


def _integer_oracle_unique_rounding_row(y_bits: int, x_bits: int) -> str:
    lower, upper, negative = _atan2_integer_oracle_interval(y_bits, x_bits)
    scale = 1 << ATAN2_INTEGER_ORACLE_BITS
    lower_bits = _nearest_binary64_bits(Fraction(lower, scale))
    upper_bits = _nearest_binary64_bits(Fraction(upper, scale))
    assert lower_bits == upper_bits
    expected = lower_bits | (SIGN_BIT if negative else 0)
    return (
        f"  {{UINT64_C(0x{y_bits:016x}), UINT64_C(0x{x_bits:016x}), "
        f"UINT64_C(0x{expected:016x})}}"
    )


def _integer_oracle_unique_rounding_harness_source() -> str:
    pairs = _deterministic_pairs()
    rows = ",\n".join(starmap(_integer_oracle_unique_rounding_row, pairs))
    return f"""#include "math_transcendental_bits.h"
#include <stdint.h>
typedef struct Vector {{ uint64_t y_bits, x_bits, expected_bits; }} Vector;
static const Vector vectors[] = {{
{rows}
}};
int main(void) {{
  uint32_t i = 0;
  while (i < (uint32_t)(sizeof(vectors) / sizeof(vectors[0]))) {{
    uint64_t bits = UINT64_C(0xdeadbeefdeadbeef);
    const Vector *v = &vectors[i];
    if (!malbolge_guest_math_atan2_unique_binary64(
            v->y_bits, v->x_bits, &bits) ||
        bits != v->expected_bits) {{
      return 83;
    }}
    ++i;
  }}
  return i == UINT32_C({len(pairs)}) ? 0 : 84;
}}
"""


def _unique_rounding_row(y_bits: int, x_bits: int) -> str:
    lower, upper, negative = _atan2_exact_interval(y_bits, x_bits)
    lower_bits = _nearest_binary64_bits(lower)
    upper_bits = _nearest_binary64_bits(upper)
    assert lower_bits == upper_bits
    expected = lower_bits | (SIGN_BIT if negative else 0)
    return (
        f"  {{UINT64_C(0x{y_bits:016x}), UINT64_C(0x{x_bits:016x}), "
        f"UINT64_C(0x{expected:016x})}}"
    )


def _unique_rounding_harness_source() -> str:
    rows = ",\n".join(starmap(_unique_rounding_row, _atan_interval_pairs()))
    return f"""#include "math_transcendental_bits.h"
#include <stdint.h>
typedef struct Vector {{ uint64_t y_bits, x_bits, expected_bits; }} Vector;
static const Vector vectors[] = {{
{rows}
}};
int main(void) {{
  uint32_t i = 0, resolved = 0;
  while (i < (uint32_t)(sizeof(vectors) / sizeof(vectors[0]))) {{
    uint64_t bits = UINT64_C(0xdeadbeefdeadbeef);
    const Vector *v = &vectors[i];
    if (malbolge_guest_math_atan2_unique_binary64(
            v->y_bits, v->x_bits, &bits)) {{
      if (bits != v->expected_bits) return 80;
      ++resolved;
    }} else if (bits != UINT64_C(0xdeadbeefdeadbeef)) {{
      return 81;
    }}
    ++i;
  }}
  return resolved == UINT32_C(64) ? 0 : 82;
}}
"""


def _stress_harness_source() -> str:
    return f"""#include \"math_transcendental_bits.h\"
#include <stdint.h>
#define SIGN UINT64_C(0x8000000000000000)
#define EXPONENT UINT64_C(0x7ff0000000000000)
static uint64_t next_word(uint64_t *state) {{
  *state = *state * UINT64_C({LCG_MULTIPLIER}) + UINT64_C({LCG_INCREMENT});
  return *state;
}}
static int finite_nonzero(uint64_t bits) {{
  const uint64_t magnitude = bits & ~SIGN;
  return magnitude != UINT64_C(0) && (magnitude & EXPONENT) != EXPONENT;
}}
int main(void) {{
  uint64_t state = UINT64_C(0x{ATAN2_STRESS_SEED:016x});
  uint32_t index = UINT32_C(0);
  uint32_t finite = UINT32_C(0);
  uint32_t resolved = UINT32_C(0);
  while (index < UINT32_C({ATAN2_STRESS_PAIR_COUNT})) {{
    const uint64_t y_bits = next_word(&state);
    const uint64_t x_bits = next_word(&state);
    uint64_t output_bits = UINT64_C(0);
    if (finite_nonzero(y_bits) && finite_nonzero(x_bits)) {{
      ++finite;
      if (malbolge_guest_math_atan2_unique_binary64(
              y_bits, x_bits, &output_bits)) {{
        ++resolved;
      }}
    }}
    ++index;
  }}
  return finite == UINT32_C({ATAN2_STRESS_FINITE_COUNT}) && resolved == finite
             ? 0
             : 90;
}}
"""


def _small_ratio_pairs() -> tuple[tuple[int, int], ...]:
    state = SMALL_RATIO_LCG_SEED
    pairs = [
        (ATAN_IDENTITY_MAX_BITS, ONE_BITS),
        (SIGN_BIT | ATAN_IDENTITY_MAX_BITS, ONE_BITS),
        (ATAN_IDENTITY_MAX_BITS + 1, ONE_BITS),
        (1, ONE_BITS),
        (ONE_BITS, 0x41A0000000000000),
    ]
    while len(pairs) < SMALL_RATIO_VECTOR_COUNT:
        state = (state * LCG_MULTIPLIER + LCG_INCREMENT) & ALL_BITS
        magnitude = 1 + state % ATAN_IDENTITY_MAX_BITS
        y_bits = magnitude | (SIGN_BIT if state & 1 else 0)
        x_bits = ONE_BITS if state & 2 else THREE_BITS
        pairs.append((y_bits, x_bits))
    return tuple(pairs)


def _small_ratio_rounding_margin_safe(ratio: Fraction) -> bool:
    exponent = _floor_log2(ratio)
    safe = False
    if MIN_NORMAL_EXPONENT <= exponent <= ATAN_MARGIN_MAX_EXPONENT:
        ulp = Fraction(1, 1 << (52 - exponent))
        scaled = ratio / ulp
        fraction = scaled - (scaled.numerator // scaled.denominator)
        if fraction < Fraction(1, 2):
            safe = True
        elif fraction > Fraction(1, 2):
            if exponent == ATAN_MARGIN_MAX_EXPONENT:
                safe = fraction >= ATAN_TOP_MARGIN_THRESHOLD
            else:
                margin_shift = -((2 * exponent) + 55)
                safe = fraction - Fraction(1, 2) >= Fraction(
                    1, 3 * (1 << margin_shift)
                )
    return safe


def _subnormal_atan_bits(ratio: Fraction, rounded: int) -> int | None:
    if _floor_log2(ratio) >= MIN_NORMAL_EXPONENT:
        return None
    scaled = ratio * (1 << 1074)
    lower = scaled.numerator // scaled.denominator
    fraction = scaled - lower
    return lower if fraction == Fraction(1, 2) else rounded


def _expected_small_ratio_special(y_bits: int, x_bits: int) -> tuple[int, int]:
    ratio = _raw_fraction(y_bits) / _raw_fraction(x_bits)
    rounded = _nearest_binary64_bits(ratio)
    result = (KERNEL_REQUIRED_STATUS, 0)
    if ratio <= ATAN_IDENTITY_MAX:
        subnormal = _subnormal_atan_bits(ratio, rounded)
        if subnormal is not None:
            result = (RESOLVED_STATUS, subnormal | (y_bits & SIGN_BIT))
        else:
            exactly_binary64 = _raw_fraction(rounded) == ratio
            safe = exactly_binary64 or _small_ratio_rounding_margin_safe(ratio)
            if safe:
                result = (RESOLVED_STATUS, rounded | (y_bits & SIGN_BIT))
    return result


def _small_ratio_row(y_bits: int, x_bits: int) -> str:
    status, bits = _expected_small_ratio_special(y_bits, x_bits)
    return (
        "  {"
        f"UINT64_C(0x{y_bits:016x}), UINT64_C(0x{x_bits:016x}), "
        f"UINT32_C({status}), UINT64_C(0x{bits:016x})"
        "}"
    )


def _margin_fraction(ratio: Fraction, expected_exponent: int) -> Fraction:
    exponent = _floor_log2(ratio)
    assert exponent == expected_exponent
    ulp = Fraction(1, 1 << (52 - exponent))
    scaled = ratio / ulp
    return scaled - (scaled.numerator // scaled.denominator)


def _margin_row(y_bits: int, x_bits: int) -> str:
    status, special_bits = _expected_small_ratio_special(y_bits, x_bits)
    lower, upper, negative = _atan2_integer_oracle_interval(y_bits, x_bits)
    scale = 1 << ATAN2_INTEGER_ORACLE_BITS
    lower_bits = _nearest_binary64_bits(Fraction(lower, scale))
    upper_bits = _nearest_binary64_bits(Fraction(upper, scale))
    assert lower_bits == upper_bits
    expected = lower_bits | (SIGN_BIT if negative else 0)
    return (
        "  {"
        f"UINT64_C(0x{y_bits:016x}), UINT64_C(0x{x_bits:016x}), "
        f"UINT32_C({status}), UINT64_C(0x{special_bits:016x}), "
        f"UINT64_C(0x{expected:016x})"
        "}"
    )


def _margin_harness_source(pairs: tuple[tuple[int, int], ...]) -> str:
    rows = ",\n".join(starmap(_margin_row, pairs))
    return f"""#include \"math_transcendental_bits.h\"
#include <stdint.h>
typedef struct Vector {{
  uint64_t y_bits, x_bits;
  uint32_t special_status;
  uint64_t special_bits, expected_bits;
}} Vector;
static const Vector vectors[] = {{
{rows}
}};
int main(void) {{
  uint32_t index = UINT32_C(0);
  while (index < (uint32_t)(sizeof(vectors) / sizeof(vectors[0]))) {{
    const Vector *v = &vectors[index];
    const MalbolgeGuestMathSpecialResult special =
        malbolge_guest_math_atan2_special(v->y_bits, v->x_bits);
    uint64_t output_bits = UINT64_C(0xdeadbeefdeadbeef);
    if ((uint32_t)special.status != v->special_status ||
        (v->special_status == UINT32_C({RESOLVED_STATUS}) &&
         special.bits != v->special_bits) ||
        !malbolge_guest_math_atan2_unique_binary64(
            v->y_bits, v->x_bits, &output_bits) ||
        output_bits != v->expected_bits) {{
      return 85;
    }}
    ++index;
  }}
  return 0;
}}
"""


def _small_ratio_harness_source() -> str:
    rows = ",\n".join(starmap(_small_ratio_row, _small_ratio_pairs()))
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
  uint32_t i = 0;
  while (i < (uint32_t)(sizeof(vectors) / sizeof(vectors[0]))) {{
    const Vector *v = &vectors[i];
    const MalbolgeGuestMathSpecialResult result =
        malbolge_guest_math_atan2_special(v->y_bits, v->x_bits);
    if ((uint32_t)result.status != v->status || result.bits != v->bits) {{
      return 20;
    }}
    ++i;
  }}
  return 0;
}}
"""


def _reconstruction_fields(
    swapped: int, y_negative: int, x_negative: int
) -> tuple[int, int, int]:
    if x_negative == 0:
        base, operation = (
            (ATAN2_BASE_ZERO, ATAN2_RATIO_ADD)
            if swapped == 0
            else (ATAN2_BASE_HALF_PI, ATAN2_RATIO_SUBTRACT)
        )
    else:
        base, operation = (
            (ATAN2_BASE_PI, ATAN2_RATIO_SUBTRACT)
            if swapped == 0
            else (ATAN2_BASE_HALF_PI, ATAN2_RATIO_ADD)
        )
    return base, operation, y_negative


def _row(y_bits: int, x_bits: int) -> str:
    geometry = _expected(y_bits, x_bits)
    base, ratio_operation, negative = _reconstruction_fields(
        geometry[3], geometry[4], geometry[5]
    )
    ratio = min(_raw_fraction(y_bits), _raw_fraction(x_bits)) / max(
        _raw_fraction(y_bits), _raw_fraction(x_bits)
    )
    rounded = _nearest_binary64_bits(ratio)
    return (
        "  {"
        f"UINT64_C(0x{y_bits:016x}), UINT64_C(0x{x_bits:016x}), "
        f"UINT64_C(0x{geometry[0]:016x}), UINT64_C(0x{geometry[1]:016x}), "
        f"INT32_C({geometry[2]}), UINT32_C({geometry[3]}), "
        f"UINT32_C({geometry[4]}), UINT32_C({geometry[5]}), "
        f"UINT64_C(0x{rounded:016x}), UINT32_C({base}), "
        f"UINT32_C({ratio_operation}), UINT32_C({negative})"
        "}"
    )


def _harness_source() -> str:
    rows = ",\n".join(starmap(_row, _deterministic_pairs()))
    return f"""#include \"math_transcendental_bits.h\"
#include <stdint.h>
typedef struct Vector {{
  uint64_t y_bits, x_bits, numerator, denominator;
  int32_t delta;
  uint32_t swapped, y_negative, x_negative;
  uint64_t rounded;
  uint32_t base, ratio_operation, negative;
}} Vector;
static const Vector vectors[] = {{
{rows}
}};
int main(void) {{
  uint32_t i = 0;
  while (i < (uint32_t)(sizeof(vectors) / sizeof(vectors[0]))) {{
    MalbolgeGuestMathAtan2KernelInput result;
    MalbolgeGuestMathAtan2Reconstruction reconstruction;
    uint64_t rounded = UINT64_C(0);
    const Vector *v = &vectors[i];
    if (!malbolge_guest_math_atan2_kernel_input(
            v->y_bits, v->x_bits, &result) ||
        result.numerator_significand != v->numerator ||
        result.denominator_significand != v->denominator ||
        result.exponent_delta != v->delta || result.swapped != v->swapped ||
        result.y_negative != v->y_negative ||
        result.x_negative != v->x_negative ||
        !malbolge_guest_math_ratio_nearest_binary64(&result, &rounded) ||
        rounded != v->rounded ||
        !malbolge_guest_math_atan2_reconstruction(
            v->y_bits, v->x_bits, &reconstruction) ||
        reconstruction.ratio.numerator_significand != v->numerator ||
        reconstruction.ratio.denominator_significand != v->denominator ||
        reconstruction.ratio.exponent_delta != v->delta ||
        reconstruction.ratio.swapped != v->swapped ||
        reconstruction.ratio.y_negative != v->y_negative ||
        reconstruction.ratio.x_negative != v->x_negative ||
        (uint32_t)reconstruction.base != v->base ||
        (uint32_t)reconstruction.ratio_operation != v->ratio_operation ||
        reconstruction.negative != v->negative) {{
      return 10;
    }}
    ++i;
  }}
  return 0;
}}
"""


def test_atan2_kernel_input_matches_exact_fraction_geometry(
    tmp_path: Path,
) -> None:
    """Match 519 exact ratios and nearest-even binary64 quotient bits."""
    harness = tmp_path / "atan2-kernel-input.c"
    executable = tmp_path / "atan2-kernel-input"
    _ = harness.write_text(_harness_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
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


def test_atan_kernel_reduction_matches_exact_fraction_identity(
    tmp_path: Path,
) -> None:
    """Reduce 519 exact atan ratios to a residual below the Pell cutoff."""
    harness = tmp_path / "atan-kernel-reduction.c"
    executable = tmp_path / "atan-kernel-reduction"
    _ = harness.write_text(_atan_reduction_harness_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
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


def test_atan_quarter_cut_is_strictly_self_reducing() -> None:
    """Prove the 169/408 cut maps its upper branch below the same cut."""
    transformed = (1 - ATAN_QUARTER_CUT) / (1 + ATAN_QUARTER_CUT)
    assert (
        ATAN_QUARTER_TRANSFORMED_CUT.numerator,
        ATAN_QUARTER_TRANSFORMED_CUT.denominator,
    ) == (transformed.numerator, transformed.denominator)
    assert ATAN_QUARTER_TRANSFORMED_CUT < ATAN_QUARTER_CUT
    assert ATAN_QUARTER_UPPER_PRODUCT == ATAN_QUARTER_LOWER_PRODUCT + 1


def _alternating_atan_interval(
    value: Fraction, terms: int
) -> tuple[Fraction, Fraction]:
    total = Fraction(0)
    square = value * value
    power = value
    for index in range(terms):
        term = power / ((2 * index) + 1)
        total = total + term if index % 2 == 0 else total - term
        power *= square
    remainder = power / ((2 * terms) + 1)
    if terms % 2 == 0:
        return total, total + remainder
    return total - remainder, total


@cache
def _quarter_pi_machin_interval() -> tuple[Fraction, Fraction]:
    fifth = _alternating_atan_interval(Fraction(1, 5), PI_MACHIN_FIFTH_TERMS)
    one_239 = _alternating_atan_interval(Fraction(1, 239), PI_MACHIN_239_TERMS)
    return (4 * fifth[0]) - one_239[1], (4 * fifth[1]) - one_239[0]


def _atan_series_remainder_bound(terms: int) -> Fraction:
    first_omitted_power = (2 * terms) + 1
    return ATAN_QUARTER_CUT**first_omitted_power / first_omitted_power


def test_quarter_pi_fixed_interval_is_certified_by_machin_identity() -> None:
    """Enclose pi/4 in one exact Q0.192 cell using rational series bounds."""
    lower, upper = _quarter_pi_machin_interval()
    scale = 1 << FIXED_INTERVAL_BITS
    encoded_lower = Fraction(QUARTER_PI_LOWER_FIXED, scale)
    encoded_upper = Fraction(QUARTER_PI_UPPER_FIXED, scale)
    assert encoded_lower < lower < upper < encoded_upper
    assert upper - lower < Fraction(1, 1 << (FIXED_INTERVAL_BITS + 8))


def test_atan_series_60_terms_is_minimal_for_160_bit_truncation() -> None:
    """Bound the runtime next-term ceiling; hard rounding remains unresolved."""
    target = Fraction(1, 1 << ATAN_SERIES_TARGET_BITS)
    previous = _atan_series_remainder_bound(ATAN_SERIES_PREVIOUS_TERMS)
    admitted = _atan_series_remainder_bound(ATAN_SERIES_TERMS)
    fixed_cut = Fraction(ATAN_CUT_UPPER_FIXED, 1 << FIXED_INTERVAL_BITS)
    fixed_remainder = fixed_cut ** ((2 * ATAN_SERIES_TERMS) + 1)
    fixed_remainder /= (2 * ATAN_SERIES_TERMS) + 1
    assert previous > target
    assert admitted < target
    assert fixed_remainder < target


def test_atan2_kernel_plan_composes_quadrant_and_atan_reduction(
    tmp_path: Path,
) -> None:
    """Compose 519 atan2 pairs into one bounded residual kernel plan."""
    harness = tmp_path / "atan2-kernel-plan.c"
    executable = tmp_path / "atan2-kernel-plan"
    _ = harness.write_text(_atan2_plan_harness_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
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


def test_atan_residual_q192_interval_matches_fraction_floor_ceil(
    tmp_path: Path,
) -> None:
    """Enclose all 519 reduced residuals by directed binary long division."""
    harness = tmp_path / "atan-residual-fixed.c"
    executable = tmp_path / "atan-residual-fixed"
    _ = harness.write_text(_fixed_ratio_harness_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
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


def test_atan_q192_interval_encloses_exact_rational_series(
    tmp_path: Path,
) -> None:
    """Enclose exact 60-term rational intervals over a stratified corpus."""
    harness = tmp_path / "atan-q192-interval.c"
    executable = tmp_path / "atan-q192-interval"
    _ = harness.write_text(_atan_interval_harness_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
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


def test_atan2_q192_interval_encloses_symbolic_plan(
    tmp_path: Path,
) -> None:
    """Enclose composed quarter-pi and atan intervals over 64 finite pairs."""
    harness = tmp_path / "atan2-q192-interval.c"
    executable = tmp_path / "atan2-q192-interval"
    _ = harness.write_text(_atan2_interval_harness_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
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


def test_atan2_unique_rounding_is_sound_and_conservative(
    tmp_path: Path,
) -> None:
    """Resolve all 64 cases by composing exact and Q192 authorities."""
    harness = tmp_path / "atan2-unique-rounding.c"
    executable = tmp_path / "atan2-unique-rounding"
    _ = harness.write_text(_unique_rounding_harness_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
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


def test_atan2_integer_oracle_encloses_fraction_authority() -> None:
    """Cross-check Q1152 bounds against the exact Fraction oracle."""
    scale = 1 << ATAN2_INTEGER_ORACLE_BITS
    for y_bits, x_bits in _atan_interval_pairs():
        integer_lower, integer_upper, integer_negative = (
            _atan2_integer_oracle_interval(y_bits, x_bits)
        )
        exact_lower, exact_upper, exact_negative = _atan2_exact_interval(
            y_bits, x_bits
        )
        assert Fraction(integer_lower, scale) <= exact_lower
        assert Fraction(integer_upper, scale) >= exact_upper
        assert integer_negative == exact_negative


def test_atan2_unique_rounding_matches_519_pair_integer_oracle(
    tmp_path: Path,
) -> None:
    """Match a Q1152 integer-only atan/Machin oracle over all 519 pairs."""
    harness = tmp_path / "atan2-integer-oracle-rounding.c"
    executable = tmp_path / "atan2-integer-oracle-rounding"
    _ = harness.write_text(
        _integer_oracle_unique_rounding_harness_source(), encoding="utf-8"
    )
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
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


def test_atan2_unique_rounding_retains_fixed_seed_million_pair_coverage(
    tmp_path: Path,
) -> None:
    """Retain million-pair resolution coverage; exact oracles own soundness."""
    harness = tmp_path / "atan2-million-pair-stress.c"
    executable = tmp_path / "atan2-million-pair-stress"
    _ = harness.write_text(_stress_harness_source(), encoding="utf-8")
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


def test_atan2_top_binade_margin_threshold_matches_q1152_oracle(
    tmp_path: Path,
) -> None:
    """Straddle the e=-27 early-resolution threshold with certified vectors."""
    below_ratio = _raw_fraction(ATAN_TOP_MARGIN_PAIRS[0][0]) / _raw_fraction(
        ATAN_TOP_MARGIN_PAIRS[0][1]
    )
    above_ratio = _raw_fraction(ATAN_TOP_MARGIN_PAIRS[1][0]) / _raw_fraction(
        ATAN_TOP_MARGIN_PAIRS[1][1]
    )
    below = _margin_fraction(below_ratio, ATAN_MARGIN_MAX_EXPONENT)
    above = _margin_fraction(above_ratio, ATAN_MARGIN_MAX_EXPONENT)
    assert 0 < ATAN_TOP_MARGIN_THRESHOLD - below < Fraction(1, 100_000)
    assert 0 < above - ATAN_TOP_MARGIN_THRESHOLD < Fraction(1, 100_000)
    assert not _small_ratio_rounding_margin_safe(below_ratio)
    assert _small_ratio_rounding_margin_safe(above_ratio)

    harness = tmp_path / "atan2-top-margin.c"
    executable = tmp_path / "atan2-top-margin"
    _ = harness.write_text(
        _margin_harness_source(ATAN_TOP_MARGIN_PAIRS), encoding="utf-8"
    )
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
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


def test_atan2_scaled_margin_threshold_matches_q1152_oracle(
    tmp_path: Path,
) -> None:
    """Straddle the e=-28 dynamic-margin threshold with certified vectors."""
    below_ratio = _raw_fraction(ATAN_SCALED_MARGIN_PAIRS[0][0]) / _raw_fraction(
        ATAN_SCALED_MARGIN_PAIRS[0][1]
    )
    above_ratio = _raw_fraction(ATAN_SCALED_MARGIN_PAIRS[1][0]) / _raw_fraction(
        ATAN_SCALED_MARGIN_PAIRS[1][1]
    )
    below = _margin_fraction(below_ratio, ATAN_MARGIN_MAX_EXPONENT - 1)
    above = _margin_fraction(above_ratio, ATAN_MARGIN_MAX_EXPONENT - 1)
    assert 0 < ATAN_SCALED_MARGIN_THRESHOLD - below < Fraction(1, 40_000)
    assert 0 < above - ATAN_SCALED_MARGIN_THRESHOLD < Fraction(1, 40_000)
    assert not _small_ratio_rounding_margin_safe(below_ratio)
    assert _small_ratio_rounding_margin_safe(above_ratio)

    harness = tmp_path / "atan2-scaled-margin.c"
    executable = tmp_path / "atan2-scaled-margin"
    _ = harness.write_text(
        _margin_harness_source(ATAN_SCALED_MARGIN_PAIRS), encoding="utf-8"
    )
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
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


def test_atan2_small_ratio_classifier_matches_exact_fraction_gate(
    tmp_path: Path,
) -> None:
    """Resolve only exact binary64 ratios inside the proved atan interval."""
    harness = tmp_path / "atan2-small-ratio.c"
    executable = tmp_path / "atan2-small-ratio"
    _ = harness.write_text(_small_ratio_harness_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
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


def test_small_ratio_policy_keeps_ambiguous_rounding_fail_closed() -> None:
    """Keep subnormal closure and the normal margin policy fail closed."""
    statuses = [
        _expected_small_ratio_special(y_bits, x_bits)[0]
        for y_bits, x_bits in _small_ratio_pairs()
    ]
    assert statuses.count(RESOLVED_STATUS) == EXPECTED_SMALL_RATIO_RESOLVED
    assert (
        statuses.count(KERNEL_REQUIRED_STATUS)
        == EXPECTED_SMALL_RATIO_UNRESOLVED
    )
