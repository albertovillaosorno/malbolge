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
//   - Transport-neutral positive relative waiting for tiered product lifecycle
//     orchestration.
// - Must-Not:
//   - Expose wall-clock epochs, measure elapsed time, choose cadence, retry
//     policy, or spawn background workers.
// - Allows:
//   - Inputs: one positive relative duration in canonical nanoseconds.
//   - Outputs: completion or adapter-local wait failure.
//   - Side effects: delegated only to the selected relative-wait adapter.
// - Split-When:
//   - Cancellation, async wake handles, or cross-process scheduling gains
//     independent meaning.
// - Merge-When:
//   - One outbound timing contract owns both relative waiting and scheduling.
// - Summary:
//   - Waits for an explicit positive relative duration without clock semantics.
// - Description:
//   - This port grants delay capability only; lifecycle policy remains caller
//     owned.
// - Usage:
//   - Product orchestration may wait between explicit lifecycle turns.
// - Defaults:
//   - Zero-duration waits are unrepresentable.
//

//! Outbound relative-wait dependency for tiered product lifecycle work.

use std::num::NonZeroU64;

/// Result of one explicit relative wait.
pub type NativeContinuationRelativeWaitResult<WaitError> =
    Result<(), WaitError>;

/// Positive relative waiting without wall-clock or cadence authority.
pub trait NativeContinuationRelativeWait {
    /// Adapter-local wait failure.
    type Error;

    /// Waits for one positive canonical nanosecond duration.
    ///
    /// # Errors
    ///
    /// Returns adapter-local wait failure without changing lifecycle policy.
    fn wait_nanoseconds(
        &mut self,
        nanoseconds: NonZeroU64,
    ) -> NativeContinuationRelativeWaitResult<Self::Error>;
}
