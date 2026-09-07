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
int malbolge_guest_math_ratio_nearest_binary64(
    const MalbolgeGuestMathAtan2KernelInput *input, uint64_t *output_bits);

#endif
