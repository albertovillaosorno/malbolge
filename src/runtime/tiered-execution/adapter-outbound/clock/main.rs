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
//   - Standard-library monotonic interval measurement for tiered execution.
// - Must-Not:
//   - Expose wall-clock time, sleep, mutate telemetry, or select retry policy.
// - Allows:
//   - Inputs: opaque `Instant` start evidence issued through this adapter.
//   - Outputs: exact representable elapsed nanoseconds or representation error.
//   - Side effects: process-local monotonic clock observation only.
// - Split-When:
//   - Another runtime clock or hardware timer needs independent lifecycle.
// - Merge-When:
//   - Standard `Instant` remains the only tiered monotonic clock
//     implementation.
// - Summary:
//   - Binds tiered interval timing to `std::time::Instant`.
// - Description:
//   - Opaque start evidence prevents callers from depending on timer internals.
// - Usage:
//   - Selected by composition roots that need cached-retry latency samples.
// - Defaults:
//   - Elapsed durations wider than `u64` nanoseconds fail closed.
//

//! Standard-library monotonic interval clock for tiered execution.

use std::time::Instant;

use crate::monotonic_clock::NativeContinuationMonotonicClock;

/// Why a standard monotonic interval could not produce exact nanoseconds.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationSystemMonotonicClockError {
    /// Elapsed nanoseconds exceeded the exact `u64` telemetry representation.
    NanosecondRepresentation,
}

type SystemClockError = NativeContinuationSystemMonotonicClockError;

/// Opaque standard-library start token for one monotonic interval.
#[derive(Clone, Copy, Debug)]
pub struct NativeContinuationSystemMonotonicClockStart {
    instant: Instant,
}

/// Stateless standard-library monotonic interval clock adapter.
#[derive(Clone, Copy, Debug, Default)]
pub struct NativeContinuationSystemMonotonicClock;

impl NativeContinuationSystemMonotonicClock {
    /// Creates one standard-library monotonic interval clock adapter.
    #[must_use]
    pub const fn new() -> Self {
        Self
    }
}

impl NativeContinuationMonotonicClock
    for NativeContinuationSystemMonotonicClock
{
    type Error = NativeContinuationSystemMonotonicClockError;
    type Start = NativeContinuationSystemMonotonicClockStart;

    fn begin(&mut self) -> Self::Start {
        NativeContinuationSystemMonotonicClockStart { instant: Instant::now() }
    }

    fn elapsed_nanoseconds(
        &mut self,
        start: Self::Start,
    ) -> Result<u64, Self::Error> {
        u64::try_from(start.instant.elapsed().as_nanos())
            .map_err(|_error| SystemClockError::NanosecondRepresentation)
    }
}
