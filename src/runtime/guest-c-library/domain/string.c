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
//   - Guest implementations of admitted narrow null-terminated string routines.
// - Must-Not:
//   - Use locale, allocation, host libc, or hidden platform string services.
// - Allows:
//   - Inputs: valid guest byte strings admitted by the public string contract.
//   - Outputs: standard narrow-string lengths, comparisons, and destinations.
//   - Side effects: writes only through caller-provided destination strings.
// - Split-When:
//   - Split when another string family gains an independent semantic contract.
// - Merge-When:
//   - Merge when another guest module owns these exact narrow-string semantics.
// - Summary:
//   - Freestanding guest implementations of the v1 narrow-string subset.
// - Description:
//   - Operates bytewise and therefore has no locale or host encoding
//     dependency.
// - Usage:
//   - Linked into guest programs that reference admitted string functions.
// - Defaults:
//   - Standard C destination-capacity and termination preconditions apply.
//

//! Guest-owned narrow-string primitives with bytewise deterministic semantics.

#include "string.h"

size_t strlen(const char *text)
{
    size_t length = 0U;

    while (text[length] != '\0')
    {
        ++length;
    }
    return length;
}

int strcmp(const char *left, const char *right)
{
    size_t index = 0U;

    while (left[index] != '\0' && left[index] == right[index])
    {
        ++index;
    }
    return (int)(unsigned char)left[index] -
           (int)(unsigned char)right[index];
}

char *strcpy(char *restrict destination, const char *restrict source)
{
    size_t index = 0U;

    do
    {
        destination[index] = source[index];
    } while (source[index++] != '\0');
    return destination;
}

char *strncpy(char *restrict destination, const char *restrict source,
              size_t count)
{
    size_t index = 0U;

    while (index < count && source[index] != '\0')
    {
        destination[index] = source[index];
        ++index;
    }
    while (index < count)
    {
        destination[index] = '\0';
        ++index;
    }
    return destination;
}

char *strcat(char *restrict destination, const char *restrict source)
{
    size_t out = strlen(destination);
    size_t in = 0U;

    do
    {
        destination[out++] = source[in];
    } while (source[in++] != '\0');
    return destination;
}
