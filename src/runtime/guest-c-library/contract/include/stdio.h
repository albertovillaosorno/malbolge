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
//   - Exact declarations for contracted byte-stream and formatting routines.
// - Must-Not:
//   - Expose FILE handles, host descriptors, locale, or ambient host streams.
// - Allows:
//   - Inputs: guest source requiring stable byte-I/O or formatting signatures.
//   - Outputs: declarations only; source preflight owns availability rejection.
//   - Side effects: none.
// - Split-When:
//   - Split when stream and formatting surfaces gain independent lifecycles.
// - Merge-When:
//   - Merge when another header owns these exact guest stdio signatures.
// - Summary:
//   - Declaration-only version-one byte-stream and formatting contract.
// - Description:
//   - Declares deterministic APIs without importing hosted stdio state.
// - Usage:
//   - Calls fail preflight until startup/lowering availability gates complete.
// - Defaults:
//   - No host standard stream or formatter is a fallback.
//

//! Declaration-only byte stream and formatting surface for malbolge-libc-v1.

#ifndef MALBOLGE_GUEST_LIBC_STDIO_H
#define MALBOLGE_GUEST_LIBC_STDIO_H

#include <stdarg.h>
#include <stddef.h>

#define EOF (-1)

int getchar(void);
int putchar(int value);
int snprintf(char *restrict destination, size_t size,
             const char *restrict format, ...);
int vsnprintf(char *restrict destination, size_t size,
              const char *restrict format, va_list arguments);

#endif
