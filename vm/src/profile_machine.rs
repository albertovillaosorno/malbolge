// File:
//   - profile_machine.rs
// Path:
//   - vm/src/profile_machine.rs
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
//   - Safe Rust execution for canonical schema-v2 ternary target profiles.
// - Must-Not:
//   - Reinterpret classic `Word`, emulate Ben defects, or borrow host width.
// - Allows:
//   - Inputs: canonical profile descriptor, validated source bytes, byte input.
//   - Outputs: deterministic profile-width state, I/O, termination,
//   - diagnostics.
//   - Side effects: caller-owned allocation and in-memory guest state only.
// - Split-When:
//   - Split when a later profile schema requires a different memory model.
// - Merge-When:
//   - Merge when the classic machine becomes a zero-cost specialization of this
//   - profile-driven transition engine without weakening classic type safety.
// - Summary:
//   - Executes N-trit single-word-modular Malbolge profiles in safe Rust.
// - Description:
//   - Generalizes word/address width while preserving normative sequential
//   - decode, crazy, rotate, self-modification, encryption, and byte I/O.
// - Usage:
//   - Use for canonical current/versioned profiles after explicit selection.
// - Defaults:
//   - Supports profiles within the explicit `safe-rust-profiled` capability.
//
// Related documents:
// - docs/technical/compatibility/scalable-malbolge-memory-model.md
// - docs/technical/compatibility/required-profile-diagnostics.md
// - docs/technical/specification/malbolge-1998.md
//
// Large file:
//   - false
//

//! Profile-driven safe Rust execution for scalable ternary Malbolge machines.

use std::fmt::{Display, Formatter, Result as FormatResult};

use crate::{
    AnnotatedLoadError, CRAZY_CHUNK_TRITS, DECODE_TABLE, DECODE_TABLE_LEN,
    ProfileDescriptor, ProfileMachineObservation, ProfileMemoryDelta,
    ProfileMemoryRead, ProfileMemoryReads, ProfileMemoryWrite,
    ProfileRequirementError, ProfileStepTrace, RunOutcome, StepOutcome,
    Termination, TraceInput, XLAT2, canonicalize_annotated_source,
    crazy_chunk_lookup, preflight_profile, safe_rust_profiled_capability,
};

const GRAPHICAL_MAX: u32 = 126;
const GRAPHICAL_MIN: u32 = 33;
const OUTPUT_MODULUS: u32 = 256;
const TERNARY_RADIX: u32 = 3;

/// Registers for one profile-driven Malbolge machine.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct ProfileRegisters {
    /// Accumulator register `A` in the selected profile word domain.
    pub accumulator: u32,
    /// Code pointer register `C` in the selected profile address domain.
    pub code_pointer: u32,
    /// Data pointer register `D` in the selected profile address domain.
    pub data_pointer: u32,
}

/// Complete validated I/O portion of one profile-machine checkpoint.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ProfileMachineIoState {
    input: Vec<u8>,
    input_cursor: usize,
    output: Vec<u8>,
    termination: Option<Termination>,
}

impl ProfileMachineIoState {
    /// Returns the immutable full input stream carried by this checkpoint.
    #[must_use]
    pub fn input(&self) -> &[u8] {
        &self.input
    }

    /// Returns the number of input bytes already consumed at the checkpoint.
    #[must_use]
    pub const fn input_consumed(&self) -> usize {
        self.input_cursor
    }

    /// Constructs one validated I/O checkpoint.
    ///
    /// # Errors
    ///
    /// Returns [`ProfileMachineError::InputCursorOutOfRange`] when the cursor
    /// is beyond the supplied input stream.
    pub fn new(
        input: Vec<u8>,
        input_cursor: usize,
        output: Vec<u8>,
        termination: Option<Termination>,
    ) -> Result<Self, ProfileMachineError> {
        validate_input_cursor(input.len(), input_cursor)?;
        Ok(Self {
            input,
            input_cursor,
            output,
            termination,
        })
    }

    /// Returns bytes already committed to guest output at the checkpoint.
    #[must_use]
    pub fn output(&self) -> &[u8] {
        &self.output
    }

    /// Returns the stable termination reason recorded by the checkpoint.
    #[must_use]
    pub const fn termination(&self) -> Option<Termination> {
        self.termination
    }
}

/// Complete validated checkpoint of one profile-driven machine.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ProfileMachineState {
    io: ProfileMachineIoState,
    memory: Vec<u32>,
    profile: &'static ProfileDescriptor,
    registers: ProfileRegisters,
}

impl ProfileMachineState {
    /// Returns the validated I/O checkpoint carried by this complete state.
    #[must_use]
    pub const fn io(&self) -> &ProfileMachineIoState {
        &self.io
    }

    /// Returns the exact profile-width memory image carried by the checkpoint.
    #[must_use]
    pub fn memory(&self) -> &[u32] {
        &self.memory
    }

    /// Constructs one complete validated profile-machine checkpoint.
    ///
    /// # Errors
    ///
    /// Returns [`ProfileMachineError`] when the profile exceeds runtime
    /// capability or memory shape/words or registers are invalid.
    pub fn new(
        profile: &'static ProfileDescriptor,
        memory: Vec<u32>,
        registers: ProfileRegisters,
        io: ProfileMachineIoState,
    ) -> Result<Self, ProfileMachineError> {
        preflight_profile(
            profile,
            profile.memory_words(),
            safe_rust_profiled_capability(),
        )?;
        validate_state_memory(profile, &memory)?;
        validate_state_registers(profile, registers)?;
        Ok(Self {
            io,
            memory,
            profile,
            registers,
        })
    }

    /// Returns the exact canonical profile bound to this checkpoint.
    #[must_use]
    pub const fn profile(&self) -> &'static ProfileDescriptor {
        self.profile
    }

    /// Returns the profile-width register values at the checkpoint.
    #[must_use]
    pub const fn registers(&self) -> ProfileRegisters {
        self.registers
    }
}

/// Deterministic source-admission failure for a profile-driven machine.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ProfileLoadError {
    /// The source lacks the two words required by the fill recurrence.
    InsufficientRecurrenceBase,
    /// A graphical byte decodes to an instruction forbidden at load time.
    InvalidInstruction {
        /// Loaded word position after whitespace removal.
        position: u32,
        /// Original graphical source byte.
        byte: u8,
    },
    /// A non-whitespace source byte is outside graphical ASCII.
    InvalidSourceByte {
        /// Byte offset in the original source stream.
        offset: usize,
        /// Rejected raw byte value.
        byte: u8,
    },
    /// The exact profile memory image could not be reserved.
    MemoryAllocation,
    /// More non-whitespace words were supplied than profile memory can hold.
    SourceTooLong,
}

/// Stable identity of one profile-width machine register.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ProfileRegisterName {
    /// Accumulator register `A`.
    Accumulator,
    /// Code pointer register `C`.
    CodePointer,
    /// Data pointer register `D`.
    DataPointer,
}

impl ProfileRegisterName {
    const fn stable_id(self) -> &'static str {
        match self {
            Self::Accumulator => "A",
            Self::CodePointer => "C",
            Self::DataPointer => "D",
        }
    }
}

/// Typed failure of profile-driven construction or one machine transition.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ProfileMachineError {
    /// A public address is outside the selected profile domain.
    AddressOutOfRange {
        /// Rejected raw address.
        address: u32,
    },
    /// Supplied checkpoint cursor is beyond its input stream.
    InputCursorOutOfRange {
        /// Exact supplied input length.
        input_len: usize,
        /// Rejected cursor value.
        observed: usize,
    },
    /// Self-encryption would access a non-graphical target cell.
    InvalidEncryptionTarget {
        /// Resulting profile-width code pointer selected for encryption.
        pointer: u32,
        /// Cell value observed after instruction-specific effects.
        value: u32,
    },
    /// Source loading failed before machine construction.
    Load(ProfileLoadError),
    /// Supplied state memory length differs from the selected profile image.
    MemoryImageLength {
        /// Exact profile memory length.
        expected: u32,
        /// Supplied host-vector length.
        observed: usize,
    },
    /// Exact memory-domain indexing unexpectedly failed internally.
    MemoryInvariant,
    /// A supplied state memory word is outside the selected word domain.
    MemoryWordOutOfRange {
        /// Exact profile-width memory address.
        address: u32,
        /// Rejected raw word value.
        value: u32,
    },
    /// The selected profile exceeds this runtime's explicit capability.
    Profile(ProfileRequirementError),
    /// A supplied register is outside the selected word/address domain.
    RegisterOutOfRange {
        /// Rejected register identity.
        register: ProfileRegisterName,
        /// Rejected raw register value.
        value: u32,
    },
    /// A translation-table lookup failed inside its admitted domain.
    TranslationTableInvariant,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ProfileInstruction {
    Crazy,
    Halt,
    Input,
    JumpCode,
    JumpData,
    NoOperation,
    Output,
    Rotate,
}

#[derive(Clone, Copy, Debug)]
struct ProfileTransitionPlan {
    input_advance: bool,
    memory_write: Option<(u32, u32)>,
    output: Option<u8>,
    registers: ProfileRegisters,
}

#[derive(Clone, Copy, Debug)]
struct ProfileStepExecution {
    memory_delta: ProfileMemoryDelta,
    memory_reads: ProfileMemoryReads,
    result: Result<StepOutcome, ProfileMachineError>,
}

impl ProfileStepExecution {
    const fn continued(
        memory_delta: ProfileMemoryDelta,
        memory_reads: ProfileMemoryReads,
    ) -> Self {
        Self {
            memory_delta,
            memory_reads,
            result: Ok(StepOutcome::Continued),
        }
    }

    fn error(
        memory_reads: ProfileMemoryReads,
        error: ProfileMachineError,
    ) -> Self {
        Self {
            memory_delta: ProfileMemoryDelta::default(),
            memory_reads,
            result: Err(error),
        }
    }

    fn outcome(memory_reads: ProfileMemoryReads, outcome: StepOutcome) -> Self {
        Self {
            memory_delta: ProfileMemoryDelta::default(),
            memory_reads,
            result: Ok(outcome),
        }
    }
}

/// Owned safe Rust machine for one explicitly selected canonical profile.
#[derive(Clone, Debug)]
pub struct ProfileMachine {
    input: Vec<u8>,
    input_cursor: usize,
    memory: Vec<u32>,
    output: Vec<u8>,
    profile: &'static ProfileDescriptor,
    registers: ProfileRegisters,
    termination: Option<Termination>,
}

impl Display for ProfileLoadError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::InsufficientRecurrenceBase => f.write_str(
                "profile source requires at least two non-whitespace words",
            ),
            Self::InvalidInstruction { position, byte } => write!(
                f,
                "source byte {byte} at loaded position {position} is invalid"
            ),
            Self::InvalidSourceByte { offset, byte } => write!(
                f,
                "source byte {byte} at offset {offset} is not graphical ASCII"
            ),
            Self::MemoryAllocation => {
                f.write_str("profile memory allocation failed")
            },
            Self::SourceTooLong => {
                f.write_str("source exceeds selected profile memory image")
            },
        }
    }
}

impl Display for ProfileMachineError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::AddressOutOfRange { address } => {
                write!(f, "profile address {address} is outside memory")
            },
            Self::InputCursorOutOfRange { input_len, observed } => write!(
                f,
                "profile input cursor {observed} exceeds length {input_len}"
            ),
            Self::InvalidEncryptionTarget { pointer, value } => {
                write!(f, "self-encryption target {pointer} contains ")?;
                write!(f, "non-graphical value {value}")
            },
            Self::Load(error) => Display::fmt(error, f),
            Self::MemoryImageLength { expected, observed } => write!(
                f,
                "profile state memory length {observed} differs from {expected}"
            ),
            Self::MemoryInvariant => {
                f.write_str("profile memory invariant failed")
            },
            Self::MemoryWordOutOfRange { address, value } => write!(
                f,
                "profile state memory[{address}]={value} is outside word domain"
            ),
            Self::Profile(error) => Display::fmt(error, f),
            Self::RegisterOutOfRange { register, value } => write!(
                f,
                "profile state register {}={value} is outside word domain",
                register.stable_id()
            ),
            Self::TranslationTableInvariant => {
                f.write_str("profile translation-table invariant failed")
            },
        }
    }
}

impl From<ProfileLoadError> for ProfileMachineError {
    fn from(error: ProfileLoadError) -> Self {
        Self::Load(error)
    }
}

impl From<ProfileRequirementError> for ProfileMachineError {
    fn from(error: ProfileRequirementError) -> Self {
        Self::Profile(error)
    }
}

impl ProfileMachine {
    fn commit(
        &mut self,
        plan: ProfileTransitionPlan,
        encrypted: u32,
    ) -> Result<(), ProfileMachineError> {
        let encryption_pointer = plan.registers.code_pointer;
        if let Some((write_pointer, value)) = plan.memory_write
            && write_pointer != encryption_pointer
        {
            self.write(write_pointer, value)?;
        }
        self.write(encryption_pointer, encrypted)?;
        self.registers = ProfileRegisters {
            accumulator: plan.registers.accumulator,
            code_pointer: successor(
                plan.registers.code_pointer,
                self.profile.word_modulus(),
            ),
            data_pointer: successor(
                plan.registers.data_pointer,
                self.profile.word_modulus(),
            ),
        };
        if plan.input_advance {
            self.input_cursor = self.input_cursor.saturating_add(1);
        }
        if let Some(byte) = plan.output {
            self.output.push(byte);
        }
        Ok(())
    }

    /// Canonicalizes annotated source for one explicit target profile.
    ///
    /// Raw [`Self::from_source`] remains canonical-only and never interprets
    /// hash comments.
    ///
    /// # Errors
    ///
    /// Returns [`AnnotatedLoadError<ProfileMachineError>`] when annotated
    /// presentation, profile capability, or canonical loading fails.
    pub fn from_annotated_source(
        profile: &'static ProfileDescriptor,
        source: &[u8],
        input: Vec<u8>,
    ) -> Result<Self, AnnotatedLoadError<ProfileMachineError>> {
        let canonical = canonicalize_annotated_source(source)
            .map_err(AnnotatedLoadError::Annotated)?;
        Self::from_source(profile, canonical.bytes(), input)
            .map_err(AnnotatedLoadError::Load)
    }

    /// Restores a machine from one already validated complete checkpoint.
    #[must_use]
    pub fn from_snapshot(state: ProfileMachineState) -> Self {
        Self {
            input: state.io.input,
            input_cursor: state.io.input_cursor,
            memory: state.memory,
            output: state.io.output,
            profile: state.profile,
            registers: state.registers,
            termination: state.io.termination,
        }
    }

    /// Loads source and constructs a machine for one canonical target profile.
    ///
    /// # Errors
    ///
    /// Returns [`ProfileMachineError`] when the profile exceeds runtime
    /// capability or source cannot initialize the exact profile memory image.
    pub fn from_source(
        profile: &'static ProfileDescriptor,
        source: &[u8],
        input: Vec<u8>,
    ) -> Result<Self, ProfileMachineError> {
        preflight_profile(
            profile,
            profile.memory_words(),
            safe_rust_profiled_capability(),
        )?;
        let memory = load_profile(profile, source)?;
        Ok(Self {
            input,
            input_cursor: 0,
            memory,
            output: Vec::new(),
            profile,
            registers: ProfileRegisters::default(),
            termination: None,
        })
    }

    /// Constructs a machine from one complete validated profile-width state.
    ///
    /// This verification/deoptimization boundary accepts only an exact memory
    /// image and in-domain register values. It never truncates or wraps
    /// supplied host values during construction.
    ///
    /// # Errors
    ///
    /// Returns [`ProfileMachineError`] when the profile exceeds runtime
    /// capability, memory length/words are invalid, or any register is outside
    /// the selected profile domain.
    pub fn from_state(
        profile: &'static ProfileDescriptor,
        memory: Vec<u32>,
        input: Vec<u8>,
        registers: ProfileRegisters,
    ) -> Result<Self, ProfileMachineError> {
        let io = ProfileMachineIoState::new(input, 0, Vec::new(), None)?;
        let state = ProfileMachineState::new(profile, memory, registers, io)?;
        Ok(Self::from_snapshot(state))
    }

    /// Returns the immutable full input stream carried by this machine.
    #[must_use]
    pub fn input(&self) -> &[u8] {
        &self.input
    }

    /// Returns the number of input bytes consumed by committed transitions.
    #[must_use]
    pub const fn input_consumed(&self) -> usize {
        self.input_cursor
    }

    /// Returns the complete immutable profile-width memory image.
    #[must_use]
    pub fn memory(&self) -> &[u32] {
        &self.memory
    }

    fn memory_delta(
        &self,
        plan: &ProfileTransitionPlan,
        encrypted: u32,
    ) -> Result<ProfileMemoryDelta, ProfileMachineError> {
        let encryption_pointer = plan.registers.code_pointer;
        let data = if let Some((write_pointer, value)) = plan.memory_write
            && write_pointer != encryption_pointer
        {
            let before = self.read(write_pointer)?;
            (before != value).then_some(ProfileMemoryWrite {
                address: write_pointer,
                after: value,
                before,
            })
        } else {
            None
        };
        let encryption_before = self.read(encryption_pointer)?;
        let encryption =
            (encryption_before != encrypted).then_some(ProfileMemoryWrite {
                address: encryption_pointer,
                after: encrypted,
                before: encryption_before,
            });
        Ok(ProfileMemoryDelta { data, encryption })
    }

    /// Reads one guest memory word by exact profile-width address.
    ///
    /// # Errors
    ///
    /// Returns [`ProfileMachineError::AddressOutOfRange`] outside the selected
    /// profile domain, or an invariant error if exact memory indexing fails.
    pub fn memory_word(
        &self,
        address: u32,
    ) -> Result<u32, ProfileMachineError> {
        if address >= self.profile.memory_words() {
            return Err(ProfileMachineError::AddressOutOfRange { address });
        }
        self.read(address)
    }

    const fn observation(&self) -> ProfileMachineObservation {
        ProfileMachineObservation {
            input_consumed: self.input_cursor,
            output_len: self.output.len(),
            registers: self.registers,
            termination: self.termination,
        }
    }

    /// Returns all bytes emitted by committed output instructions.
    #[must_use]
    pub fn output(&self) -> &[u8] {
        &self.output
    }

    fn plan(
        &self,
        decoded: ProfileInstruction,
        memory_reads: &mut ProfileMemoryReads,
    ) -> Result<ProfileTransitionPlan, ProfileMachineError> {
        let mut plan = ProfileTransitionPlan {
            input_advance: false,
            memory_write: None,
            output: None,
            registers: self.registers,
        };
        match decoded {
            ProfileInstruction::Crazy => {
                self.plan_crazy(&mut plan, memory_reads)?;
            },
            ProfileInstruction::Halt | ProfileInstruction::NoOperation => {},
            ProfileInstruction::Input => self.plan_input(&mut plan),
            ProfileInstruction::JumpCode => {
                plan.registers.code_pointer =
                    self.semantic_data_read(memory_reads)?;
            },
            ProfileInstruction::JumpData => {
                plan.registers.data_pointer =
                    self.semantic_data_read(memory_reads)?;
            },
            ProfileInstruction::Output => {
                plan.output = Some(low_byte(self.registers.accumulator));
            },
            ProfileInstruction::Rotate => {
                self.plan_rotate(&mut plan, memory_reads)?;
            },
        }
        Ok(plan)
    }

    fn plan_crazy(
        &self,
        plan: &mut ProfileTransitionPlan,
        memory_reads: &mut ProfileMemoryReads,
    ) -> Result<(), ProfileMachineError> {
        let data = self.semantic_data_read(memory_reads)?;
        let value = profile_crazy(
            data,
            self.registers.accumulator,
            self.profile.word_trits(),
        );
        plan.registers.accumulator = value;
        plan.memory_write = Some((self.registers.data_pointer, value));
        Ok(())
    }

    fn plan_input(&self, plan: &mut ProfileTransitionPlan) {
        if let Some(byte) = self.input.get(self.input_cursor).copied() {
            plan.registers.accumulator = u32::from(byte);
            plan.input_advance = true;
        } else {
            plan.registers.accumulator = self.profile.eof_word();
        }
    }

    fn plan_rotate(
        &self,
        plan: &mut ProfileTransitionPlan,
        memory_reads: &mut ProfileMemoryReads,
    ) -> Result<(), ProfileMachineError> {
        let data = self.semantic_data_read(memory_reads)?;
        let value = profile_rotate(data, self.profile.word_modulus());
        plan.registers.accumulator = value;
        plan.memory_write = Some((self.registers.data_pointer, value));
        Ok(())
    }

    /// Returns the exact canonical profile selected for this machine.
    #[must_use]
    pub const fn profile(&self) -> &'static ProfileDescriptor {
        self.profile
    }

    fn read(&self, address: u32) -> Result<u32, ProfileMachineError> {
        let index = usize::try_from(address)
            .ok()
            .ok_or(ProfileMachineError::MemoryInvariant)?;
        self.memory
            .get(index)
            .copied()
            .ok_or(ProfileMachineError::MemoryInvariant)
    }

    /// Returns the current profile-width register values.
    #[must_use]
    pub const fn registers(&self) -> ProfileRegisters {
        self.registers
    }

    /// Executes at most `step_budget` normative profile-driven steps.
    ///
    /// # Errors
    ///
    /// Returns [`ProfileMachineError`] when any transition cannot commit.
    pub fn run(
        &mut self,
        step_budget: usize,
    ) -> Result<RunOutcome, ProfileMachineError> {
        if let Some(reason) = self.termination {
            return Ok(RunOutcome::Terminated { reason, steps: 0 });
        }
        let mut steps = 0usize;
        while steps < step_budget {
            let outcome = self.step()?;
            steps = steps.saturating_add(1);
            if let StepOutcome::Terminated(reason) = outcome {
                return Ok(RunOutcome::Terminated { reason, steps });
            }
        }
        Ok(RunOutcome::BudgetExhausted { steps })
    }

    /// Executes at most `step_budget` profile-driven steps with observation.
    ///
    /// The observer receives exactly one immutable [`ProfileStepTrace`] for
    /// each requested step. Observation cannot mutate machine state or
    /// profile choice.
    ///
    /// # Errors
    ///
    /// Returns [`ProfileMachineError`] when any transition cannot commit. A
    /// failing requested step is delivered to `observer` before the error
    /// returns.
    pub fn run_traced<Observer>(
        &mut self,
        step_budget: usize,
        observer: &mut Observer,
    ) -> Result<RunOutcome, ProfileMachineError>
    where
        Observer: FnMut(&ProfileStepTrace),
    {
        if let Some(reason) = self.termination {
            return Ok(RunOutcome::Terminated { reason, steps: 0 });
        }
        let mut steps = 0usize;
        while steps < step_budget {
            let outcome = self.step_traced(observer)?;
            steps = steps.saturating_add(1);
            if let StepOutcome::Terminated(reason) = outcome {
                return Ok(RunOutcome::Terminated { reason, steps });
            }
        }
        Ok(RunOutcome::BudgetExhausted { steps })
    }

    fn semantic_data_read(
        &self,
        memory_reads: &mut ProfileMemoryReads,
    ) -> Result<u32, ProfileMachineError> {
        let address = self.registers.data_pointer;
        let value = self.read(address)?;
        memory_reads.data = Some(ProfileMemoryRead { address, value });
        Ok(value)
    }

    /// Clones the complete machine state into a validated checkpoint value.
    ///
    /// The memory image is copied deliberately so the checkpoint owns an exact
    /// restoration point independent from later interpreter mutation.
    #[must_use]
    pub fn snapshot_state(&self) -> ProfileMachineState {
        ProfileMachineState {
            io: ProfileMachineIoState {
                input: self.input.clone(),
                input_cursor: self.input_cursor,
                output: self.output.clone(),
                termination: self.termination,
            },
            memory: self.memory.clone(),
            profile: self.profile,
            registers: self.registers,
        }
    }

    /// Executes one atomic normative profile-driven transition.
    ///
    /// # Errors
    ///
    /// Returns [`ProfileMachineError`] when a transition cannot commit exactly.
    pub fn step(&mut self) -> Result<StepOutcome, ProfileMachineError> {
        self.step_execution().result
    }

    fn step_after_decode(
        &mut self,
        decoded: ProfileInstruction,
        mut memory_reads: ProfileMemoryReads,
    ) -> ProfileStepExecution {
        if decoded == ProfileInstruction::Halt {
            self.termination = Some(Termination::HaltInstruction);
            return ProfileStepExecution::outcome(
                memory_reads,
                StepOutcome::Terminated(Termination::HaltInstruction),
            );
        }
        let plan = match self.plan(decoded, &mut memory_reads) {
            Ok(value) => value,
            Err(error) => {
                return ProfileStepExecution::error(memory_reads, error);
            },
        };
        let encrypted = match self.validate_encryption(&plan, &mut memory_reads)
        {
            Ok(value) => value,
            Err(error) => {
                return ProfileStepExecution::error(memory_reads, error);
            },
        };
        let memory_delta = match self.memory_delta(&plan, encrypted) {
            Ok(value) => value,
            Err(error) => {
                return ProfileStepExecution::error(memory_reads, error);
            },
        };
        if let Err(error) = self.commit(plan, encrypted) {
            return ProfileStepExecution::error(memory_reads, error);
        }
        ProfileStepExecution::continued(memory_delta, memory_reads)
    }

    fn step_after_fetch(
        &mut self,
        cell: u32,
        memory_reads: ProfileMemoryReads,
    ) -> ProfileStepExecution {
        if !profile_cell_is_graphical(cell) {
            self.termination = Some(Termination::NonGraphicalCell);
            return ProfileStepExecution::outcome(
                memory_reads,
                StepOutcome::Terminated(Termination::NonGraphicalCell),
            );
        }
        let Some(decoded) =
            decode_profile_instruction(cell, self.registers.code_pointer)
        else {
            return ProfileStepExecution::error(
                memory_reads,
                ProfileMachineError::TranslationTableInvariant,
            );
        };
        self.step_after_decode(profile_instruction(decoded), memory_reads)
    }

    fn step_execution(&mut self) -> ProfileStepExecution {
        let mut memory_reads = ProfileMemoryReads::default();
        if let Some(reason) = self.termination {
            return ProfileStepExecution::outcome(
                memory_reads,
                StepOutcome::Terminated(reason),
            );
        }
        let address = self.registers.code_pointer;
        let cell = match self.read(address) {
            Ok(value) => value,
            Err(error) => {
                return ProfileStepExecution::error(memory_reads, error);
            },
        };
        memory_reads.fetch = Some(ProfileMemoryRead { address, value: cell });
        self.step_after_fetch(cell, memory_reads)
    }

    /// Executes one atomic profile-driven transition and emits trace evidence.
    ///
    /// The observer is called exactly once for this requested step, including
    /// stable termination and rejected transitions.
    ///
    /// # Errors
    ///
    /// Returns [`ProfileMachineError`] when the transition cannot commit. The
    /// exact rejection is included in the emitted [`ProfileStepTrace`].
    pub fn step_traced<Observer>(
        &mut self,
        observer: &mut Observer,
    ) -> Result<StepOutcome, ProfileMachineError>
    where
        Observer: FnMut(&ProfileStepTrace),
    {
        let before = self.observation();
        let execution = self.step_execution();
        let fetched_cell = execution.memory_reads.fetch.map(|read| read.value);
        let decoded = fetched_cell
            .filter(|cell| profile_cell_is_graphical(*cell))
            .and_then(|cell| {
                decode_profile_instruction(cell, before.registers.code_pointer)
            });
        let decoded_instruction = decoded.map(profile_instruction);
        let result = execution.result;
        let memory_delta = execution.memory_delta;
        let memory_reads = execution.memory_reads;
        let after = self.observation();
        let input = if result == Ok(StepOutcome::Continued)
            && decoded_instruction == Some(ProfileInstruction::Input)
        {
            if after.input_consumed > before.input_consumed {
                self.input
                    .get(before.input_consumed)
                    .copied()
                    .map(TraceInput::Byte)
            } else {
                Some(TraceInput::EndOfInput)
            }
        } else {
            None
        };
        let output = if after.output_len > before.output_len {
            self.output.get(before.output_len).copied()
        } else {
            None
        };
        observer(&ProfileStepTrace {
            after,
            before,
            decoded,
            fetched_cell,
            input,
            memory_delta,
            memory_reads,
            output,
            profile: self.profile,
            result,
        });
        result
    }

    /// Returns the current stable termination reason, if any.
    #[must_use]
    pub const fn termination(&self) -> Option<Termination> {
        self.termination
    }

    fn validate_encryption(
        &self,
        plan: &ProfileTransitionPlan,
        memory_reads: &mut ProfileMemoryReads,
    ) -> Result<u32, ProfileMachineError> {
        let pointer = plan.registers.code_pointer;
        let target = if let Some((write_pointer, value)) = plan.memory_write
            && write_pointer == pointer
        {
            value
        } else {
            let value = self.read(pointer)?;
            memory_reads.encryption =
                Some(ProfileMemoryRead { address: pointer, value });
            value
        };
        if !profile_cell_is_graphical(target) {
            return Err(ProfileMachineError::InvalidEncryptionTarget {
                pointer,
                value: target,
            });
        }
        profile_encrypt(target)
            .ok_or(ProfileMachineError::TranslationTableInvariant)
    }

    fn write(
        &mut self,
        address: u32,
        value: u32,
    ) -> Result<(), ProfileMachineError> {
        if value >= self.profile.word_modulus() {
            return Err(ProfileMachineError::MemoryInvariant);
        }
        let index = usize::try_from(address)
            .ok()
            .ok_or(ProfileMachineError::MemoryInvariant)?;
        let cell = self
            .memory
            .get_mut(index)
            .ok_or(ProfileMachineError::MemoryInvariant)?;
        *cell = value;
        Ok(())
    }
}

const fn validate_input_cursor(
    input_len: usize,
    observed: usize,
) -> Result<(), ProfileMachineError> {
    if observed > input_len {
        return Err(ProfileMachineError::InputCursorOutOfRange {
            input_len,
            observed,
        });
    }
    Ok(())
}

fn validate_state_memory(
    profile: &ProfileDescriptor,
    memory: &[u32],
) -> Result<(), ProfileMachineError> {
    let expected = profile.memory_words();
    let expected_len = usize::try_from(expected)
        .ok()
        .ok_or(ProfileMachineError::MemoryInvariant)?;
    if memory.len() != expected_len {
        return Err(ProfileMachineError::MemoryImageLength {
            expected,
            observed: memory.len(),
        });
    }
    for (index, value) in memory.iter().copied().enumerate() {
        if value >= profile.word_modulus() {
            let address = u32::try_from(index)
                .ok()
                .ok_or(ProfileMachineError::MemoryInvariant)?;
            return Err(ProfileMachineError::MemoryWordOutOfRange {
                address,
                value,
            });
        }
    }
    Ok(())
}

const fn validate_state_register(
    profile: &ProfileDescriptor,
    register: ProfileRegisterName,
    value: u32,
) -> Result<(), ProfileMachineError> {
    if value >= profile.word_modulus() {
        return Err(ProfileMachineError::RegisterOutOfRange {
            register,
            value,
        });
    }
    Ok(())
}

fn validate_state_registers(
    profile: &ProfileDescriptor,
    registers: ProfileRegisters,
) -> Result<(), ProfileMachineError> {
    validate_state_register(
        profile,
        ProfileRegisterName::Accumulator,
        registers.accumulator,
    )?;
    validate_state_register(
        profile,
        ProfileRegisterName::CodePointer,
        registers.code_pointer,
    )?;
    validate_state_register(
        profile,
        ProfileRegisterName::DataPointer,
        registers.data_pointer,
    )
}

/// Reports whether one profile-width cell is graphical ASCII for decode.
#[must_use]
pub const fn profile_cell_is_graphical(value: u32) -> bool {
    value >= GRAPHICAL_MIN && value <= GRAPHICAL_MAX
}

fn load_profile(
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<Vec<u32>, ProfileLoadError> {
    let memory_words = usize::try_from(profile.memory_words())
        .ok()
        .ok_or(ProfileLoadError::MemoryAllocation)?;
    let mut words = Vec::new();
    for (offset, byte) in source.iter().copied().enumerate() {
        if byte.is_ascii_whitespace() {
            continue;
        }
        if !(33..=126).contains(&byte) {
            return Err(ProfileLoadError::InvalidSourceByte { offset, byte });
        }
        if words.len() >= memory_words {
            return Err(ProfileLoadError::SourceTooLong);
        }
        let position = u32::try_from(words.len())
            .ok()
            .ok_or(ProfileLoadError::MemoryAllocation)?;
        let cell = u32::from(byte);
        let decoded = decode_profile_instruction(cell, position)
            .ok_or(ProfileLoadError::InvalidInstruction { position, byte })?;
        if !matches!(
            decoded,
            b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o'
        ) {
            return Err(ProfileLoadError::InvalidInstruction {
                position,
                byte,
            });
        }
        words.push(cell);
    }
    if words.len() < 2 {
        return Err(ProfileLoadError::InsufficientRecurrenceBase);
    }
    let additional = memory_words.saturating_sub(words.len());
    words
        .try_reserve_exact(additional)
        .map_err(|_error| ProfileLoadError::MemoryAllocation)?;
    while words.len() < memory_words {
        let previous = words
            .last()
            .copied()
            .ok_or(ProfileLoadError::InsufficientRecurrenceBase)?;
        let older_index = words.len().saturating_sub(2);
        let older = words
            .get(older_index)
            .copied()
            .ok_or(ProfileLoadError::InsufficientRecurrenceBase)?;
        words.push(profile_crazy(older, previous, profile.word_trits()));
    }
    Ok(words)
}

fn low_byte(value: u32) -> u8 {
    let reduced = value.rem_euclid(OUTPUT_MODULUS);
    u8::try_from(reduced).ok().unwrap_or(0)
}

fn profile_crazy(mut data: u32, mut accumulator: u32, trits: u8) -> u32 {
    let mut place = 1u32;
    let mut remaining_trits = trits;
    let mut result = 0u32;
    while remaining_trits > 0 {
        let chunk_trits = remaining_trits.min(CRAZY_CHUNK_TRITS);
        let chunk_modulus = ternary_modulus(chunk_trits);
        let data_chunk = u16::try_from(data.rem_euclid(chunk_modulus))
            .ok()
            .unwrap_or(0);
        let accumulator_chunk =
            u16::try_from(accumulator.rem_euclid(chunk_modulus))
                .ok()
                .unwrap_or(0);
        let chunk =
            u32::from(crazy_chunk_lookup(data_chunk, accumulator_chunk))
                .rem_euclid(chunk_modulus);
        result = result.saturating_add(chunk.saturating_mul(place));
        data = data.div_euclid(chunk_modulus);
        accumulator = accumulator.div_euclid(chunk_modulus);
        place = place.saturating_mul(chunk_modulus);
        remaining_trits = remaining_trits.saturating_sub(chunk_trits);
    }
    result
}

/// Decodes one profile-width instruction cell at its exact code position.
///
/// Returns `None` when `cell` is outside graphical ASCII. Graphical cells use
/// the same normative position-dependent translation table as the classic VM;
/// wider profile code pointers are reduced by the 94-position decode phase.
#[must_use]
pub fn decode_profile_instruction(cell: u32, code_pointer: u32) -> Option<u8> {
    if !profile_cell_is_graphical(cell) {
        return None;
    }
    let cell_offset =
        usize::try_from(cell.saturating_sub(GRAPHICAL_MIN)).ok()?;
    let phase = usize::try_from(
        code_pointer.rem_euclid(u32::try_from(DECODE_TABLE_LEN).ok()?),
    )
    .ok()?;
    let index = cell_offset
        .saturating_mul(DECODE_TABLE_LEN)
        .saturating_add(phase);
    DECODE_TABLE.get(index).copied()
}

fn profile_encrypt(cell: u32) -> Option<u32> {
    if !profile_cell_is_graphical(cell) {
        return None;
    }
    let index = usize::try_from(cell.saturating_sub(GRAPHICAL_MIN)).ok()?;
    XLAT2.get(index).copied().map(u32::from)
}

const fn profile_instruction(decoded: u8) -> ProfileInstruction {
    match decoded {
        b'*' => ProfileInstruction::Rotate,
        b'/' => ProfileInstruction::Output,
        b'<' => ProfileInstruction::Input,
        b'i' => ProfileInstruction::JumpCode,
        b'j' => ProfileInstruction::JumpData,
        b'p' => ProfileInstruction::Crazy,
        b'v' => ProfileInstruction::Halt,
        _ => ProfileInstruction::NoOperation,
    }
}

const fn profile_rotate(value: u32, modulus: u32) -> u32 {
    let quotient = value.div_euclid(TERNARY_RADIX);
    let low_trit = value.rem_euclid(TERNARY_RADIX);
    let high_weight = modulus.div_euclid(TERNARY_RADIX);
    quotient.saturating_add(low_trit.saturating_mul(high_weight))
}

const fn successor(value: u32, modulus: u32) -> u32 {
    if value == modulus.saturating_sub(1) {
        0
    } else {
        value.saturating_add(1)
    }
}

const fn ternary_modulus(trits: u8) -> u32 {
    let mut value = 1u32;
    let mut index = 0u8;
    while index < trits {
        value = value.saturating_mul(TERNARY_RADIX);
        index = index.saturating_add(1);
    }
    value
}
