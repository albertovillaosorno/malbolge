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
//   - Transport-neutral monotonic interval measurement for tiered execution.
// - Must-Not:
//   - Expose wall-clock epochs, sleep, interpret telemetry, or mutate policy.
// - Allows:
//   - Inputs: one opaque adapter-issued interval start token.
//   - Outputs: exact elapsed nanoseconds or adapter-local failure evidence.
//   - Side effects: delegated only to the selected monotonic clock adapter.
// - Split-When:
//   - Async timers or cross-process clock correlation gain independent meaning.
// - Merge-When:
//   - One outbound clock contract owns all tiered runtime interval measurement.
// - Summary:
//   - Measures caller-delimited intervals without exposing wall-clock time.
// - Description:
//   - Start ownership remains opaque; elapsed conversion is adapter-owned.
// - Usage:
//   - Begin before caller-owned work and finish after that work completes.
// - Defaults:
//   - No clock reading is persisted or interpreted by this port.
//

//! Outbound monotonic interval clock contract for tiered execution.

/// Result of finishing one monotonic interval into exact nanoseconds.
pub type NativeContinuationMonotonicClockElapsedResult<ClockError> =
    Result<u64, ClockError>;

/// Monotonic interval clock with adapter-owned opaque start evidence.
pub trait NativeContinuationMonotonicClock {
    /// Adapter-local observation or nanosecond-conversion failure.
    type Error;

    /// Opaque interval start token issued by this clock implementation.
    type Start;

    /// Begins one caller-delimited monotonic interval.
    fn begin(&mut self) -> Self::Start;

    /// Converts one completed interval to exact elapsed nanoseconds.
    ///
    /// # Errors
    ///
    /// Returns adapter-local elapsed-time or representation failure.
    fn elapsed_nanoseconds(
        &mut self,
        start: Self::Start,
    ) -> NativeContinuationMonotonicClockElapsedResult<Self::Error>;
}
