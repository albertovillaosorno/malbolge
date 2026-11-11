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
//   - Exact public guest byte-stream wrapper identities consumed by lowering.
// - Must-Not:
//   - Mark libc routines available, execute wrappers, or inspect host streams.
// - Allows:
//   - Inputs: exact public wrapper and target-profile identities.
//   - Outputs: immutable wrapper planning requests.
//   - Side effects: none.
// - Split-When:
//   - Another libc wrapper family requires independent lowering semantics.
// - Merge-When:
//   - Another inbound port owns these exact byte-stream wrapper identities.
// - Summary:
//   - Carries contracted getchar/putchar identity into target planning.
// - Description:
//   - Availability remains owned by the canonical libc authority.
// - Usage:
//   - Compiler integration supplies reviewed libc wrapper identities here.
// - Defaults:
//   - Unknown wrapper or profile identities fail closed downstream.
//

//! Inbound public guest byte-stream wrapper requests.

/// One exact public byte-stream wrapper planning request.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ByteStreamWrapperRequest {
    /// Exact public guest libc routine identity.
    pub identity: String,
    /// Exact selected target-profile identity.
    pub target_profile: String,
}
