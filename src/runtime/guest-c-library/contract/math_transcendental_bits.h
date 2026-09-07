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
//   - Exact raw-binary64 preclassification for transcendental guest math.
// - Must-Not:
//   - Approximate finite transcendental values or change libc availability.
// - Allows:
//   - Inputs: raw binary64 words and one admitted unary operation identity.
//   - Outputs: exact results, symbolic atan2 reconstruction, or ratio bits.
//   - Side effects: none.
// - Split-When:
//   - Range reduction or approximation kernels gain independent proof policy.
// - Merge-When:
//   - Complete correctly-rounded transcendental implementations own this step.
// - Summary:
//   - Resolves only exact transcendental edge cases before numerical kernels.
// - Description:
//   - Resolves proved small-angle, small-ratio, and special-case results.
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
int malbolge_guest_math_ratio_nearest_binary64(
    const MalbolgeGuestMathAtan2KernelInput *input, uint64_t *output_bits);

#endif
