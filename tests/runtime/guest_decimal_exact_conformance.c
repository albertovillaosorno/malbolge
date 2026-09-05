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
//   - Independent exact-decimal vectors for finite binary64/binary128 bits.
// - Must-Not:
//   - Use native floating conversion or host decimal formatting as an oracle.
// - Allows:
//   - Inputs: fixed raw binary64 and binary128 representations.
//   - Outputs: zero only when exact canonical digits and shift match vectors.
//   - Side effects: test-local result storage only.
// - Split-When:
//   - Decimal format spelling gains separate conversion-level vectors.
// - Merge-When:
//   - Complete decimal-format tests own this decomposition evidence directly.
// - Summary:
//   - Locks zero, fractions, subnormal/normal edges, and maximum finite values.
// - Description:
//   - Expected digits are exact integer arithmetic facts, not libc output.
// - Usage:
//   - Built by guest-runtime C conformance and direct strict local validation.
// - Defaults:
//   - Either sign bit has the same magnitude representation.
//

//! Exact finite binary64/binary128-to-decimal decomposition vectors.

#include "guest_decimal_exact.h"

#include <stddef.h>
#include <stdint.h>

static int same_digits(const MalbolgeGuestDecimalExact *value,
                       const char *expected) {
  uint32_t index = UINT32_C(0);

  while (index < value->digit_count && expected[index] != '\0') {
    if (value->digits[index] != expected[index]) {
      return 0;
    }
    ++index;
  }
  return index == value->digit_count && expected[index] == '\0';
}

static int check(uint64_t bits, const char *digits, int32_t shift) {
  MalbolgeGuestDecimalExact value;

  return malbolge_guest_decimal_from_binary64(bits, &value) ==
             MALBOLGE_GUEST_RUNTIME_VALID &&
         value.decimal_shift == shift && same_digits(&value, digits);
}


static int same_prefix128(const MalbolgeGuestDecimalExact128 *value,
                          const char *expected) {
  uint32_t index = UINT32_C(0);

  while (expected[index] != '\0') {
    if (index >= value->digit_count ||
        value->digits[index] != expected[index]) {
      return 0;
    }
    ++index;
  }
  return 1;
}

static int same_suffix128(const MalbolgeGuestDecimalExact128 *value,
                          const char *expected) {
  uint32_t count = UINT32_C(0);
  uint32_t index = UINT32_C(0);

  while (expected[count] != '\0') {
    ++count;
  }
  if (count > value->digit_count) {
    return 0;
  }
  index = value->digit_count - count;
  count = UINT32_C(0);
  while (expected[count] != '\0') {
    if (value->digits[index + count] != expected[count]) {
      return 0;
    }
    ++count;
  }
  return 1;
}

static int check128(uint64_t low, uint64_t high, const char *digits,
                    int32_t shift) {
  MalbolgeGuestDecimalExact128 value;
  uint32_t index = UINT32_C(0);

  if (malbolge_guest_decimal_from_binary128(low, high, &value) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      value.decimal_shift != shift) {
    return 0;
  }
  while (index < value.digit_count && digits[index] != '\0') {
    if (value.digits[index] != digits[index]) {
      return 0;
    }
    ++index;
  }
  return index == value.digit_count && digits[index] == '\0';
}

static int test_binary128(void) {
  MalbolgeGuestDecimalExact128 value;

  if (!check128(UINT64_C(0), UINT64_C(0), "0", INT32_C(0)) ||
      !check128(UINT64_C(0), UINT64_C(0x8000000000000000), "0", INT32_C(0)) ||
      !check128(UINT64_C(0), UINT64_C(0x3fff000000000000), "1", INT32_C(0)) ||
      !check128(UINT64_C(0), UINT64_C(0x3fff800000000000), "15",
                INT32_C(-1)) ||
      !check128(UINT64_C(0), UINT64_C(0x4002400000000000), "1", INT32_C(1))) {
    return 1;
  }
  if (malbolge_guest_decimal_from_binary128(UINT64_C(1), UINT64_C(0), &value) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      value.digit_count != UINT32_C(11529) ||
      value.decimal_shift != INT32_C(-16494) ||
      !same_prefix128(&value,
                      "647517511943802511092443895822764655249956933803") ||
      !same_suffix128(&value,
                      "243575463379929857410388649441301822662353515625")) {
    return 2;
  }
  if (malbolge_guest_decimal_from_binary128(
          UINT64_MAX, UINT64_C(0x0001ffffffffffff), &value) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      value.digit_count != UINT32_C(11563) ||
      value.decimal_shift != INT32_C(-16494) ||
      !same_prefix128(
          &value,
          "6724206286224187012525355634643504557678646745890431387773758636") ||
      !same_suffix128(
          &value,
          "6943825085925512756424536620070142589611350558698177337646484375")) {
    return 3;
  }
  if (malbolge_guest_decimal_from_binary128(
          UINT64_MAX, UINT64_C(0x7ffeffffffffffff), &value) !=
          MALBOLGE_GUEST_RUNTIME_VALID ||
      value.digit_count != UINT32_C(4933) ||
      value.decimal_shift != INT32_C(0) ||
      !same_prefix128(&value,
                      "118973149535723176508575932662800701619646905264") ||
      !same_suffix128(&value,
                      "341763535189105548847634608972381760403137363968")) {
    return 4;
  }
  if (malbolge_guest_decimal_from_binary128(
          UINT64_C(0), UINT64_C(0x7fff000000000000), &value) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      malbolge_guest_decimal_from_binary128(
          UINT64_C(1), UINT64_C(0x7fff800000000000), &value) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      malbolge_guest_decimal_from_binary128(UINT64_C(0), UINT64_C(0), NULL) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT) {
    return 5;
  }
  return 0;
}

int main(void) {
  MalbolgeGuestDecimalExact value;
  const int binary128 = test_binary128();

  if (!check(UINT64_C(0), "0", INT32_C(0)) ||
      !check(UINT64_C(0x8000000000000000), "0", INT32_C(0))) {
    return 1;
  }
  if (!check(UINT64_C(0x3ff0000000000000), "1", INT32_C(0)) ||
      !check(UINT64_C(0x4024000000000000), "1", INT32_C(1)) ||
      !check(UINT64_C(0x3ff8000000000000), "15", INT32_C(-1))) {
    return 2;
  }
  if (!check(UINT64_C(0x3fb999999999999a),
             "1000000000000000055511151231257827021181583404541015625",
             INT32_C(-55))) {
    return 3;
  }
  if (!check(UINT64_C(1),
             "494065645841246544176568792868221372365059802614324764425585"
             "682500675507270208751865299836361635992379796564695445717730"
             "926656710355939796398774796010781878126300713190311404527845"
             "817167848982103688718636056998730723050006387409153564984387"
             "312473397273169615140031715385398074126238565591171026658556"
             "686768187039560310624931945271591492455329305456544401127480"
             "129709999541931989409080416563324524757147869014726780159355"
             "238611550134803526493472019379026810710749170333222684475333"
             "572083243193609238289345836806010601150616980975307834227731"
             "832924790498252473077637592724787465608477820373446969953364"
             "701797267771758512566055119913150489110145103786273816725095"
             "583738973359899366480994116420570263709027924276754456522908"
             "7538682506419718265533447265625",
             INT32_C(-1074))) {
    return 4;
  }
  if (!check(UINT64_C(0x7fefffffffffffff),
             "179769313486231570814527423731704356798070567525844996598917"
             "476803157260780028538760589558632766878171540458953514382464"
             "234321326889464182768467546703537516986049910576551282076245"
             "490090389328944075868508455133942304583236903222948165808559"
             "332123348274797826204144723168738177180919299881250404026184"
             "124858368",
             INT32_C(0))) {
    return 5;
  }
  if (malbolge_guest_decimal_from_binary64(UINT64_C(0x7ff0000000000000),
                                           &value) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      malbolge_guest_decimal_from_binary64(UINT64_C(0x7ff8000000000001),
                                           &value) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT ||
      malbolge_guest_decimal_from_binary64(UINT64_C(0), NULL) !=
          MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT) {
    return 6;
  }
  if (binary128 != 0) {
    return 10 + binary128;
  }
  return 0;
}
