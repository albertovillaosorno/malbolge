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
//   - Complete C23 source with two real discarded reads and independent output.
// - Must-Not:
//   - Simulate input on the host or assume either read succeeds.
// - Allows:
//   - Inputs: arbitrary finite binary stdin, including empty and EOF.
//   - Outputs: one constant byte after exactly two getchar calls.
//   - Side effects: guest input and output only.
// - Split-When:
//   - General mutable C I/O supersedes the exact source proof.
// - Merge-When:
//   - General source-C mixed effect trace covers this bounded case.
// - Summary:
//   - Two EOF-capable guest reads must precede one independent output.
//
#include <stdio.h>
void emit(void) { getchar(); getchar(); putchar(223); }
