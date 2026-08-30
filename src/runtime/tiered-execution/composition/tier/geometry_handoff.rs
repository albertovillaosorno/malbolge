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
//   - One-step normative replay of explicit-geometry portable IR.
// - Must-Not:
//   - Grant native authority, reconstruct geometry tokens, or trust v5 bytes.
// - Allows:
//   - Inputs: one validated checkpoint and one explicit-geometry v5 program.
//   - Outputs: exact completion or fail-closed entry checkpoint.
//   - Side effects: owned safe-Rust interpreter mutation only.
// - Split-When:
//   - Multistep geometry continuations gain independent scheduling policy.
// - Merge-When:
//   - Ordinary interpreter handoff accepts the same geometry-bound authority.
// - Summary:
//   - Preserves opaque derived geometry while revalidating v5 normatively.
// - Description:
//   - Admits checkpoint metadata, replays one step, and compares full v5 IR.
// - Usage:
//   - Used before any future derived-geometry continuation or native retry.
// - Defaults:
//   - Candidate IR is untrusted; mismatch returns the untouched entry state.
//

//! Geometry-preserving normative replay for one explicit-geometry v5 step.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{
    ExecutionGeometryRegionEffectProgram, ProfileExecutionGeometryRequirement,
    ProfileMachine, ProfileMachineError, ProfileMachineObservation,
    ProfileMachineState, StepOutcome, StepProgramProjectionError,
    TargetProfileRequirement, target_profile,
};

/// Rejection before a geometry-bound interpreter step can begin.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryHandoffAdmissionError {
    /// The checkpoint's opaque geometry disagrees with the v5 declaration.
    CheckpointGeometry,
    /// The checkpoint observation differs from the retained v5 entry.
    CheckpointObservation,
    /// The checkpoint selected a different canonical profile.
    CheckpointProfile,
    /// The v5 region addresses beyond its declared execution geometry.
    ExecutionCapacity,
    /// A required entry-memory value differs before execution.
    LiveIn {
        /// Exact guest address checked at admission.
        address: u32,
        /// Value retained by v5 evidence.
        expected: u32,
        /// Value carried by the checkpoint.
        observed: u32,
    },
    /// One required address is outside the checkpoint memory image.
    LiveInAddress {
        /// Exact guest address that could not be inspected.
        address: u32,
    },
    /// Canonical profile fingerprint differs from the v5 declaration.
    ProfileFingerprint,
    /// Canonical profile requirement differs from the v5 declaration.
    ProfileRequirement,
    /// The v5 wrapper unexpectedly retained no one-step entry observation.
    ProgramShape,
    /// The v5 program names no canonical profile in the registry.
    UnknownProfile,
}

/// Why normative geometry-bound replay failed after admission.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryHandoffExecutionCause {
    /// The profile machine rejected the requested step.
    Machine(ProfileMachineError),
    /// The traced normative step differed from the retained v5 program.
    ProgramMismatch,
    /// The normative trace could not be projected back to v5.
    Projection(StepProgramProjectionError),
    /// The profile machine returned without publishing its trace callback.
    TraceMissing,
}

/// Admitted one-step replay retaining an opaque checkpoint geometry token.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryInterpreterHandoff {
    checkpoint: ProfileMachineState,
    program: ExecutionGeometryRegionEffectProgram,
}

/// Successful geometry-preserving normative replay.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryInterpreterHandoffCompletion {
    outcome: StepOutcome,
    program: ExecutionGeometryRegionEffectProgram,
    state: ProfileMachineState,
}

/// Fail-closed replay result retaining the untouched entry checkpoint.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryInterpreterHandoffFailure {
    cause: ExecutionGeometryHandoffExecutionCause,
    program: ExecutionGeometryRegionEffectProgram,
    state: ProfileMachineState,
}

/// Result of one admitted explicit-geometry interpreter replay.
pub type ExecutionGeometryInterpreterHandoffResult = Result<
    ExecutionGeometryInterpreterHandoffCompletion,
    Box<ExecutionGeometryInterpreterHandoffFailure>,
>;

impl Display for ExecutionGeometryHandoffAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::CheckpointGeometry => {
                f.write_str("v5 checkpoint geometry drifted")
            },
            Self::CheckpointObservation => {
                f.write_str("v5 checkpoint observation drifted")
            },
            Self::CheckpointProfile => {
                f.write_str("v5 checkpoint profile drifted")
            },
            Self::ExecutionCapacity => {
                f.write_str("v5 program exceeds its execution geometry")
            },
            Self::LiveIn {
                address,
                expected,
                observed,
            } => write!(
                f,
                "v5 live-in {address}: expected {expected}, got {observed}",
            ),
            Self::LiveInAddress { address } => {
                write!(f, "v5 live-in address {address} is unavailable")
            },
            Self::ProgramShape => f.write_str("v5 program is not one step"),
            Self::ProfileFingerprint => {
                f.write_str("v5 profile fingerprint drifted")
            },
            Self::ProfileRequirement => {
                f.write_str("v5 profile requirement drifted")
            },
            Self::UnknownProfile => f.write_str("v5 profile is unknown"),
        }
    }
}

impl Display for ExecutionGeometryHandoffExecutionCause {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Machine(error) => write!(f, "v5 interpreter step: {error}"),
            Self::ProgramMismatch => {
                f.write_str("normative trace differs from v5 program")
            },
            Self::Projection(error) => write!(
                f,
                "normative v5 projection failed: {}",
                projection_error_id(*error),
            ),
            Self::TraceMissing => f.write_str("normative v5 trace is missing"),
        }
    }
}

impl Display for ExecutionGeometryInterpreterHandoffFailure {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "explicit-geometry interpreter handoff failed: {}",
            self.cause
        )
    }
}

impl ExecutionGeometryInterpreterHandoff {
    /// Replays one admitted v5 step normatively and accepts exact reprojection.
    ///
    /// Any machine, projection, or program mismatch returns the untouched entry
    /// checkpoint. No native artifact or v5 byte stream receives authority.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryInterpreterHandoffFailure`] when normative
    /// execution, trace projection, or exact v5 comparison fails.
    pub fn execute(self) -> ExecutionGeometryInterpreterHandoffResult {
        let Self { checkpoint, program } = self;
        let entry = checkpoint.clone();
        let mut machine = ProfileMachine::from_snapshot(checkpoint);
        let mut trace_slot = None;
        let outcome = machine
            .step_traced(&mut |trace| trace_slot = Some(*trace))
            .map_err(|error| {
                failure(
                    ExecutionGeometryHandoffExecutionCause::Machine(error),
                    program.clone(),
                    entry.clone(),
                )
            })?;
        let Some(trace) = trace_slot else {
            return Err(failure(
                ExecutionGeometryHandoffExecutionCause::TraceMissing,
                program,
                entry,
            ));
        };
        let observed =
            ExecutionGeometryRegionEffectProgram::from_profile_step_trace(
                &trace,
            )
            .map_err(|error| {
                failure(
                    ExecutionGeometryHandoffExecutionCause::Projection(error),
                    program.clone(),
                    entry.clone(),
                )
            })?;
        if observed != program {
            return Err(failure(
                ExecutionGeometryHandoffExecutionCause::ProgramMismatch,
                program,
                entry,
            ));
        }
        Ok(ExecutionGeometryInterpreterHandoffCompletion {
            outcome,
            program,
            state: machine.snapshot_state(),
        })
    }

    /// Admits one v5 candidate against a validated checkpoint authority.
    ///
    /// The checkpoint is the only source of opaque geometry authority. V5
    /// geometry is declarative and must exactly match its visible projection.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryHandoffAdmissionError`] when profile,
    /// geometry, entry observation, capacity, or live-ins drift.
    pub fn new(
        program: ExecutionGeometryRegionEffectProgram,
        checkpoint: ProfileMachineState,
    ) -> Result<Self, ExecutionGeometryHandoffAdmissionError> {
        admit_profile(&program, &checkpoint)?;
        admit_checkpoint(&program, &checkpoint)?;
        admit_live_ins(&program, checkpoint.memory())?;
        Ok(Self { checkpoint, program })
    }
}

impl ExecutionGeometryInterpreterHandoffCompletion {
    /// Returns the public result of the normatively replayed step.
    #[must_use]
    pub const fn outcome(&self) -> StepOutcome {
        self.outcome
    }

    /// Returns the exact v5 program accepted by normative reprojection.
    #[must_use]
    pub const fn program(&self) -> &ExecutionGeometryRegionEffectProgram {
        &self.program
    }

    /// Returns the final checkpoint retaining the opaque execution geometry.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        &self.state
    }
}

impl ExecutionGeometryInterpreterHandoffFailure {
    /// Returns why normative replay failed.
    #[must_use]
    pub const fn cause(&self) -> ExecutionGeometryHandoffExecutionCause {
        self.cause
    }

    /// Returns the untrusted v5 candidate that failed replay.
    #[must_use]
    pub const fn program(&self) -> &ExecutionGeometryRegionEffectProgram {
        &self.program
    }

    /// Returns the untouched admitted entry checkpoint.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        &self.state
    }
}

fn admit_checkpoint(
    program: &ExecutionGeometryRegionEffectProgram,
    checkpoint: &ProfileMachineState,
) -> Result<(), ExecutionGeometryHandoffAdmissionError> {
    let geometry = ProfileExecutionGeometryRequirement::from_execution_geometry(
        checkpoint.geometry(),
    );
    if geometry != program.execution_geometry() {
        return Err(ExecutionGeometryHandoffAdmissionError::CheckpointGeometry);
    }
    if !program.fits_execution_geometry_capacity() {
        return Err(ExecutionGeometryHandoffAdmissionError::ExecutionCapacity);
    }
    let Some(entry) = program.entry_observation() else {
        return Err(ExecutionGeometryHandoffAdmissionError::ProgramShape);
    };
    if state_observation(checkpoint) != entry {
        return Err(
            ExecutionGeometryHandoffAdmissionError::CheckpointObservation,
        );
    }
    Ok(())
}

fn admit_live_ins(
    program: &ExecutionGeometryRegionEffectProgram,
    memory: &[u32],
) -> Result<(), ExecutionGeometryHandoffAdmissionError> {
    for live_in in program.memory_live_ins() {
        let Ok(index) = usize::try_from(live_in.address) else {
            return Err(
                ExecutionGeometryHandoffAdmissionError::LiveInAddress {
                    address: live_in.address,
                },
            );
        };
        let Some(observed) = memory.get(index).copied() else {
            return Err(
                ExecutionGeometryHandoffAdmissionError::LiveInAddress {
                    address: live_in.address,
                },
            );
        };
        if observed != live_in.value {
            return Err(ExecutionGeometryHandoffAdmissionError::LiveIn {
                address: live_in.address,
                expected: live_in.value,
                observed,
            });
        }
    }
    Ok(())
}

fn admit_profile(
    program: &ExecutionGeometryRegionEffectProgram,
    checkpoint: &ProfileMachineState,
) -> Result<(), ExecutionGeometryHandoffAdmissionError> {
    let Some(profile) = target_profile(program.profile_id()) else {
        return Err(ExecutionGeometryHandoffAdmissionError::UnknownProfile);
    };
    if checkpoint.profile() != profile {
        return Err(ExecutionGeometryHandoffAdmissionError::CheckpointProfile);
    }
    if profile.fingerprint() != program.profile_fingerprint() {
        return Err(ExecutionGeometryHandoffAdmissionError::ProfileFingerprint);
    }
    if TargetProfileRequirement::from_descriptor(profile)
        != *program.profile_requirement()
    {
        return Err(ExecutionGeometryHandoffAdmissionError::ProfileRequirement);
    }
    Ok(())
}

fn failure(
    cause: ExecutionGeometryHandoffExecutionCause,
    program: ExecutionGeometryRegionEffectProgram,
    state: ProfileMachineState,
) -> Box<ExecutionGeometryInterpreterHandoffFailure> {
    Box::new(ExecutionGeometryInterpreterHandoffFailure {
        cause,
        program,
        state,
    })
}

const fn projection_error_id(
    error: StepProgramProjectionError,
) -> &'static str {
    match error {
        StepProgramProjectionError::ConflictingMemoryRead => {
            "conflicting-memory-read"
        },
        StepProgramProjectionError::ExecutionGeometry => "execution-geometry",
        StepProgramProjectionError::FetchAddress => "fetch-address",
        StepProgramProjectionError::FetchValue => "fetch-value",
        StepProgramProjectionError::MissingFetch => "missing-fetch",
        StepProgramProjectionError::Outcome => "outcome",
        StepProgramProjectionError::RejectedTrace => "rejected-trace",
        StepProgramProjectionError::TerminatedEntry => "terminated-entry",
    }
}

fn state_observation(state: &ProfileMachineState) -> ProfileMachineObservation {
    ProfileMachineObservation {
        input_consumed: state.io().input_consumed(),
        output_len: state.io().output().len(),
        registers: state.registers(),
        termination: state.io().termination(),
    }
}
