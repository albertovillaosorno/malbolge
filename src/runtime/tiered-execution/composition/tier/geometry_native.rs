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
//   - Admission binding one verified v5 native artifact and load image to the
//   - opaque execution geometry carried by one validated VM checkpoint.
// - Must-Not:
//   - Map executable memory, invoke machine code, forge geometry tokens, or
//   - route v5 through legacy direct-native execution APIs.
// - Allows:
//   - Inputs: verified explicit-geometry initial-halt artifact, exact v5 IR,
//   - and one complete validated profile-machine checkpoint.
//   - Outputs: an affine checkpoint-bound native admission value.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Split when geometry-aware executable lifecycle or invocation gains
//   - independent policy.
// - Merge-When:
//   - Merge when one geometry-native owner subsumes admission and execution.
// - Summary:
//   - Makes opaque checkpoint geometry prerequisite to v5 native authority.
// - Description:
//   - Rechecks exact v5 identity beside normative checkpoint admission before
//   - retaining any load-image evidence.
// - Usage:
//   - Construct before any future geometry-aware mapping or invocation bridge.
// - Defaults:
//   - Artifact, profile, geometry, observation, capacity, or live-in drift
//   - fails closed without exposing executable authority.
//

//! Checkpoint-bound admission for explicit-geometry native artifacts.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;

use malbolge::{
    ExecutionGeometryRegionEffectProgram, ProfileMachineError,
    ProfileMachineIoState, ProfileMachineState,
};

use crate::execution_cache::{NativeArtifactKey, NativeIdentityError};
use crate::execution_native::{
    NativeRegionBuffers, NativeRegionInvocationError,
    NativeRegionInvocationOutcome, PreparedNativeRegionInvocation,
    ReadyExecutionGeometryNativeExecutable, VerifiedDirectLoadError,
    VerifiedExecutionGeometryInitialHaltNativeObjectArtifact,
    VerifiedExecutionGeometryLoadImage,
};
use crate::geometry_interpreter_handoff::{
    ExecutionGeometryHandoffAdmissionError, ExecutionGeometryInterpreterHandoff,
};

type InitialHaltBindingError = ExecutionGeometryNativeInitialHaltBindingError;

/// Failure before one v5 native artifact can retain checkpoint-bound authority.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeInitialHaltAdmissionError {
    /// Verified artifact identity differs from the exact requested v5 program.
    ArtifactIdentity,
    /// Opaque checkpoint authority disagrees with the requested v5 program.
    Checkpoint(ExecutionGeometryHandoffAdmissionError),
    /// Exact v5 native identity could not be reconstructed.
    Identity(NativeIdentityError),
    /// Verified COFF could not become one relocation-free aligned load image.
    Load(VerifiedDirectLoadError),
}

/// Failure while binding one prepared v5 call to synchronized code.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeInitialHaltBindingError {
    /// Synchronized executable image differs from checkpoint-bound admission.
    ExecutableIdentity,
}

/// Failure while admitting one completed geometry-bound ABI transition.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeInitialHaltCompletionError {
    /// Native result disagreed with the exact prepared transition.
    Invocation(NativeRegionInvocationError),
    /// Reconstructing the opaque-geometry checkpoint failed validation.
    State(ProfileMachineError),
}

/// Failure while preparing checkpoint-exact caller buffers for the v5 ABI.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeInitialHaltPreparationError {
    /// Borrowed input bytes differ from the admitted checkpoint.
    Input,
    /// Native ABI preparation rejected the exact v5 halt contract.
    Invocation(NativeRegionInvocationError),
    /// Borrowed memory differs from the admitted checkpoint.
    Memory,
    /// Borrowed output bytes differ from the admitted checkpoint.
    Output,
}

/// Verified v5 initial-halt artifact inseparably bound to one opaque
/// checkpoint.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeInitialHaltAdmission {
    artifact: VerifiedExecutionGeometryInitialHaltNativeObjectArtifact,
    checkpoint: ProfileMachineState,
    load_image: VerifiedExecutionGeometryLoadImage,
    program: ExecutionGeometryRegionEffectProgram,
}

/// Prepared checkpoint-owned ABI call bound to exact synchronized v5 code.
#[derive(Debug)]
pub struct ExecutionGeometryNativeInitialHaltBoundCall<
    'admission,
    'buffers,
    'executable,
> {
    executable: &'executable ReadyExecutionGeometryNativeExecutable,
    prepared: PreparedExecutionGeometryNativeInitialHalt<'admission, 'buffers>,
}

/// One admitted result retaining the opaque checkpoint geometry token.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeInitialHaltCompletion {
    outcome: NativeRegionInvocationOutcome,
    state: ProfileMachineState,
}

/// Borrow-scoped v5 ABI contract retaining checkpoint-bound admission.
#[derive(Debug)]
pub struct PreparedExecutionGeometryNativeInitialHalt<'admission, 'buffers> {
    admission: &'admission ExecutionGeometryNativeInitialHaltAdmission,
    invocation: PreparedNativeRegionInvocation<'buffers>,
}

impl Display for ExecutionGeometryNativeInitialHaltAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::ArtifactIdentity => {
                f.write_str("v5 native artifact identity differs from program")
            },
            Self::Checkpoint(error) => Display::fmt(error, f),
            Self::Identity(_error) => {
                f.write_str("v5 native identity reconstruction failed")
            },
            Self::Load(error) => Display::fmt(error, f),
        }
    }
}

impl Display for ExecutionGeometryNativeInitialHaltBindingError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str("v5 synchronized executable identity differs from call")
    }
}

impl Display for ExecutionGeometryNativeInitialHaltCompletionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Invocation(error) => Display::fmt(error, f),
            Self::State(error) => Display::fmt(error, f),
        }
    }
}

impl Display for ExecutionGeometryNativeInitialHaltPreparationError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Input => {
                f.write_str("v5 native input differs from checkpoint")
            },
            Self::Invocation(error) => Display::fmt(error, f),
            Self::Memory => {
                f.write_str("v5 native memory differs from checkpoint")
            },
            Self::Output => {
                f.write_str("v5 native output differs from checkpoint")
            },
        }
    }
}

impl ExecutionGeometryNativeInitialHaltAdmission {
    /// Returns the exact verified v5 native artifact retained by admission.
    #[must_use]
    pub const fn artifact(
        &self,
    ) -> &VerifiedExecutionGeometryInitialHaltNativeObjectArtifact {
        &self.artifact
    }

    /// Returns the normative checkpoint carrying opaque geometry authority.
    #[must_use]
    pub const fn checkpoint(&self) -> &ProfileMachineState {
        &self.checkpoint
    }

    /// Returns the relocation-free load image bound to the same exact v5 key.
    #[must_use]
    pub const fn load_image(&self) -> &VerifiedExecutionGeometryLoadImage {
        &self.load_image
    }

    /// Binds verified v5 native evidence to one already validated checkpoint.
    ///
    /// The checkpoint's opaque geometry token remains the execution authority.
    /// Exact program/artifact identity is reconstructed independently before a
    /// load image is retained. No executable mapping or call is performed.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeInitialHaltAdmissionError`] when
    /// checkpoint admission, exact v5 artifact identity, or load-image
    /// extraction fails.
    pub fn new(
        program: ExecutionGeometryRegionEffectProgram,
        checkpoint: ProfileMachineState,
        artifact: VerifiedExecutionGeometryInitialHaltNativeObjectArtifact,
    ) -> Result<Self, ExecutionGeometryNativeInitialHaltAdmissionError> {
        let _checkpoint_admission = ExecutionGeometryInterpreterHandoff::new(
            program.clone(),
            checkpoint.clone(),
        )
        .map_err(
            ExecutionGeometryNativeInitialHaltAdmissionError::Checkpoint,
        )?;
        let expected_key = NativeArtifactKey::new_execution_geometry(
            &program,
            artifact.key().target().clone(),
        )
        .map_err(ExecutionGeometryNativeInitialHaltAdmissionError::Identity)?;
        if artifact.key() != &expected_key {
            use ExecutionGeometryNativeInitialHaltAdmissionError as Error;
            return Err(Error::ArtifactIdentity);
        }
        let load_image =
            VerifiedExecutionGeometryLoadImage::from_initial_halt(&artifact)
                .map_err(
                    ExecutionGeometryNativeInitialHaltAdmissionError::Load,
                )?;
        Ok(Self {
            artifact,
            checkpoint,
            load_image,
            program,
        })
    }

    /// Prepares exact checkpoint-owned buffers for the guarded v5 halt ABI.
    ///
    /// Borrowed memory, input, and committed output must match the admitted
    /// checkpoint byte-for-byte. The resulting value retains this admission and
    /// deliberately exposes no raw state pointer or executable-call method.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeInitialHaltPreparationError`] when any
    /// caller buffer drifts or native ABI preparation rejects the exact halt.
    pub fn prepare<'admission, 'buffers>(
        &'admission self,
        buffers: NativeRegionBuffers<'buffers>,
    ) -> Result<
        PreparedExecutionGeometryNativeInitialHalt<'admission, 'buffers>,
        ExecutionGeometryNativeInitialHaltPreparationError,
    > {
        let (memory, input, output) = buffers.into_parts();
        if input != self.checkpoint.io().input() {
            return Err(
                ExecutionGeometryNativeInitialHaltPreparationError::Input,
            );
        }
        if memory != self.checkpoint.memory() {
            return Err(
                ExecutionGeometryNativeInitialHaltPreparationError::Memory,
            );
        }
        if output != self.checkpoint.io().output() {
            return Err(
                ExecutionGeometryNativeInitialHaltPreparationError::Output,
            );
        }
        let invocation =
            PreparedNativeRegionInvocation::new_execution_geometry_initial_halt(
                &self.program,
                memory,
                input,
                output,
            )
            .map_err(
                ExecutionGeometryNativeInitialHaltPreparationError::Invocation,
            )?;
        Ok(PreparedExecutionGeometryNativeInitialHalt {
            admission: self,
            invocation,
        })
    }

    /// Returns the exact v5 program whose declarative geometry was admitted.
    #[must_use]
    pub const fn program(&self) -> &ExecutionGeometryRegionEffectProgram {
        &self.program
    }
}

impl ExecutionGeometryNativeInitialHaltBoundCall<'_, '_, '_> {
    /// Simulates the exact expected foreign transition for contract tests.
    #[cfg(test)]
    #[doc(hidden)]
    pub fn apply_expected_for_test(&mut self) {
        self.prepared.apply_expected_for_test();
    }

    /// Admits one raw status through the checkpoint-owned prepared call.
    ///
    /// This method does not invoke machine code. It only verifies a status and
    /// caller-visible state after some future geometry-specific runner call.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeInitialHaltCompletionError`] when the
    /// completed transition or reconstructed checkpoint fails admission.
    pub fn complete(
        self,
        raw_status: i32,
    ) -> Result<
        ExecutionGeometryNativeInitialHaltCompletion,
        ExecutionGeometryNativeInitialHaltCompletionError,
    > {
        self.prepared.complete(raw_status)
    }

    /// Returns the synchronized entrypoint retained by this identity binding.
    #[must_use]
    pub const fn entry_address(&self) -> NonZeroUsize {
        self.executable.entry_address()
    }

    /// Returns the exact synchronized v5 executable bound to this call.
    #[must_use]
    pub const fn executable(&self) -> &ReadyExecutionGeometryNativeExecutable {
        self.executable
    }
}

impl ExecutionGeometryNativeInitialHaltCompletion {
    /// Returns the exact admitted native call outcome.
    #[must_use]
    pub const fn outcome(&self) -> NativeRegionInvocationOutcome {
        self.outcome
    }

    /// Returns the complete checkpoint retaining opaque geometry authority.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        &self.state
    }
}

impl<'admission, 'buffers>
    PreparedExecutionGeometryNativeInitialHalt<'admission, 'buffers>
{
    /// Simulates the exact expected foreign transition for contract tests.
    #[cfg(test)]
    #[doc(hidden)]
    pub fn apply_expected_for_test(&mut self) {
        self.invocation.apply_expected_for_test();
    }

    /// Binds this prepared checkpoint-owned call to exact synchronized v5 code.
    ///
    /// Identity mismatch consumes and aborts the prepared call, restoring its
    /// entry snapshot. The returned bound value still exposes no raw state
    /// pointer and has no machine-code invocation method.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeInitialHaltBindingError`] when the
    /// ready executable carries any different verified load image.
    pub fn bind_executable<'executable>(
        self,
        executable: &'executable ReadyExecutionGeometryNativeExecutable,
    ) -> Result<
        ExecutionGeometryNativeInitialHaltBoundCall<
            'admission,
            'buffers,
            'executable,
        >,
        ExecutionGeometryNativeInitialHaltBindingError,
    > {
        let Self { admission, invocation } = self;
        if admission.load_image() != executable.image() {
            let error = InitialHaltBindingError::ExecutableIdentity;
            invocation.abort();
            return Err(error);
        }
        let prepared = Self { admission, invocation };
        Ok(
            ExecutionGeometryNativeInitialHaltBoundCall {
                executable,
                prepared,
            },
        )
    }

    /// Admits one raw status and reconstructs the opaque-geometry checkpoint.
    ///
    /// `Applied` can succeed only after the underlying ABI verifier observes
    /// the exact halt transition. `GuardMiss` retains the untouched entry
    /// checkpoint.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeInitialHaltCompletionError`] when
    /// native result admission or checkpoint reconstruction fails.
    pub fn complete(
        self,
        raw_status: i32,
    ) -> Result<
        ExecutionGeometryNativeInitialHaltCompletion,
        ExecutionGeometryNativeInitialHaltCompletionError,
    > {
        let outcome = self.invocation.complete(raw_status).map_err(
            ExecutionGeometryNativeInitialHaltCompletionError::Invocation,
        )?;
        let state = completion_state(self.admission, outcome)?;
        Ok(ExecutionGeometryNativeInitialHaltCompletion { outcome, state })
    }
}

fn completion_state(
    admission: &ExecutionGeometryNativeInitialHaltAdmission,
    outcome: NativeRegionInvocationOutcome,
) -> Result<
    ProfileMachineState,
    ExecutionGeometryNativeInitialHaltCompletionError,
> {
    let checkpoint = admission.checkpoint();
    let NativeRegionInvocationOutcome::Applied(observation) = outcome else {
        return Ok(checkpoint.clone());
    };
    let io = ProfileMachineIoState::new(
        checkpoint.io().input().to_vec(),
        observation.input_consumed,
        checkpoint.io().output().to_vec(),
        observation.termination,
    )
    .map_err(ExecutionGeometryNativeInitialHaltCompletionError::State)?;
    ProfileMachineState::new_with_geometry(
        checkpoint.geometry(),
        checkpoint.memory().to_vec(),
        observation.registers,
        io,
    )
    .map_err(ExecutionGeometryNativeInitialHaltCompletionError::State)
}
