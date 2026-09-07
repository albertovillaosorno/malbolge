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
//   - Fixed vectors for exact finite atan2 kernel-input normalization.
// - Must-Not:
//   - Divide floating values or treat normalized ratios as atan estimates.
// - Allows:
//   - Inputs: finite nonzero binary64 raw words plus special rejection cases.
//   - Outputs: exact significand/exponent/sign/swap geometry or no mutation.
//   - Side effects: test-local output structures only.
// - Split-When:
//   - A numerical atan kernel needs independent approximation evidence.
// - Merge-When:
//   - Complete atan2 conformance owns the same exact input normalization.
// - Summary:
//   - Locks reduction of finite atan2 magnitudes to an exact ratio in [0,1].
// - Description:
//   - Covers equal, swapped, subnormal, extreme, signed, and rejected inputs.
// - Usage:
//   - Compiled directly with the internal transcendental bit substrate.
// - Defaults:
//   - Rejected special inputs leave caller-owned output bytes unchanged.
//

//! Exact finite-ratio normalization vectors for the future atan2 kernel.

#include "math_transcendental_bits.h"

#include <stddef.h>
#include <stdint.h>

static int fields_equal(const MalbolgeGuestMathAtan2KernelInput *value,
                        uint64_t numerator, uint64_t denominator,
                        int32_t exponent_delta, uint32_t swapped,
                        uint32_t y_negative, uint32_t x_negative) {
  return value->numerator_significand == numerator &&
         value->denominator_significand == denominator &&
         value->exponent_delta == exponent_delta && value->swapped == swapped &&
         value->y_negative == y_negative && value->x_negative == x_negative;
}


static int reconstruction_equal(
    const MalbolgeGuestMathAtan2Reconstruction *value,
    MalbolgeGuestMathAtan2Base base,
    MalbolgeGuestMathAtan2RatioOperation ratio_operation, uint32_t negative,
    uint32_t swapped, uint32_t x_negative) {
  return value->base == base && value->ratio_operation == ratio_operation &&
         value->negative == negative && value->ratio.swapped == swapped &&
         value->ratio.x_negative == x_negative;
}

static int test_reconstruction(void) {
  MalbolgeGuestMathAtan2Reconstruction output;

  if (!malbolge_guest_math_atan2_reconstruction(
          UINT64_C(0x3ff0000000000000), UINT64_C(0x4000000000000000),
          &output) ||
      !reconstruction_equal(&output, MALBOLGE_GUEST_MATH_ATAN2_BASE_ZERO,
                            MALBOLGE_GUEST_MATH_ATAN2_RATIO_ADD, UINT32_C(0),
                            UINT32_C(0), UINT32_C(0))) {
    return 1;
  }
  if (!malbolge_guest_math_atan2_reconstruction(
          UINT64_C(0x4000000000000000), UINT64_C(0x3ff0000000000000),
          &output) ||
      !reconstruction_equal(&output, MALBOLGE_GUEST_MATH_ATAN2_BASE_HALF_PI,
                            MALBOLGE_GUEST_MATH_ATAN2_RATIO_SUBTRACT,
                            UINT32_C(0), UINT32_C(1), UINT32_C(0))) {
    return 2;
  }
  if (!malbolge_guest_math_atan2_reconstruction(
          UINT64_C(0x3ff0000000000000), UINT64_C(0xc000000000000000),
          &output) ||
      !reconstruction_equal(&output, MALBOLGE_GUEST_MATH_ATAN2_BASE_PI,
                            MALBOLGE_GUEST_MATH_ATAN2_RATIO_SUBTRACT,
                            UINT32_C(0), UINT32_C(0), UINT32_C(1))) {
    return 3;
  }
  if (!malbolge_guest_math_atan2_reconstruction(
          UINT64_C(0xc000000000000000), UINT64_C(0xbff0000000000000),
          &output) ||
      !reconstruction_equal(&output, MALBOLGE_GUEST_MATH_ATAN2_BASE_HALF_PI,
                            MALBOLGE_GUEST_MATH_ATAN2_RATIO_ADD, UINT32_C(1),
                            UINT32_C(1), UINT32_C(1))) {
    return 4;
  }

  output.ratio.numerator_significand = UINT64_C(0x55);
  output.base = MALBOLGE_GUEST_MATH_ATAN2_BASE_PI;
  output.ratio_operation = MALBOLGE_GUEST_MATH_ATAN2_RATIO_ADD;
  output.negative = UINT32_C(9);
  if (malbolge_guest_math_atan2_reconstruction(
          UINT64_C(0), UINT64_C(0x3ff0000000000000), &output) ||
      output.ratio.numerator_significand != UINT64_C(0x55) ||
      output.base != MALBOLGE_GUEST_MATH_ATAN2_BASE_PI ||
      output.ratio_operation != MALBOLGE_GUEST_MATH_ATAN2_RATIO_ADD ||
      output.negative != UINT32_C(9) ||
      malbolge_guest_math_atan2_reconstruction(
          UINT64_C(0x3ff0000000000000), UINT64_C(0x3ff0000000000000), NULL)) {
    return 5;
  }
  return 0;
}

static int reduction_equal(
    const MalbolgeGuestMathAtanKernelReduction *value, uint64_t numerator,
    uint64_t denominator, int32_t exponent_delta,
    MalbolgeGuestMathAtanBase base,
    MalbolgeGuestMathAtan2RatioOperation operation) {
  return value->residual.numerator == numerator &&
         value->residual.denominator == denominator &&
         value->residual.exponent_delta == exponent_delta &&
         value->base == base && value->ratio_operation == operation;
}

static int test_atan_reduction(void) {
  MalbolgeGuestMathAtan2KernelInput input = {
      UINT64_C(0x0010000000000000), UINT64_C(0x0010000000000000),
      INT32_C(-2), UINT32_C(0), UINT32_C(0), UINT32_C(0)};
  MalbolgeGuestMathAtanKernelReduction output;

  if (!malbolge_guest_math_atan_kernel_reduction(&input, &output) ||
      !reduction_equal(&output, UINT64_C(0x0010000000000000),
                       UINT64_C(0x0010000000000000), INT32_C(-2),
                       MALBOLGE_GUEST_MATH_ATAN_BASE_ZERO,
                       MALBOLGE_GUEST_MATH_ATAN2_RATIO_ADD)) {
    return 1;
  }
  input.exponent_delta = INT32_C(0);
  if (!malbolge_guest_math_atan_kernel_reduction(&input, &output) ||
      !reduction_equal(&output, UINT64_C(0),
                       UINT64_C(0x0020000000000000), INT32_C(0),
                       MALBOLGE_GUEST_MATH_ATAN_BASE_QUARTER_PI,
                       MALBOLGE_GUEST_MATH_ATAN2_RATIO_SUBTRACT)) {
    return 2;
  }
  input.numerator_significand = UINT64_C(0x0016000000000000);
  input.denominator_significand = UINT64_C(0x0010000000000000);
  input.exponent_delta = INT32_C(-1);
  if (!malbolge_guest_math_atan_kernel_reduction(&input, &output) ||
      !reduction_equal(&output, UINT64_C(0x000a000000000000),
                       UINT64_C(0x0036000000000000), INT32_C(0),
                       MALBOLGE_GUEST_MATH_ATAN_BASE_QUARTER_PI,
                       MALBOLGE_GUEST_MATH_ATAN2_RATIO_SUBTRACT)) {
    return 3;
  }

  output.residual.numerator = UINT64_C(0x55);
  output.base = MALBOLGE_GUEST_MATH_ATAN_BASE_QUARTER_PI;
  input.numerator_significand = UINT64_C(0x0010000000000001);
  input.denominator_significand = UINT64_C(0x0010000000000000);
  input.exponent_delta = INT32_C(0);
  if (malbolge_guest_math_atan_kernel_reduction(&input, &output) ||
      output.residual.numerator != UINT64_C(0x55) ||
      output.base != MALBOLGE_GUEST_MATH_ATAN_BASE_QUARTER_PI ||
      malbolge_guest_math_atan_kernel_reduction(NULL, &output) ||
      malbolge_guest_math_atan_kernel_reduction(&input, NULL)) {
    return 4;
  }
  return 0;
}

static int plan_equal(const MalbolgeGuestMathAtan2KernelPlan *value,
                      uint64_t numerator, uint64_t denominator,
                      int32_t exponent_delta,
                      MalbolgeGuestMathAtan2QuarterPiBase quarter_pi_base,
                      MalbolgeGuestMathAtan2RatioOperation operation,
                      uint32_t negative) {
  return value->residual.numerator == numerator &&
         value->residual.denominator == denominator &&
         value->residual.exponent_delta == exponent_delta &&
         value->quarter_pi_base == quarter_pi_base &&
         value->ratio_operation == operation && value->negative == negative;
}

static int test_kernel_plan(void) {
  MalbolgeGuestMathAtan2KernelPlan output;
  const uint64_t one_third_numerator = UINT64_C(0x0010000000000000);
  const uint64_t one_third_denominator = UINT64_C(0x0030000000000000);

  if (!malbolge_guest_math_atan2_kernel_plan(
          UINT64_C(0x3ff0000000000000), UINT64_C(0x4000000000000000),
          &output) ||
      !plan_equal(&output, one_third_numerator, one_third_denominator,
                  INT32_C(0), MALBOLGE_GUEST_MATH_ATAN2_QUARTER_BASE_ONE,
                  MALBOLGE_GUEST_MATH_ATAN2_RATIO_SUBTRACT, UINT32_C(0))) {
    return 1;
  }
  if (!malbolge_guest_math_atan2_kernel_plan(
          UINT64_C(0x4000000000000000), UINT64_C(0x3ff0000000000000),
          &output) ||
      !plan_equal(&output, one_third_numerator, one_third_denominator,
                  INT32_C(0), MALBOLGE_GUEST_MATH_ATAN2_QUARTER_BASE_ONE,
                  MALBOLGE_GUEST_MATH_ATAN2_RATIO_ADD, UINT32_C(0))) {
    return 2;
  }
  if (!malbolge_guest_math_atan2_kernel_plan(
          UINT64_C(0x3ff0000000000000), UINT64_C(0xc000000000000000),
          &output) ||
      !plan_equal(&output, one_third_numerator, one_third_denominator,
                  INT32_C(0), MALBOLGE_GUEST_MATH_ATAN2_QUARTER_BASE_THREE,
                  MALBOLGE_GUEST_MATH_ATAN2_RATIO_ADD, UINT32_C(0))) {
    return 3;
  }
  if (!malbolge_guest_math_atan2_kernel_plan(
          UINT64_C(0xc000000000000000), UINT64_C(0xbff0000000000000),
          &output) ||
      !plan_equal(&output, one_third_numerator, one_third_denominator,
                  INT32_C(0), MALBOLGE_GUEST_MATH_ATAN2_QUARTER_BASE_THREE,
                  MALBOLGE_GUEST_MATH_ATAN2_RATIO_SUBTRACT, UINT32_C(1))) {
    return 4;
  }
  if (!malbolge_guest_math_atan2_kernel_plan(
          UINT64_C(0x3ff0000000000000), UINT64_C(0x4010000000000000),
          &output) ||
      !plan_equal(&output, UINT64_C(0x0010000000000000),
                  UINT64_C(0x0010000000000000), INT32_C(-2),
                  MALBOLGE_GUEST_MATH_ATAN2_QUARTER_BASE_ZERO,
                  MALBOLGE_GUEST_MATH_ATAN2_RATIO_ADD, UINT32_C(0))) {
    return 5;
  }

  output.residual.numerator = UINT64_C(0x55);
  output.residual.denominator = UINT64_C(0xaa);
  output.residual.exponent_delta = INT32_C(7);
  output.quarter_pi_base = MALBOLGE_GUEST_MATH_ATAN2_QUARTER_BASE_FOUR;
  output.ratio_operation = MALBOLGE_GUEST_MATH_ATAN2_RATIO_ADD;
  output.negative = UINT32_C(9);
  if (malbolge_guest_math_atan2_kernel_plan(
          UINT64_C(0), UINT64_C(0x3ff0000000000000), &output) ||
      output.residual.numerator != UINT64_C(0x55) ||
      output.residual.denominator != UINT64_C(0xaa) ||
      output.residual.exponent_delta != INT32_C(7) ||
      output.quarter_pi_base != MALBOLGE_GUEST_MATH_ATAN2_QUARTER_BASE_FOUR ||
      output.ratio_operation != MALBOLGE_GUEST_MATH_ATAN2_RATIO_ADD ||
      output.negative != UINT32_C(9) ||
      malbolge_guest_math_atan2_kernel_plan(
          UINT64_C(0x3ff0000000000000), UINT64_C(0x3ff0000000000000), NULL)) {
    return 6;
  }
  return 0;
}

static int test_ratio_rounding(void) {
  MalbolgeGuestMathAtan2KernelInput input = {
      UINT64_C(0x0010000000000000), UINT64_C(0x0010000000000000),
      INT32_C(0), UINT32_C(0), UINT32_C(0), UINT32_C(0)};
  uint64_t bits = UINT64_C(0x55);

  if (!malbolge_guest_math_ratio_nearest_binary64(&input, &bits) ||
      bits != UINT64_C(0x3ff0000000000000)) {
    return 1;
  }
  input.exponent_delta = INT32_C(-1);
  if (!malbolge_guest_math_ratio_nearest_binary64(&input, &bits) ||
      bits != UINT64_C(0x3fe0000000000000)) {
    return 2;
  }
  input.exponent_delta = INT32_C(-1074);
  if (!malbolge_guest_math_ratio_nearest_binary64(&input, &bits) ||
      bits != UINT64_C(0x0000000000000001)) {
    return 3;
  }
  input.numerator_significand = UINT64_C(0x001ffffffffffffe);
  input.denominator_significand = UINT64_C(0x0010000000000000);
  input.exponent_delta = INT32_C(-1);
  if (!malbolge_guest_math_ratio_nearest_binary64(&input, &bits) ||
      bits != UINT64_C(0x3feffffffffffffe)) {
    return 4;
  }
  input.numerator_significand = UINT64_C(0x0010000000000000);
  input.denominator_significand = UINT64_C(0x001fffffffffffff);
  input.exponent_delta = INT32_C(-2097);
  if (!malbolge_guest_math_ratio_nearest_binary64(&input, &bits) ||
      bits != UINT64_C(0)) {
    return 5;
  }
  bits = UINT64_C(0x55);
  input.exponent_delta = INT32_C(1);
  if (malbolge_guest_math_ratio_nearest_binary64(&input, &bits) ||
      bits != UINT64_C(0x55)) {
    return 6;
  }
  input.exponent_delta = INT32_C(-2098);
  if (malbolge_guest_math_ratio_nearest_binary64(&input, &bits) ||
      bits != UINT64_C(0x55)) {
    return 7;
  }
  input.exponent_delta = INT32_C(0);
  input.numerator_significand = UINT64_C(0x0010000000000001);
  input.denominator_significand = UINT64_C(0x0010000000000000);
  if (malbolge_guest_math_ratio_nearest_binary64(&input, &bits) ||
      bits != UINT64_C(0x55) ||
      malbolge_guest_math_ratio_nearest_binary64(NULL, &bits) ||
      malbolge_guest_math_ratio_nearest_binary64(&input, NULL)) {
    return 8;
  }
  return 0;
}

int main(void) {
  MalbolgeGuestMathAtan2KernelInput output;
  const int reconstruction = test_reconstruction();
  const int reduction = test_atan_reduction();
  const int plan = test_kernel_plan();
  const int rounding = test_ratio_rounding();

  if (reconstruction != 0) {
    return 10 + reconstruction;
  }
  if (reduction != 0) {
    return 15 + reduction;
  }
  if (plan != 0) {
    return 30 + plan;
  }
  if (rounding != 0) {
    return 20 + rounding;
  }

  if (!malbolge_guest_math_atan2_kernel_input(
          UINT64_C(0x3ff0000000000000), UINT64_C(0x3ff0000000000000),
          &output) ||
      !fields_equal(&output, UINT64_C(0x0010000000000000),
                    UINT64_C(0x0010000000000000), INT32_C(0), UINT32_C(0),
                    UINT32_C(0), UINT32_C(0))) {
    return 1;
  }
  if (!malbolge_guest_math_atan2_kernel_input(
          UINT64_C(0xc000000000000000), UINT64_C(0x3ff0000000000000),
          &output) ||
      !fields_equal(&output, UINT64_C(0x0010000000000000),
                    UINT64_C(0x0010000000000000), INT32_C(-1), UINT32_C(1),
                    UINT32_C(1), UINT32_C(0))) {
    return 2;
  }
  if (!malbolge_guest_math_atan2_kernel_input(
          UINT64_C(0x0000000000000001), UINT64_C(0x3ff0000000000000),
          &output) ||
      !fields_equal(&output, UINT64_C(0x0010000000000000),
                    UINT64_C(0x0010000000000000), INT32_C(-1074),
                    UINT32_C(0), UINT32_C(0), UINT32_C(0))) {
    return 3;
  }
  if (!malbolge_guest_math_atan2_kernel_input(
          UINT64_C(0x000fffffffffffff), UINT64_C(0x0010000000000000),
          &output) ||
      !fields_equal(&output, UINT64_C(0x001ffffffffffffe),
                    UINT64_C(0x0010000000000000), INT32_C(-1), UINT32_C(0),
                    UINT32_C(0), UINT32_C(0))) {
    return 4;
  }
  if (!malbolge_guest_math_atan2_kernel_input(
          UINT64_C(0x7fefffffffffffff), UINT64_C(0x0000000000000001),
          &output) ||
      !fields_equal(&output, UINT64_C(0x0010000000000000),
                    UINT64_C(0x001fffffffffffff), INT32_C(-2097),
                    UINT32_C(1), UINT32_C(0), UINT32_C(0))) {
    return 5;
  }
  output.numerator_significand = UINT64_C(0x55);
  output.denominator_significand = UINT64_C(0xaa);
  output.exponent_delta = INT32_C(7);
  output.swapped = UINT32_C(9);
  output.y_negative = UINT32_C(9);
  output.x_negative = UINT32_C(9);
  if (malbolge_guest_math_atan2_kernel_input(
          UINT64_C(0), UINT64_C(0x3ff0000000000000), &output) ||
      output.numerator_significand != UINT64_C(0x55) ||
      output.denominator_significand != UINT64_C(0xaa) ||
      output.exponent_delta != INT32_C(7) || output.swapped != UINT32_C(9) ||
      output.y_negative != UINT32_C(9) || output.x_negative != UINT32_C(9)) {
    return 6;
  }
  if (malbolge_guest_math_atan2_kernel_input(
          UINT64_C(0x3ff0000000000000), UINT64_C(0x7ff0000000000000),
          &output) ||
      output.numerator_significand != UINT64_C(0x55) ||
      output.denominator_significand != UINT64_C(0xaa) ||
      output.exponent_delta != INT32_C(7) || output.swapped != UINT32_C(9) ||
      output.y_negative != UINT32_C(9) || output.x_negative != UINT32_C(9)) {
    return 7;
  }
  if (malbolge_guest_math_atan2_kernel_input(
          UINT64_C(0x7ff8000000000001), UINT64_C(0x3ff0000000000000),
          &output) ||
      output.numerator_significand != UINT64_C(0x55) ||
      output.denominator_significand != UINT64_C(0xaa)) {
    return 8;
  }
  if (malbolge_guest_math_atan2_kernel_input(
          UINT64_C(0x3ff0000000000000), UINT64_C(0x3ff0000000000000), NULL)) {
    return 9;
  }
  return 0;
}
