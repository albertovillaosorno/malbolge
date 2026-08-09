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
//   - Positive source evidence for executable guest memory/string routines.
// - Must-Not:
//   - Use allocation, streams, formatting, math, or host-dependent facilities.
// - Allows:
//   - Inputs: local byte arrays and narrow strings.
//   - Outputs: one deterministic integer result.
//   - Side effects: writes only to local arrays.
// - Split-When:
//   - Split when another guest-library family becomes executable.
// - Merge-When:
//   - Merge when another fixture owns this exact positive libc surface.
// - Summary:
//   - Accepted memory and narrow-string guest libc fixture.
// - Description:
//   - References all nine executable memory/string routines.
// - Usage:
//   - Consumed by guest-libc source and manual-validator regressions.
// - Defaults:
//   - Any unavailable routine belongs in the rejected fixture corpus.
//

//! Positive malbolge-libc-v1 executable routine coverage.

#include <string.h>

int libc_memory_string_probe(void) {
  unsigned char source[4] = {1U, 2U, 3U, 4U};
  unsigned char destination[4];
  char first[12] = "ab";
  char second[8];
  char padded[5];

  (void)memcpy(destination, source, sizeof(source));
  (void)memmove(destination + 1, destination, 3U);
  (void)memset(destination, 0, 1U);
  (void)strcpy(second, "guest");
  (void)strncpy(padded, "x", sizeof(padded));
  (void)strcat(first, "cd");
  return memcmp(source, destination, 1U) + (int)strlen(second) +
         strcmp(first, "abcd");
}
