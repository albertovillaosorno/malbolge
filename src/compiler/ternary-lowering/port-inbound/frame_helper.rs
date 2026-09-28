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
//   - Exact guest call-frame helper identities entering ternary lowering.
// - Must-Not:
//   - Inspect frame values, parse ABI JSON, or execute validation.
// - Allows:
//   - Inputs: exact ABI/runtime/helper identities.
//   - Outputs: immutable frame-helper requests.
//   - Side effects: none.
// - Split-When:
//   - Another frame helper needs a distinct request shape.
// - Merge-When:
//   - Another inbound port owns these exact frame-helper identities.
// - Summary:
//   - Carries canonical call-frame validation identity into lowering.
// - Description:
//   - Keeps ABI/runtime identity explicit before semantic realization.
// - Usage:
//   - Compiler/runtime linkage supplies reviewed frame-helper identities here.
// - Defaults:
//   - Unknown identities fail closed downstream.
//

//! Inbound guest-runtime call-frame helper requests.

/// One exact guest call-frame helper request.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FrameHelperRequest {
    /// Exact guest ABI identity.
    pub abi_id: String,
    /// Exact guest-runtime helper declaration identity.
    pub identity: String,
    /// Exact guest-runtime contract identity.
    pub runtime_id: String,
}
