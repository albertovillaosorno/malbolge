// File:
//   - machine.rs
// Path:
//   - vm/src/machine.rs
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
//   - Atomic single-step transitions for the normative classic Malbolge
//     machine.
// - Must-Not:
//   - Reproduce historical C undefined behavior or hide host execution helpers.
// - Allows:
//   - Inputs: classic memory, registers, and deterministic byte input.
//   - Outputs: state transitions, termination, byte output, and typed errors.
//   - Side effects: mutation only of the owned VM state and output buffer.
// - Split-When:
//   - Split when tracing or execution scheduling gains an independent
//     lifecycle.
// - Merge-When:
//   - Merge when another module owns the same normative transition function.
// - Summary:
//   - Executes one exact classic instruction transition at a time.
// - Description:
//   - Plans and validates transitions before committing guest-visible mutation.
// - Usage:
//   - Used by interpreters, conformance tests, and future execution engines.
// - Defaults:
//   - Invalid self-encryption targets fail before any transition is committed.
//
// Related documents:
// - docs/technical/specification/malbolge-1998.md
// - docs/technical/runtime/vm/safe-rust-malbolge-vm.md
//
// Large file:
//   - false
//

//! Atomic single-step execution for the normative classic machine.

use std::fmt::{Display, Formatter, Result as FormatResult};

use crate::loader::{LoadError, load};
use crate::trace::{MachineObservation, StepTrace, TraceInput};
use crate::{
    ExecutionMode, Memory, MemoryError, Word, decode_instruction, encrypt,
};

/// Classic machine registers.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct Registers {
    /// Accumulator register `A`.
    pub accumulator: Word,
    /// Code pointer register `C`.
    pub code_pointer: Word,
    /// Data pointer register `D`.
    pub data_pointer: Word,
}

/// Stable termination reason for the normative classic machine.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Termination {
    /// A decoded `v` instruction terminated execution immediately.
    HaltInstruction,
    /// The current cell was outside graphical ASCII before decode.
    NonGraphicalCell,
}

/// Result of bounded machine execution.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RunOutcome {
    /// The requested number of steps completed without termination.
    BudgetExhausted {
        /// Number of semantic steps executed in this run request.
        steps: usize,
    },
    /// Execution reached a stable termination condition.
    Terminated {
        /// Stable semantic reason execution stopped.
        reason: Termination,
        /// Number of semantic steps executed in this run request.
        steps: usize,
    },
}
/// Result of one requested machine step.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum StepOutcome {
    /// One instruction committed and execution may continue.
    Continued,
    /// Execution is terminated with the recorded reason.
    Terminated(Termination),
}

/// Reproducible historical behavior that cannot be emulated safely.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LegacyBehavior {
    /// Historical code would index the encryption table outside its domain.
    InvalidSelfEncryptionTarget {
        /// Resulting code pointer selected by the legacy transition.
        pointer: Word,
        /// Non-graphical value that would become the table index source.
        value: Word,
    },
}

/// Typed failure of a classic machine transition.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum MachineError {
    /// Self-encryption would access a non-graphical target cell.
    InvalidEncryptionTarget {
        /// Resulting code pointer selected for encryption.
        pointer: Word,
        /// Cell value observed after instruction-specific effects.
        value: Word,
    },
    /// A fixed-memory invariant unexpectedly failed.
    Memory(MemoryError),
    /// A translation-table lookup failed inside its admitted domain.
    TranslationTableInvariant,
    /// Explicit legacy behavior cannot be reproduced without historical UB.
    UnsupportedLegacyBehavior(LegacyBehavior),
}

impl Display for MachineError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::InvalidEncryptionTarget { pointer, value } => write!(
                f,
                "self-encryption target {} contains non-graphical value {}",
                pointer.value(),
                value.value()
            ),
            Self::Memory(error) => Display::fmt(error, f),
            Self::UnsupportedLegacyBehavior(
                LegacyBehavior::InvalidSelfEncryptionTarget { pointer, value },
            ) => write!(
                f,
                concat!(
                    "legacy-ben cannot safely emulate self-encryption at {}",
                    " with value {}",
                ),
                pointer.value(),
                value.value()
            ),
            Self::TranslationTableInvariant => {
                f.write_str("classic translation-table invariant failed")
            },
        }
    }
}

impl From<MemoryError> for MachineError {
    fn from(error: MemoryError) -> Self {
        Self::Memory(error)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Instruction {
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
struct TransitionPlan {
    input_advance: bool,
    memory_write: Option<(Word, Word)>,
    output: Option<u8>,
    registers: Registers,
}

/// Owned classic Malbolge machine state and deterministic byte streams.
#[derive(Clone, Debug)]
pub struct Machine {
    input: Vec<u8>,
    input_cursor: usize,
    memory: Memory,
    output: Vec<u8>,
    registers: Registers,
    termination: Option<Termination>,
}

impl Machine {
    fn commit(
        &mut self,
        plan: TransitionPlan,
        encrypted: Word,
    ) -> Result<(), MachineError> {
        let encryption_pointer = plan.registers.code_pointer;
        if let Some((write_pointer, value)) = plan.memory_write
            && write_pointer != encryption_pointer
        {
            self.memory.replace(write_pointer, value)?;
        }
        self.memory.replace(encryption_pointer, encrypted)?;
        self.registers = Registers {
            accumulator: plan.registers.accumulator,
            code_pointer: plan.registers.code_pointer.successor(),
            data_pointer: plan.registers.data_pointer.successor(),
        };
        if plan.input_advance {
            self.input_cursor = self.input_cursor.saturating_add(1);
        }
        if let Some(byte) = plan.output {
            self.output.push(byte);
        }
        Ok(())
    }

    /// Loads source and constructs the default machine state.
    ///
    /// # Errors
    ///
    /// Returns [`LoadError`] when the source cannot initialize classic memory.
    pub fn from_source(
        source: &[u8],
        input: Vec<u8>,
    ) -> Result<Self, LoadError> {
        load(source).map(|memory| Self::new(memory, input))
    }

    /// Returns the number of input bytes consumed by committed transitions.
    #[must_use]
    pub const fn input_consumed(&self) -> usize {
        self.input_cursor
    }

    /// Reads one current guest memory word.
    ///
    /// # Errors
    ///
    /// Returns [`MemoryError`] if the fixed memory invariant is broken.
    pub fn memory_word(&self, address: Word) -> Result<Word, MemoryError> {
        self.memory.read(address)
    }

    /// Constructs the default zero-register machine over validated memory.
    #[must_use]
    pub fn new(memory: Memory, input: Vec<u8>) -> Self {
        Self::with_registers(memory, input, Registers::default())
    }

    const fn observation(&self) -> MachineObservation {
        MachineObservation {
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
        decoded: Instruction,
    ) -> Result<TransitionPlan, MachineError> {
        let mut plan = TransitionPlan {
            input_advance: false,
            memory_write: None,
            output: None,
            registers: self.registers,
        };
        match decoded {
            Instruction::Crazy => self.plan_crazy(&mut plan)?,
            Instruction::Halt | Instruction::NoOperation => {},
            Instruction::Input => self.plan_input(&mut plan),
            Instruction::JumpCode => {
                plan.registers.code_pointer =
                    self.memory.read(self.registers.data_pointer)?;
            },
            Instruction::JumpData => {
                plan.registers.data_pointer =
                    self.memory.read(self.registers.data_pointer)?;
            },
            Instruction::Output => {
                plan.output = Some(self.registers.accumulator.low_byte());
            },
            Instruction::Rotate => self.plan_rotate(&mut plan)?,
        }
        Ok(plan)
    }

    fn plan_crazy(
        &self,
        plan: &mut TransitionPlan,
    ) -> Result<(), MachineError> {
        let value = self
            .memory
            .read(self.registers.data_pointer)?
            .crazy(self.registers.accumulator);
        plan.registers.accumulator = value;
        plan.memory_write = Some((self.registers.data_pointer, value));
        Ok(())
    }

    fn plan_input(&self, plan: &mut TransitionPlan) {
        if let Some(byte) = self.input.get(self.input_cursor).copied() {
            plan.registers.accumulator = Word::from_byte(byte);
            plan.input_advance = true;
        } else {
            plan.registers.accumulator = Word::MAX;
        }
    }

    fn plan_rotate(
        &self,
        plan: &mut TransitionPlan,
    ) -> Result<(), MachineError> {
        let value = self.memory.read(self.registers.data_pointer)?.rotate();
        plan.registers.accumulator = value;
        plan.memory_write = Some((self.registers.data_pointer, value));
        Ok(())
    }

    /// Returns the current register values.
    #[must_use]
    pub const fn registers(&self) -> Registers {
        self.registers
    }

    /// Executes at most `step_budget` semantic steps.
    ///
    /// # Errors
    ///
    /// Returns [`MachineError`] when any requested transition cannot commit.
    pub fn run(
        &mut self,
        step_budget: usize,
    ) -> Result<RunOutcome, MachineError> {
        self.run_in_mode(step_budget, ExecutionMode::Specification)
    }

    pub(crate) fn run_in_mode(
        &mut self,
        step_budget: usize,
        mode: ExecutionMode,
    ) -> Result<RunOutcome, MachineError> {
        if let Some(reason) = self.termination {
            return Ok(RunOutcome::Terminated { reason, steps: 0 });
        }
        let mut steps = 0usize;
        while steps < step_budget {
            let outcome = self.step_in_mode(mode)?;
            steps = steps.saturating_add(1);
            if let StepOutcome::Terminated(reason) = outcome {
                return Ok(RunOutcome::Terminated { reason, steps });
            }
        }
        Ok(RunOutcome::BudgetExhausted { steps })
    }

    /// Executes at most `step_budget` steps and observes every requested step.
    ///
    /// The observer receives exactly one immutable [`StepTrace`] for each step
    /// request performed by this call. Observation cannot mutate machine state.
    ///
    /// # Errors
    ///
    /// Returns [`MachineError`] when any requested transition cannot commit.
    /// The failing step is still delivered to `observer` before the error
    /// returns.
    pub fn run_traced<Observer>(
        &mut self,
        step_budget: usize,
        observer: &mut Observer,
    ) -> Result<RunOutcome, MachineError>
    where
        Observer: FnMut(&StepTrace),
    {
        self.run_traced_in_mode(
            step_budget,
            ExecutionMode::Specification,
            observer,
        )
    }

    pub(crate) fn run_traced_in_mode<Observer>(
        &mut self,
        step_budget: usize,
        mode: ExecutionMode,
        observer: &mut Observer,
    ) -> Result<RunOutcome, MachineError>
    where
        Observer: FnMut(&StepTrace),
    {
        if let Some(reason) = self.termination {
            return Ok(RunOutcome::Terminated { reason, steps: 0 });
        }
        let mut steps = 0usize;
        while steps < step_budget {
            let outcome = self.step_traced_in_mode(mode, observer)?;
            steps = steps.saturating_add(1);
            if let StepOutcome::Terminated(reason) = outcome {
                return Ok(RunOutcome::Terminated { reason, steps });
            }
        }
        Ok(RunOutcome::BudgetExhausted { steps })
    }

    /// Executes one atomic normative transition.
    ///
    /// # Errors
    ///
    /// Returns [`MachineError`] when a transition cannot commit atomically.
    pub fn step(&mut self) -> Result<StepOutcome, MachineError> {
        self.step_in_mode(ExecutionMode::Specification)
    }

    pub(crate) fn step_in_mode(
        &mut self,
        mode: ExecutionMode,
    ) -> Result<StepOutcome, MachineError> {
        if let Some(reason) = self.termination {
            return Ok(StepOutcome::Terminated(reason));
        }
        let cell = self.memory.read(self.registers.code_pointer)?;
        if !cell.is_graphical() {
            if mode == ExecutionMode::LegacyBen {
                return Ok(StepOutcome::Continued);
            }
            self.termination = Some(Termination::NonGraphicalCell);
            return Ok(StepOutcome::Terminated(Termination::NonGraphicalCell));
        }
        let decoded = decode_instruction(cell, self.registers.code_pointer)
            .ok_or(MachineError::TranslationTableInvariant)?;
        let decoded_instruction = instruction(decoded, mode);
        if decoded_instruction == Instruction::Halt {
            self.termination = Some(Termination::HaltInstruction);
            return Ok(StepOutcome::Terminated(Termination::HaltInstruction));
        }
        let plan = self.plan(decoded_instruction)?;
        let encrypted = self.validate_encryption(&plan, mode)?;
        self.commit(plan, encrypted)?;
        Ok(StepOutcome::Continued)
    }

    /// Executes one atomic transition and emits deterministic trace evidence.
    ///
    /// The observer is called exactly once for the requested step, including
    /// stable termination and rejected transitions.
    ///
    /// # Errors
    ///
    /// Returns [`MachineError`] when the transition cannot commit atomically.
    /// The rejection is included in the emitted [`StepTrace`].
    pub fn step_traced<Observer>(
        &mut self,
        observer: &mut Observer,
    ) -> Result<StepOutcome, MachineError>
    where
        Observer: FnMut(&StepTrace),
    {
        self.step_traced_in_mode(ExecutionMode::Specification, observer)
    }

    pub(crate) fn step_traced_in_mode<Observer>(
        &mut self,
        mode: ExecutionMode,
        observer: &mut Observer,
    ) -> Result<StepOutcome, MachineError>
    where
        Observer: FnMut(&StepTrace),
    {
        let before = self.observation();
        let fetched_cell = if before.termination.is_none() {
            self.memory.read(before.registers.code_pointer).ok()
        } else {
            None
        };
        let decoded =
            fetched_cell
                .filter(|cell| cell.is_graphical())
                .and_then(|cell| {
                    decode_instruction(cell, before.registers.code_pointer)
                });
        let decoded_instruction = decoded.map(|byte| instruction(byte, mode));
        let result = self.step_in_mode(mode);
        let after = self.observation();
        let input = if result == Ok(StepOutcome::Continued)
            && decoded_instruction == Some(Instruction::Input)
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
        observer(&StepTrace {
            after,
            before,
            decoded,
            fetched_cell,
            input,
            mode,
            output,
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
        plan: &TransitionPlan,
        mode: ExecutionMode,
    ) -> Result<Word, MachineError> {
        let pointer = plan.registers.code_pointer;
        let target = if let Some((write_pointer, value)) = plan.memory_write
            && write_pointer == pointer
        {
            value
        } else {
            self.memory.read(pointer)?
        };
        if !target.is_graphical() {
            return match mode {
                ExecutionMode::LegacyBen => {
                    Err(MachineError::UnsupportedLegacyBehavior(
                        LegacyBehavior::InvalidSelfEncryptionTarget {
                            pointer,
                            value: target,
                        },
                    ))
                },
                ExecutionMode::Specification => {
                    Err(MachineError::InvalidEncryptionTarget {
                        pointer,
                        value: target,
                    })
                },
            };
        }
        encrypt(target).ok_or(MachineError::TranslationTableInvariant)
    }

    /// Constructs a machine with explicit registers for verification fixtures.
    #[must_use]
    pub const fn with_registers(
        memory: Memory,
        input: Vec<u8>,
        registers: Registers,
    ) -> Self {
        Self {
            input,
            input_cursor: 0,
            memory,
            output: Vec::new(),
            registers,
            termination: None,
        }
    }
}

const fn instruction(decoded: u8, mode: ExecutionMode) -> Instruction {
    match mode {
        ExecutionMode::LegacyBen => legacy_instruction(decoded),
        ExecutionMode::Specification => specification_instruction(decoded),
    }
}

const fn legacy_instruction(decoded: u8) -> Instruction {
    match decoded {
        b'*' => Instruction::Rotate,
        b'/' => Instruction::Input,
        b'<' => Instruction::Output,
        b'i' => Instruction::JumpCode,
        b'j' => Instruction::JumpData,
        b'p' => Instruction::Crazy,
        b'v' => Instruction::Halt,
        _ => Instruction::NoOperation,
    }
}

const fn specification_instruction(decoded: u8) -> Instruction {
    match decoded {
        b'*' => Instruction::Rotate,
        b'/' => Instruction::Output,
        b'<' => Instruction::Input,
        b'i' => Instruction::JumpCode,
        b'j' => Instruction::JumpData,
        b'p' => Instruction::Crazy,
        b'v' => Instruction::Halt,
        _ => Instruction::NoOperation,
    }
}
