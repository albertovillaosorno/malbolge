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
//   - Executable no-CRT behavior checks for the available guest libc subset.
// - Must-Not:
//   - Link a host C runtime or test routines still marked unavailable.
// - Allows:
//   - Inputs: fixed in-process byte arrays and narrow strings.
//   - Outputs: zero on exact semantic agreement, otherwise a stable code.
//   - Side effects: writes only to local automatic arrays.
// - Split-When:
//   - Split when another libc family requires an independent executable probe.
// - Merge-When:
//   - Merge when another harness owns these exact guest-library semantics.
// - Summary:
//   - No-CRT executable evidence for guest memory and string routines.
// - Description:
//   - Exercises all currently available malbolge-libc-v1 function symbols.
// - Usage:
//   - Compiled with the pinned Clang and linked with lld-link `/nodefaultlib`.
// - Defaults:
//   - Any semantic mismatch returns a distinct nonzero process status.
//

//! Executable guest-libc regression with no host C runtime dependency.

#include "string.h"

static int same_bytes(const unsigned char *left,
                      const unsigned char *right,
                      size_t count)
{
    return memcmp(left, right, count) == 0;
}

int probe_entry(void)
{
    unsigned char source[6] = {1U, 2U, 3U, 4U, 5U, 6U};
    unsigned char copied[6] = {0U, 0U, 0U, 0U, 0U, 0U};
    unsigned char moved[7] = {1U, 2U, 3U, 4U, 5U, 6U, 7U};
    unsigned char expected_move[7] = {1U, 2U, 1U, 2U, 3U, 4U, 5U};
    char text[16] = "abc";
    char copy[8];
    char bounded[6] = {'x', 'x', 'x', 'x', 'x', 'x'};

    if (memcpy(copied, source, sizeof(source)) != copied ||
        !same_bytes(copied, source, sizeof(source)))
    {
        return 1;
    }
    if (memset(copied, 0xa5, 3U) != copied || copied[0] != 0xa5U ||
        copied[1] != 0xa5U || copied[2] != 0xa5U)
    {
        return 2;
    }
    if (memmove(moved + 2, moved, 5U) != moved + 2 ||
        !same_bytes(moved, expected_move, sizeof(moved)))
    {
        return 3;
    }
    if (strlen(text) != 3U || strcmp("abc", "abc") != 0 ||
        strcmp("abc", "abd") >= 0 || strcmp("abd", "abc") <= 0)
    {
        return 4;
    }
    if (strcpy(copy, "guest") != copy || strcmp(copy, "guest") != 0)
    {
        return 5;
    }
    if (strncpy(bounded, "ab", sizeof(bounded)) != bounded ||
        bounded[0] != 'a' || bounded[1] != 'b' || bounded[2] != '\0' ||
        bounded[5] != '\0')
    {
        return 6;
    }
    if (strcat(text, "def") != text || strcmp(text, "abcdef") != 0)
    {
        return 7;
    }
    return 0;
}
