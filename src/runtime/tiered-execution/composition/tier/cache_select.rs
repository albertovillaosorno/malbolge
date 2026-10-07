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
//   - Pure caller-selected precedence over completed reuse/pressure cache-limit
//     arbitration.
// - Must-Not:
//   - Assess telemetry, invent limits, mutate caches, publish durable state, or
//     override deferred evidence.
// - Allows:
//   - Inputs: one exact two-signal cache-limit arbitration and one explicit
//     precedence mode.
//   - Outputs: agreed, deferred, selected, unavailable, or withheld evidence.
//   - Side effects: none.
// - Split-When:
//   - Signals beyond reuse/pressure or weighted precedence gains authority.
// - Merge-When:
//   - Product orchestration owns precedence and activation atomically.
// - Summary:
//   - Resolves ready cache-limit disagreement only by explicit caller choice.
// - Description:
//   - Agreement is invariant and insufficient evidence always defers.
// - Usage:
//   - Arbitrate first, then apply one immutable caller-selected precedence.
// - Defaults:
//   - Agreement-only precedence withholds ready disagreement.
//

//! Caller-selected precedence over exact cache-limit recommendation evidence.

use crate::executable_cache_limits_recommendation as cache_rec;

type Arbitration =
    cache_rec::NativeExecutableCacheLimitsTwoSignalRecommendation;
type Recommendation = cache_rec::NativeExecutableCacheLimitsRecommendation;

/// Explicit caller policy for resolving ready reuse/pressure disagreement.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsPrecedence {
    /// Preserve agreement-only authority and withhold ready disagreement.
    #[default]
    AgreementOnly,
    /// Select exact pressure-driven limits when that signal is ready.
    Pressure,
    /// Select exact reuse-driven limits when that signal is ready.
    Reuse,
}

/// Exact result of applying caller precedence to cache-limit arbitration.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsPrecedenceSelection {
    /// Existing two-signal agreement already authorized this recommendation.
    Agreed {
        /// Exact arbitration evidence retained unchanged.
        arbitration: Arbitration,
        /// Exact agreed cache-limit recommendation.
        recommendation: Recommendation,
    },
    /// At least one signal lacked evidence; precedence was not applied.
    Deferred {
        /// Exact deferred arbitration evidence retained unchanged.
        arbitration: Arbitration,
    },
    /// Ready disagreement was resolved by explicit caller precedence.
    Selected {
        /// Exact conflicting arbitration evidence retained unchanged.
        arbitration: Arbitration,
        /// Explicit caller precedence selecting the recommendation.
        precedence: NativeExecutableCacheLimitsPrecedence,
        /// Exact selected cache-limit recommendation.
        recommendation: Recommendation,
    },
    /// Selected signal was not ready in otherwise conflicting evidence.
    Unavailable {
        /// Exact conflicting arbitration evidence retained unchanged.
        arbitration: Arbitration,
        /// Explicit precedence whose selected signal was unavailable.
        precedence: NativeExecutableCacheLimitsPrecedence,
    },
    /// Agreement-only precedence withheld ready disagreement.
    Withheld {
        /// Exact conflicting arbitration evidence retained unchanged.
        arbitration: Arbitration,
    },
}

impl NativeExecutableCacheLimitsPrecedenceSelection {
    /// Returns recommendation authority only for agreement or ready selection.
    #[must_use]
    pub const fn recommendation(self) -> Option<Recommendation> {
        match self {
            Self::Agreed { recommendation, .. }
            | Self::Selected { recommendation, .. } => Some(recommendation),
            Self::Deferred { .. }
            | Self::Unavailable { .. }
            | Self::Withheld { .. } => None,
        }
    }
}

const fn selected_recommendation(
    pressure: Recommendation,
    reuse: Recommendation,
    precedence: NativeExecutableCacheLimitsPrecedence,
) -> Option<Recommendation> {
    let candidate = match precedence {
        NativeExecutableCacheLimitsPrecedence::AgreementOnly => return None,
        NativeExecutableCacheLimitsPrecedence::Pressure => pressure,
        NativeExecutableCacheLimitsPrecedence::Reuse => reuse,
    };
    match candidate.limits() {
        Some(_) => Some(candidate),
        None => None,
    }
}

/// Applies explicit caller precedence without changing arbitration evidence.
#[must_use]
pub fn select_native_executable_cache_limits_precedence(
    arbitration: &Arbitration,
    precedence: NativeExecutableCacheLimitsPrecedence,
) -> NativeExecutableCacheLimitsPrecedenceSelection {
    type Selection = NativeExecutableCacheLimitsPrecedenceSelection;

    let evidence = *arbitration;
    match evidence {
        Arbitration::Agreed { recommendation, .. } => Selection::Agreed {
            arbitration: evidence,
            recommendation,
        },
        Arbitration::Deferred { .. } => {
            Selection::Deferred { arbitration: evidence }
        },
        Arbitration::Conflict { pressure, reuse } => match precedence {
            NativeExecutableCacheLimitsPrecedence::AgreementOnly => {
                Selection::Withheld { arbitration: evidence }
            },
            NativeExecutableCacheLimitsPrecedence::Pressure
            | NativeExecutableCacheLimitsPrecedence::Reuse => {
                selected_recommendation(pressure, reuse, precedence).map_or(
                    Selection::Unavailable {
                        arbitration: evidence,
                        precedence,
                    },
                    |recommendation| Selection::Selected {
                        arbitration: evidence,
                        precedence,
                        recommendation,
                    },
                )
            },
        },
    }
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_limits_precedence.rs"]
mod tests;
