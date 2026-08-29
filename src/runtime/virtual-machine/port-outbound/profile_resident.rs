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
//   - Transport-neutral outbound exchange for resident profile wire batches.
// - Must-Not:
//   - Name process APIs, accelerator vendors, or VM verifier authority.
// - Allows:
//   - Inputs: homogeneous resident wire request views.
//   - Outputs: input-ordered resident wire results or explicit unavailability.
//   - Side effects: delegated to the selected outbound transport
//     implementation.
// - Split-When:
//   - Async or persistent-session exchange requires independent lifetime
//     policy.
// - Merge-When:
//   - One outbound resident wire exchange contract remains sufficient.
// - Summary:
//   - Carries MBPRN2-compatible resident batches to replaceable transports.
// - Description:
//   - Keeps process/device effects outside application and domain semantics.
// - Usage:
//   - Implemented by process or future resident accelerator transports.
// - Defaults:
//   - Transport failure returns no results and leaves safe-Rust fallback
//     intact.
//

//! Outbound transport contract for resident profile wire batches.

use crate::profile_resident_wire::{
    ProfileResidentWireRequest, ProfileResidentWireResult,
};

/// Replaceable transport for one already-admitted homogeneous resident batch.
pub trait ProfileResidentTransport {
    /// Attempts one input-ordered wire batch without interpreting VM authority.
    fn exchange(
        &mut self,
        requests: &[ProfileResidentWireRequest<'_>],
    ) -> Option<Vec<Option<ProfileResidentWireResult>>>;
}
