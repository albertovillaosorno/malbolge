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
//   - Exact register-masked v6 sequence planning, loaded execution, and
//     cleanup.
// - Must-Not:
//   - Project v6 authority into legacy/v5 types, fuse objects, or admit a
//   - terminated semantic prefix.
// - Allows:
//   - Inputs: ordered v6 one-step programs, verified artifacts, adapters,
//   - runners, one rebased entry observation, and caller buffers.
//   - Outputs: validated sequence plans, loaded owners, indexed
//     outcomes/failures,
//   - aggregate resident weight, and retryable cleanup ownership.
//   - Side effects: executable load/release only through the supplied adapter;
//   - execution only through the dedicated register-masked runner port.
// - Split-When:
//   - Multi-entry eviction/cache policy or heterogeneous v6 templates need an
//   - independent store or dispatcher.
// - Merge-When:
//   - One general register-masked execution coordinator owns planning,
//     residency,
//   - and sequence policy without crossing the legacy/v5 trust boundary.
// - Summary:
//   - Validates the whole v6 chain before mapping and executes retained
//     mappings
//   - in semantic order.
// - Description:
//   - Current halt-fetch-only coverage permits one terminal step; the topology
//   - contract already rejects termination before a later sequence position.
// - Usage:
//   - Build a plan from verified artifacts, load it once, execute, then
//     release.
// - Defaults:
//   - Current-step failure rolls back that step; release is explicit and
//     reverse.
//

//! Exact loaded-sequence execution for register-masked v6 native artifacts.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{
    EFFECT_IR_REGISTER_MASK_VERSION, ProfileMachineObservation,
    RegisterMaskedRegionEffectProgram,
};

use super::direct::VerifiedRegisterMaskedHaltFetchNativeObjectArtifact;
use super::invocation::{NativeRegionBuffers, NativeRegionInvocationOutcome};
use super::platform::{
    NativeExecutableMemoryAdapter, RegisterMaskedNativeExecutableReleaseFailure,
};
use super::register_masked_resident::{
    RegisterMaskedNativeExecutableOwner,
    RegisterMaskedNativeOwnerExecutionFailure,
    RegisterMaskedNativeOwnerLoadFailure,
};
use super::runner::RegisterMaskedNativeRunner;
use crate::execution_cache::{NativeArtifactKey, NativeIdentityError};

/// Failure while admitting an ordered register-masked v6 sequence plan.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RegisterMaskedNativeSequencePlanError {
    /// Verified-artifact count differs from semantic program count.
    ArtifactCount {
        /// Number of semantic programs supplied by the caller.
        programs: usize,
        /// Number of verified artifacts supplied by the caller.
        artifacts: usize,
    },
    /// One verified artifact differs from the exact v6 program at that step.
    ArtifactIdentity {
        /// Zero-based mismatching sequence position.
        index: usize,
    },
    /// A register-masked sequence must contain at least one semantic step.
    Empty,
    /// Exact v6 native identity could not be reconstructed for one position.
    Identity {
        /// Zero-based sequence position whose identity failed.
        index: usize,
        /// Exact identity-construction failure.
        error: NativeIdentityError,
    },
    /// Adjacent trace observations are not byte-exactly continuous.
    ObservationChain {
        /// Zero-based step whose entry disagrees with the prior exit.
        index: usize,
    },
    /// One step changed canonical profile identity or requirement.
    ProfileMismatch {
        /// Zero-based step whose canonical profile identity changed.
        index: usize,
    },
    /// One candidate is not one complete register-masked v6 effect.
    ProgramShape {
        /// Zero-based structurally invalid step position.
        index: usize,
    },
    /// One verified artifact targets a different host/backend identity.
    TargetMismatch {
        /// Zero-based step whose target differs from the first step.
        index: usize,
    },
    /// A terminated observation was followed by another candidate step.
    TerminationBeforeEnd {
        /// Zero-based non-final step that terminated execution.
        index: usize,
    },
}

/// Ordered v6 programs and exact verified artifacts admitted as one sequence.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RegisterMaskedNativeSequencePlan {
    artifacts: Vec<VerifiedRegisterMaskedHaltFetchNativeObjectArtifact>,
    entry: ProfileMachineObservation,
    exit: ProfileMachineObservation,
    programs: Vec<RegisterMaskedRegionEffectProgram>,
}

/// Indexed failure while loading every mapping for one exact v6 sequence.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedNativeSequenceLoadFailure<MemoryError> {
    cause: Box<RegisterMaskedNativeOwnerLoadFailure<MemoryError>>,
    cleanup_failure:
        Option<Box<RegisterMaskedNativeSequenceReleaseFailure<MemoryError>>>,
    index: usize,
    loaded_count: usize,
}

/// Aggregate v6 release failure retaining every still-owned ready executable.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedNativeSequenceReleaseFailure<MemoryError> {
    attempted_count: usize,
    failures: Vec<RegisterMaskedNativeExecutableReleaseFailure<MemoryError>>,
    released_count: usize,
}

/// Result of loading every mapping for one exact register-masked sequence.
pub type RegisterMaskedNativeSequenceLoadResult<MemoryError> = Result<
    LoadedRegisterMaskedNativeSequence,
    Box<RegisterMaskedNativeSequenceLoadFailure<MemoryError>>,
>;

/// Result of releasing every mapping retained by one v6 sequence owner.
pub type RegisterMaskedNativeSequenceReleaseResult<MemoryError> =
    Result<(), Box<RegisterMaskedNativeSequenceReleaseFailure<MemoryError>>>;

/// One fully loaded exact register-masked sequence retained for repeated calls.
#[derive(Debug)]
pub struct LoadedRegisterMaskedNativeSequence {
    owners: Vec<RegisterMaskedNativeExecutableOwner>,
    plan: RegisterMaskedNativeSequencePlan,
}

/// Admitted result of executing one loaded register-masked v6 sequence.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RegisterMaskedNativeSequenceOutcome {
    /// Every semantic sequence step applied exactly.
    Applied {
        /// Exact final runtime observation after all committed steps.
        observation: ProfileMachineObservation,
        /// Number of committed semantic steps.
        steps: usize,
    },
    /// One semantic guard missed without applying the current step.
    GuardMiss {
        /// Zero-based step at which interpreter execution may resume.
        index: usize,
        /// Exact runtime observation at the resume boundary.
        observation: ProfileMachineObservation,
    },
}

/// Indexed current-step failure with exact committed-prefix evidence.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedNativeSequenceExecutionFailure<RunnerError> {
    cause: Box<RegisterMaskedNativeOwnerExecutionFailure<RunnerError>>,
    completed_steps: usize,
    observation: ProfileMachineObservation,
    step_index: usize,
}

/// Result of executing one already-loaded exact v6 sequence.
pub type RegisterMaskedNativeSequenceExecutionResult<RunnerError> = Result<
    RegisterMaskedNativeSequenceOutcome,
    Box<RegisterMaskedNativeSequenceExecutionFailure<RunnerError>>,
>;

impl Display for RegisterMaskedNativeSequencePlanError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::ArtifactCount { artifacts, programs } => write!(
                f,
                "v6 sequence has {artifacts} artifacts for {programs} programs",
            ),
            Self::ArtifactIdentity { index } => {
                write!(
                    f,
                    "v6 sequence artifact identity differs at step {index}"
                )
            },
            Self::Empty => {
                f.write_str("v6 sequence requires at least one step")
            },
            Self::Identity { index, .. } => {
                write!(f, "v6 sequence identity failed at step {index}")
            },
            Self::ObservationChain { index } => {
                write!(f, "v6 sequence observation chain broke at step {index}")
            },
            Self::ProfileMismatch { index } => {
                write!(f, "v6 sequence profile changed at step {index}")
            },
            Self::ProgramShape { index } => {
                write!(f, "v6 sequence step {index} is not one complete effect")
            },
            Self::TargetMismatch { index } => {
                write!(f, "v6 sequence target changed at step {index}")
            },
            Self::TerminationBeforeEnd { index } => {
                write!(f, "v6 step {index} terminated before sequence end")
            },
        }
    }
}

impl RegisterMaskedNativeSequencePlan {
    /// Returns every exact verified v6 artifact in semantic execution order.
    #[must_use]
    pub fn artifacts(
        &self,
    ) -> &[VerifiedRegisterMaskedHaltFetchNativeObjectArtifact] {
        &self.artifacts
    }

    /// Returns the exact trace entry observation retained by this plan.
    #[must_use]
    pub const fn entry(&self) -> ProfileMachineObservation {
        self.entry
    }

    /// Returns the exact trace exit observation retained by this plan.
    #[must_use]
    pub const fn exit(&self) -> ProfileMachineObservation {
        self.exit
    }

    /// Returns whether this sequence contains no semantic steps.
    ///
    /// Admitted plans are always non-empty; this completes collection-style
    /// inspection without weakening construction.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.programs.is_empty()
    }

    /// Returns the number of exact semantic steps retained by this plan.
    #[must_use]
    pub const fn len(&self) -> usize {
        self.programs.len()
    }

    /// Loads every exact sequence mapping before publishing a reusable owner.
    ///
    /// A later load failure releases the complete ready prefix in reverse
    /// order. Any failed prefix cleanup remains retryable through the
    /// returned failure.
    ///
    /// # Errors
    ///
    /// Returns [`RegisterMaskedNativeSequenceLoadFailure`] with exact failed
    /// index, loaded-prefix count, and optional cleanup ownership.
    pub fn load<Adapter>(
        &self,
        adapter: &mut Adapter,
    ) -> RegisterMaskedNativeSequenceLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let mut owners = Vec::with_capacity(self.len());
        for (index, (program, artifact)) in
            self.programs.iter().zip(&self.artifacts).enumerate()
        {
            match RegisterMaskedNativeExecutableOwner::load(
                adapter, program, artifact,
            ) {
                Ok(owner) => owners.push(owner),
                Err(cause) => {
                    let loaded_count = owners.len();
                    let cleanup_failure =
                        release_register_masked_owners(adapter, owners).err();
                    return Err(Box::new(
                        RegisterMaskedNativeSequenceLoadFailure {
                            cause,
                            cleanup_failure,
                            index,
                            loaded_count,
                        },
                    ));
                },
            }
        }
        Ok(LoadedRegisterMaskedNativeSequence {
            owners,
            plan: self.clone(),
        })
    }

    /// Admits complete sequence topology and exact artifact identity.
    ///
    /// The entire semantic chain is checked before any executable mapping can
    /// be allocated. Current halt-fetch-only v6 coverage means a valid plan has
    /// one terminal step; a later position after halt is rejected explicitly.
    ///
    /// # Errors
    ///
    /// Returns [`RegisterMaskedNativeSequencePlanError`] for empty, malformed,
    /// profile/target-mixed, discontinuous, prematurely terminated, or
    /// identity-mismatched input.
    pub fn new(
        programs: &[RegisterMaskedRegionEffectProgram],
        artifacts: &[VerifiedRegisterMaskedHaltFetchNativeObjectArtifact],
    ) -> Result<Self, RegisterMaskedNativeSequencePlanError> {
        if programs.is_empty() {
            return Err(RegisterMaskedNativeSequencePlanError::Empty);
        }
        if programs.len() != artifacts.len() {
            return Err(RegisterMaskedNativeSequencePlanError::ArtifactCount {
                programs: programs.len(),
                artifacts: artifacts.len(),
            });
        }
        validate_program_chain(programs)?;
        validate_artifact_chain(programs, artifacts)?;
        let entry = programs
            .first()
            .and_then(|program| program.program.effects.first())
            .map(|effect| effect.before)
            .ok_or(RegisterMaskedNativeSequencePlanError::ProgramShape {
                index: 0,
            })?;
        let exit_index = programs.len().saturating_sub(1);
        let exit = programs
            .last()
            .and_then(|program| program.program.effects.first())
            .map(|effect| effect.after)
            .ok_or(RegisterMaskedNativeSequencePlanError::ProgramShape {
                index: exit_index,
            })?;
        Ok(Self {
            artifacts: artifacts.to_vec(),
            entry,
            exit,
            programs: programs.to_vec(),
        })
    }

    /// Returns exact register-masked programs in semantic execution order.
    #[must_use]
    pub fn programs(&self) -> &[RegisterMaskedRegionEffectProgram] {
        &self.programs
    }
}

impl<MemoryError> RegisterMaskedNativeSequenceLoadFailure<MemoryError> {
    /// Returns retryable prefix-cleanup failure, when cleanup also failed.
    #[must_use]
    pub const fn cleanup_failure(
        &self,
    ) -> Option<&RegisterMaskedNativeSequenceReleaseFailure<MemoryError>> {
        match &self.cleanup_failure {
            Some(failure) => Some(failure),
            None => None,
        }
    }

    /// Returns the zero-based sequence position whose load failed.
    #[must_use]
    pub const fn index(&self) -> usize {
        self.index
    }

    /// Consumes this failure and returns retryable prefix cleanup ownership.
    #[must_use]
    pub fn into_cleanup_failure(
        self,
    ) -> Option<RegisterMaskedNativeSequenceReleaseFailure<MemoryError>> {
        self.cleanup_failure.map(|failure| *failure)
    }

    /// Returns the number of mappings ready before the failed position.
    #[must_use]
    pub const fn loaded_count(&self) -> usize {
        self.loaded_count
    }

    /// Returns the exact owner-load failure at the failed position.
    #[must_use]
    pub const fn owner_failure(
        &self,
    ) -> &RegisterMaskedNativeOwnerLoadFailure<MemoryError> {
        &self.cause
    }
}

impl<MemoryError: Display> Display
    for RegisterMaskedNativeSequenceLoadFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "v6 sequence load failed at step {}: {}",
            self.index, self.cause,
        )?;
        if self.cleanup_failure.is_some() {
            f.write_str("; loaded-prefix cleanup also failed")?;
        }
        Ok(())
    }
}

impl<MemoryError> RegisterMaskedNativeSequenceReleaseFailure<MemoryError> {
    /// Returns the number of mappings attempted by this release pass.
    #[must_use]
    pub const fn attempted_count(&self) -> usize {
        self.attempted_count
    }

    /// Returns the number of mappings still retained after this pass.
    #[must_use]
    pub const fn failed_count(&self) -> usize {
        self.failures.len()
    }

    /// Returns all exact ready-executable failures retained for retry.
    #[must_use]
    pub fn failures(
        &self,
    ) -> &[RegisterMaskedNativeExecutableReleaseFailure<MemoryError>] {
        &self.failures
    }

    /// Returns the number of mappings released by this pass.
    #[must_use]
    pub const fn released_count(&self) -> usize {
        self.released_count
    }

    /// Retries every still-owned mapping and retains repeated failures only.
    ///
    /// # Errors
    ///
    /// Returns another aggregate failure when at least one release still fails.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> RegisterMaskedNativeSequenceReleaseResult<MemoryError>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = MemoryError>,
    {
        retry_register_masked_release_failures(adapter, self.failures)
    }
}

impl<MemoryError: Display> Display
    for RegisterMaskedNativeSequenceReleaseFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "v6 sequence release retained {} of {} mappings",
            self.failed_count(),
            self.attempted_count,
        )
    }
}

impl LoadedRegisterMaskedNativeSequence {
    /// Executes retained mappings in semantic order without adapter work.
    ///
    /// Complete sequence topology and artifact identity were admitted before
    /// loading. Each current-step failure restores that step through the owner
    /// contract; already committed prior steps remain committed. Guard miss
    /// returns the exact current runtime observation and resume index.
    ///
    /// # Errors
    ///
    /// Returns [`RegisterMaskedNativeSequenceExecutionFailure`] with exact
    /// current-step and committed-prefix evidence.
    pub fn execute<Runner>(
        &self,
        runner: &mut Runner,
        entry: ProfileMachineObservation,
        buffers: NativeRegionBuffers<'_>,
    ) -> RegisterMaskedNativeSequenceExecutionResult<Runner::Error>
    where
        Runner: RegisterMaskedNativeRunner,
    {
        let (memory, input, output) = buffers.into_parts();
        let mut observation = entry;
        for (index, owner) in self.owners.iter().enumerate() {
            let outcome = owner
                .execute(
                    runner,
                    observation,
                    NativeRegionBuffers::new(&mut *memory, input, &mut *output),
                )
                .map_err(|cause| {
                    Box::new(RegisterMaskedNativeSequenceExecutionFailure {
                        cause,
                        completed_steps: index,
                        observation,
                        step_index: index,
                    })
                })?;
            match outcome {
                NativeRegionInvocationOutcome::Applied(next) => {
                    observation = next;
                },
                NativeRegionInvocationOutcome::GuardMiss => {
                    return Ok(
                        RegisterMaskedNativeSequenceOutcome::GuardMiss {
                            index,
                            observation,
                        },
                    );
                },
            }
        }
        Ok(RegisterMaskedNativeSequenceOutcome::Applied {
            observation,
            steps: self.owners.len(),
        })
    }

    /// Returns whether this loaded sequence owns no executable mappings.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.owners.is_empty()
    }

    /// Returns the number of retained executable mappings.
    #[must_use]
    pub const fn len(&self) -> usize {
        self.owners.len()
    }

    /// Returns exact total mapped bytes, or `None` on host-size overflow.
    #[must_use]
    pub fn mapped_bytes(&self) -> Option<usize> {
        self.owners.iter().try_fold(0usize, |total, owner| {
            total.checked_add(owner.resident_weight().mapped_bytes())
        })
    }

    /// Returns the exact admitted sequence plan retained beside the mappings.
    #[must_use]
    pub const fn plan(&self) -> &RegisterMaskedNativeSequencePlan {
        &self.plan
    }

    /// Releases every retained mapping in reverse semantic order.
    ///
    /// Every mapping is attempted even after an earlier cleanup failure. Failed
    /// releases retain exact ready-executable ownership for explicit retry.
    ///
    /// # Errors
    ///
    /// Returns [`RegisterMaskedNativeSequenceReleaseFailure`] when at least one
    /// mapping remains owned after the release pass.
    pub fn release<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> RegisterMaskedNativeSequenceReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        release_register_masked_owners(adapter, self.owners)
    }
}

impl<RunnerError> RegisterMaskedNativeSequenceExecutionFailure<RunnerError> {
    /// Returns the number of exact sequence steps committed before failure.
    #[must_use]
    pub const fn completed_steps(&self) -> usize {
        self.completed_steps
    }

    /// Returns the exact current-step owner execution failure.
    #[must_use]
    pub const fn execution_failure(
        &self,
    ) -> &RegisterMaskedNativeOwnerExecutionFailure<RunnerError> {
        &self.cause
    }

    /// Returns the exact runtime observation at the failed step boundary.
    #[must_use]
    pub const fn observation(&self) -> ProfileMachineObservation {
        self.observation
    }

    /// Returns the next semantic step index for interpreter continuation.
    #[must_use]
    pub const fn resume_index(&self) -> usize {
        self.step_index
    }

    /// Returns the zero-based v6 step whose execution failed.
    #[must_use]
    pub const fn step_index(&self) -> usize {
        self.step_index
    }
}

impl<RunnerError: Display> Display
    for RegisterMaskedNativeSequenceExecutionFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "v6 sequence step {} failed after {} committed steps: {}",
            self.step_index, self.completed_steps, self.cause,
        )
    }
}

impl RegisterMaskedNativeSequenceOutcome {
    /// Returns the number of sequence steps committed before this outcome.
    #[must_use]
    pub const fn completed_steps(self) -> usize {
        match self {
            Self::Applied { steps, .. } => steps,
            Self::GuardMiss { index, .. } => index,
        }
    }

    /// Returns the exact runtime observation at the continuation boundary.
    #[must_use]
    pub const fn observation(self) -> ProfileMachineObservation {
        match self {
            Self::Applied { observation, .. }
            | Self::GuardMiss { observation, .. } => observation,
        }
    }

    /// Returns the next semantic step index for interpreter continuation.
    #[must_use]
    pub const fn resume_index(self) -> usize {
        match self {
            Self::Applied { steps, .. } => steps,
            Self::GuardMiss { index, .. } => index,
        }
    }
}

fn validate_program_chain(
    programs: &[RegisterMaskedRegionEffectProgram],
) -> Result<(), RegisterMaskedNativeSequencePlanError> {
    let first = programs
        .first()
        .ok_or(RegisterMaskedNativeSequencePlanError::Empty)?;
    let mut previous_after = None;
    for (index, program) in programs.iter().enumerate() {
        let [effect] = program.program.effects.as_slice() else {
            return Err(RegisterMaskedNativeSequencePlanError::ProgramShape {
                index,
            });
        };
        if program.format_version() != EFFECT_IR_REGISTER_MASK_VERSION
            || program.program.step_budget != 1
            || program.register_writes.len() != 1
        {
            return Err(RegisterMaskedNativeSequencePlanError::ProgramShape {
                index,
            });
        }
        if !same_sequence_profile(first, program) {
            return Err(
                RegisterMaskedNativeSequencePlanError::ProfileMismatch {
                    index,
                },
            );
        }
        if previous_after.is_some_and(|after| after != effect.before) {
            return Err(
                RegisterMaskedNativeSequencePlanError::ObservationChain {
                    index,
                },
            );
        }
        let is_final = index == programs.len().saturating_sub(1);
        if !is_final && effect.after.termination.is_some() {
            return Err(
                RegisterMaskedNativeSequencePlanError::TerminationBeforeEnd {
                    index,
                },
            );
        }
        previous_after = Some(effect.after);
    }
    Ok(())
}

fn validate_artifact_chain(
    programs: &[RegisterMaskedRegionEffectProgram],
    artifacts: &[VerifiedRegisterMaskedHaltFetchNativeObjectArtifact],
) -> Result<(), RegisterMaskedNativeSequencePlanError> {
    let first_target = artifacts
        .first()
        .ok_or(RegisterMaskedNativeSequencePlanError::Empty)?
        .key()
        .target();
    for (index, (program, artifact)) in
        programs.iter().zip(artifacts).enumerate()
    {
        if artifact.key().target() != first_target {
            return Err(
                RegisterMaskedNativeSequencePlanError::TargetMismatch { index },
            );
        }
        let expected = NativeArtifactKey::new_register_masked(
            program,
            artifact.key().target().clone(),
        )
        .map_err(|error| {
            RegisterMaskedNativeSequencePlanError::Identity { index, error }
        })?;
        if artifact.key() != &expected {
            return Err(
                RegisterMaskedNativeSequencePlanError::ArtifactIdentity {
                    index,
                },
            );
        }
    }
    Ok(())
}

fn same_sequence_profile(
    first: &RegisterMaskedRegionEffectProgram,
    candidate: &RegisterMaskedRegionEffectProgram,
) -> bool {
    candidate.program.profile_id == first.program.profile_id
        && candidate.program.profile_fingerprint
            == first.program.profile_fingerprint
        && candidate.program.profile_requirement
            == first.program.profile_requirement
}

fn release_register_masked_owners<Adapter>(
    adapter: &mut Adapter,
    owners: Vec<RegisterMaskedNativeExecutableOwner>,
) -> RegisterMaskedNativeSequenceReleaseResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let attempted_count = owners.len();
    let mut failures = Vec::new();
    let mut released_count = 0usize;
    for owner in owners.into_iter().rev() {
        match owner.release(adapter) {
            Ok(()) => released_count = released_count.saturating_add(1),
            Err(failure) => failures.push(*failure),
        }
    }
    register_masked_release_pass_result(
        attempted_count,
        released_count,
        failures,
    )
}

fn retry_register_masked_release_failures<Adapter>(
    adapter: &mut Adapter,
    pending: Vec<RegisterMaskedNativeExecutableReleaseFailure<Adapter::Error>>,
) -> RegisterMaskedNativeSequenceReleaseResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let attempted_count = pending.len();
    let mut failures = Vec::new();
    let mut released_count = 0usize;
    for failure in pending {
        match failure.retry(adapter) {
            Ok(()) => released_count = released_count.saturating_add(1),
            Err(retry_failure) => failures.push(retry_failure),
        }
    }
    register_masked_release_pass_result(
        attempted_count,
        released_count,
        failures,
    )
}

fn register_masked_release_pass_result<MemoryError>(
    attempted_count: usize,
    released_count: usize,
    failures: Vec<RegisterMaskedNativeExecutableReleaseFailure<MemoryError>>,
) -> RegisterMaskedNativeSequenceReleaseResult<MemoryError> {
    if failures.is_empty() {
        Ok(())
    } else {
        Err(Box::new(RegisterMaskedNativeSequenceReleaseFailure {
            attempted_count,
            failures,
            released_count,
        }))
    }
}
