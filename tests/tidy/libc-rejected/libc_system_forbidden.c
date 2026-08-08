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
//   - Negative evidence for permanently host-dependent process control.
// - Must-Not:
//   - Claim process spawning is merely an unfinished guest libc facility.
// - Allows:
//   - Inputs: one fixed command byte string.
//   - Outputs: one source-located MALBOLGE-LIBC-002 diagnostic.
//   - Side effects: none because validation rejects the call before lowering.
// - Split-When:
//   - Split when another forbidden host semantic needs independent evidence.
// - Merge-When:
//   - Merge when another fixture owns this exact process-control rejection.
// - Summary:
//   - Forbidden host-process system fixture.
// - Description:
//   - Distinguishes host-dependent semantics from future guest functionality.
// - Usage:
//   - Consumed by guest-libc source preflight regression tests.
// - Defaults:
//   - Rejection occurs at the system reference in this source file.
//

//! Host process control is outside malbolge-libc-v1 by design.

extern int system(const char *command);

int libc_system_probe(void)
{
    return system("ignored");
}
