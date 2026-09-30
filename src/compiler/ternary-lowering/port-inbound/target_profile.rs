// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE-APACHE-2.0
//
// Boundary-Contract:
// - Owns:
//   - Narrow target-profile I/O projection consumed by ternary lowering.
// - Must-Not:
//   - Import runtime profile implementation types or parse profile JSON.
// - Allows:
//   - Inputs: copied canonical profile identity and byte-I/O machine semantics.
//   - Outputs: immutable profile-I/O projection records.
//   - Side effects: none.
// - Split-When:
//   - Another profile semantic family needs independent lowering policy.
// - Merge-When:
//   - Another inbound port owns this exact target I/O projection.
// - Summary:
//   - Carries authoritative target I/O opcode and EOF semantics into lowering.
// - Description:
//   - Keeps compiler machine realization bound to canonical profile authority.
// - Usage:
//   - Compiler composition copies fields from an admitted ProfileDescriptor.
// - Defaults:
//   - Missing or contradictory projection state fails closed downstream.
//

//! Inbound target-profile I/O projection for machine realization.

/// Canonical target-profile I/O semantics required by byte-effect realization.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TargetProfileIo {
    /// Canonical all-two-trit EOF sentinel.
    pub eof_word: u32,
    /// Decoded machine instruction byte assigned to input.
    pub input_instruction: u8,
    /// Decoded machine instruction byte assigned to output.
    pub output_instruction: u8,
    /// Exact canonical target-profile identity.
    pub profile_id: String,
}
