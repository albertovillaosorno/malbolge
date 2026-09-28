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
//   - Exact guest heap-helper identities entering ternary lowering.
// - Must-Not:
//   - Choose arena addresses, inspect heap values, or execute allocation.
// - Allows:
//   - Inputs: exact ABI/runtime/helper identities.
//   - Outputs: immutable heap-helper requests.
//   - Side effects: none.
// - Split-When:
//   - Another heap helper needs independently shaped linkage inputs.
// - Merge-When:
//   - Another inbound port owns these exact heap-helper identities.
// - Summary:
//   - Carries canonical heap initialization identity into lowering.
// - Description:
//   - Keeps ABI/runtime identity explicit before semantic realization.
// - Usage:
//   - Compiler/runtime linkage supplies reviewed heap-helper identities here.
// - Defaults:
//   - Unknown identities fail closed downstream.
//

//! Inbound guest-runtime heap-helper requests.

/// One exact guest heap-helper request.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct HeapHelperRequest {
    /// Exact guest ABI identity.
    pub abi_id: String,
    /// Exact guest-runtime helper declaration identity.
    pub identity: String,
    /// Exact guest-runtime contract identity.
    pub runtime_id: String,
}
