// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Exact reduction and certified fixed-point transcendental intervals.
// - Must-Not:
//   - Publish unproved finite transcendental rounding or change availability.
// - Allows:
//   - Inputs: raw binary64 words and one admitted unary operation identity.
//   - Outputs: exact results, symbolic reconstruction, ratios, or certified
//     fixed-point intervals.
//   - Side effects: none.
// - Split-When:
//   - Public rounding or wider-precision fallback gains independent policy.
// - Merge-When:
//   - Complete correctly-rounded transcendental implementations own this step.
// - Summary:
//   - Resolves only exact transcendental edge cases before numerical kernels.
// - Description:
//   - Resolves proved cases and encloses reduced atan values in fixed point.
// - Usage:
//   - Internal guest-libc substrate; public sin/cos/atan2 remain gated.
// - Defaults:
//   - Finite values outside proved exact cases report kernel-required.
//   - Rejected atan2 kernel inputs never mutate caller-owned output geometry.
//

//! Internal exact edge-case classifier for future transcendental kernels.

#ifndef MALBOLGE_GUEST_MATH_TRANSCENDENTAL_BITS_H
#define MALBOLGE_GUEST_MATH_TRANSCENDENTAL_BITS_H

#include <stdint.h>

typedef enum MalbolgeGuestMathUnaryOperation {
  MALBOLGE_GUEST_MATH_SIN = 1,
  MALBOLGE_GUEST_MATH_COS = 2,
} MalbolgeGuestMathUnaryOperation;

typedef enum MalbolgeGuestMathSpecialStatus {
  MALBOLGE_GUEST_MATH_SPECIAL_INVALID = 0,
  MALBOLGE_GUEST_MATH_SPECIAL_RESOLVED = 1,
  MALBOLGE_GUEST_MATH_SPECIAL_KERNEL_REQUIRED = 2,
} MalbolgeGuestMathSpecialStatus;

typedef struct MalbolgeGuestMathSpecialResult {
  MalbolgeGuestMathSpecialStatus status;
  uint64_t bits;
} MalbolgeGuestMathSpecialResult;

typedef struct MalbolgeGuestMathAtan2KernelInput {
  uint64_t numerator_significand;
  uint64_t denominator_significand;
  int32_t exponent_delta;
  uint32_t swapped;
  uint32_t y_negative;
  uint32_t x_negative;
} MalbolgeGuestMathAtan2KernelInput;

typedef enum MalbolgeGuestMathAtan2Base {
  MALBOLGE_GUEST_MATH_ATAN2_BASE_ZERO = 0,
  MALBOLGE_GUEST_MATH_ATAN2_BASE_HALF_PI = 1,
  MALBOLGE_GUEST_MATH_ATAN2_BASE_PI = 2,
} MalbolgeGuestMathAtan2Base;

typedef enum MalbolgeGuestMathAtan2RatioOperation {
  MALBOLGE_GUEST_MATH_ATAN2_RATIO_ADD = 1,
  MALBOLGE_GUEST_MATH_ATAN2_RATIO_SUBTRACT = 2,
} MalbolgeGuestMathAtan2RatioOperation;

typedef struct MalbolgeGuestMathAtan2Reconstruction {
  MalbolgeGuestMathAtan2KernelInput ratio;
  MalbolgeGuestMathAtan2Base base;
  MalbolgeGuestMathAtan2RatioOperation ratio_operation;
  uint32_t negative;
} MalbolgeGuestMathAtan2Reconstruction;

typedef struct MalbolgeGuestMathExactRatio {
  uint64_t numerator;
  uint64_t denominator;
  int32_t exponent_delta;
} MalbolgeGuestMathExactRatio;

typedef enum MalbolgeGuestMathAtanBase {
  MALBOLGE_GUEST_MATH_ATAN_BASE_ZERO = 0,
  MALBOLGE_GUEST_MATH_ATAN_BASE_QUARTER_PI = 1,
} MalbolgeGuestMathAtanBase;

typedef struct MalbolgeGuestMathAtanKernelReduction {
  MalbolgeGuestMathExactRatio residual;
  MalbolgeGuestMathAtanBase base;
  MalbolgeGuestMathAtan2RatioOperation ratio_operation;
} MalbolgeGuestMathAtanKernelReduction;

typedef enum MalbolgeGuestMathAtan2QuarterPiBase {
  MALBOLGE_GUEST_MATH_ATAN2_QUARTER_BASE_ZERO = 0,
  MALBOLGE_GUEST_MATH_ATAN2_QUARTER_BASE_ONE = 1,
  MALBOLGE_GUEST_MATH_ATAN2_QUARTER_BASE_TWO = 2,
  MALBOLGE_GUEST_MATH_ATAN2_QUARTER_BASE_THREE = 3,
  MALBOLGE_GUEST_MATH_ATAN2_QUARTER_BASE_FOUR = 4,
} MalbolgeGuestMathAtan2QuarterPiBase;

typedef struct MalbolgeGuestMathAtan2KernelPlan {
  MalbolgeGuestMathExactRatio residual;
  MalbolgeGuestMathAtan2QuarterPiBase quarter_pi_base;
  MalbolgeGuestMathAtan2RatioOperation ratio_operation;
  uint32_t negative;
} MalbolgeGuestMathAtan2KernelPlan;

#define MALBOLGE_GUEST_MATH_FIXED_192_LIMBS UINT32_C(7)

typedef struct MalbolgeGuestMathFixed192 {
  uint32_t limbs[MALBOLGE_GUEST_MATH_FIXED_192_LIMBS];
} MalbolgeGuestMathFixed192;

typedef struct MalbolgeGuestMathFixed192Interval {
  MalbolgeGuestMathFixed192 lower;
  MalbolgeGuestMathFixed192 upper;
} MalbolgeGuestMathFixed192Interval;

typedef struct MalbolgeGuestMathAtan2Interval {
  MalbolgeGuestMathFixed192Interval magnitude;
  uint32_t negative;
} MalbolgeGuestMathAtan2Interval;

#define MALBOLGE_GUEST_MATH_FIXED_224_LIMBS UINT32_C(8)

typedef struct MalbolgeGuestMathFixed224 {
  uint32_t limbs[MALBOLGE_GUEST_MATH_FIXED_224_LIMBS];
} MalbolgeGuestMathFixed224;

typedef struct MalbolgeGuestMathFixed224Interval {
  MalbolgeGuestMathFixed224 lower;
  MalbolgeGuestMathFixed224 upper;
} MalbolgeGuestMathFixed224Interval;

typedef struct MalbolgeGuestMathAtan2Interval224 {
  MalbolgeGuestMathFixed224Interval magnitude;
  uint32_t negative;
} MalbolgeGuestMathAtan2Interval224;

#define MALBOLGE_GUEST_MATH_FIXED_256_LIMBS UINT32_C(9)

typedef struct MalbolgeGuestMathFixed256 {
  uint32_t limbs[MALBOLGE_GUEST_MATH_FIXED_256_LIMBS];
} MalbolgeGuestMathFixed256;

typedef struct MalbolgeGuestMathFixed256Interval {
  MalbolgeGuestMathFixed256 lower;
  MalbolgeGuestMathFixed256 upper;
} MalbolgeGuestMathFixed256Interval;

typedef struct MalbolgeGuestMathAtan2Interval256 {
  MalbolgeGuestMathFixed256Interval magnitude;
  uint32_t negative;
} MalbolgeGuestMathAtan2Interval256;

typedef struct MalbolgeGuestMathDyadic {
  uint64_t numerator;
  uint32_t denominator_shift;
  uint32_t negative;
} MalbolgeGuestMathDyadic;

typedef struct MalbolgeGuestMathAtan2CellMidpoints {
  MalbolgeGuestMathDyadic lower;
  MalbolgeGuestMathDyadic upper;
} MalbolgeGuestMathAtan2CellMidpoints;

MalbolgeGuestMathSpecialResult malbolge_guest_math_unary_special(
    MalbolgeGuestMathUnaryOperation operation, uint64_t bits);
MalbolgeGuestMathSpecialResult malbolge_guest_math_atan2_special(
    uint64_t y_bits, uint64_t x_bits);
int malbolge_guest_math_atan2_kernel_input(
    uint64_t y_bits, uint64_t x_bits,
    MalbolgeGuestMathAtan2KernelInput *output);
int malbolge_guest_math_atan2_reconstruction(
    uint64_t y_bits, uint64_t x_bits,
    MalbolgeGuestMathAtan2Reconstruction *output);
int malbolge_guest_math_atan_kernel_reduction(
    const MalbolgeGuestMathAtan2KernelInput *input,
    MalbolgeGuestMathAtanKernelReduction *output);
int malbolge_guest_math_atan2_kernel_plan(
    uint64_t y_bits, uint64_t x_bits, MalbolgeGuestMathAtan2KernelPlan *output);
int malbolge_guest_math_quarter_pi_interval(
    MalbolgeGuestMathFixed192Interval *output);
int malbolge_guest_math_atan2_base_interval(
    MalbolgeGuestMathAtan2QuarterPiBase base,
    MalbolgeGuestMathFixed192Interval *output);
int malbolge_guest_math_exact_ratio_interval(
    const MalbolgeGuestMathExactRatio *input,
    MalbolgeGuestMathFixed192Interval *output);
int malbolge_guest_math_atan_residual_interval(
    const MalbolgeGuestMathExactRatio *input,
    MalbolgeGuestMathFixed192Interval *output);
int malbolge_guest_math_atan2_interval(
    uint64_t y_bits, uint64_t x_bits, MalbolgeGuestMathAtan2Interval *output);
int malbolge_guest_math_atan2_interval224(
    uint64_t y_bits, uint64_t x_bits,
    MalbolgeGuestMathAtan2Interval224 *output);
int malbolge_guest_math_atan2_interval256(
    uint64_t y_bits, uint64_t x_bits,
    MalbolgeGuestMathAtan2Interval256 *output);
int malbolge_guest_math_fixed192_unique_binary64(
    const MalbolgeGuestMathFixed192Interval *input, uint64_t *output_bits);
int malbolge_guest_math_fixed224_unique_binary64(
    const MalbolgeGuestMathFixed224Interval *input, uint64_t *output_bits);
int malbolge_guest_math_fixed256_unique_binary64(
    const MalbolgeGuestMathFixed256Interval *input, uint64_t *output_bits);
int malbolge_guest_math_atan2_cell_midpoints(
    uint64_t output_bits, MalbolgeGuestMathAtan2CellMidpoints *output);
int malbolge_guest_math_dyadic_fixed_limb_count(
    const MalbolgeGuestMathDyadic *input, uint32_t fraction_bits,
    uint32_t *required_limbs);
int malbolge_guest_math_dyadic_write_fixed(
    const MalbolgeGuestMathDyadic *input, uint32_t fraction_bits,
    uint32_t *limbs, uint32_t limb_capacity);
int malbolge_guest_math_fixed_add(
    const uint32_t *left, const uint32_t *right, uint32_t limb_count,
    uint32_t *output);
int malbolge_guest_math_fixed_subtract(
    const uint32_t *left, const uint32_t *right, uint32_t limb_count,
    uint32_t *output);
int malbolge_guest_math_fixed_multiply_floor(
    const uint32_t *left, const uint32_t *right, uint32_t limb_count,
    uint32_t fraction_limbs, uint32_t *output, uint32_t *scratch,
    uint32_t scratch_capacity, uint32_t *discarded);
int malbolge_guest_math_fixed_divide_small_floor(
    const uint32_t *input, uint32_t limb_count, uint32_t divisor,
    uint32_t *output, uint32_t *remainder);
int malbolge_guest_math_fixed_multiply_ceil(
    const uint32_t *left, const uint32_t *right, uint32_t limb_count,
    uint32_t fraction_limbs, uint32_t *output, uint32_t *scratch,
    uint32_t scratch_capacity, uint32_t *discarded);
int malbolge_guest_math_fixed_divide_small_ceil(
    const uint32_t *input, uint32_t limb_count, uint32_t divisor,
    uint32_t *output, uint32_t *remainder);
int malbolge_guest_math_fixed_interval_add(
    const uint32_t *left_lower, const uint32_t *left_upper,
    const uint32_t *right_lower, const uint32_t *right_upper,
    uint32_t limb_count, uint32_t *output_lower, uint32_t *output_upper);
int malbolge_guest_math_fixed_interval_subtract(
    const uint32_t *left_lower, const uint32_t *left_upper,
    const uint32_t *right_lower, const uint32_t *right_upper,
    uint32_t limb_count, uint32_t *output_lower, uint32_t *output_upper);
int malbolge_guest_math_fixed_interval_multiply(
    const uint32_t *left_lower, const uint32_t *left_upper,
    const uint32_t *right_lower, const uint32_t *right_upper,
    uint32_t limb_count, uint32_t fraction_limbs, uint32_t *output_lower,
    uint32_t *output_upper, uint32_t *scratch, uint32_t scratch_capacity);
int malbolge_guest_math_fixed_interval_divide_small(
    const uint32_t *input_lower, const uint32_t *input_upper,
    uint32_t limb_count, uint32_t divisor, uint32_t *output_lower,
    uint32_t *output_upper, uint32_t *scratch, uint32_t scratch_capacity);
int malbolge_guest_math_atan2_unique_binary64(
    uint64_t y_bits, uint64_t x_bits, uint64_t *output_bits);
int malbolge_guest_math_ratio_nearest_binary64(
    const MalbolgeGuestMathAtan2KernelInput *input, uint64_t *output_bits);

#endif
