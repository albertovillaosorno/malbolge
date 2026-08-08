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
//   - Guest implementations of byte-copy, move, fill, and comparison routines.
// - Must-Not:
//   - Call host libc, allocate storage, or depend on host pointer
//     representation.
// - Allows:
//   - Inputs: valid guest object ranges described by the public string
//     contract.
//   - Outputs: standard memory-routine return values and byte comparisons.
//   - Side effects: writes only within caller-supplied destination ranges.
// - Split-When:
//   - Split when one memory primitive requires an independent implementation.
// - Merge-When:
//   - Merge when another guest module owns these exact memory semantics.
// - Summary:
//   - Freestanding guest implementations of standard memory primitives.
// - Description:
//   - Uses byte loops only, preserving the deterministic guest object model.
// - Usage:
//   - Linked into guest programs that reference the admitted string surface.
// - Defaults:
//   - Standard C preconditions remain caller obligations.
//

//! Guest-owned byte memory primitives with no external library dependency.

#include "string.h"
#include <stdint.h>

void *memcpy(void *restrict destination, const void *restrict source,
             size_t count)
{
    unsigned char *out = (unsigned char *)destination;
    const unsigned char *in = (const unsigned char *)source;
    size_t index;

    for (index = 0; index < count; ++index)
    {
        out[index] = in[index];
    }
    return destination;
}

void *memmove(void *destination, const void *source, size_t count)
{
    unsigned char *out = (unsigned char *)destination;
    const unsigned char *in = (const unsigned char *)source;
    uintptr_t out_address = (uintptr_t)destination;
    uintptr_t in_address = (uintptr_t)source;
    size_t index;

    if (out == in || count == 0U)
    {
        return destination;
    }
    if (out_address < in_address)
    {
        for (index = 0; index < count; ++index)
        {
            out[index] = in[index];
        }
        return destination;
    }
    index = count;
    while (index != 0U)
    {
        --index;
        out[index] = in[index];
    }
    return destination;
}

void *memset(void *destination, int value, size_t count)
{
    unsigned char *out = (unsigned char *)destination;
    unsigned char byte = (unsigned char)value;
    size_t index;

    for (index = 0; index < count; ++index)
    {
        out[index] = byte;
    }
    return destination;
}

int memcmp(const void *left, const void *right, size_t count)
{
    const unsigned char *a = (const unsigned char *)left;
    const unsigned char *b = (const unsigned char *)right;
    size_t index;

    for (index = 0; index < count; ++index)
    {
        if (a[index] < b[index])
        {
            return -1;
        }
        if (a[index] > b[index])
        {
            return 1;
        }
    }
    return 0;
}
