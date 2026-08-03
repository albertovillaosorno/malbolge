// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Safe preparation and fail-closed completion of one native region call.
// - Must-Not:
//   - Allocate executable memory, invoke foreign code, or weaken IR semantics.
// - Allows:
//   - Inputs: one exact effect program and caller-owned guest buffers.
//   - Outputs: a borrow-scoped call contract and verified native result.
//   - Side effects: process-local snapshots, foreign buffer mutation, and
//   - deterministic restoration after rejected completion.
// - Split-When:
//   - Executable loading or the unsafe foreign-call boundary gains policy.
// - Merge-When:
//   - One native runner owns preparation, invocation, and result admission.
// - Summary:
//   - Verifies one native call against exact portable-effect evidence.
// - Description:
//   - Snapshots entry state and derives the only admitted applied state.
// - Usage:
//   - Prepared immediately before a future verified native entry call.
// - Defaults:
//   - Unknown status, invalid arguments, mutation on misses, and drift restore
//   - the entry snapshot and fail closed.
//

//! Safe preparation and completion contract for one native region call.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{
    ProfileMachineObservation, ProfileMemoryWrite, RunOutcome, TraceInput,
};

use super::abi::{
    NativeRegionCallFrame, NativeRegionCallFrameError,
    NativeRegionObservationError, NativeRegionState, NativeRegionStatus,
    NativeRegionStatusError,
};
use super::direct::{DirectNativeKind, VerifiedDirectNativeArtifact};
use crate::execution_cache::{
    NativeArtifactKey, NativeIdentityError, NativeTargetIdentity,
};
use crate::execution_ir::{EFFECT_IR_VERSION, EffectOp, RegionEffectProgram};

type U32Mismatch = (usize, u32, u32);
type U8Mismatch = (usize, u8, u8);

/// Mutable surface whose exact native-call contract was violated.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeRegionMutationSurface {
    /// Guest memory.
    Memory,
    /// Guest output capacity.
    Output,
    /// ABI state fields, including borrowed buffer topology.
    State,
}

/// Successfully admitted outcome of one native region call.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeRegionInvocationOutcome {
    /// The exact portable transition committed.
    Applied(ProfileMachineObservation),
    /// A semantic guard missed without observable mutation.
    GuardMiss,
}

/// Failure while preparing or admitting one native region invocation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeRegionInvocationError {
    /// The applied guest-memory image differs from the exact expected image.
    AppliedMemory {
        /// First mismatching guest address.
        address: usize,
        /// Exact expected word.
        expected: u32,
        /// Observed foreign-mutated word.
        observed: u32,
    },
    /// The applied observation differs from the exact IR exit observation.
    AppliedObservation,
    /// The applied output capacity differs from the exact expected image.
    AppliedOutput {
        /// First mismatching output position.
        index: usize,
        /// Exact expected byte.
        expected: u8,
        /// Observed foreign-mutated byte.
        observed: u8,
    },
    /// Applied native code changed a pointer or immutable buffer capacity.
    AppliedState,
    /// Borrowed call-frame construction failed.
    CallFrame(NativeRegionCallFrameError),
    /// One required entry-memory value disagrees with caller memory.
    EntryMemory {
        /// Guest address whose entry value disagreed.
        address: u32,
        /// Exact required entry word.
        expected: u32,
        /// Caller-provided entry word.
        observed: u32,
    },
    /// The exact byte-input claim disagrees with the borrowed input buffer.
    InputByte {
        /// Input position read by the effect.
        index: usize,
        /// Exact byte claimed by the IR.
        expected: u8,
        /// Borrowed input byte.
        observed: u8,
    },
    /// An EOF effect was prepared before the borrowed input was exhausted.
    InputEndOfFile {
        /// Entry input cursor.
        cursor: usize,
        /// Borrowed input length.
        input_len: usize,
    },
    /// Input cursor movement disagrees with the declared input effect.
    InputTransition,
    /// A safely prepared call unexpectedly reported invalid arguments.
    InvalidArgument,
    /// Caller memory is smaller than the program's exact direct footprint.
    MemoryCapacity {
        /// Available caller-owned words.
        available: usize,
        /// Minimum exact words required by the program.
        required: u64,
    },
    /// Guard miss or invalid-argument status mutated an observable surface.
    NonAppliedMutation {
        /// Returned native status.
        status: NativeRegionStatus,
        /// First surface whose snapshot changed.
        surface: NativeRegionMutationSurface,
    },
    /// A foreign-mutated state could not be decoded safely.
    Observation(NativeRegionObservationError),
    /// Output cursor movement disagrees with the declared output effect.
    OutputTransition,
    /// The program is not one complete canonical effect.
    ProgramShape,
    /// Native code returned an unknown status integer.
    Status(NativeRegionStatusError),
}

/// Borrowed guest buffers used by one native region invocation.
#[derive(Debug)]
pub struct NativeRegionBuffers<'buffers> {
    input: &'buffers [u8],
    memory: &'buffers mut [u32],
    output: &'buffers mut [u8],
}

/// Failure while binding one verified direct artifact to one exact call.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum VerifiedDirectInvocationError {
    /// The safe guard-miss stub has no state-applying invocation authority.
    ArtifactDeoptimization,
    /// The verified artifact key differs from the exact requested program.
    ArtifactIdentity,
    /// Exact native identity could not be reconstructed.
    Identity(NativeIdentityError),
    /// Guest-buffer preparation or result admission failed.
    Invocation(NativeRegionInvocationError),
}

/// One exact verified artifact inseparably bound to one ABI invocation.
#[derive(Debug)]
pub struct PreparedVerifiedDirectInvocation<'artifact, 'buffers> {
    artifact: &'artifact VerifiedDirectNativeArtifact,
    invocation: PreparedNativeRegionInvocation<'buffers>,
}

/// Borrow-scoped exact contract surrounding one future native entry call.
#[derive(Debug)]
pub struct PreparedNativeRegionInvocation<'buffers> {
    entry_memory: Vec<u32>,
    entry_output: Vec<u8>,
    entry_state: NativeRegionState,
    expected_memory: Vec<u32>,
    expected_observation: ProfileMachineObservation,
    expected_output: Vec<u8>,
    expected_state: NativeRegionState,
    frame: NativeRegionCallFrame<'buffers>,
}

impl<'buffers> NativeRegionBuffers<'buffers> {
    /// Groups caller-owned memory, input, and output for one exact native call.
    #[must_use]
    pub const fn new(
        memory: &'buffers mut [u32],
        input: &'buffers [u8],
        output: &'buffers mut [u8],
    ) -> Self {
        Self { input, memory, output }
    }
}

impl VerifiedDirectInvocationError {
    const fn message(self) -> &'static str {
        match self {
            Self::ArtifactDeoptimization => {
                "deoptimization artifact cannot apply guest state"
            },
            Self::ArtifactIdentity => {
                "verified artifact identity differs from the requested program"
            },
            Self::Identity(_) => {
                "verified invocation identity construction failed"
            },
            Self::Invocation(_) => "verified native invocation contract failed",
        }
    }
}

impl Display for VerifiedDirectInvocationError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(self.message())
    }
}

impl NativeRegionInvocationError {
    const fn message(self) -> &'static str {
        match self {
            Self::AppliedMemory { .. } => "native applied memory differs",
            Self::AppliedObservation => "native applied observation differs",
            Self::AppliedOutput { .. } => "native applied output differs",
            Self::AppliedState => "native applied ABI topology differs",
            Self::CallFrame(_) => "native call frame is invalid",
            Self::EntryMemory { .. } => "native entry memory differs",
            Self::InputByte { .. } => "native input byte differs",
            Self::InputEndOfFile { .. } => "native EOF claim is premature",
            Self::InputTransition => "native input transition is inconsistent",
            Self::InvalidArgument => "native call rejected prepared arguments",
            Self::MemoryCapacity { .. } => {
                "native memory capacity is insufficient"
            },
            Self::NonAppliedMutation { .. } => {
                "non-applied native call mutated state"
            },
            Self::Observation(_) => "native observation is invalid",
            Self::OutputTransition => {
                "native output transition is inconsistent"
            },
            Self::ProgramShape => "native program is not one canonical effect",
            Self::Status(_) => "native status is unknown",
        }
    }
}

impl Display for NativeRegionInvocationError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(self.message())
    }
}

impl<'artifact, 'buffers>
    PreparedVerifiedDirectInvocation<'artifact, 'buffers>
{
    /// Simulates the exact expected foreign transition for contract tests.
    #[cfg(test)]
    #[doc(hidden)]
    pub fn apply_expected_for_test(&mut self) {
        self.invocation.apply_expected_for_test();
    }

    /// Returns the exact semantically admitted direct artifact.
    #[must_use]
    pub const fn artifact(&self) -> &VerifiedDirectNativeArtifact {
        self.artifact
    }

    /// Admits one raw native status and restores state on every rejection.
    ///
    /// # Errors
    ///
    /// Returns [`VerifiedDirectInvocationError::Invocation`] when the foreign
    /// result violates the exact call contract.
    pub fn complete(
        self,
        raw_status: i32,
    ) -> Result<NativeRegionInvocationOutcome, VerifiedDirectInvocationError>
    {
        self.invocation
            .complete(raw_status)
            .map_err(VerifiedDirectInvocationError::Invocation)
    }

    /// Binds one verified state-applying artifact to one exact program call.
    ///
    /// # Errors
    ///
    /// Returns [`VerifiedDirectInvocationError`] when the artifact is deopt,
    /// its complete key differs from `program`, identity reconstruction fails,
    /// or guest-buffer preparation fails.
    pub fn new(
        artifact: &'artifact VerifiedDirectNativeArtifact,
        program: &RegionEffectProgram,
        buffers: NativeRegionBuffers<'buffers>,
    ) -> Result<Self, VerifiedDirectInvocationError> {
        if artifact.kind() == DirectNativeKind::Deopt {
            return Err(VerifiedDirectInvocationError::ArtifactDeoptimization);
        }
        let expected_key =
            NativeArtifactKey::new(program, artifact.key().target().clone())
                .map_err(VerifiedDirectInvocationError::Identity)?;
        if artifact.key() != &expected_key {
            return Err(VerifiedDirectInvocationError::ArtifactIdentity);
        }
        let NativeRegionBuffers { input, memory, output } = buffers;
        let invocation =
            PreparedNativeRegionInvocation::new(program, memory, input, output)
                .map_err(VerifiedDirectInvocationError::Invocation)?;
        Ok(Self { artifact, invocation })
    }

    /// Returns canonical verified COFF bytes for the bound artifact.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        self.artifact.object()
    }

    /// Returns the mutable ABI state pointer for the future unsafe invoker.
    #[must_use]
    pub const fn state_mut_ptr(&mut self) -> *mut NativeRegionState {
        self.invocation.state_mut_ptr()
    }

    /// Returns the exact target assumptions bound to this invocation.
    #[must_use]
    pub const fn target(&self) -> &NativeTargetIdentity {
        self.artifact.key().target()
    }

    /// Returns the exact selected Windows target triple.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.artifact.target_triple()
    }
}

impl<'buffers> PreparedNativeRegionInvocation<'buffers> {
    /// Simulates the exact expected foreign transition for contract tests.
    #[cfg(test)]
    #[doc(hidden)]
    pub fn apply_expected_for_test(&mut self) {
        self.frame.replace_state_for_invocation(self.expected_state);
        self.frame
            .memory_mut_for_invocation()
            .copy_from_slice(&self.expected_memory);
        self.frame
            .output_mut_for_invocation()
            .copy_from_slice(&self.expected_output);
    }

    /// Admits the raw status and all caller-visible state after a foreign call.
    ///
    /// `Applied` requires exact IR exit state, memory, and output.
    /// `GuardMiss` requires complete snapshot preservation.
    ///
    /// # Errors
    ///
    /// Returns [`NativeRegionInvocationError`] for unknown statuses, invalid
    /// foreign state, non-atomic misses, or applied semantic drift. Every error
    /// restores the complete entry snapshot before returning.
    pub fn complete(
        mut self,
        raw_status: i32,
    ) -> Result<NativeRegionInvocationOutcome, NativeRegionInvocationError>
    {
        let result = match NativeRegionStatus::try_from(raw_status) {
            Ok(NativeRegionStatus::Applied) => self.complete_applied(),
            Ok(status @ NativeRegionStatus::GuardMiss) => {
                self.complete_non_applied(status)
            },
            Ok(status @ NativeRegionStatus::InvalidArgument) => self
                .complete_non_applied(status)
                .and(Err(NativeRegionInvocationError::InvalidArgument)),
            Err(error) => Err(NativeRegionInvocationError::Status(error)),
        };
        if result.is_err() {
            self.restore_entry();
        }
        result
    }

    fn complete_applied(
        &self,
    ) -> Result<NativeRegionInvocationOutcome, NativeRegionInvocationError>
    {
        let observed_observation = self
            .frame
            .state()
            .observation()
            .map_err(NativeRegionInvocationError::Observation)?;
        if observed_observation != self.expected_observation {
            return Err(NativeRegionInvocationError::AppliedObservation);
        }
        if *self.frame.state() != self.expected_state {
            return Err(NativeRegionInvocationError::AppliedState);
        }
        if let Some((address, expected_word, observed_word)) =
            first_u32_mismatch(&self.expected_memory, self.frame.memory())
        {
            return Err(NativeRegionInvocationError::AppliedMemory {
                address,
                expected: expected_word,
                observed: observed_word,
            });
        }
        if let Some((index, expected_byte, observed_byte)) =
            first_u8_mismatch(&self.expected_output, self.frame.output())
        {
            return Err(NativeRegionInvocationError::AppliedOutput {
                index,
                expected: expected_byte,
                observed: observed_byte,
            });
        }
        Ok(NativeRegionInvocationOutcome::Applied(observed_observation))
    }

    fn complete_non_applied(
        &self,
        status: NativeRegionStatus,
    ) -> Result<NativeRegionInvocationOutcome, NativeRegionInvocationError>
    {
        if *self.frame.state() != self.entry_state {
            return Err(NativeRegionInvocationError::NonAppliedMutation {
                status,
                surface: NativeRegionMutationSurface::State,
            });
        }
        if self.frame.memory() != self.entry_memory {
            return Err(NativeRegionInvocationError::NonAppliedMutation {
                status,
                surface: NativeRegionMutationSurface::Memory,
            });
        }
        if self.frame.output() != self.entry_output {
            return Err(NativeRegionInvocationError::NonAppliedMutation {
                status,
                surface: NativeRegionMutationSurface::Output,
            });
        }
        Ok(NativeRegionInvocationOutcome::GuardMiss)
    }

    /// Returns the exact expected successful exit observation.
    #[must_use]
    pub const fn expected_observation(&self) -> ProfileMachineObservation {
        self.expected_observation
    }

    /// Returns the immutable input bytes retained by the ABI frame.
    #[must_use]
    pub const fn input(&self) -> &[u8] {
        self.frame.input()
    }

    /// Returns caller-owned guest memory visible after a future call.
    #[must_use]
    pub const fn memory(&self) -> &[u32] {
        self.frame.memory()
    }

    /// Prepares one exact native call over caller-owned guest buffers.
    ///
    /// Preparation validates unit program shape, memory footprint, live-ins,
    /// input evidence, output movement, and memory-write before-values before
    /// exposing the raw call-frame pointer.
    ///
    /// # Errors
    ///
    /// Returns [`NativeRegionInvocationError`] when an exact entry or effect
    /// requirement disagrees with the caller-owned buffers.
    pub fn new(
        program: &RegionEffectProgram,
        memory: &'buffers mut [u32],
        input: &'buffers [u8],
        output: &'buffers mut [u8],
    ) -> Result<Self, NativeRegionInvocationError> {
        let effect = exact_effect(program)?;
        let required = program.required_memory_words();
        if u64::try_from(memory.len())
            .map_or(true, |available| available < required)
        {
            return Err(NativeRegionInvocationError::MemoryCapacity {
                available: memory.len(),
                required,
            });
        }
        validate_live_ins(program, memory)?;
        validate_input(effect, input)?;

        let entry_memory = memory.to_vec();
        let entry_output = output.to_vec();
        let mut expected_memory = entry_memory.clone();
        apply_write(&mut expected_memory, effect.memory_delta.data)?;
        apply_write(&mut expected_memory, effect.memory_delta.encryption)?;
        let expected_output = derive_expected_output(effect, &entry_output)?;

        let frame =
            NativeRegionCallFrame::new(memory, input, output, effect.before)
                .map_err(NativeRegionInvocationError::CallFrame)?;
        let entry_state = *frame.state();
        let expected_state = entry_state
            .with_observation(effect.after)
            .map_err(NativeRegionInvocationError::CallFrame)?;
        Ok(Self {
            entry_memory,
            entry_output,
            entry_state,
            expected_memory,
            expected_observation: effect.after,
            expected_output,
            expected_state,
            frame,
        })
    }

    /// Returns the complete caller-owned output capacity.
    #[must_use]
    pub const fn output(&self) -> &[u8] {
        self.frame.output()
    }

    fn restore_entry(&mut self) {
        self.frame.replace_state_for_invocation(self.entry_state);
        self.frame
            .memory_mut_for_invocation()
            .copy_from_slice(&self.entry_memory);
        self.frame
            .output_mut_for_invocation()
            .copy_from_slice(&self.entry_output);
    }

    /// Returns the mutable ABI state pointer for one future unsafe invoker.
    ///
    /// This method does not call or dereference foreign code. The prepared
    /// contract must remain exclusively borrowed until [`Self::complete`].
    #[must_use]
    pub const fn state_mut_ptr(&mut self) -> *mut NativeRegionState {
        self.frame.state_mut_ptr()
    }

    /// Simulates one foreign guest-memory mutation for contract tests.
    #[cfg(test)]
    #[doc(hidden)]
    pub fn write_memory_for_test(
        &mut self,
        address: usize,
        value: u32,
    ) -> bool {
        let Some(cell) =
            self.frame.memory_mut_for_invocation().get_mut(address)
        else {
            return false;
        };
        *cell = value;
        true
    }
}

fn exact_effect(
    program: &RegionEffectProgram,
) -> Result<EffectOp, NativeRegionInvocationError> {
    let [effect] = program.effects.as_slice() else {
        return Err(NativeRegionInvocationError::ProgramShape);
    };
    let expected_outcome = effect
        .after
        .termination
        .map_or(RunOutcome::BudgetExhausted { steps: 1 }, |reason| {
            RunOutcome::Terminated { reason, steps: 1 }
        });
    if program.format_version != EFFECT_IR_VERSION
        || program.step_budget != 1
        || program.outcome != expected_outcome
        || effect.before.termination.is_some()
    {
        return Err(NativeRegionInvocationError::ProgramShape);
    }
    Ok(*effect)
}

fn validate_live_ins(
    program: &RegionEffectProgram,
    memory: &[u32],
) -> Result<(), NativeRegionInvocationError> {
    for live_in in &program.memory_live_ins {
        let address = usize::try_from(live_in.address).map_err(|_error| {
            NativeRegionInvocationError::MemoryCapacity {
                available: memory.len(),
                required: u64::from(live_in.address).saturating_add(1),
            }
        })?;
        let observed = memory.get(address).copied().ok_or_else(|| {
            NativeRegionInvocationError::MemoryCapacity {
                available: memory.len(),
                required: u64::from(live_in.address).saturating_add(1),
            }
        })?;
        if observed != live_in.value {
            return Err(NativeRegionInvocationError::EntryMemory {
                address: live_in.address,
                expected: live_in.value,
                observed,
            });
        }
    }
    Ok(())
}

fn validate_input(
    effect: EffectOp,
    input: &[u8],
) -> Result<(), NativeRegionInvocationError> {
    let before = effect.before.input_consumed;
    let after = effect.after.input_consumed;
    match effect.input {
        None if after == before => Ok(()),
        None => Err(NativeRegionInvocationError::InputTransition),
        Some(TraceInput::Byte(expected)) => {
            let Some(expected_after) = before.checked_add(1) else {
                return Err(NativeRegionInvocationError::InputTransition);
            };
            if after != expected_after {
                return Err(NativeRegionInvocationError::InputTransition);
            }
            let observed = input
                .get(before)
                .copied()
                .ok_or(NativeRegionInvocationError::InputTransition)?;
            if observed == expected {
                Ok(())
            } else {
                Err(NativeRegionInvocationError::InputByte {
                    index: before,
                    expected,
                    observed,
                })
            }
        },
        Some(TraceInput::EndOfInput)
            if before == input.len() && after == before =>
        {
            Ok(())
        },
        Some(TraceInput::EndOfInput) if before != input.len() => {
            Err(NativeRegionInvocationError::InputEndOfFile {
                cursor: before,
                input_len: input.len(),
            })
        },
        Some(TraceInput::EndOfInput) => {
            Err(NativeRegionInvocationError::InputTransition)
        },
    }
}

fn apply_write(
    memory: &mut [u32],
    candidate: Option<ProfileMemoryWrite>,
) -> Result<(), NativeRegionInvocationError> {
    let Some(memory_write) = candidate else {
        return Ok(());
    };
    let available = memory.len();
    let address = usize::try_from(memory_write.address).map_err(|_error| {
        NativeRegionInvocationError::MemoryCapacity {
            available,
            required: u64::from(memory_write.address).saturating_add(1),
        }
    })?;
    let cell = memory.get_mut(address).ok_or_else(|| {
        NativeRegionInvocationError::MemoryCapacity {
            available,
            required: u64::from(memory_write.address).saturating_add(1),
        }
    })?;
    if *cell != memory_write.before {
        return Err(NativeRegionInvocationError::EntryMemory {
            address: memory_write.address,
            expected: memory_write.before,
            observed: *cell,
        });
    }
    *cell = memory_write.after;
    Ok(())
}

fn derive_expected_output(
    effect: EffectOp,
    entry: &[u8],
) -> Result<Vec<u8>, NativeRegionInvocationError> {
    let before = effect.before.output_len;
    let after = effect.after.output_len;
    let mut expected = entry.to_vec();
    match effect.output {
        None if after == before => Ok(expected),
        None => Err(NativeRegionInvocationError::OutputTransition),
        Some(value) => {
            let Some(expected_after) = before.checked_add(1) else {
                return Err(NativeRegionInvocationError::OutputTransition);
            };
            if after != expected_after {
                return Err(NativeRegionInvocationError::OutputTransition);
            }
            let cell = expected
                .get_mut(before)
                .ok_or(NativeRegionInvocationError::OutputTransition)?;
            *cell = value;
            Ok(expected)
        },
    }
}

fn first_u32_mismatch(
    expected_words: &[u32],
    observed_words: &[u32],
) -> Option<U32Mismatch> {
    expected_words
        .iter()
        .copied()
        .zip(observed_words.iter().copied())
        .enumerate()
        .find_map(|(index, (expected_word, observed_word))| {
            (expected_word != observed_word).then_some((
                index,
                expected_word,
                observed_word,
            ))
        })
}

fn first_u8_mismatch(
    expected_bytes: &[u8],
    observed_bytes: &[u8],
) -> Option<U8Mismatch> {
    expected_bytes
        .iter()
        .copied()
        .zip(observed_bytes.iter().copied())
        .enumerate()
        .find_map(|(index, (expected_byte, observed_byte))| {
            (expected_byte != observed_byte).then_some((
                index,
                expected_byte,
                observed_byte,
            ))
        })
}
