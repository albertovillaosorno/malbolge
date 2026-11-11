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
//   - Standard-library blocking relative waits for tiered product lifecycle
//     orchestration.
// - Must-Not:
//   - Read wall-clock time, measure latency, choose cadence, select policy,
//     spawn workers, or expose thread handles.
// - Allows:
//   - Inputs: one positive canonical nanosecond duration.
//   - Outputs: infallible completion after the standard-library wait returns.
//   - Side effects: blocks the current host thread for the requested duration.
// - Split-When:
//   - Async timers, cancellation, or another host runtime needs independent
//     lifecycle.
// - Merge-When:
//   - Standard blocking wait remains the only tiered relative-wait adapter.
// - Summary:
//   - Binds explicit relative waiting to `std::thread::sleep`.
// - Description:
//   - It owns no scheduling loop; callers decide whether and when to wait.
// - Usage:
//   - Selected by product lifecycle orchestration that permits blocking waits.
// - Defaults:
//   - Only positive durations are accepted by the outbound port.
//

//! Standard-library blocking relative wait for tiered lifecycle orchestration.

use std::convert::Infallible;
use std::num::NonZeroU64;
use std::thread;
use std::time::Duration;

use crate::relative_wait::NativeContinuationRelativeWait;

/// Stateless standard-library relative-wait adapter.
#[derive(Clone, Copy, Debug, Default)]
pub struct NativeContinuationSystemRelativeWait;

impl NativeContinuationSystemRelativeWait {
    /// Creates one standard-library blocking relative-wait adapter.
    #[must_use]
    pub const fn new() -> Self {
        Self
    }
}

impl NativeContinuationRelativeWait for NativeContinuationSystemRelativeWait {
    type Error = Infallible;

    fn wait_nanoseconds(
        &mut self,
        nanoseconds: NonZeroU64,
    ) -> Result<(), Self::Error> {
        thread::sleep(Duration::from_nanos(nanoseconds.get()));
        Ok(())
    }
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/relative_wait.rs"]
mod tests;
