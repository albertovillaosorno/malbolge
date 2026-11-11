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
//   - Stable product reason taxonomy for caller-stopped cache-trigger retries.
// - Must-Not:
//   - Decide when to retry or stop, infer pacing, inspect clocks, persist
//     state, or spawn unattended work.
// - Allows:
//   - Inputs: an explicit product reason selected by the caller.
//   - Outputs: typed reason identity and a stable diagnostic identifier.
//   - Side effects: none.
// - Split-When:
//   - Retry-stop reasons gain independent payloads or persistence semantics.
// - Merge-When:
//   - One cache-trigger policy owner subsumes reason selection and taxonomy.
// - Summary:
//   - Names why product policy explicitly stops cache-trigger conflict retry.
// - Description:
//   - Attempt-budget exhaustion and non-retry terminal outcomes are not caller
//     stops and therefore do not acquire one of these reasons automatically.
// - Usage:
//   - Use only with explicit caller `Stop(reason)` decisions.
// - Defaults:
//   - No default reason exists; reasonless exits remain reasonless.
//

//! Stable product reasons for explicit cache-trigger retry stops.

/// Why product policy explicitly stopped one cache-trigger conflict retry.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsRetryStopReason {
    /// One exact conflict was sufficient evidence to return ownership.
    ContentionObserved,
    /// A caller-owned policy limit stopped retry before attempt exhaustion.
    PolicyLimit,
}

impl NativeExecutableCacheLimitsRetryStopReason {
    /// Returns the stable diagnostic identifier for this product reason.
    #[must_use]
    pub const fn id(self) -> &'static str {
        match self {
            Self::ContentionObserved => "contention-observed",
            Self::PolicyLimit => "policy-limit",
        }
    }
}
