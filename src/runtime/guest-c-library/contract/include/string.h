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
//   - Public declarations for the currently executable guest string surface.
// - Must-Not:
//   - Import a host libc ABI or promise unavailable guest runtime facilities.
// - Allows:
//   - Inputs: guest objects and byte counts admitted by malbolge-c32-v1.
//   - Outputs: standard C memory and narrow-string results.
//   - Side effects: writes only through caller-provided destination objects.
// - Split-When:
//   - Split when another header gains an independent guest-library lifecycle.
// - Merge-When:
//   - Merge when another contract owns these exact standard declarations.
// - Summary:
//   - Version-one executable guest memory and narrow-string declarations.
// - Description:
//   - Exposes only routines backed by repository-owned guest C implementations.
// - Usage:
//   - Selected before host headers by the deterministic guest-C frontend.
// - Defaults:
//   - Routines outside this header remain unavailable unless separately
//     declared.
//

//! Executable memory and narrow-string subset of malbolge-libc-v1.

#ifndef MALBOLGE_GUEST_LIBC_STRING_H
#define MALBOLGE_GUEST_LIBC_STRING_H

#include <stddef.h>

void *memcpy(void *restrict destination, const void *restrict source,
             size_t count);
void *memmove(void *destination, const void *source, size_t count);
void *memset(void *destination, int value, size_t count);
int memcmp(const void *left, const void *right, size_t count);
size_t strlen(const char *text);
int strcmp(const char *left, const char *right);
char *strcpy(char *restrict destination, const char *restrict source);
char *strncpy(char *restrict destination, const char *restrict source,
              size_t count);
char *strcat(char *restrict destination, const char *restrict source);

#endif
