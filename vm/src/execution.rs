// File:
//   - execution.rs
// Path:
//   - vm/src/execution.rs
//
// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Path-Rule:
//   - All paths in this header are repository-root relative.
//
// Boundary-Contract:
// - Owns:
//   - Explicit mode selection around the normative safe-Rust machine state.
// - Must-Not:
//   - Make `legacy-ben` implicit or let legacy results satisfy verification.
// - Allows:
//   - Inputs: validated classic source/state, byte input, and explicit mode.
//   - Outputs: mode-tagged execution results, traces, and diagnostics.
//   - Side effects: mutation only of the owned in-memory machine state.
// - Split-When:
//   - Split when a compatibility implementation gains a separate lifecycle.
// - Merge-When:
//   - Merge when mode selection no longer needs an explicit trust boundary.
// - Summary:
//   - Opt-in execution facade separating normative and legacy behavior.
// - Description:
//   - Keeps `Machine` normative while routing explicit compatibility execution.
// - Usage:
//   - Use only when callers must select an execution mode deliberately.
// - Defaults:
//   - Legacy execution is unavailable unless the `legacy-ben` feature is built.
//
// Related documents:
// - docs/technical/runtime/vm/specification-and-legacy-interpreter-modes.md
// - docs/technical/adr/verification-trust-boundary.md
//
// Large file:
//   - false
//

//! Explicit execution facade for normative and historical-compatibility modes.

use std::fmt::{Display, Formatter, Result as FormatResult};

use crate::{
    AnnotatedLoadError, ExecutionMode, LoadError, Machine, MachineError,
    Memory, MemoryError, ProfileDescriptor, ProfileRequirementError, Registers,
    RunOutcome, StepOutcome, StepTrace, Termination, Word,
    canonicalize_annotated_source, historical_profile, preflight_profile,
    safe_rust_classic_capability,
};

/// Mode-tagged failure from construction or execution.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ExecutionError {
    kind: ExecutionErrorKind,
    mode: ExecutionMode,
}

impl ExecutionError {
    const fn disabled(mode: ExecutionMode) -> Self {
        Self {
            kind: ExecutionErrorKind::LegacyBenDisabled,
            mode,
        }
    }

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
            ExecutionErrorKind::LegacyBenDisabled => {
                f.write_str("legacy-ben support is disabled in this build")
            },
            ExecutionErrorKind::Load(error) => Display::fmt(&error, f),
            ExecutionErrorKind::Machine(error) => Display::fmt(&error, f),
            ExecutionErrorKind::Profile(error) => Display::fmt(&error, f),
        }
    }
}

/// Stable execution-failure category.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionErrorKind {
    /// Legacy compatibility was explicitly requested in a build without it.
    LegacyBenDisabled,
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
    fn check_mode(mode: ExecutionMode) -> Result<(), ExecutionError> {
        if mode == ExecutionMode::LegacyBen && !cfg!(feature = "legacy-ben") {
            Err(ExecutionError::disabled(mode))
        } else {
            Ok(())
        }
    }

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
        Self::check_mode(mode)?;
        preflight_profile(
            profile,
            profile.memory_words(),
            safe_rust_classic_capability(),
        )
        .map_err(|error| ExecutionError::profile(mode, error))?;
        let machine = Machine::from_source(source, input)
            .map_err(|error| ExecutionError::load(mode, error))?;
        Ok(Self { machine, mode, profile })
    }

    /// Constructs an execution facade from validated state.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionError`] when the requested mode is disabled.
    pub fn from_state(
        memory: Memory,
        input: Vec<u8>,
        registers: Registers,
        mode: ExecutionMode,
    ) -> Result<Self, ExecutionError> {
        Self::check_mode(mode)?;
        Ok(Self {
            machine: Machine::with_registers(memory, input, registers),
            mode,
            profile: historical_profile(),
        })
    }

    /// Returns the number of input bytes consumed by committed transitions.
    #[must_use]
    pub const fn input_consumed(&self) -> usize {
        self.machine.input_consumed()
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
