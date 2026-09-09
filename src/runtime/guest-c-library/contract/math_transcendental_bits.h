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

typedef struct MalbolgeGuestMathRationalHeight {
  uint32_t numerator_bits;
  uint32_t denominator_bits;
  uint32_t height_bits;
} MalbolgeGuestMathRationalHeight;

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

typedef struct MalbolgeGuestMathLambertArgumentBounds {
  uint32_t numerator_bits;
  uint32_t denominator_shift;
  int32_t square_over_denominator_pow2_exponent_upper;
  uint32_t normalizing_halvings;
  uint32_t normalized_denominator_shift;
  int32_t normalized_scale_pow2_exponent_upper;
} MalbolgeGuestMathLambertArgumentBounds;

typedef struct MalbolgeGuestMathAtan2SeparationParameters {
  MalbolgeGuestMathRationalHeight ratio_height;
  uint32_t lower_midpoint_shift;
  uint32_t upper_midpoint_shift;
  uint32_t midpoint_shift_max;
  MalbolgeGuestMathLambertArgumentBounds lower_lambert;
  MalbolgeGuestMathLambertArgumentBounds upper_lambert;
  int32_t lambert_scale_pow2_exponent_upper;
} MalbolgeGuestMathAtan2SeparationParameters;

typedef struct MalbolgeGuestMathExponentialArgumentBounds {
  uint32_t alpha_height_pow2_exponent_upper;
  uint32_t inverse_denominator_bits;
  uint32_t inverse_house_pow2_exponent_upper;
} MalbolgeGuestMathExponentialArgumentBounds;

typedef struct MalbolgeGuestMathAtan2ExponentialBridgeBounds {
  uint32_t linear_polynomial_height_pow2_exponent_upper;
  uint32_t rational_denominator_bits;
  MalbolgeGuestMathExponentialArgumentBounds lower_midpoint;
  MalbolgeGuestMathExponentialArgumentBounds upper_midpoint;
  uint32_t alpha_height_pow2_exponent_upper;
  uint32_t inverse_denominator_bits_max;
  uint32_t inverse_house_pow2_exponent_upper;
} MalbolgeGuestMathAtan2ExponentialBridgeBounds;

typedef struct MalbolgeGuestMathAtan2RefinementPlan {
  uint32_t stage;
  uint32_t fraction_limbs;
  uint32_t terms;
  uint32_t required_scratch_limbs;
} MalbolgeGuestMathAtan2RefinementPlan;

typedef struct MalbolgeGuestMathAtan2RefinementProgress {
  uint32_t certified;
  MalbolgeGuestMathAtan2RefinementPlan plan;
} MalbolgeGuestMathAtan2RefinementProgress;

typedef struct MalbolgeGuestMathAtan2Candidates {
  uint32_t count;
  uint64_t bits[2];
} MalbolgeGuestMathAtan2Candidates;

typedef struct MalbolgeGuestMathAtan2CandidateProgress {
  uint32_t certified;
  uint64_t bits;
  MalbolgeGuestMathAtan2RefinementPlan plan;
} MalbolgeGuestMathAtan2CandidateProgress;

typedef struct MalbolgeGuestMathAtan2CandidateRange {
  uint64_t lower_bits;
  uint64_t upper_bits;
} MalbolgeGuestMathAtan2CandidateRange;

typedef struct MalbolgeGuestMathAtan2RangeProgress {
  uint32_t certified;
  uint64_t bits;
  MalbolgeGuestMathAtan2CandidateRange remaining;
  MalbolgeGuestMathAtan2RefinementPlan plan;
} MalbolgeGuestMathAtan2RangeProgress;

typedef enum MalbolgeGuestMathAtan2HandoffStatus {
  MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_RETRY = 0,
  MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_FAST_RESOLVED = 1,
  MALBOLGE_GUEST_MATH_ATAN2_HANDOFF_REFINED_RESOLVED = 2,
} MalbolgeGuestMathAtan2HandoffStatus;

typedef struct MalbolgeGuestMathAtan2HandoffProgress {
  MalbolgeGuestMathAtan2HandoffStatus status;
  uint64_t y_bits;
  uint64_t x_bits;
  uint64_t bits;
  MalbolgeGuestMathAtan2CandidateRange remaining;
  MalbolgeGuestMathAtan2RefinementPlan plan;
} MalbolgeGuestMathAtan2HandoffProgress;

typedef struct MalbolgeGuestMathAtan2ScratchRequirement {
  uint32_t limbs;
  uint32_t bytes;
  uint32_t alignment;
} MalbolgeGuestMathAtan2ScratchRequirement;

MalbolgeGuestMathSpecialResult malbolge_guest_math_unary_special(
    MalbolgeGuestMathUnaryOperation operation, uint64_t bits);
MalbolgeGuestMathSpecialResult malbolge_guest_math_atan2_special(
    uint64_t y_bits, uint64_t x_bits);
int malbolge_guest_math_atan2_kernel_input(
    uint64_t y_bits, uint64_t x_bits,
    MalbolgeGuestMathAtan2KernelInput *output);
int malbolge_guest_math_atan2_ratio_reduced_height(
    const MalbolgeGuestMathAtan2KernelInput *input,
    MalbolgeGuestMathRationalHeight *output);
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
int malbolge_guest_math_fixed256_candidates(
    const MalbolgeGuestMathFixed256Interval *input,
    MalbolgeGuestMathAtan2Candidates *output);
int malbolge_guest_math_fixed256_candidate_range(
    const MalbolgeGuestMathFixed256Interval *input,
    MalbolgeGuestMathAtan2CandidateRange *output);
int malbolge_guest_math_atan2_cell_midpoints(
    uint64_t output_bits, MalbolgeGuestMathAtan2CellMidpoints *output);
int malbolge_guest_math_dyadic_lambert_argument_bounds(
    const MalbolgeGuestMathDyadic *midpoint,
    MalbolgeGuestMathLambertArgumentBounds *output);
int malbolge_guest_math_atan2_separation_parameters(
    uint64_t y_bits, uint64_t x_bits, uint64_t candidate_bits,
    MalbolgeGuestMathAtan2SeparationParameters *output);
int malbolge_guest_math_dyadic_exponential_argument_bounds(
    const MalbolgeGuestMathDyadic *midpoint,
    MalbolgeGuestMathExponentialArgumentBounds *output);
int malbolge_guest_math_atan2_exponential_bridge_bounds(
    uint64_t y_bits, uint64_t x_bits, uint64_t candidate_bits,
    MalbolgeGuestMathAtan2ExponentialBridgeBounds *output);
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
int malbolge_guest_math_fixed_taylor_term_interval(
    const uint32_t *term_lower, const uint32_t *term_upper,
    const uint32_t *square_lower, const uint32_t *square_upper,
    uint32_t limb_count, uint32_t fraction_limbs, uint32_t divisor,
    uint32_t *output_lower, uint32_t *output_upper, uint32_t *scratch,
    uint32_t scratch_capacity);
int malbolge_guest_math_fixed_signed_add(
    const uint32_t *left, uint32_t left_negative, const uint32_t *right,
    uint32_t right_negative, uint32_t limb_count, uint32_t *output,
    uint32_t *output_negative);
int malbolge_guest_math_fixed_signed_interval_add(
    const uint32_t *left_lower, uint32_t left_lower_negative,
    const uint32_t *left_upper, uint32_t left_upper_negative,
    const uint32_t *right_lower, uint32_t right_lower_negative,
    const uint32_t *right_upper, uint32_t right_upper_negative,
    uint32_t limb_count, uint32_t *output_lower,
    uint32_t *output_lower_negative, uint32_t *output_upper,
    uint32_t *output_upper_negative, uint32_t *scratch,
    uint32_t scratch_capacity);
int malbolge_guest_math_fixed_sin_taylor_interval(
    const uint32_t *input_lower, const uint32_t *input_upper,
    uint32_t limb_count, uint32_t fraction_limbs, uint32_t terms,
    uint32_t *output_lower, uint32_t *output_lower_negative,
    uint32_t *output_upper, uint32_t *output_upper_negative,
    uint32_t *scratch, uint32_t scratch_capacity);
int malbolge_guest_math_fixed_cos_taylor_interval(
    const uint32_t *input_lower, const uint32_t *input_upper,
    uint32_t limb_count, uint32_t fraction_limbs, uint32_t terms,
    uint32_t *output_lower, uint32_t *output_lower_negative,
    uint32_t *output_upper, uint32_t *output_upper_negative,
    uint32_t *scratch, uint32_t scratch_capacity);
int malbolge_guest_math_fixed_sincos_double_interval(
    const uint32_t *sin_lower, uint32_t sin_lower_negative,
    const uint32_t *sin_upper, uint32_t sin_upper_negative,
    const uint32_t *cos_lower, uint32_t cos_lower_negative,
    const uint32_t *cos_upper, uint32_t cos_upper_negative,
    uint32_t limb_count, uint32_t fraction_limbs, uint32_t *output_sin_lower,
    uint32_t *output_sin_lower_negative, uint32_t *output_sin_upper,
    uint32_t *output_sin_upper_negative, uint32_t *output_cos_lower,
    uint32_t *output_cos_lower_negative, uint32_t *output_cos_upper,
    uint32_t *output_cos_upper_negative, uint32_t *proven, uint32_t *scratch,
    uint32_t scratch_capacity);
int malbolge_guest_math_fixed_sincos_double_transport(
    const uint32_t *sin_lower, uint32_t sin_lower_negative,
    const uint32_t *sin_upper, uint32_t sin_upper_negative,
    const uint32_t *cos_lower, uint32_t cos_lower_negative,
    const uint32_t *cos_upper, uint32_t cos_upper_negative,
    uint32_t limb_count, uint32_t fraction_limbs, uint32_t doublings,
    uint32_t *output_sin_lower, uint32_t *output_sin_lower_negative,
    uint32_t *output_sin_upper, uint32_t *output_sin_upper_negative,
    uint32_t *output_cos_lower, uint32_t *output_cos_lower_negative,
    uint32_t *output_cos_upper, uint32_t *output_cos_upper_negative,
    uint32_t *proven, uint32_t *scratch, uint32_t scratch_capacity);
int malbolge_guest_math_dyadic_normalized_sincos_interval(
    const MalbolgeGuestMathDyadic *midpoint, uint32_t fraction_limbs,
    uint32_t terms, uint32_t *output_sin_lower,
    uint32_t *output_sin_lower_negative, uint32_t *output_sin_upper,
    uint32_t *output_sin_upper_negative, uint32_t *output_cos_lower,
    uint32_t *output_cos_lower_negative, uint32_t *output_cos_upper,
    uint32_t *output_cos_upper_negative, uint32_t *proven, uint32_t *scratch,
    uint32_t scratch_capacity);
int malbolge_guest_math_positive_ratio_tangent_compare(
    const MalbolgeGuestMathAtan2KernelInput *ratio,
    const uint32_t *sin_lower, const uint32_t *sin_upper,
    const uint32_t *cos_lower, const uint32_t *cos_upper,
    uint32_t limb_count, int32_t *comparison, uint32_t *scratch,
    uint32_t scratch_capacity);
int malbolge_guest_math_positive_midpoint_compare(
    const MalbolgeGuestMathAtan2KernelInput *ratio,
    const MalbolgeGuestMathDyadic *midpoint, uint32_t fraction_limbs,
    uint32_t terms, int32_t *comparison, uint32_t *scratch,
    uint32_t scratch_capacity);
int malbolge_guest_math_midpoint_compare(
    const MalbolgeGuestMathAtan2KernelInput *ratio,
    const MalbolgeGuestMathDyadic *midpoint, uint32_t fraction_limbs,
    uint32_t terms, int32_t *comparison, uint32_t *scratch,
    uint32_t scratch_capacity);
int malbolge_guest_math_normalized_midpoint_compare(
    const MalbolgeGuestMathAtan2KernelInput *ratio,
    const MalbolgeGuestMathDyadic *midpoint, uint32_t fraction_limbs,
    uint32_t terms, int32_t *comparison, uint32_t *scratch,
    uint32_t scratch_capacity);
int malbolge_guest_math_atan2_refinement_attempt(
    uint64_t y_bits, uint64_t x_bits, uint64_t candidate_bits,
    uint32_t fraction_limbs, uint32_t terms, uint32_t *certified,
    uint32_t *scratch, uint32_t scratch_capacity);
int malbolge_guest_math_atan2_normalized_refinement_attempt(
    uint64_t y_bits, uint64_t x_bits, uint64_t candidate_bits,
    uint32_t fraction_limbs, uint32_t terms, uint32_t *certified,
    uint32_t *scratch, uint32_t scratch_capacity);
int malbolge_guest_math_atan2_refinement_plan(
    uint32_t stage, MalbolgeGuestMathAtan2RefinementPlan *output);
int malbolge_guest_math_atan2_normalized_refinement_plan(
    uint32_t stage, MalbolgeGuestMathAtan2RefinementPlan *output);
int malbolge_guest_math_atan2_refine_available(
    uint64_t y_bits, uint64_t x_bits, uint64_t candidate_bits,
    uint32_t start_stage, uint32_t *scratch, uint32_t scratch_capacity,
    MalbolgeGuestMathAtan2RefinementProgress *output);
int malbolge_guest_math_atan2_normalized_refine_available(
    uint64_t y_bits, uint64_t x_bits, uint64_t candidate_bits,
    uint32_t start_stage, uint32_t *scratch, uint32_t scratch_capacity,
    MalbolgeGuestMathAtan2RefinementProgress *output);
int malbolge_guest_math_atan2_q256_candidates(
    uint64_t y_bits, uint64_t x_bits,
    MalbolgeGuestMathAtan2Candidates *output);
int malbolge_guest_math_atan2_refine_candidates_available(
    uint64_t y_bits, uint64_t x_bits,
    const MalbolgeGuestMathAtan2Candidates *candidates, uint32_t start_stage,
    uint32_t *scratch, uint32_t scratch_capacity,
    MalbolgeGuestMathAtan2CandidateProgress *output);
int malbolge_guest_math_atan2_q256_refine_available(
    uint64_t y_bits, uint64_t x_bits, uint32_t start_stage, uint32_t *scratch,
    uint32_t scratch_capacity, MalbolgeGuestMathAtan2CandidateProgress *output);
int malbolge_guest_math_atan2_q256_candidate_range(
    uint64_t y_bits, uint64_t x_bits,
    MalbolgeGuestMathAtan2CandidateRange *output);
int malbolge_guest_math_atan2_refine_range_available(
    uint64_t y_bits, uint64_t x_bits,
    const MalbolgeGuestMathAtan2CandidateRange *range, uint32_t start_stage,
    uint32_t *scratch, uint32_t scratch_capacity,
    MalbolgeGuestMathAtan2RangeProgress *output);
int malbolge_guest_math_atan2_q256_refine_range_available(
    uint64_t y_bits, uint64_t x_bits, uint32_t start_stage, uint32_t *scratch,
    uint32_t scratch_capacity, MalbolgeGuestMathAtan2RangeProgress *output);
int malbolge_guest_math_atan2_refine_q256_interval_available(
    uint64_t y_bits, uint64_t x_bits,
    const MalbolgeGuestMathAtan2Interval256 *interval, uint32_t start_stage,
    uint32_t *scratch, uint32_t scratch_capacity,
    MalbolgeGuestMathAtan2HandoffProgress *output);
int malbolge_guest_math_atan2_handoff_available(
    uint64_t y_bits, uint64_t x_bits, uint32_t start_stage, uint32_t *scratch,
    uint32_t scratch_capacity, MalbolgeGuestMathAtan2HandoffProgress *output);
int malbolge_guest_math_atan2_resume_handoff_available(
    uint64_t y_bits, uint64_t x_bits,
    const MalbolgeGuestMathAtan2HandoffProgress *previous, uint32_t *scratch,
    uint32_t scratch_capacity, MalbolgeGuestMathAtan2HandoffProgress *output);
int malbolge_guest_math_atan2_refinement_scratch_requirement(
    const MalbolgeGuestMathAtan2RefinementPlan *plan,
    MalbolgeGuestMathAtan2ScratchRequirement *output);
int malbolge_guest_math_atan2_unique_binary64(
    uint64_t y_bits, uint64_t x_bits, uint64_t *output_bits);
int malbolge_guest_math_ratio_nearest_binary64(
    const MalbolgeGuestMathAtan2KernelInput *input, uint64_t *output_bits);

#endif
