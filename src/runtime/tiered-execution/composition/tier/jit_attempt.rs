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
//   - Composition from one scheduled JIT rescue into a bounded compiler
//     attempt.
// - Must-Not:
//   - Select performance policy, admit artifacts, install code, or execute it.
// - Allows:
//   - Inputs: one immutable rescue schedule and one compiler adapter.
//   - Outputs: AOT bypass, interpreter fallback, or untrusted JIT candidate.
//   - Side effects: at most one delegated compilation for `JitCompilation`.
// - Split-When:
//   - Candidate admission or executable installation gains independent policy.
// - Merge-When:
//   - Rescue scheduling owns compiler invocation atomically.
// - Summary:
//   - Invokes bounded compilation only for an explicitly scheduled JIT miss.
// - Description:
//   - Every other route bypasses the compiler and preserves its prior evidence.
// - Usage:
//   - Called after AOT lookup, performance gate, and explicit budget
//     scheduling.
// - Defaults:
//   - Invalid internal schedule state fails closed to the interpreter.
//

//! Scheduled JIT compilation composition before candidate admission.

use crate::execution_cache::NativeArtifactKey;
use crate::jit_compilation::{
    NativeTierJitCompilationAttempt, NativeTierJitCompilationFallback,
    attempt_jit_compilation,
};
use crate::jit_compiler_port::NativeTierJitCompiler;
use crate::native_tier_jit_rescue::{
    NativeTierJitRescueRoute, NativeTierJitRescueSchedule,
};

/// Final route after one scheduled pre-admission JIT compilation attempt.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeTierScheduledJitRoute {
    /// Exact AOT artifact remains selected; compiler was bypassed.
    AheadOfExecution,
    /// Native optimization failed closed to normative interpreter authority.
    Interpreter,
    /// One untrusted candidate is ready for independent artifact admission.
    JitCandidate,
}

/// Why a scheduled route fell back before native artifact admission.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeTierScheduledJitFallback<CompilerError> {
    /// Bounded compiler application returned one exact fallback reason.
    Compilation(NativeTierJitCompilationFallback<CompilerError>),
    /// A private schedule invariant was inconsistent with its selected route.
    InvalidSchedule,
}

/// Result retaining the original schedule plus optional compilation evidence.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeTierScheduledJitAttempt<Artifact, CompilerError> {
    candidate: Option<Artifact>,
    elapsed_nanoseconds: Option<u64>,
    fallback: Option<NativeTierScheduledJitFallback<CompilerError>>,
    object_bytes: Option<usize>,
    route: NativeTierScheduledJitRoute,
    schedule: NativeTierJitRescueSchedule,
}

impl<Artifact, CompilerError>
    NativeTierScheduledJitAttempt<Artifact, CompilerError>
{
    /// Returns the untrusted candidate when bounded compilation succeeded.
    #[must_use]
    pub const fn candidate(&self) -> Option<&Artifact> {
        self.candidate.as_ref()
    }

    /// Returns exact compiler elapsed time for a successful candidate.
    #[must_use]
    pub const fn elapsed_nanoseconds(&self) -> Option<u64> {
        self.elapsed_nanoseconds
    }

    /// Returns exact pre-admission fallback evidence, when present.
    #[must_use]
    pub const fn fallback(
        &self,
    ) -> Option<&NativeTierScheduledJitFallback<CompilerError>> {
        self.fallback.as_ref()
    }

    /// Returns exact compiler object size for a successful candidate.
    #[must_use]
    pub const fn object_bytes(&self) -> Option<usize> {
        self.object_bytes
    }

    /// Returns the final pre-admission route.
    #[must_use]
    pub const fn route(&self) -> NativeTierScheduledJitRoute {
        self.route
    }

    /// Returns the complete original rescue schedule and provenance.
    #[must_use]
    pub const fn schedule(&self) -> &NativeTierJitRescueSchedule {
        &self.schedule
    }
}

/// Executes at most one bounded compiler attempt for a scheduled JIT miss.
#[must_use]
pub fn attempt_scheduled_jit<Artifact, CompilerError, Compiler>(
    schedule: NativeTierJitRescueSchedule,
    compiler: &mut Compiler,
) -> NativeTierScheduledJitAttempt<Artifact, CompilerError>
where
    Compiler: NativeTierJitCompiler<NativeArtifactKey, Artifact, CompilerError>,
{
    match schedule.route() {
        NativeTierJitRescueRoute::AheadOfExecution => bypass_attempt(
            schedule,
            NativeTierScheduledJitRoute::AheadOfExecution,
        ),
        NativeTierJitRescueRoute::Interpreter => {
            bypass_attempt(schedule, NativeTierScheduledJitRoute::Interpreter)
        },
        NativeTierJitRescueRoute::JitEligible => invalid_schedule(schedule),
        NativeTierJitRescueRoute::JitCompilation => {
            attempt_scheduled_compilation(schedule, compiler)
        },
    }
}

fn attempt_scheduled_compilation<Artifact, CompilerError, Compiler>(
    schedule: NativeTierJitRescueSchedule,
    compiler: &mut Compiler,
) -> NativeTierScheduledJitAttempt<Artifact, CompilerError>
where
    Compiler: NativeTierJitCompiler<NativeArtifactKey, Artifact, CompilerError>,
{
    let (Some(identity), Some(budget)) =
        (schedule.uncovered_key(), schedule.budget())
    else {
        return invalid_schedule(schedule);
    };
    let compilation = attempt_jit_compilation(compiler, identity, budget);
    match compilation {
        NativeTierJitCompilationAttempt::Candidate {
            artifact,
            elapsed_nanoseconds,
            object_bytes,
        } => NativeTierScheduledJitAttempt {
            candidate: Some(artifact),
            elapsed_nanoseconds: Some(elapsed_nanoseconds),
            fallback: None,
            object_bytes: Some(object_bytes),
            route: NativeTierScheduledJitRoute::JitCandidate,
            schedule,
        },
        NativeTierJitCompilationAttempt::Interpreter { reason } => {
            NativeTierScheduledJitAttempt {
                candidate: None,
                elapsed_nanoseconds: None,
                fallback: Some(NativeTierScheduledJitFallback::Compilation(
                    reason,
                )),
                object_bytes: None,
                route: NativeTierScheduledJitRoute::Interpreter,
                schedule,
            }
        },
    }
}

const fn bypass_attempt<Artifact, CompilerError>(
    schedule: NativeTierJitRescueSchedule,
    route: NativeTierScheduledJitRoute,
) -> NativeTierScheduledJitAttempt<Artifact, CompilerError> {
    NativeTierScheduledJitAttempt {
        candidate: None,
        elapsed_nanoseconds: None,
        fallback: None,
        object_bytes: None,
        route,
        schedule,
    }
}

const fn invalid_schedule<Artifact, CompilerError>(
    schedule: NativeTierJitRescueSchedule,
) -> NativeTierScheduledJitAttempt<Artifact, CompilerError> {
    NativeTierScheduledJitAttempt {
        candidate: None,
        elapsed_nanoseconds: None,
        fallback: Some(NativeTierScheduledJitFallback::InvalidSchedule),
        object_bytes: None,
        route: NativeTierScheduledJitRoute::Interpreter,
        schedule,
    }
}
