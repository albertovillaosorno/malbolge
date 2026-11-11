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
//   - Exact pure guest-runtime helper identities consumed by ternary lowering.
// - Must-Not:
//   - Execute helper semantics, perform host I/O, or reinterpret target
//     profiles.
// - Allows:
//   - Inputs: exact helper and target-profile identities.
//   - Outputs: immutable helper requests.
//   - Side effects: none.
// - Split-When:
//   - Stateful runtime helpers require a separate lifecycle boundary.
// - Merge-When:
//   - Another inbound port owns these exact pure helper identities.
// - Summary:
//   - Carries pure byte-stream helper identity into semantic realization.
// - Description:
//   - Keeps runtime helper identity distinct from raw machine I/O intrinsics.
// - Usage:
//   - Compiler/runtime linkage supplies reviewed helper identities here.
// - Defaults:
//   - Unknown identities or profile drift fail closed downstream.
//

//! Inbound pure guest-runtime byte-stream helper requests.

/// One exact pure guest-runtime helper request.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RuntimeHelperRequest {
    /// Exact guest-runtime helper declaration identity.
    pub identity: String,
    /// Exact selected target-profile identity.
    pub target_profile: String,
}
