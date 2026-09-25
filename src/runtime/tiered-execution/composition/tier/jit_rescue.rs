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

use malbolge::RegionEffectProgram;

use crate::execution_cache::NativeArtifactKey;
use crate::execution_native::{
    AheadOfExecutionPreflightedTier, VerifiedDirectNativeArtifact,
};
pub use crate::jit_compiler_port::NativeTierJitCompilationBudget;
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
    /// The promoted identity has an explicit caller-owned compilation budget.
    JitCompilation,
    /// The uncovered identity passed the performance gate and may attempt JIT.
    JitEligible,
}

/// Scheduled AOT/JIT/interpreter route before any compilation side effect.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeTierJitRescueSchedule {
    artifact: Option<Arc<VerifiedDirectNativeArtifact>>,
    budget: Option<NativeTierJitCompilationBudget>,
    performance_block: Option<NativeTierJitPromotionBlock>,
    route: NativeTierJitRescueRoute,
    uncovered_key: Option<Box<NativeArtifactKey>>,
    uncovered_program: Option<Box<RegionEffectProgram>>,
}

/// AOT-first result retaining optional artifact or performance-rejection
/// evidence.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeTierJitRescueSelection {
    artifact: Option<Arc<VerifiedDirectNativeArtifact>>,
    performance_block: Option<NativeTierJitPromotionBlock>,
    route: NativeTierJitRescueRoute,
    uncovered_key: Option<Box<NativeArtifactKey>>,
    uncovered_program: Option<Box<RegionEffectProgram>>,
}

impl NativeTierJitRescueSchedule {
    /// Returns the retained exact AOT artifact, when selected.
    #[must_use]
    pub const fn artifact(&self) -> Option<&Arc<VerifiedDirectNativeArtifact>> {
        self.artifact.as_ref()
    }

    /// Returns the mandatory JIT compilation budget, when scheduled.
    #[must_use]
    pub const fn budget(&self) -> Option<NativeTierJitCompilationBudget> {
        self.budget
    }

    /// Returns the performance rejection for one uncovered identity, if any.
    #[must_use]
    pub const fn performance_block(
        &self,
    ) -> Option<NativeTierJitPromotionBlock> {
        self.performance_block
    }

    /// Returns the scheduled AOT/JIT/interpreter route.
    #[must_use]
    pub const fn route(&self) -> NativeTierJitRescueRoute {
        self.route
    }

    /// Returns the exact AOT-miss identity retained for possible JIT work.
    #[must_use]
    pub fn uncovered_key(&self) -> Option<&NativeArtifactKey> {
        self.uncovered_key.as_deref()
    }

    /// Returns the exact AOT-miss IR retained for compilation/admission.
    #[must_use]
    pub fn uncovered_program(&self) -> Option<&RegionEffectProgram> {
        self.uncovered_program.as_deref()
    }
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

    /// Returns the exact AOT-miss IR retained for compilation/admission.
    #[must_use]
    pub fn uncovered_program(&self) -> Option<&RegionEffectProgram> {
        self.uncovered_program.as_deref()
    }
}

/// Attaches one explicit compilation budget only to a promoted AOT miss.
///
/// Exact AOT hits, host fallback, and performance-rejected misses discard the
/// supplied JIT budget. This boundary performs no compilation and cannot infer
/// resource or time ceilings on the caller's behalf.
#[must_use]
pub fn schedule_aot_first_jit_rescue(
    selection: NativeTierJitRescueSelection,
    budget: NativeTierJitCompilationBudget,
) -> NativeTierJitRescueSchedule {
    let scheduled_budget = (selection.route
        == NativeTierJitRescueRoute::JitEligible)
        .then_some(budget);
    let route = if scheduled_budget.is_some() {
        NativeTierJitRescueRoute::JitCompilation
    } else {
        selection.route
    };
    NativeTierJitRescueSchedule {
        artifact: selection.artifact,
        budget: scheduled_budget,
        performance_block: selection.performance_block,
        route,
        uncovered_key: selection.uncovered_key,
        uncovered_program: selection.uncovered_program,
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
                uncovered_program: None,
            }
        },
        AheadOfExecutionPreflightedTier::Interpreter => {
            NativeTierJitRescueSelection {
                artifact: None,
                performance_block: None,
                route: NativeTierJitRescueRoute::Interpreter,
                uncovered_key: None,
                uncovered_program: None,
            }
        },
        AheadOfExecutionPreflightedTier::Uncovered { key, program } => {
            match assess_performance() {
                NativeTierJitPromotionAssessment::Interpreter { reason } => {
                    NativeTierJitRescueSelection {
                        artifact: None,
                        performance_block: Some(reason),
                        route: NativeTierJitRescueRoute::Interpreter,
                        uncovered_key: Some(key),
                        uncovered_program: Some(program),
                    }
                },
                NativeTierJitPromotionAssessment::Promote => {
                    NativeTierJitRescueSelection {
                        artifact: None,
                        performance_block: None,
                        route: NativeTierJitRescueRoute::JitEligible,
                        uncovered_key: Some(key),
                        uncovered_program: Some(program),
                    }
                },
            }
        },
    }
}
