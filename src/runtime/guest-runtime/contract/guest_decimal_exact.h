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
//   - Exact canonical decimal magnitude for finite ABI binary64/binary128 bits.
// - Must-Not:
//   - Use host floating arithmetic, allocation, locale, or native formatting.
// - Allows:
//   - Inputs: one raw binary64 or low/high binary128 representation.
//   - Outputs: exact decimal digits plus a signed base-ten power.
//   - Side effects: caller-owned result publication after complete conversion.
// - Split-When:
//   - Another floating representation requires independently bounded scratch.
// - Merge-When:
//   - Decimal floating formatting directly owns this exact representation.
// - Summary:
//   - Converts finite binary floating magnitude into bounded exact decimal
//     form.
// - Description:
//   - Uses base-10000 limbs and 32-bit-only multiply/carry arithmetic.
// - Usage:
//   - Decimal printf conversions consume the exact digits before rounding.
// - Defaults:
//   - Zero is digits "0" with shift zero; infinities and NaNs fail closed.
//

//! Exact bounded decimal representation of finite binary64/binary128 magnitude.

#ifndef MALBOLGE_GUEST_DECIMAL_EXACT_H
#define MALBOLGE_GUEST_DECIMAL_EXACT_H

#include "guest_runtime.h"

#include <stdint.h>

#define MALBOLGE_GUEST_DECIMAL_BINARY64_DIGITS UINT32_C(768)
#define MALBOLGE_GUEST_DECIMAL_BINARY128_DIGITS UINT32_C(11564)

typedef struct MalbolgeGuestDecimalExact {
  char digits[768];
  uint32_t digit_count;
  int32_t decimal_shift;
} MalbolgeGuestDecimalExact;

typedef struct MalbolgeGuestDecimalExact128 {
  char digits[11564];
  uint32_t digit_count;
  int32_t decimal_shift;
} MalbolgeGuestDecimalExact128;

MalbolgeGuestRuntimeStatus malbolge_guest_decimal_from_binary64(
    uint64_t bits, MalbolgeGuestDecimalExact *result);
MalbolgeGuestRuntimeStatus malbolge_guest_decimal_from_binary128(
    uint64_t low, uint64_t high, MalbolgeGuestDecimalExact128 *result);

#endif
