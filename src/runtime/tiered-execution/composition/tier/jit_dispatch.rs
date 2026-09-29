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
//   - Guest binding and execution through one already installed verified JIT.
// - Must-Not:
//   - Compile, admit, allocate, release, cache, or directly invoke unsafe code.
// - Allows:
//   - Inputs: installed JIT authority, caller-owned guest buffers, and runner.
//   - Outputs: exact applied/guard-miss outcome or fail-closed dispatch
//     evidence.
//   - Side effects: only guest mutations admitted by the verified call
//     contract.
// - Split-When:
//   - JIT residency, release, or executable-cache policy gains shared
//     ownership.
// - Merge-When:
//   - Installation and dispatch become one transactional lifecycle boundary.
// - Summary:
//   - Dispatches an installed JIT only through existing verified loaded-call
//     admission.
// - Description:
//   - Reconstructs the exact call from retained IR/artifact authority, binds it
//     to the retained synchronized mapping, and delegates the foreign call to a
//     caller-owned runner. Preparation, runner, and completion failures retain
//     the installed mapping and restore guest state where mutation was
//     possible.
// - Usage:
//   - Apply after install_scheduled_jit returns InstalledJit.
// - Defaults:
//   - Any preparation or loaded-call failure leaves the caller with the same
//     installed JIT authority for explicit retry or later lifecycle policy.
//

//! Guest dispatch through an already installed verified JIT mapping.

use crate::execution_native::{
    NativeExecutableRunner, NativeLoadedExecutionFailure, NativeRegionBuffers,
    NativeRegionInvocationOutcome,
    PreparedVerifiedDirectInvocation as PreparedJit,
    VerifiedDirectInvocationError, execute_loaded_verified_native,
};
use crate::native_tier_jit_installation::NativeTierInstalledJit;

/// Failure while dispatching one already installed verified JIT.
#[derive(Debug, Eq, PartialEq)]
pub enum JitDispatchFailure<RunnerError> {
    /// Binding, runner, or completion failed after preparation.
    Execution(Box<NativeLoadedExecutionFailure<RunnerError>>),
    /// Caller buffers could not be bound to the retained verified program.
    Preparation(VerifiedDirectInvocationError),
}

/// Result of dispatching one installed verified JIT mapping.
pub type InstalledJitDispatchResult<RunnerError> =
    Result<NativeRegionInvocationOutcome, JitDispatchFailure<RunnerError>>;

/// Dispatches one installed JIT without executable-memory lifecycle work.
///
/// The retained artifact and portable IR are re-bound to caller-owned guest
/// buffers before the synchronized executable may reach the runner. The shared
/// loaded-call boundary then rechecks executable identity and restores the
/// complete prepared guest snapshot on runner or completion failure.
///
/// # Errors
///
/// Returns Preparation when caller buffers do not satisfy the retained program
/// and Execution when exact executable binding, the runner, or semantic
/// completion fails.
pub fn dispatch_installed_jit<Runner>(
    installed: &NativeTierInstalledJit,
    runner: &mut Runner,
    buffers: NativeRegionBuffers<'_>,
) -> InstalledJitDispatchResult<Runner::Error>
where
    Runner: NativeExecutableRunner,
{
    let artifact = installed.artifact();
    let program = installed.program();
    let preparation = PreparedJit::new(artifact, program, buffers);
    let prepared = preparation.map_err(JitDispatchFailure::Preparation)?;
    execute_loaded_verified_native(runner, installed.executable(), prepared)
        .map_err(JitDispatchFailure::Execution)
}
