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
