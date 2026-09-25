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
//   - Invokes and independently times only explicitly scheduled JIT
//     compilation.
// - Description:
//   - Other routes bypass work; candidate exposure requires an in-budget clock.
// - Usage:
//   - Called after AOT lookup, performance gate, and explicit budget
//     scheduling.
// - Defaults:
//   - Invalid internal schedule state fails closed to the interpreter.
//

//! Scheduled JIT compilation composition before candidate admission.

use std::num::NonZeroU64;

use crate::execution_cache::NativeArtifactKey;
use crate::jit_compilation::{
    NativeTierJitCompilationAttempt, NativeTierJitCompilationFallback,
    attempt_jit_compilation,
};
use crate::jit_compiler_port::NativeTierJitCompiler;
use crate::monotonic_clock::NativeContinuationMonotonicClock;
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
pub enum NativeTierScheduledJitFallback<CompilerError, ClockError> {
    /// Candidate timing could not be independently observed.
    Clock(ClockError),
    /// Bounded compiler application returned one exact fallback reason.
    Compilation(NativeTierJitCompilationFallback<CompilerError>),
    /// A private schedule invariant was inconsistent with its selected route.
    InvalidSchedule,
    /// Candidate completed beyond the caller's outer latency ceiling.
    OuterLatencyLimit {
        /// Positive caller-owned synchronous latency ceiling.
        maximum_nanoseconds: NonZeroU64,
        /// Exact outer elapsed time measured by the composition clock.
        observed_nanoseconds: u64,
    },
}

/// Result retaining the original schedule plus optional compilation evidence.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeTierScheduledJitAttempt<Artifact, CompilerError, ClockError> {
    candidate: Option<Artifact>,
    elapsed_nanoseconds: Option<u64>,
    fallback: Option<NativeTierScheduledJitFallback<CompilerError, ClockError>>,
    object_bytes: Option<usize>,
    route: NativeTierScheduledJitRoute,
    schedule: NativeTierJitRescueSchedule,
}

impl<Artifact, CompilerError, ClockError>
    NativeTierScheduledJitAttempt<Artifact, CompilerError, ClockError>
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
    ) -> Option<&NativeTierScheduledJitFallback<CompilerError, ClockError>>
    {
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
pub fn attempt_scheduled_jit<Artifact, CompilerError, Compiler, Clock>(
    schedule: NativeTierJitRescueSchedule,
    compiler: &mut Compiler,
    clock: &mut Clock,
) -> NativeTierScheduledJitAttempt<Artifact, CompilerError, Clock::Error>
where
    Clock: NativeContinuationMonotonicClock,
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
            attempt_scheduled_compilation(schedule, compiler, clock)
        },
    }
}

fn attempt_scheduled_compilation<Artifact, CompilerError, Compiler, Clock>(
    schedule: NativeTierJitRescueSchedule,
    compiler: &mut Compiler,
    clock: &mut Clock,
) -> NativeTierScheduledJitAttempt<Artifact, CompilerError, Clock::Error>
where
    Clock: NativeContinuationMonotonicClock,
    Compiler: NativeTierJitCompiler<NativeArtifactKey, Artifact, CompilerError>,
{
    let (Some(identity), Some(budget)) =
        (schedule.uncovered_key(), schedule.budget())
    else {
        return invalid_schedule(schedule);
    };
    let started = clock.begin();
    let compilation = attempt_jit_compilation(compiler, identity, budget);
    let measured = clock.elapsed_nanoseconds(started);
    match compilation {
        NativeTierJitCompilationAttempt::Candidate {
            artifact,
            elapsed_nanoseconds,
            object_bytes,
        } => {
            let observed_nanoseconds = match measured {
                Ok(value) => value,
                Err(error) => {
                    return clock_failure(schedule, error);
                },
            };
            if observed_nanoseconds > budget.maximum_nanoseconds.get() {
                return outer_latency_failure(
                    schedule,
                    budget.maximum_nanoseconds,
                    observed_nanoseconds,
                );
            }
            NativeTierScheduledJitAttempt {
                candidate: Some(artifact),
                elapsed_nanoseconds: Some(elapsed_nanoseconds),
                fallback: None,
                object_bytes: Some(object_bytes),
                route: NativeTierScheduledJitRoute::JitCandidate,
                schedule,
            }
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

const fn clock_failure<Artifact, CompilerError, ClockError>(
    schedule: NativeTierJitRescueSchedule,
    error: ClockError,
) -> NativeTierScheduledJitAttempt<Artifact, CompilerError, ClockError> {
    NativeTierScheduledJitAttempt {
        candidate: None,
        elapsed_nanoseconds: None,
        fallback: Some(NativeTierScheduledJitFallback::Clock(error)),
        object_bytes: None,
        route: NativeTierScheduledJitRoute::Interpreter,
        schedule,
    }
}

const fn outer_latency_failure<Artifact, CompilerError, ClockError>(
    schedule: NativeTierJitRescueSchedule,
    maximum_nanoseconds: NonZeroU64,
    observed_nanoseconds: u64,
) -> NativeTierScheduledJitAttempt<Artifact, CompilerError, ClockError> {
    NativeTierScheduledJitAttempt {
        candidate: None,
        elapsed_nanoseconds: None,
        fallback: Some(NativeTierScheduledJitFallback::OuterLatencyLimit {
            maximum_nanoseconds,
            observed_nanoseconds,
        }),
        object_bytes: None,
        route: NativeTierScheduledJitRoute::Interpreter,
        schedule,
    }
}

const fn bypass_attempt<Artifact, CompilerError, ClockError>(
    schedule: NativeTierJitRescueSchedule,
    route: NativeTierScheduledJitRoute,
) -> NativeTierScheduledJitAttempt<Artifact, CompilerError, ClockError> {
    NativeTierScheduledJitAttempt {
        candidate: None,
        elapsed_nanoseconds: None,
        fallback: None,
        object_bytes: None,
        route,
        schedule,
    }
}

const fn invalid_schedule<Artifact, CompilerError, ClockError>(
    schedule: NativeTierJitRescueSchedule,
) -> NativeTierScheduledJitAttempt<Artifact, CompilerError, ClockError> {
    NativeTierScheduledJitAttempt {
        candidate: None,
        elapsed_nanoseconds: None,
        fallback: Some(NativeTierScheduledJitFallback::InvalidSchedule),
        object_bytes: None,
        route: NativeTierScheduledJitRoute::Interpreter,
        schedule,
    }
}
