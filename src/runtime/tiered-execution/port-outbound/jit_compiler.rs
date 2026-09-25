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
//   - Replaceable budget-enforcing JIT compilation transport.
// - Must-Not:
//   - Select AOT/JIT policy, interpret guest semantics, or admit artifacts.
// - Allows:
//   - Inputs: exact identity plus positive time/object-byte ceilings.
//   - Outputs: compiled candidate or exact non-compilation outcome.
//   - Side effects: delegated entirely to the selected compiler adapter.
// - Split-When:
//   - Compilation and executable installation require independent transports.
// - Merge-When:
//   - One outbound native compiler contract owns the same bounded attempt.
// - Summary:
//   - Requires compiler-side enforcement of synchronous JIT ceilings.
// - Description:
//   - Budget exhaustion, cancellation, and unsupported input publish no
//     artifact.
// - Usage:
//   - Consumed only after AOT miss and performance promotion.
// - Defaults:
//   - No compiler adapter means interpreter fallback remains authoritative.
//

//! Outbound budget-enforcing JIT compiler contract.

use std::num::{NonZeroU64, NonZeroUsize};

/// Caller-owned hard ceilings for one synchronous JIT compilation attempt.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeTierJitCompilationBudget {
    /// Maximum synchronous compilation latency in nanoseconds.
    pub maximum_nanoseconds: NonZeroU64,
    /// Maximum admitted compiled object size in bytes.
    pub maximum_object_bytes: NonZeroUsize,
}

/// Immutable request for one exact bounded JIT compilation attempt.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeTierJitCompilationRequest<'identity, Identity> {
    /// Exact caller-owned compilation budget.
    pub budget: NativeTierJitCompilationBudget,
    /// Exact identity that the compiler may specialize.
    pub identity: &'identity Identity,
}

/// Compiler-reported outcome before independent artifact admission.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeTierJitCompilerOutcome<Artifact> {
    /// The compiler stopped because its synchronous latency ceiling expired.
    BudgetExhausted {
        /// Exact elapsed compiler time observed by the enforcing adapter.
        elapsed_nanoseconds: u64,
    },
    /// Compilation stopped because the adapter observed cancellation.
    Cancelled,
    /// One candidate was produced within the adapter-enforced ceilings.
    Compiled {
        /// Untrusted candidate requiring independent admission.
        artifact: Artifact,
        /// Exact elapsed compiler time observed by the enforcing adapter.
        elapsed_nanoseconds: u64,
        /// Exact serialized/installed candidate object size.
        object_bytes: usize,
    },
    /// This compiler cannot specialize the exact requested identity.
    Unsupported,
}

/// Result of one compiler-port attempt before application revalidation.
pub type NativeTierJitCompilerResult<Artifact, CompilerError> =
    Result<NativeTierJitCompilerOutcome<Artifact>, CompilerError>;

/// Replaceable synchronous compiler that must enforce supplied ceilings.
pub trait NativeTierJitCompiler<Identity, Artifact, CompilerError> {
    /// Attempts one exact compilation while enforcing both positive ceilings.
    ///
    /// `BudgetExhausted`, `Cancelled`, `Unsupported`, and `Err` must publish no
    /// candidate artifact. `Compiled` may return only after both ceilings were
    /// honored; application orchestration rechecks reported observations.
    ///
    /// # Errors
    ///
    /// Returns only adapter-local failures for which no candidate is published.
    fn compile(
        &mut self,
        request: NativeTierJitCompilationRequest<'_, Identity>,
    ) -> NativeTierJitCompilerResult<Artifact, CompilerError>;
}
