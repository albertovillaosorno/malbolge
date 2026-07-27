// Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier: MIT
//
// Freestanding behavior harness. This file contains no DOOM source code.

#include "m_fixed.h"
#include <stddef.h>

int _fltused = 0;

int abs(int value)
{
    return value < 0 ? -value : value;
}

void I_Error(void)
{
    __builtin_trap();
}

void *M_Memcpy(void *destination, const void *source, size_t length)
{
    unsigned char *out = (unsigned char *)destination;
    const unsigned char *in = (const unsigned char *)source;
    size_t index;

    for (index = 0; index < length; ++index)
    {
        out[index] = in[index];
    }
    return destination;
}

int probe_entry(void)
{
    fixed_t product = FixedMul((fixed_t)98304, (fixed_t)131072);
    fixed_t quotient = FixedDiv((fixed_t)458752, (fixed_t)131072);

    return (int)(((unsigned int)product >> 8) ^ ((unsigned int)quotient >> 4));
}
