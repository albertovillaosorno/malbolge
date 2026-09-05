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
//   - Exact canonical decimal magnitude for finite ABI binary64 bit patterns.
// - Must-Not:
//   - Use host floating arithmetic, allocation, locale, or native formatting.
// - Allows:
//   - Inputs: one raw binary64 representation, including either sign bit.
//   - Outputs: exact decimal digits plus a signed base-ten power.
//   - Side effects: caller-owned result publication after complete conversion.
// - Split-When:
//   - Binary128 exact-decimal geometry requires materially larger scratch.
// - Merge-When:
//   - Decimal floating formatting directly owns this exact representation.
// - Summary:
//   - Converts finite binary64 magnitude into bounded exact decimal form.
// - Description:
//   - Uses base-10000 limbs and 32-bit-only multiply/carry arithmetic.
// - Usage:
//   - Decimal printf conversions consume the exact digits before rounding.
// - Defaults:
//   - Zero is digits "0" with shift zero; infinities and NaNs fail closed.
//

//! Exact bounded decimal representation of finite binary64 magnitude.

#ifndef MALBOLGE_GUEST_DECIMAL_EXACT_H
#define MALBOLGE_GUEST_DECIMAL_EXACT_H

#include "guest_runtime.h"

#include <stdint.h>

#define MALBOLGE_GUEST_DECIMAL_BINARY64_DIGITS UINT32_C(768)

typedef struct MalbolgeGuestDecimalExact {
  char digits[768];
  uint32_t digit_count;
  int32_t decimal_shift;
} MalbolgeGuestDecimalExact;

MalbolgeGuestRuntimeStatus malbolge_guest_decimal_from_binary64(
    uint64_t bits, MalbolgeGuestDecimalExact *result);

#endif
