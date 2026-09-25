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
//   - AOT-first composition of exact lookup with JIT performance eligibility.
// - Must-Not:
//   - Measure latency, compile native code, execute artifacts, or mutate
//     caches.
// - Allows:
//   - Inputs: one completed AOT lookup and lazy performance assessment.
//   - Outputs: retained AOT, JIT eligibility, or interpreter fallback.
//   - Side effects: evaluates performance only for an uncovered AOT identity.
// - Split-When:
//   - JIT compilation/dispatch gains independently testable ownership.
// - Merge-When:
//   - Product tier selection owns AOT lookup and rescue admission atomically.
// - Summary:
//   - Keeps exact AOT hits ahead of performance-gated JIT rescue.
// - Description:
//   - Host fallback and AOT hits never consult JIT performance evidence.
// - Usage:
//   - Apply after read-only AOT lookup and before any future JIT compilation.
// - Defaults:
//   - Uncovered states stay interpreted unless performance explicitly promotes.
//

//! AOT-first JIT rescue eligibility without compilation or execution.

use std::sync::Arc;

use crate::execution_cache::NativeArtifactKey;
use crate::execution_native::{
    AheadOfExecutionPreflightedTier, VerifiedDirectNativeArtifact,
};
use crate::native_tier_performance_gate::{
    NativeTierJitPromotionAssessment, NativeTierJitPromotionBlock,
};

/// Route selected before any future JIT compilation is attempted.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeTierJitRescueRoute {
    /// Reuse one exact precompiled artifact without consulting the JIT gate.
    AheadOfExecution,
    /// Stay on the normative interpreter.
    Interpreter,
    /// The uncovered identity passed the performance gate and may attempt JIT.
    JitEligible,
}

/// AOT-first result retaining optional artifact or performance-rejection
/// evidence.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeTierJitRescueSelection {
    artifact: Option<Arc<VerifiedDirectNativeArtifact>>,
    performance_block: Option<NativeTierJitPromotionBlock>,
    route: NativeTierJitRescueRoute,
    uncovered_key: Option<Box<NativeArtifactKey>>,
}

impl NativeTierJitRescueSelection {
    /// Returns the retained exact AOT artifact, when selected.
    #[must_use]
    pub const fn artifact(&self) -> Option<&Arc<VerifiedDirectNativeArtifact>> {
        self.artifact.as_ref()
    }

    /// Returns the performance rejection for one uncovered identity, if any.
    #[must_use]
    pub const fn performance_block(
        &self,
    ) -> Option<NativeTierJitPromotionBlock> {
        self.performance_block
    }

    /// Returns the selected AOT/JIT/interpreter route.
    #[must_use]
    pub const fn route(&self) -> NativeTierJitRescueRoute {
        self.route
    }

    /// Returns the exact AOT-miss identity retained for possible JIT rescue.
    #[must_use]
    pub fn uncovered_key(&self) -> Option<&NativeArtifactKey> {
        self.uncovered_key.as_deref()
    }
}

/// Applies AOT-first precedence and lazily evaluates JIT rescue performance.
///
/// `assess_performance` is invoked only for
/// [`AheadOfExecutionPreflightedTier::Uncovered`]. Exact AOT hits and
/// host-format interpreter fallback bypass performance policy entirely.
#[must_use]
pub fn select_aot_first_jit_rescue<AssessPerformance>(
    aot: AheadOfExecutionPreflightedTier,
    assess_performance: AssessPerformance,
) -> NativeTierJitRescueSelection
where
    AssessPerformance: FnOnce() -> NativeTierJitPromotionAssessment,
{
    match aot {
        AheadOfExecutionPreflightedTier::Direct(artifact) => {
            NativeTierJitRescueSelection {
                artifact: Some(artifact),
                performance_block: None,
                route: NativeTierJitRescueRoute::AheadOfExecution,
                uncovered_key: None,
            }
        },
        AheadOfExecutionPreflightedTier::Interpreter => {
            NativeTierJitRescueSelection {
                artifact: None,
                performance_block: None,
                route: NativeTierJitRescueRoute::Interpreter,
                uncovered_key: None,
            }
        },
        AheadOfExecutionPreflightedTier::Uncovered(uncovered_key) => {
            match assess_performance() {
                NativeTierJitPromotionAssessment::Interpreter { reason } => {
                    NativeTierJitRescueSelection {
                        artifact: None,
                        performance_block: Some(reason),
                        route: NativeTierJitRescueRoute::Interpreter,
                        uncovered_key: Some(uncovered_key),
                    }
                },
                NativeTierJitPromotionAssessment::Promote => {
                    NativeTierJitRescueSelection {
                        artifact: None,
                        performance_block: None,
                        route: NativeTierJitRescueRoute::JitEligible,
                        uncovered_key: Some(uncovered_key),
                    }
                },
            }
        },
    }
}
