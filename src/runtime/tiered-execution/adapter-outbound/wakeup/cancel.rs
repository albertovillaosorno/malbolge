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
//   - Standard-library cooperative cancellation and blocking relative waits.
// - Must-Not:
//   - Spawn threads, choose scheduler policy, promise precise wake deadlines,
//     use wall-clock epochs, or control guest execution.
// - Allows:
//   - Inputs: positive nanosecond delays and explicit cancellation requests.
//   - Outputs: elapsed, cancelled, or exact lock/condition failure.
//   - Side effects: one mutex-protected cancellation flag and notifications.
// - Split-When:
//   - Async wake or cancellation reset becomes independently owned.
// - Merge-When:
//   - A shared timing host adapter owns all blocking wakeup paths.
// - Summary:
//   - Wakes relative waits cooperatively through a shared condition variable.
// - Description:
//   - Sticky cancellation is checked under the mutex before and after waits;
//     spurious wakes cannot count as elapsed time.
// - Usage:
//   - Construct one wait/handle pair and hand the handle to the owner that may
//     request stop; the caller owns any spawned thread.
// - Defaults:
//   - Fresh pairs are not cancelled and never spawn work.
//

//! Standard-library interruptible relative wait and cancellation handle.

use std::num::NonZeroU64;
use std::sync::{Arc, Condvar, Mutex};
use std::time::Duration;

use crate::interruptible_wait::{
    NativeContinuationInterruptibleWait,
    NativeContinuationInterruptibleWaitOutcome as Outcome,
};

/// Failure to synchronize cancellation state or establish wait completion.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationSystemInterruptibleWaitError {
    /// Neither cancellation nor timeout was confirmed by the wait primitive.
    IndeterminateWake,
    /// The cancellation-state mutex was poisoned by a panicking owner.
    Poisoned,
}

type Error = NativeContinuationSystemInterruptibleWaitError;

#[derive(Debug, Default)]
struct SharedState {
    cancelled: Mutex<bool>,
    wake: Condvar,
}

/// Cloneable request-only handle for sticky cooperative cancellation.
#[derive(Clone, Debug)]
pub struct NativeContinuationSystemCancellationHandle {
    shared: Arc<SharedState>,
}

impl NativeContinuationSystemCancellationHandle {
    /// Sets sticky cancellation, notifying every current waiter.
    ///
    /// Returns `true` exactly once when the state first becomes cancelled.
    ///
    /// # Errors
    ///
    /// Returns mutex poison without claiming a successful transition.
    pub fn cancel(&self) -> Result<bool, Error> {
        let mut state = self
            .shared
            .cancelled
            .lock()
            .map_err(|_poisoned| Error::Poisoned)?;
        let newly_cancelled = !*state;
        *state = true;
        drop(state);
        self.shared.wake.notify_all();
        Ok(newly_cancelled)
    }
}

/// Standard-library wait endpoint for one sticky cancellation scope.
#[derive(Debug)]
pub struct NativeContinuationSystemInterruptibleWait {
    shared: Arc<SharedState>,
}

impl NativeContinuationSystemInterruptibleWait {
    /// Creates a wait endpoint plus independently movable cancellation handle.
    #[must_use]
    pub fn new_pair() -> (Self, NativeContinuationSystemCancellationHandle) {
        let shared = Arc::new(SharedState::default());
        (
            Self {
                shared: Arc::clone(&shared),
            },
            NativeContinuationSystemCancellationHandle { shared },
        )
    }
}

impl NativeContinuationInterruptibleWait
    for NativeContinuationSystemInterruptibleWait
{
    type Error = Error;

    fn is_cancelled(&self) -> Result<bool, Self::Error> {
        let state = self
            .shared
            .cancelled
            .lock()
            .map_err(|_poisoned| Error::Poisoned)?;
        Ok(*state)
    }

    fn wait_nanoseconds(
        &mut self,
        nanoseconds: NonZeroU64,
    ) -> Result<Outcome, Self::Error> {
        let (after_wait, status) = self
            .shared
            .wake
            .wait_timeout_while(
                self.shared
                    .cancelled
                    .lock()
                    .map_err(|_poisoned| Error::Poisoned)?,
                Duration::from_nanos(nanoseconds.get()),
                |cancelled| !*cancelled,
            )
            .map_err(|_poisoned| Error::Poisoned)?;
        let cancelled = *after_wait;
        drop(after_wait);
        if cancelled {
            Ok(Outcome::Cancelled)
        } else if status.timed_out() {
            Ok(Outcome::Elapsed)
        } else {
            Err(Error::IndeterminateWake)
        }
    }
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/interruptible_wait.rs"]
mod tests;
