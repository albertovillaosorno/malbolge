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
//   - Deterministic tests for timed native-process completion admission.
// - Must-Not:
//   - Replace host-real deadline tests or define native protocol semantics.
// - Allows:
//   - Inputs: private process-session deadline helpers and typed outcomes.
//   - Outputs: tests for before, at, and beyond the exchange deadline.
//   - Side effects: none; all time observations are supplied by the caller.
// - Split-When:
//   - Completion admission needs an independent externally visible API.
// - Merge-When:
//   - The retained session deadline boundary ceases to exist.
// - Summary:
//   - Rejects queued native responses admitted at or after the deadline.
// - Description:
//   - Tests pure deadline classification without relying on scheduler races.
// - Usage:
//   - Included by the owning native process-session module in test builds.
// - Defaults:
//   - Production builds never compile this test module.
//

//! Pure deadline checks for completed native process frame exchanges.

#[test]
fn completed_frames_admit_only_before_the_deadline() -> Result<(), String> {
    use std::time::Duration;

    use super::{NativeProcessSessionError, finish_timed_exchange};

    let budget = Duration::from_millis(10);
    let response = vec![0x13u8, 0x37];
    if finish_timed_exchange(budget, Duration::ZERO, Ok(response.clone()))
        != Ok(response.clone())
        || finish_timed_exchange(
            budget,
            Duration::from_nanos(9_999_999),
            Ok(response.clone()),
        ) != Ok(response.clone())
        || finish_timed_exchange(budget, budget, Ok(response.clone()))
            != Err(NativeProcessSessionError::ExchangeTimeout)
        || finish_timed_exchange(
            budget,
            Duration::from_millis(11),
            Ok(response),
        ) != Err(NativeProcessSessionError::ExchangeTimeout)
    {
        return Err(String::from("completed frame deadline admission drifted"));
    }
    Ok(())
}

#[test]
fn late_transport_failures_cannot_extend_a_deadline() -> Result<(), String> {
    use std::io::ErrorKind;
    use std::time::Duration;

    use super::{NativeProcessSessionError, finish_timed_exchange};

    let budget = Duration::from_millis(10);
    let error = NativeProcessSessionError::Read(ErrorKind::UnexpectedEof);
    if finish_timed_exchange(budget, Duration::from_millis(9), Err(error))
        != Err(error)
        || finish_timed_exchange(budget, budget, Err(error))
            != Err(NativeProcessSessionError::ExchangeTimeout)
        || finish_timed_exchange(Duration::ZERO, Duration::ZERO, Ok(vec![]))
            != Err(NativeProcessSessionError::ExchangeTimeout)
    {
        return Err(String::from("expired transport completion was admitted"));
    }
    Ok(())
}

#[test]
fn timed_worker_capacity_recycles_slots() -> Result<(), String> {
    use std::sync::atomic::{AtomicUsize, Ordering};

    use super::{NativeProcessSessionError, TimedExchangeWorkerPermit};

    let active = AtomicUsize::new(0);
    let first = TimedExchangeWorkerPermit::acquire(&active, 2)
        .map_err(|error| format!("first permit: {error:?}"))?;
    let second = TimedExchangeWorkerPermit::acquire(&active, 2)
        .map_err(|error| format!("second permit: {error:?}"))?;
    if !matches!(
        TimedExchangeWorkerPermit::acquire(&active, 2),
        Err(NativeProcessSessionError::WorkerCapacityExceeded)
    ) || active.load(Ordering::Acquire) != 2
    {
        return Err(String::from("timed worker ownership exceeded its cap"));
    }
    drop(first);
    let replacement = TimedExchangeWorkerPermit::acquire(&active, 2)
        .map_err(|error| format!("reused permit: {error:?}"))?;
    if active.load(Ordering::Acquire) != 2 {
        return Err(String::from("timed worker permit was not recycled"));
    }
    drop(second);
    drop(replacement);
    if active.load(Ordering::Acquire) != 0 {
        return Err(String::from("timed worker permits leaked after release"));
    }
    for (count, limit) in [(0, 0), (usize::MAX, usize::MAX)] {
        let full = AtomicUsize::new(count);
        if !matches!(
            TimedExchangeWorkerPermit::acquire(&full, limit),
            Err(NativeProcessSessionError::WorkerCapacityExceeded)
        ) || full.load(Ordering::Acquire) != count
        {
            return Err(String::from("zero/overflow permit capacity admitted"));
        }
    }
    Ok(())
}

#[test]
fn timed_exchange_worker_capacity_checks_are_atomic() -> Result<(), String> {
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::sync::{Arc, Barrier};
    use std::thread;

    use super::{NativeProcessSessionError, TimedExchangeWorkerPermit};

    let active = AtomicUsize::new(0);
    let start = Arc::new(Barrier::new(16));
    let owned = thread::scope(|scope| {
        let mut workers = Vec::new();
        for _ in 0..16 {
            let start = Arc::clone(&start);
            let active = &active;
            workers.push(scope.spawn(move || {
                let _arrived = start.wait();
                TimedExchangeWorkerPermit::acquire(active, 4)
            }));
        }
        workers
            .into_iter()
            .map(thread::ScopedJoinHandle::join)
            .collect::<Vec<_>>()
    });
    let mut permits = Vec::new();
    let mut rejected = 0;
    for worker in owned {
        match worker.map_err(|_panic| String::from("worker panicked"))? {
            Ok(permit) => permits.push(permit),
            Err(NativeProcessSessionError::WorkerCapacityExceeded) => {
                rejected += 1;
            },
            Err(error) => {
                return Err(format!("unexpected permit error: {error:?}"));
            },
        }
    }
    if permits.len() != 4
        || rejected != 12
        || active.load(Ordering::Acquire) != 4
    {
        return Err(String::from(
            "concurrent permit acquisition overcommitted",
        ));
    }
    drop(permits);
    if active.load(Ordering::Acquire) != 0 {
        return Err(String::from("concurrent permits remained retained"));
    }
    Ok(())
}
