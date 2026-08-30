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
//   - One-step and affine multistep replay of explicit-geometry portable IR.
// - Must-Not:
//   - Grant native authority, reconstruct geometry tokens, or trust v5 bytes.
// - Allows:
//   - Inputs: validated checkpoints and ordered explicit-geometry v5 programs.
//   - Outputs: exact completion, suspension, or fail-closed checkpoint.
//   - Side effects: owned safe-Rust interpreter mutation only.
// - Split-When:
//   - Geometry continuations gain native admission or scheduling policy.
// - Merge-When:
//   - Ordinary interpreter handoff accepts the same geometry-bound authority.
// - Summary:
//   - Preserves opaque derived geometry while revalidating v5 normatively.
// - Description:
//   - Replays one or more v5 steps and retains exact admitted prefix state.
// - Usage:
//   - Used for derived-geometry interpreter replay before native admission.
// - Defaults:
//   - Candidate IR is untrusted; mismatch returns the untouched entry state.
//

//! Geometry-preserving normative replay for explicit-geometry v5 steps.

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

/// Rejection while binding a multistep v5 sequence to one checkpoint.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryContinuationAdmissionError {
    /// A geometry continuation requires at least one one-step program.
    Empty,
    /// One step directly addresses beyond its declared execution geometry.
    ExecutionCapacity {
        /// Zero-based failing sequence position.
        index: usize,
    },
    /// One step changed the declarative execution geometry.
    GeometryDrift {
        /// Zero-based mismatching sequence position.
        index: usize,
    },
    /// Adjacent v5 step observations are not byte-exactly continuous.
    ObservationChain {
        /// Zero-based step whose entry differs from the prior exit.
        index: usize,
    },
    /// One step changed canonical profile identity or requirement.
    ProfileDrift {
        /// Zero-based mismatching sequence position.
        index: usize,
    },
    /// One v5 wrapper lacks its required one-step observation shape.
    ProgramShape {
        /// Zero-based malformed sequence position.
        index: usize,
    },
    /// Initial checkpoint admission failed before any transition.
    Step {
        /// Zero-based sequence position, currently always zero.
        index: usize,
        /// Exact one-step checkpoint admission failure.
        error: ExecutionGeometryHandoffAdmissionError,
    },
    /// A terminated v5 observation was followed by another candidate step.
    TerminationBeforeEnd {
        /// Zero-based non-final step that declared termination.
        index: usize,
    },
}

/// Why an admitted multistep geometry continuation failed during replay.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryContinuationExecutionCause {
    /// A later step no longer admits the checkpoint produced by prior replay.
    Admission(ExecutionGeometryHandoffAdmissionError),
    /// The completed checkpoint differed from the retained final observation.
    FinalObservation,
    /// Normative one-step replay failed at the current sequence position.
    Step(ExecutionGeometryHandoffExecutionCause),
}

/// Affine multistep v5 replay retaining opaque checkpoint geometry authority.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryInterpreterContinuation {
    expected_exit: ProfileMachineObservation,
    expected_outcome: malbolge::RunOutcome,
    programs: Vec<ExecutionGeometryRegionEffectProgram>,
    resume_index: usize,
    state: ProfileMachineState,
}

/// Completed multistep geometry replay with exact original program evidence.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryInterpreterContinuationCompletion {
    outcome: malbolge::RunOutcome,
    programs: Vec<ExecutionGeometryRegionEffectProgram>,
    state: ProfileMachineState,
}

/// One budgeted multistep geometry replay result.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryContinuationBudgetOutcome {
    /// All retained v5 steps replayed and reprojected exactly.
    Completed(ExecutionGeometryInterpreterContinuationCompletion),
    /// Budget ended before all retained v5 steps replayed.
    Suspended(ExecutionGeometryInterpreterContinuation),
}

/// Fail-closed multistep replay retaining the last admitted checkpoint.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryInterpreterContinuationFailure {
    cause: ExecutionGeometryContinuationExecutionCause,
    index: usize,
    programs: Vec<ExecutionGeometryRegionEffectProgram>,
    state: ProfileMachineState,
}

/// Result of completing all remaining explicit-geometry continuation work.
pub type ExecutionGeometryInterpreterContinuationResult = Result<
    ExecutionGeometryInterpreterContinuationCompletion,
    Box<ExecutionGeometryInterpreterContinuationFailure>,
>;

/// Result of one budgeted explicit-geometry continuation slice.
pub type ExecutionGeometryInterpreterContinuationBudgetResult = Result<
    ExecutionGeometryContinuationBudgetOutcome,
    Box<ExecutionGeometryInterpreterContinuationFailure>,
>;

#[derive(Clone, Copy)]
struct ExecutionGeometryContinuationBoundary {
    exit: ProfileMachineObservation,
    outcome: malbolge::RunOutcome,
}

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

impl Display for ExecutionGeometryContinuationAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Empty => f.write_str("v5 continuation is empty"),
            Self::ExecutionCapacity { index } => {
                write!(f, "v5 continuation step {index} exceeds geometry")
            },
            Self::GeometryDrift { index } => {
                write!(f, "v5 continuation geometry changed at step {index}")
            },
            Self::ObservationChain { index } => write!(
                f,
                "v5 continuation observation chain broke at step {index}",
            ),
            Self::ProfileDrift { index } => {
                write!(f, "v5 continuation profile changed at step {index}")
            },
            Self::ProgramShape { index } => {
                write!(f, "v5 continuation step {index} is not one step")
            },
            Self::Step { error, index } => {
                write!(f, "v5 continuation step {index} admission: {error}")
            },
            Self::TerminationBeforeEnd { index } => write!(
                f,
                "v5 continuation step {index} terminates before the end",
            ),
        }
    }
}

impl Display for ExecutionGeometryContinuationExecutionCause {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Admission(error) => {
                write!(f, "v5 continuation admission: {error}")
            },
            Self::FinalObservation => {
                f.write_str("v5 continuation final observation drifted")
            },
            Self::Step(error) => write!(f, "v5 continuation replay: {error}"),
        }
    }
}

impl Display for ExecutionGeometryInterpreterContinuationFailure {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "explicit-geometry continuation failed at step {}: {}",
            self.index, self.cause
        )
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
        admit_program(&program, &checkpoint)?;
        Ok(Self { checkpoint, program })
    }
}

impl ExecutionGeometryInterpreterContinuation {
    /// Returns the number of sequence steps already replayed exactly.
    #[must_use]
    pub const fn completed_steps(&self) -> usize {
        self.resume_index
    }

    /// Replays every remaining v5 step and requires exact reprojection.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryInterpreterContinuationFailure`] at the first
    /// step whose checkpoint admission or normative reprojection fails.
    pub fn execute(mut self) -> ExecutionGeometryInterpreterContinuationResult {
        while self.resume_index < self.programs.len() {
            self = execute_continuation_step(self)?;
        }
        finish_continuation(self)
    }

    /// Replays at most `step_budget` remaining v5 steps.
    ///
    /// A zero budget performs no transition and returns the same continuation.
    /// Successful partial replay retains the exact opaque geometry token in its
    /// new checkpoint.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryInterpreterContinuationFailure`] at the first
    /// step whose checkpoint admission or normative reprojection fails.
    pub fn execute_with_budget(
        mut self,
        step_budget: usize,
    ) -> ExecutionGeometryInterpreterContinuationBudgetResult {
        let target = self
            .resume_index
            .saturating_add(step_budget)
            .min(self.programs.len());
        while self.resume_index < target {
            self = execute_continuation_step(self)?;
        }
        if self.resume_index == self.programs.len() {
            let completion = finish_continuation(self)?;
            Ok(ExecutionGeometryContinuationBudgetOutcome::Completed(
                completion,
            ))
        } else {
            Ok(ExecutionGeometryContinuationBudgetOutcome::Suspended(self))
        }
    }

    /// Returns the exact final observation retained by the complete sequence.
    #[must_use]
    pub const fn expected_exit(&self) -> ProfileMachineObservation {
        self.expected_exit
    }

    /// Returns the complete sequence's expected bounded-run outcome.
    #[must_use]
    pub const fn expected_outcome(&self) -> malbolge::RunOutcome {
        self.expected_outcome
    }

    /// Binds one ordered v5 sequence to an opaque validated checkpoint token.
    ///
    /// Sequence geometry/profile/observation continuity is declarative only;
    /// every step still requires normative replay before progress is admitted.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryContinuationAdmissionError`] for empty,
    /// discontinuous, profile/geometry-mixed, over-capacity, terminated-prefix,
    /// or initial-checkpoint-incompatible sequences.
    pub fn new(
        programs: Vec<ExecutionGeometryRegionEffectProgram>,
        state: ProfileMachineState,
    ) -> Result<Self, ExecutionGeometryContinuationAdmissionError> {
        let boundary = validate_continuation_programs(&programs)?;
        let first = programs
            .first()
            .ok_or(ExecutionGeometryContinuationAdmissionError::Empty)?;
        admit_program(first, &state).map_err(|error| {
            ExecutionGeometryContinuationAdmissionError::Step {
                error,
                index: 0,
            }
        })?;
        Ok(Self {
            expected_exit: boundary.exit,
            expected_outcome: boundary.outcome,
            programs,
            resume_index: 0,
            state,
        })
    }

    /// Returns the complete ordered v5 evidence retained by this continuation.
    #[must_use]
    pub fn programs(&self) -> &[ExecutionGeometryRegionEffectProgram] {
        &self.programs
    }

    /// Returns the exact v5 suffix still requiring normative replay.
    #[must_use]
    pub fn remaining_programs(
        &self,
    ) -> &[ExecutionGeometryRegionEffectProgram] {
        self.programs.get(self.resume_index..).unwrap_or(&[])
    }

    /// Returns the number of v5 steps still requiring normative replay.
    #[must_use]
    pub const fn remaining_steps(&self) -> usize {
        self.programs.len().saturating_sub(self.resume_index)
    }

    /// Returns the next zero-based sequence position to replay.
    #[must_use]
    pub const fn resume_index(&self) -> usize {
        self.resume_index
    }

    /// Returns the last fully admitted checkpoint for this continuation.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        &self.state
    }
}

impl ExecutionGeometryInterpreterContinuationCompletion {
    /// Returns the complete bounded-run outcome after exact replay.
    #[must_use]
    pub const fn outcome(&self) -> malbolge::RunOutcome {
        self.outcome
    }

    /// Returns the complete ordered v5 evidence that replayed exactly.
    #[must_use]
    pub fn programs(&self) -> &[ExecutionGeometryRegionEffectProgram] {
        &self.programs
    }

    /// Returns the final checkpoint retaining opaque execution geometry.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        &self.state
    }
}

impl ExecutionGeometryInterpreterContinuationFailure {
    /// Returns why replay stopped at the reported sequence position.
    #[must_use]
    pub const fn cause(&self) -> ExecutionGeometryContinuationExecutionCause {
        self.cause
    }

    /// Returns the zero-based v5 step that failed admission or replay.
    #[must_use]
    pub const fn index(&self) -> usize {
        self.index
    }

    /// Returns the complete untrusted ordered v5 candidate sequence.
    #[must_use]
    pub fn programs(&self) -> &[ExecutionGeometryRegionEffectProgram] {
        &self.programs
    }

    /// Returns the last fully admitted checkpoint before the failing step.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        &self.state
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

fn admit_program(
    program: &ExecutionGeometryRegionEffectProgram,
    checkpoint: &ProfileMachineState,
) -> Result<(), ExecutionGeometryHandoffAdmissionError> {
    admit_profile(program, checkpoint)?;
    admit_checkpoint(program, checkpoint)?;
    admit_live_ins(program, checkpoint.memory())
}

fn continuation_failure(
    cause: ExecutionGeometryContinuationExecutionCause,
    index: usize,
    continuation: ExecutionGeometryInterpreterContinuation,
) -> Box<ExecutionGeometryInterpreterContinuationFailure> {
    Box::new(ExecutionGeometryInterpreterContinuationFailure {
        cause,
        index,
        programs: continuation.programs,
        state: continuation.state,
    })
}

fn execute_continuation_step(
    mut continuation: ExecutionGeometryInterpreterContinuation,
) -> Result<
    ExecutionGeometryInterpreterContinuation,
    Box<ExecutionGeometryInterpreterContinuationFailure>,
> {
    let index = continuation.resume_index;
    let Some(program) = continuation.programs.get(index).cloned() else {
        return Err(continuation_failure(
            ExecutionGeometryContinuationExecutionCause::FinalObservation,
            index,
            continuation,
        ));
    };
    if let Err(error) = admit_program(&program, &continuation.state) {
        return Err(continuation_failure(
            ExecutionGeometryContinuationExecutionCause::Admission(error),
            index,
            continuation,
        ));
    }
    let handoff = ExecutionGeometryInterpreterHandoff {
        checkpoint: continuation.state,
        program,
    };
    match handoff.execute() {
        Ok(completion) => {
            continuation.state = completion.state;
            continuation.resume_index =
                continuation.resume_index.saturating_add(1);
            Ok(continuation)
        },
        Err(failure) => {
            let ExecutionGeometryInterpreterHandoffFailure {
                cause, state, ..
            } = *failure;
            continuation.state = state;
            Err(continuation_failure(
                ExecutionGeometryContinuationExecutionCause::Step(cause),
                index,
                continuation,
            ))
        },
    }
}

fn finish_continuation(
    continuation: ExecutionGeometryInterpreterContinuation,
) -> ExecutionGeometryInterpreterContinuationResult {
    if state_observation(&continuation.state) != continuation.expected_exit {
        let index = continuation.resume_index;
        return Err(continuation_failure(
            ExecutionGeometryContinuationExecutionCause::FinalObservation,
            index,
            continuation,
        ));
    }
    Ok(ExecutionGeometryInterpreterContinuationCompletion {
        outcome: continuation.expected_outcome,
        programs: continuation.programs,
        state: continuation.state,
    })
}

fn validate_continuation_programs(
    programs: &[ExecutionGeometryRegionEffectProgram],
) -> Result<
    ExecutionGeometryContinuationBoundary,
    ExecutionGeometryContinuationAdmissionError,
> {
    use ExecutionGeometryContinuationAdmissionError as AdmissionError;

    let Some(first) = programs.first() else {
        return Err(AdmissionError::Empty);
    };
    let Some(_first_entry) = first.entry_observation() else {
        return Err(AdmissionError::ProgramShape { index: 0 });
    };
    let mut previous_exit: Option<ProfileMachineObservation> = None;
    for (index, program) in programs.iter().enumerate() {
        let Some(entry) = program.entry_observation() else {
            return Err(AdmissionError::ProgramShape { index });
        };
        let Some(exit) = program.exit_observation() else {
            return Err(AdmissionError::ProgramShape { index });
        };
        if program.execution_geometry() != first.execution_geometry() {
            return Err(AdmissionError::GeometryDrift { index });
        }
        if program.profile_id() != first.profile_id()
            || program.profile_fingerprint() != first.profile_fingerprint()
            || program.profile_requirement() != first.profile_requirement()
        {
            return Err(AdmissionError::ProfileDrift { index });
        }
        if !program.fits_execution_geometry_capacity() {
            return Err(AdmissionError::ExecutionCapacity { index });
        }
        if let Some(previous) = previous_exit {
            if previous.termination.is_some() {
                let error = AdmissionError::TerminationBeforeEnd {
                    index: index.saturating_sub(1),
                };
                return Err(error);
            }
            if previous != entry {
                let error = AdmissionError::ObservationChain { index };
                return Err(error);
            }
        }
        previous_exit = Some(exit);
    }
    let exit = previous_exit.ok_or(AdmissionError::Empty)?;
    let steps = programs.len();
    let outcome = exit
        .termination
        .map_or(malbolge::RunOutcome::BudgetExhausted { steps }, |reason| {
            malbolge::RunOutcome::Terminated { reason, steps }
        });
    Ok(ExecutionGeometryContinuationBoundary { exit, outcome })
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
