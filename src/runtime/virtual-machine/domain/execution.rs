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
//   - Explicit selection between interpreter authority and specification study.
// - Must-Not:
//   - Make specification comparison implicit or let it satisfy verification.
// - Allows:
//   - Inputs: validated classic source/state, byte input, and explicit mode.
//   - Outputs: mode-tagged execution results, traces, and diagnostics.
//   - Side effects: mutation only of the owned in-memory machine state.
// - Split-When:
//   - Split when a compatibility implementation gains a separate lifecycle.
// - Merge-When:
//   - Merge when mode selection no longer needs an explicit trust boundary.
// - Summary:
//   - Execution facade separating interpreter authority from specification
//     study.
// - Description:
//   - Keeps `Machine` interpreter-compatible while allowing explicit
//     comparison.
// - Usage:
//   - Use when callers must select an execution mode deliberately.
// - Defaults:
//   - Interpreter behavior is always available and verifier eligible.
//

//! Explicit execution facade for interpreter and specification modes.

use std::fmt::{Display, Formatter, Result as FormatResult};

use crate::annotated::{AnnotatedLoadError, canonicalize_annotated_source};
use crate::loader::{LoadError, source_word_requirement};
use crate::machine::{
    Machine, MachineError, MachineState, Registers, RunOutcome, StepOutcome,
    Termination,
};
use crate::memory::{Memory, MemoryError};
use crate::mode::ExecutionMode;
use crate::profile::{
    ProfileDescriptor, ProfileRequirementError, historical_profile,
    preflight_profile, safe_rust_classic_capability,
};
use crate::trace::StepTrace;
use crate::word::Word;

/// Mode-tagged failure from construction or execution.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ExecutionError {
    kind: ExecutionErrorKind,
    mode: ExecutionMode,
}

impl ExecutionError {
    /// Returns the stable failure category.
    #[must_use]
    pub const fn kind(self) -> ExecutionErrorKind {
        self.kind
    }

    const fn load(mode: ExecutionMode, error: LoadError) -> Self {
        Self {
            kind: ExecutionErrorKind::Load(error),
            mode,
        }
    }

    const fn machine(mode: ExecutionMode, error: MachineError) -> Self {
        Self {
            kind: ExecutionErrorKind::Machine(error),
            mode,
        }
    }

    /// Returns the execution mode attached to this diagnostic.
    #[must_use]
    pub const fn mode(self) -> ExecutionMode {
        self.mode
    }

    const fn profile(
        mode: ExecutionMode,
        error: ProfileRequirementError,
    ) -> Self {
        Self {
            kind: ExecutionErrorKind::Profile(error),
            mode,
        }
    }
}

impl Display for ExecutionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "{} execution: ", self.mode)?;
        match self.kind {
            ExecutionErrorKind::Load(error) => Display::fmt(&error, f),
            ExecutionErrorKind::Machine(error) => Display::fmt(&error, f),
            ExecutionErrorKind::Profile(error) => Display::fmt(&error, f),
        }
    }
}

/// Stable execution-failure category.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionErrorKind {
    /// Source admission failed before execution began.
    Load(LoadError),
    /// A machine transition failed after construction.
    Machine(MachineError),
    /// Target profile or runtime capability preflight failed before loading.
    Profile(ProfileRequirementError),
}

/// Owned machine with one explicit, immutable execution-mode identity.
#[derive(Clone, Debug)]
pub struct ExecutionMachine {
    machine: Machine,
    mode: ExecutionMode,
    profile: &'static ProfileDescriptor,
}

impl ExecutionMachine {
    /// Canonicalizes annotated source before explicit execution-mode selection.
    ///
    /// Raw [`Self::from_source`] remains canonical-only and never interprets
    /// hash comments.
    ///
    /// # Errors
    ///
    /// Returns [`AnnotatedLoadError`] for annotated presentation failure or the
    /// same [`ExecutionError`] produced by canonical construction.
    pub fn from_annotated_source(
        source: &[u8],
        input: Vec<u8>,
        mode: ExecutionMode,
    ) -> Result<Self, AnnotatedLoadError<ExecutionError>> {
        let canonical = canonicalize_annotated_source(source)
            .map_err(AnnotatedLoadError::Annotated)?;
        Self::from_source(canonical.bytes(), input, mode)
            .map_err(AnnotatedLoadError::Load)
    }

    /// Canonicalizes annotated source before explicit profile/mode preflight.
    ///
    /// # Errors
    ///
    /// Returns [`AnnotatedLoadError`] for annotated presentation failure or the
    /// same [`ExecutionError`] produced by canonical profile construction.
    pub fn from_annotated_source_for_profile(
        source: &[u8],
        input: Vec<u8>,
        mode: ExecutionMode,
        profile: &'static ProfileDescriptor,
    ) -> Result<Self, AnnotatedLoadError<ExecutionError>> {
        let canonical = canonicalize_annotated_source(source)
            .map_err(AnnotatedLoadError::Annotated)?;
        Self::from_source_for_profile(canonical.bytes(), input, mode, profile)
            .map_err(AnnotatedLoadError::Load)
    }

    /// Restores one complete classic checkpoint under explicit mode/profile.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionError`] when the mode is disabled or `profile` is not
    /// executable by the classic safe-Rust runtime.
    pub fn from_snapshot(
        state: MachineState,
        mode: ExecutionMode,
        profile: &'static ProfileDescriptor,
    ) -> Result<Self, ExecutionError> {
        preflight_profile(
            profile,
            u64::from(profile.memory_words()),
            safe_rust_classic_capability(),
        )
        .map_err(|error| ExecutionError::profile(mode, error))?;
        Ok(Self {
            machine: Machine::from_snapshot(state),
            mode,
            profile,
        })
    }

    /// Loads source and constructs an explicitly selected execution mode.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionError`] when the mode is disabled or loading fails.
    pub fn from_source(
        source: &[u8],
        input: Vec<u8>,
        mode: ExecutionMode,
    ) -> Result<Self, ExecutionError> {
        Self::from_source_for_profile(source, input, mode, historical_profile())
    }

    /// Loads source after an explicit canonical target-profile preflight.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionError`] when the mode is disabled, the safe Rust VM
    /// cannot implement `profile`, or source loading fails after preflight.
    pub fn from_source_for_profile(
        source: &[u8],
        input: Vec<u8>,
        mode: ExecutionMode,
        profile: &'static ProfileDescriptor,
    ) -> Result<Self, ExecutionError> {
        preflight_profile(
            profile,
            source_word_requirement(source),
            safe_rust_classic_capability(),
        )
        .map_err(|error| ExecutionError::profile(mode, error))?;
        let machine = Machine::from_source(source, input)
            .map_err(|error| ExecutionError::load(mode, error))?;
        Ok(Self { machine, mode, profile })
    }

    /// Constructs an execution facade from validated state.
    #[must_use]
    pub const fn from_state(
        memory: Memory,
        input: Vec<u8>,
        registers: Registers,
        mode: ExecutionMode,
    ) -> Self {
        Self {
            machine: Machine::with_registers(memory, input, registers),
            mode,
            profile: historical_profile(),
        }
    }

    /// Returns the immutable full input stream carried by this machine.
    #[must_use]
    pub fn input(&self) -> &[u8] {
        self.machine.input()
    }

    /// Returns the number of input bytes consumed by committed transitions.
    #[must_use]
    pub const fn input_consumed(&self) -> usize {
        self.machine.input_consumed()
    }

    /// Returns the complete immutable classic memory image.
    #[must_use]
    pub const fn memory(&self) -> &Memory {
        self.machine.memory()
    }

    /// Reads one current guest memory word.
    ///
    /// # Errors
    ///
    /// Returns [`MemoryError`] if the fixed memory invariant is broken.
    pub fn memory_word(&self, address: Word) -> Result<Word, MemoryError> {
        self.machine.memory_word(address)
    }

    /// Returns the explicit execution-mode identity.
    #[must_use]
    pub const fn mode(&self) -> ExecutionMode {
        self.mode
    }

    /// Returns all bytes emitted by committed output instructions.
    #[must_use]
    pub fn output(&self) -> &[u8] {
        self.machine.output()
    }

    /// Returns the exact canonical target profile for this machine.
    #[must_use]
    pub const fn profile(&self) -> &'static ProfileDescriptor {
        self.profile
    }

    /// Returns the current register values.
    #[must_use]
    pub const fn registers(&self) -> Registers {
        self.machine.registers()
    }

    /// Executes at most `step_budget` semantic steps in the selected mode.
    ///
    /// # Errors
    ///
    /// Returns a mode-tagged [`ExecutionError`] on rejected transitions.
    pub fn run(
        &mut self,
        step_budget: usize,
    ) -> Result<RunOutcome, ExecutionError> {
        self.machine
            .run_in_mode(step_budget, self.mode)
            .map_err(|error| ExecutionError::machine(self.mode, error))
    }

    /// Executes at most `step_budget` steps with mode-tagged trace evidence.
    ///
    /// # Errors
    ///
    /// Returns a mode-tagged [`ExecutionError`] on rejected transitions.
    pub fn run_traced<Observer>(
        &mut self,
        step_budget: usize,
        observer: &mut Observer,
    ) -> Result<RunOutcome, ExecutionError>
    where
        Observer: FnMut(&StepTrace),
    {
        self.machine
            .run_traced_in_mode(step_budget, self.mode, observer)
            .map_err(|error| ExecutionError::machine(self.mode, error))
    }

    /// Clones the complete classic machine state into a checkpoint.
    #[must_use]
    pub fn snapshot_state(&self) -> MachineState {
        self.machine.snapshot_state()
    }

    /// Executes one transition in the selected mode.
    ///
    /// # Errors
    ///
    /// Returns a mode-tagged [`ExecutionError`] when the transition is
    /// rejected.
    pub fn step(&mut self) -> Result<StepOutcome, ExecutionError> {
        self.machine
            .step_in_mode(self.mode)
            .map_err(|error| ExecutionError::machine(self.mode, error))
    }

    /// Executes one transition and emits mode-tagged trace evidence.
    ///
    /// # Errors
    ///
    /// Returns a mode-tagged [`ExecutionError`] when the transition is
    /// rejected.
    pub fn step_traced<Observer>(
        &mut self,
        observer: &mut Observer,
    ) -> Result<StepOutcome, ExecutionError>
    where
        Observer: FnMut(&StepTrace),
    {
        self.machine
            .step_traced_in_mode(self.mode, observer)
            .map_err(|error| ExecutionError::machine(self.mode, error))
    }

    /// Returns the current stable termination reason, if any.
    #[must_use]
    pub const fn termination(&self) -> Option<Termination> {
        self.machine.termination()
    }

    /// Returns whether results may satisfy normal verifier obligations.
    #[must_use]
    pub const fn verifier_eligible(&self) -> bool {
        self.mode.is_verifier_eligible()
    }
}
