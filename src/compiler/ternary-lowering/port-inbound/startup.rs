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
//   - Layout-resolved guest-runtime startup inputs consumed by ternary
//     lowering.
// - Must-Not:
//   - Choose heap addresses, parse runtime JSON, or execute guest allocation.
// - Allows:
//   - Inputs: exact ABI/profile/runtime identities and resolved guest heap
//     extent.
//   - Outputs: immutable startup request records.
//   - Side effects: none.
// - Split-When:
//   - Another startup resource family needs independent admission policy.
// - Merge-When:
//   - Another inbound port owns this exact one-shot heap-binding request.
// - Summary:
//   - Carries layout-resolved heap binding into pre-layout startup sequencing.
// - Description:
//   - Arena pointers use the canonical ABI object-pointer encoding.
// - Usage:
//   - A later layout owner supplies the resolved arena pointer and capacity.
// - Defaults:
//   - Unknown identities or malformed extents fail closed downstream.
//

//! Inbound guest-runtime startup request after heap layout is resolved.

/// Exact one-shot heap-binding startup request.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct StartupRequest {
    /// Exact guest ABI identity.
    pub abi_id: String,
    /// ABI-encoded non-null object pointer to the first arena byte.
    pub arena_pointer: u32,
    /// Exact runtime heap-binding symbol identity.
    pub bind_identity: String,
    /// Guest heap arena capacity in logical bytes.
    pub capacity: u32,
    /// Exact selected target-profile identity.
    pub target_profile: String,
    /// Module-local function identity entered after successful binding.
    pub user_entry_function: u32,
}
