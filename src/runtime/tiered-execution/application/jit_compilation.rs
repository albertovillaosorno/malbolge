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
//   - One bounded JIT compilation attempt and fail-closed interpreter fallback.
// - Must-Not:
//   - Select tier policy, admit native semantics, install code, or execute it.
// - Allows:
//   - Inputs: exact identity, explicit budget, and replaceable compiler port.
//   - Outputs: untrusted candidate or exact interpreter-fallback evidence.
//   - Side effects: one delegated bounded compiler attempt.
// - Split-When:
//   - Artifact admission or executable installation gains application
//     authority.
// - Merge-When:
//   - Another service owns the same single bounded compiler attempt.
// - Summary:
//   - Rechecks compiler budget claims before exposing a JIT candidate.
// - Description:
//   - Every non-candidate outcome preserves interpreter authority.
// - Usage:
//   - Called only for a performance-promoted scheduled JIT identity.
// - Defaults:
//   - Compiler failure is an optimization failure, not guest failure.
//

//! Bounded JIT compilation orchestration with deterministic fallback.

use std::num::{NonZeroU64, NonZeroUsize};

use crate::jit_compiler_port::{
    NativeTierJitCompilationBudget, NativeTierJitCompilationRequest,
    NativeTierJitCompiler, NativeTierJitCompilerOutcome,
};

/// Exact reason one scheduled JIT attempt retained interpreter authority.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeTierJitCompilationFallback<CompilerError> {
    /// Compiler stopped because its synchronous latency ceiling expired.
    BudgetExhausted {
        /// Exact elapsed compiler time reported by the adapter.
        elapsed_nanoseconds: u64,
    },
    /// Compiler observed cancellation and published no candidate.
    Cancelled,
    /// Compiler adapter failed without publishing a candidate.
    Compiler(CompilerError),
    /// Compiler claimed success beyond the caller's latency ceiling.
    LatencyLimit {
        /// Positive caller-owned synchronous latency ceiling.
        maximum_nanoseconds: NonZeroU64,
        /// Exact elapsed compiler time reported by the adapter.
        observed_nanoseconds: u64,
    },
    /// Compiler claimed success beyond the caller's object-size ceiling.
    ObjectByteLimit {
        /// Positive caller-owned candidate-size ceiling.
        maximum_bytes: NonZeroUsize,
        /// Exact candidate object size reported by the adapter.
        observed_bytes: usize,
    },
    /// Compiler cannot specialize the exact requested identity.
    Unsupported,
}

/// Result of one bounded compilation use case before artifact admission.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeTierJitCompilationAttempt<Artifact, CompilerError> {
    /// One untrusted candidate remained within both reported ceilings.
    Candidate {
        /// Untrusted artifact requiring independent semantic admission.
        artifact: Artifact,
        /// Exact elapsed compiler time reported by the adapter.
        elapsed_nanoseconds: u64,
        /// Exact candidate object size reported by the adapter.
        object_bytes: usize,
    },
    /// Native optimization failed closed; interpreter remains authoritative.
    Interpreter {
        /// Exact optimization failure retained for policy/telemetry.
        reason: NativeTierJitCompilationFallback<CompilerError>,
    },
}

/// Result of one bounded JIT attempt before independent artifact admission.
pub type NativeTierJitCompilationResult<Artifact, CompilerError> =
    NativeTierJitCompilationAttempt<Artifact, CompilerError>;

/// Attempts one bounded JIT compilation and rechecks observable ceilings.
///
/// The outbound compiler is responsible for stopping work at the supplied time
/// and object-size ceilings. This application boundary independently rejects a
/// `Compiled` claim whose reported observations exceed either ceiling.
#[must_use]
pub fn attempt_jit_compilation<Identity, Artifact, CompilerError, Compiler>(
    compiler: &mut Compiler,
    identity: &Identity,
    budget: NativeTierJitCompilationBudget,
) -> NativeTierJitCompilationResult<Artifact, CompilerError>
where
    Compiler: NativeTierJitCompiler<Identity, Artifact, CompilerError>,
{
    let request = NativeTierJitCompilationRequest { budget, identity };
    let outcome = match compiler.compile(request) {
        Ok(outcome) => outcome,
        Err(error) => {
            return NativeTierJitCompilationAttempt::Interpreter {
                reason: NativeTierJitCompilationFallback::Compiler(error),
            };
        },
    };
    match outcome {
        NativeTierJitCompilerOutcome::BudgetExhausted {
            elapsed_nanoseconds,
        } => NativeTierJitCompilationAttempt::Interpreter {
            reason: NativeTierJitCompilationFallback::BudgetExhausted {
                elapsed_nanoseconds,
            },
        },
        NativeTierJitCompilerOutcome::Cancelled => {
            NativeTierJitCompilationAttempt::Interpreter {
                reason: NativeTierJitCompilationFallback::Cancelled,
            }
        },
        NativeTierJitCompilerOutcome::Compiled {
            artifact,
            elapsed_nanoseconds,
            object_bytes,
        } => admit_compiled_candidate(
            artifact,
            elapsed_nanoseconds,
            object_bytes,
            budget,
        ),
        NativeTierJitCompilerOutcome::Unsupported => {
            NativeTierJitCompilationAttempt::Interpreter {
                reason: NativeTierJitCompilationFallback::Unsupported,
            }
        },
    }
}

fn admit_compiled_candidate<Artifact, CompilerError>(
    artifact: Artifact,
    elapsed_nanoseconds: u64,
    object_bytes: usize,
    budget: NativeTierJitCompilationBudget,
) -> NativeTierJitCompilationAttempt<Artifact, CompilerError> {
    if elapsed_nanoseconds > budget.maximum_nanoseconds.get() {
        return NativeTierJitCompilationAttempt::Interpreter {
            reason: NativeTierJitCompilationFallback::LatencyLimit {
                maximum_nanoseconds: budget.maximum_nanoseconds,
                observed_nanoseconds: elapsed_nanoseconds,
            },
        };
    }
    if object_bytes > budget.maximum_object_bytes.get() {
        return NativeTierJitCompilationAttempt::Interpreter {
            reason: NativeTierJitCompilationFallback::ObjectByteLimit {
                maximum_bytes: budget.maximum_object_bytes,
                observed_bytes: object_bytes,
            },
        };
    }
    NativeTierJitCompilationAttempt::Candidate {
        artifact,
        elapsed_nanoseconds,
        object_bytes,
    }
}
