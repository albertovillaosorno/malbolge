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
//   - Native debug implementation of classic guest input-word semantics.
// - Must-Not:
//   - Become part of generated Malbolge artifacts or guest semantics.
// - Allows:
//   - Inputs: one byte or EOF from inherited host stdin.
//   - Outputs: byte values 0..255 or the classic EOF word 59048.
//   - Side effects: host stdin reads and abnormal termination on I/O failure.
// - Split-When:
//   - Split when another generic guest input capability needs separate policy.
// - Merge-When:
//   - Merge when another adapter owns the identical debug-only input symbol.
// - Summary:
//   - Host adapter for debug-only classic guest byte input.
// - Description:
//   - Bridges one explicit compiler intrinsic to native stdin for debug runs.
// - Usage:
//   - Linked automatically by the CLI when its symbol appears in guest C.
// - Defaults:
//   - Return 59048 on clean EOF and abort on host input failure.
//

//! Native debug bridge for classic guest input-word semantics.

#include <stdio.h>
#include <stdlib.h>

unsigned int __malbolge_input_word(void)
{
    const int value = fgetc(stdin);

    if (value != EOF)
    {
        return (unsigned int)(unsigned char)value;
    }
    if (ferror(stdin) != 0)
    {
        abort();
    }
    return 59048U;
}
