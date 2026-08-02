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
//   - Native debug implementation of fundamental guest byte output.
// - Must-Not:
//   - Become part of generated Malbolge artifacts or guest semantics.
// - Allows:
//   - Inputs: one unsigned value supplied by a debug-run guest C program.
//   - Outputs: the low byte written exactly to inherited host stdout.
//   - Side effects: host stdout writes and abnormal termination on I/O failure.
// - Split-When:
//   - Split when another generic guest capability requires an independent ABI.
// - Merge-When:
//   - Merge when another adapter owns the identical debug-only output symbol.
// - Summary:
//   - Host adapter for debug-only guest byte output.
// - Description:
//   - Bridges one explicit guest output primitive to native stdout.
// - Usage:
//   - Linked automatically by the CLI when its symbol appears in guest C.
// - Defaults:
//   - Abort the native debug run when stdout cannot preserve a byte.
//

//! Native debug bridge for the guest's fundamental byte-output operation.

#include <stdio.h>
#include <stdlib.h>

#if defined(_WIN32)
#include <fcntl.h>
#include <io.h>
#endif

/// Binary mode is established before output because Windows text translation
/// would otherwise turn the guest byte 10 into two host bytes, 13 and 10.
static void preserve_byte_semantics(void)
{
#if defined(_WIN32)
    static int configured;

    if (configured == 0)
    {
        if (_setmode(_fileno(stdout), _O_BINARY) == -1)
        {
            abort();
        }
        configured = 1;
    }
#endif
}

/// The adapter masks to one byte because Malbolge output exposes the
/// accumulator modulo 256, then flushes so native debugging preserves visible
/// effect order.
void __malbolge_output_byte(unsigned int value)
{
    preserve_byte_semantics();
    if (fputc((int)(value & 255U), stdout) == EOF || fflush(stdout) == EOF)
    {
        abort();
    }
}
