// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Complete C23 source with two real discarded reads and byte 11 output.
// - Must-Not:
//   - Treat EOF as a byte, skip either read or simulate I/O on the host.
// - Allows:
//   - Inputs: arbitrary finite binary stdin including EOF and unread suffix.
//   - Outputs: one guest-calculated byte 11 after both reads.
//   - Side effects: genuine guest input and output only.
// - Split-When:
//   - General C I/O lowering supersedes the exact source proof.
// - Merge-When:
//   - Mutable C control flow executes with complete guest semantics.
// - Summary:
//   - Two EOF-capable reads precede one independent guest literal output.
//
#include <stdio.h>
void emit(void) { getchar(); getchar(); putchar(11); }
