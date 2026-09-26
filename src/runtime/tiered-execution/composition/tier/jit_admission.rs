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
//   - Fail-closed semantic admission of one bounded scheduled JIT candidate.
// - Must-Not:
//   - Compile candidates, select promotion policy, install code, or execute it.
// - Allows:
//   - Inputs: one completed scheduled JIT attempt and explicit runtime
//     capability.
//   - Outputs: retained AOT authority, interpreter fallback, or one verified
//     JIT artifact.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Executable installation or cache publication gains independent policy.
// - Merge-When:
//   - Scheduled compilation owns semantic admission atomically.
// - Summary:
//   - Converts untrusted scheduled JIT bytes into verified direct authority.
// - Description:
//   - Only JIT-candidate routes invoke direct semantic admission; every failure
//   - falls back to the interpreter without executable authority.
// - Usage:
//   - Apply after `attempt_scheduled_jit` and before installation or dispatch.
// - Defaults:
//   - Inconsistent internal attempt state is an interpreter fallback.
//

//! Semantic admission after bounded scheduled JIT compilation.

use std::sync::Arc;

use malbolge::RuntimeCapability;

use crate::execution_native::{
    DirectJitCandidateAdmissionError, VerifiedDirectNativeArtifact,
    admit_direct_jit_candidate,
};
use crate::native_tier_jit_attempt::{
    NativeTierScheduledJitAttempt, NativeTierScheduledJitRoute,
};

/// Admission-specific reason a completed scheduled attempt stayed interpreted.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeTierScheduledJitAdmissionRejection<'attempt> {
    /// Direct semantic verification rejected compiler-produced object bytes.
    Candidate(DirectJitCandidateAdmissionError<'attempt>),
    /// Private scheduled-attempt invariants did not retain required authority.
    InvalidAttempt,
}

/// Native authority available after semantic admission of one scheduled
/// attempt.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeTierScheduledJitAdmission<'attempt> {
    /// Reuse the exact precompiled AOT artifact selected before compilation.
    AheadOfExecution(Arc<VerifiedDirectNativeArtifact>),
    /// Normative interpreter remains authoritative.
    Interpreter {
        /// Admission rejection, when the attempt reached candidate admission.
        rejection: Option<NativeTierScheduledJitAdmissionRejection<'attempt>>,
    },
    /// Compiler bytes crossed the reviewed direct semantic verifier.
    VerifiedJit(Box<VerifiedDirectNativeArtifact>),
}

type ScheduledJitAdmission<'attempt> =
    NativeTierScheduledJitAdmission<'attempt>;
type ScheduledJitAttempt<CompilerError, ClockError> =
    NativeTierScheduledJitAttempt<Vec<u8>, CompilerError, ClockError>;

/// Admits a bounded scheduled JIT candidate before installation or dispatch.
///
/// AOT and interpreter routes perform no candidate admission. `JitCandidate`
/// requires the retained exact key/program plus object bytes from the completed
/// attempt; any missing authority or semantic rejection returns interpreter
/// fallback rather than exposing native executable authority.
#[must_use]
pub fn admit_scheduled_jit_candidate<'attempt, CompilerError, ClockError>(
    attempt: &'attempt ScheduledJitAttempt<CompilerError, ClockError>,
    runtime: &'static RuntimeCapability,
) -> NativeTierScheduledJitAdmission<'attempt> {
    match attempt.route() {
        NativeTierScheduledJitRoute::AheadOfExecution => {
            attempt.schedule().artifact().cloned().map_or_else(
                invalid_attempt,
                NativeTierScheduledJitAdmission::AheadOfExecution,
            )
        },
        NativeTierScheduledJitRoute::Interpreter => {
            NativeTierScheduledJitAdmission::Interpreter { rejection: None }
        },
        NativeTierScheduledJitRoute::JitCandidate => {
            admit_jit_candidate(attempt, runtime)
        },
    }
}

fn admit_jit_candidate<'attempt, CompilerError, ClockError>(
    attempt: &'attempt ScheduledJitAttempt<CompilerError, ClockError>,
    runtime: &'static RuntimeCapability,
) -> NativeTierScheduledJitAdmission<'attempt> {
    let (Some(candidate), Some(key), Some(program)) = (
        attempt.candidate(),
        attempt.schedule().uncovered_key(),
        attempt.schedule().uncovered_program(),
    ) else {
        return invalid_attempt();
    };
    match admit_direct_jit_candidate(program, runtime, key, candidate.clone()) {
        Ok(artifact) => {
            NativeTierScheduledJitAdmission::VerifiedJit(Box::new(artifact))
        },
        Err(error) => NativeTierScheduledJitAdmission::Interpreter {
            rejection: Some(
                NativeTierScheduledJitAdmissionRejection::Candidate(error),
            ),
        },
    }
}

const fn invalid_attempt<'attempt>() -> ScheduledJitAdmission<'attempt> {
    NativeTierScheduledJitAdmission::Interpreter {
        rejection: Some(
            NativeTierScheduledJitAdmissionRejection::InvalidAttempt,
        ),
    }
}
