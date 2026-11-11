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
//   - Raw guest-runtime intrinsic requests admitted by ternary lowering.
// - Must-Not:
//   - Implement guest-runtime mapping, host I/O, or machine opcode encoding.
// - Allows:
//   - Inputs: exact intrinsic and target-profile identities.
//   - Outputs: immutable runtime-intrinsic requests.
//   - Side effects: none.
// - Split-When:
//   - Another runtime-intrinsic family needs independent lowering semantics.
// - Merge-When:
//   - Another inbound port owns these exact declaration-only identities.
// - Summary:
//   - Separates raw runtime intrinsic identity from typed successful byte
//     effects.
// - Description:
//   - Input-word requests can represent EOF; typed ByteInput cannot.
// - Usage:
//   - Compiler composition supplies identities from guest-runtime authority.
// - Defaults:
//   - Unknown intrinsic or profile identities fail closed downstream.
//

//! Inbound declaration-only guest-runtime intrinsic requests.

/// One exact declaration-only runtime intrinsic lowering request.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RuntimeIntrinsicRequest {
    /// Exact guest-runtime declaration identity.
    pub identity: String,
    /// Exact selected target-profile identity.
    pub target_profile: String,
}
