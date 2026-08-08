// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - One deterministic guest-C ABI fixture for tools/tidy regression evidence.
// - Must-Not:
//   - Depend on native host ABI, operating-system APIs, or external state.
// - Allows:
//   - Inputs: compile-time C23 language and ABI evidence only.
//   - Outputs: deterministic accept/reject evidence for malbolge-c32-v1.
//   - Side effects: none.
// - Split-When:
//   - Split when the fixture covers an independent ABI diagnostic family.
// - Merge-When:
//   - Merge when another fixture exercises the exact same boundary condition.
// - Summary:
//   - Exercises one malbolge-c32-v1 ABI boundary.
// - Description:
//   - Compiled or inspected only by explicit guest-C compatibility tests.
// - Usage:
//   - Selected explicitly by the deterministic C ABI regression suite.
// - Defaults:
//   - No host ABI behavior is authoritative.
//

//! Confirms canonical scalar, pointer, aggregate, and endian layout.

#include <limits.h>
#include <stddef.h>

struct AbiLayoutProbe {
    char c;
    short s;
    int i;
    long l;
    long long ll;
    float f;
    double d;
    long double ld;
    void *p;
};

static_assert(CHAR_BIT == 8);
static_assert(sizeof(_Bool) == 1);
static_assert(sizeof(char) == 1);
static_assert(sizeof(short) == 2);
static_assert(sizeof(int) == 4);
static_assert(sizeof(long) == 4);
static_assert(sizeof(long long) == 8);
static_assert(sizeof(float) == 4);
static_assert(sizeof(double) == 8);
static_assert(sizeof(long double) == 16);
static_assert(sizeof(void *) == 4);
static_assert(sizeof(void (*)(void)) == 4);
static_assert(sizeof(size_t) == 4);
static_assert(sizeof(ptrdiff_t) == 4);
static_assert(sizeof(wchar_t) == 4);
static_assert(alignof(long long) == 8);
static_assert(alignof(long double) == 16);
static_assert(alignof(struct AbiLayoutProbe) == 16);
static_assert(sizeof(struct AbiLayoutProbe) == 80);
static_assert(__builtin_offsetof(struct AbiLayoutProbe, c) == 0);
static_assert(__builtin_offsetof(struct AbiLayoutProbe, s) == 2);
static_assert(__builtin_offsetof(struct AbiLayoutProbe, i) == 4);
static_assert(__builtin_offsetof(struct AbiLayoutProbe, l) == 8);
static_assert(__builtin_offsetof(struct AbiLayoutProbe, ll) == 16);
static_assert(__builtin_offsetof(struct AbiLayoutProbe, f) == 24);
static_assert(__builtin_offsetof(struct AbiLayoutProbe, d) == 32);
static_assert(__builtin_offsetof(struct AbiLayoutProbe, ld) == 48);
static_assert(__builtin_offsetof(struct AbiLayoutProbe, p) == 64);
static_assert((char)-1 < 0);
static_assert(INT_MIN == (-2147483647 - 1));
static_assert((-4 >> 1) == -2);
static_assert(__BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__);

enum SignedEnum {
    SIGNED_NEGATIVE = -1,
    SIGNED_POSITIVE = 1
};

enum UnsignedEnum {
    UNSIGNED_LARGE = 4294967295U
};

enum ByteEnum : unsigned char {
    BYTE_VALUE = 255
};

static_assert(sizeof(enum SignedEnum) == 4);
static_assert(sizeof(enum UnsignedEnum) == 4);
static_assert((enum UnsignedEnum)-1 > 0);
static_assert(sizeof(enum ByteEnum) == 1);
