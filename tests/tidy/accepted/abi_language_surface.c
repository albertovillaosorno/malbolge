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

//! Confirms difficult standard C constructs are not blanket ABI exclusions.

#include <stdarg.h>
#include <stddef.h>

struct Pair {
    long left;
    long right;
};

struct FlexBytes {
    size_t length;
    unsigned char bytes[];
};

static _Alignas(16) unsigned char aligned_storage[16];

static long recursive_sum(unsigned value)
{
    return value == 0U ? 0L : (long)value + recursive_sum(value - 1U);
}

static long add_one(long value)
{
    return value + 1L;
}

static long indirect(long (*operation)(long), long value)
{
    return operation(value);
}

static long variadic_sum(unsigned count, ...)
{
    va_list arguments;
    long result = 0L;
    unsigned index = 0U;
    va_start(arguments, count);
    for (index = 0U; index < count; ++index) {
        result += va_arg(arguments, long);
    }
    va_end(arguments);
    return result;
}

static long vla_sum(size_t count, const long values[count])
{
    long result = 0L;
    size_t index = 0U;
    for (index = 0U; index < count; ++index) {
        result += values[index];
    }
    return result;
}

long abi_language_surface(void)
{
    const long values[] = {1L, 2L, 3L};
    aligned_storage[0] = 1U;
    return recursive_sum(3U) + indirect(add_one, 4L) +
           variadic_sum(2U, 5L, 6L) + vla_sum(3U, values);
}
