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
//   - Pure cache-limit policy planning from one successful telemetry-window
//     append and caller-selected precedence.
// - Must-Not:
//   - Append telemetry, mutate cache limits, publish durable state, infer
//     thresholds, or trigger activation automatically.
// - Allows:
//   - Inputs: exact append evidence, current cache limits, caller-owned
//     recommendation configuration, and explicit precedence.
//   - Outputs: append evidence paired with exact precedence selection.
//   - Side effects: none.
// - Split-When:
//   - Automatic invocation or activation gains authority.
// - Merge-When:
//   - One orchestration owner subsumes telemetry retention and cache policy.
// - Summary:
//   - Plans cache policy from already-published retained telemetry totals.
// - Description:
//   - Window publication remains complete before policy recommendation begins.
// - Usage:
//   - Plan immediately after a successful window append, then explicitly act.
// - Defaults:
//   - Deferred or withheld selection carries no recommendation authority.
//

//! Cache-limit policy planning from published telemetry-window aggregate state.

use crate::cached_cycle::NativeContinuationCachedRetryTelemetryWindowAppend;
use crate::executable_cache_limits_precedence::{
    NativeExecutableCacheLimitsPrecedence,
    NativeExecutableCacheLimitsPrecedenceSelection,
    select_native_executable_cache_limits_precedence,
};
use crate::executable_cache_limits_recommendation::{
    NativeExecutableCacheLimitsRecommendation,
    NativeExecutableCacheLimitsTwoSignalRequest,
    recommend_native_executable_cache_limits_from_reuse_and_pressure,
};
use crate::execution_native::NativeExecutableSequenceCacheLimits;

/// Exact cache-policy plan bound to one successful telemetry-window append.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableCacheLimitsWindowPlan {
    append: NativeContinuationCachedRetryTelemetryWindowAppend,
    selection: NativeExecutableCacheLimitsPrecedenceSelection,
}

impl NativeExecutableCacheLimitsWindowPlan {
    /// Returns exact successful append evidence used for this plan.
    #[must_use]
    pub const fn append(
        self,
    ) -> NativeContinuationCachedRetryTelemetryWindowAppend {
        self.append
    }

    /// Returns cache-limit authority only when precedence selection permits it.
    #[must_use]
    pub const fn recommendation(
        self,
    ) -> Option<NativeExecutableCacheLimitsRecommendation> {
        self.selection.recommendation()
    }

    /// Returns the exact precedence-selection evidence for this append.
    #[must_use]
    pub const fn selection(
        self,
    ) -> NativeExecutableCacheLimitsPrecedenceSelection {
        self.selection
    }
}

/// Plans cache-limit policy from the aggregate totals published by one append.
///
/// The append has already mutated its telemetry window before this function is
/// called. Planning itself is pure and does not activate any recommendation.
#[must_use]
pub fn plan_native_executable_cache_limits_after_window_append(
    append: &NativeContinuationCachedRetryTelemetryWindowAppend,
    current: NativeExecutableSequenceCacheLimits,
    request: &NativeExecutableCacheLimitsTwoSignalRequest,
    precedence: NativeExecutableCacheLimitsPrecedence,
) -> NativeExecutableCacheLimitsWindowPlan {
    let arbitration =
        recommend_native_executable_cache_limits_from_reuse_and_pressure(
            append.totals(),
            current,
            request,
        );
    let selection = select_native_executable_cache_limits_precedence(
        &arbitration,
        precedence,
    );
    NativeExecutableCacheLimitsWindowPlan {
        append: *append,
        selection,
    }
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_limits_window_plan.rs"]
mod tests;
