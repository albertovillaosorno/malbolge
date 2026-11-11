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
//   - Explicit interruptible relative waits for cooperative tiered lifecycle
//     cancellation without conflating cancellation with elapsed time.
// - Must-Not:
//   - Select cadence, read wall-clock epochs, infer retry or stop policy,
//     execute lifecycle turns, or start background workers.
// - Allows:
//   - Inputs: positive canonical nanoseconds and adapter-local cancellation.
//   - Outputs: elapsed, cancelled, or an exact adapter-local failure.
//   - Side effects: delegated wait and cooperative cancellation queries only.
// - Split-When:
//   - Async futures or cross-process cancellation gains independent authority.
// - Merge-When:
//   - One timing port subsumes both cancellable and ordinary waits.
// - Summary:
//   - Makes cancellation distinct from completion of a relative wait.
// - Description:
//   - A cancellation observation is sticky for one adapter ownership scope.
// - Usage:
//   - Caller-owned lifecycle turns may stop before or during one wait.
// - Defaults:
//   - Zero-duration waits remain unrepresentable.
//

//! Explicit interruptible relative-wait dependency for tiered lifecycle work.

use std::num::NonZeroU64;

/// Terminal evidence from one cooperative relative wait.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationInterruptibleWaitOutcome {
    /// Cancellation was observed before or during the requested wait.
    Cancelled,
    /// The requested wait duration elapsed without observed cancellation.
    Elapsed,
}

/// Transport-neutral wait-and-cancellation observation contract.
pub trait NativeContinuationInterruptibleWait {
    /// Adapter-local failure, never silently converted to elapsed time.
    type Error;

    /// Checks whether cancellation has already been requested.
    ///
    /// # Errors
    ///
    /// Returns an exact adapter-local query failure.
    fn is_cancelled(&self) -> Result<bool, Self::Error>;

    /// Waits for positive relative nanoseconds, or observes cancellation.
    ///
    /// # Errors
    ///
    /// Returns an exact adapter-local wait failure without granting elapsed
    /// time or cancellation evidence.
    fn wait_nanoseconds(
        &mut self,
        nanoseconds: NonZeroU64,
    ) -> Result<NativeContinuationInterruptibleWaitOutcome, Self::Error>;
}
