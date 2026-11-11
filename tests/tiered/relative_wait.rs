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
//   - Regression evidence for the standard tiered relative-wait adapter.
// - Must-Not:
//   - Assert scheduler policy, wall-clock epochs, or timing precision.
// - Allows:
//   - Inputs: the minimum positive canonical wait duration.
//   - Outputs: successful completion through the outbound port.
//   - Side effects: one minimal host-thread relative wait.
// - Split-When:
//   - Another production wait adapter gains independent regression scope.
// - Merge-When:
//   - Relative-wait integration becomes part of product lifecycle tests.
// - Summary:
//   - Proves the standard adapter satisfies the explicit wait contract.
// - Description:
//   - No elapsed-time threshold is asserted, avoiding scheduler-sensitive
//     tests.
// - Usage:
//   - Compiled only under Rust test configuration.
// - Defaults:
//   - Uses one nanosecond, the smallest representable positive duration.
//

//! Regression coverage for the standard tiered relative-wait adapter.

use super::*;

#[test]
fn system_relative_wait_completes_minimum_positive_duration()
-> Result<(), String> {
    let Some(nanoseconds) = NonZeroU64::new(1) else {
        return Err(String::from("one nanosecond must be positive"));
    };
    let mut wait = NativeContinuationSystemRelativeWait::new();
    match wait.wait_nanoseconds(nanoseconds) {
        Ok(()) => Ok(()),
        Err(error) => match error {},
    }
}
