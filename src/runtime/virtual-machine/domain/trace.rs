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
//   - Deterministic observation records for classic VM step execution.
// - Must-Not:
//   - Perform logging, file I/O, scheduling, or change guest-visible semantics.
// - Allows:
//   - Inputs: public machine state, decoded instruction bytes, and effects.
//   - Outputs: immutable trace records suitable for verification and debugging.
//   - Side effects: none.
// - Split-When:
//   - Split when persistent trace serialization gains an independent contract.
// - Merge-When:
//   - Merge when trace evidence no longer has an independent public surface.
// - Summary:
//   - Stable in-memory evidence for every requested semantic VM step.
// - Description:
//   - Records before/after observations and committed I/O or memory effects.
// - Usage:
//   - Consumed by conformance tests, verifiers, and future debugging layers.
// - Defaults:
//   - Observation is optional and never changes the transition being observed.
//

//! Deterministic in-memory trace records for classic VM execution.

use crate::machine::{MachineError, Registers, StepOutcome, Termination};
use crate::mode::ExecutionMode;
use crate::word::Word;

/// Compact observable machine state at one trace boundary.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct MachineObservation {
    /// Number of input bytes consumed by committed transitions.
    pub input_consumed: usize,
    /// Number of output bytes emitted by committed transitions.
    pub output_len: usize,
    /// Classic register values at this observation boundary.
    pub registers: Registers,
    /// Stable termination reason, when execution has terminated.
    pub termination: Option<Termination>,
}

/// Actual changed memory cells committed by one classic step.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct MemoryDelta {
    /// Instruction-specific data-cell change when distinct from encryption.
    pub data: Option<MemoryWrite>,
    /// Final self-encryption cell change.
    pub encryption: Option<MemoryWrite>,
}

impl MemoryDelta {
    /// Returns the number of distinct memory cells changed by this step.
    #[must_use]
    pub const fn changed_cells(self) -> usize {
        let data = match self.data {
            Some(_write) => 1usize,
            None => 0usize,
        };
        let encryption = match self.encryption {
            Some(_write) => 1usize,
            None => 0usize,
        };
        data.saturating_add(encryption)
    }
}

/// One actual classic memory-cell change committed by a step.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct MemoryWrite {
    /// Classic memory address whose final value changed.
    pub address: Word,
    /// Final committed word after the step.
    pub after: Word,
    /// Word observed before the step committed.
    pub before: Word,
}

/// Input observation attached to one successfully planned input instruction.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TraceInput {
    /// One concrete byte was consumed from the deterministic input stream.
    Byte(u8),
    /// The input stream was exhausted and the selected machine EOF word was
    /// used.
    EndOfInput,
}

/// Deterministic evidence emitted for one requested machine step.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct StepTrace {
    /// Observable machine state after the requested step returns.
    pub after: MachineObservation,
    /// Observable machine state before the requested step begins.
    pub before: MachineObservation,
    /// Decoded classic instruction byte, when decode was reached.
    pub decoded: Option<u8>,
    /// Current code cell fetched for this request, when fetch succeeded.
    pub fetched_cell: Option<Word>,
    /// Input effect selected by a successfully planned input instruction.
    pub input: Option<TraceInput>,
    /// Actual committed memory changes for this requested step.
    pub memory_delta: MemoryDelta,
    /// Explicit execution-mode identity for this requested step.
    pub mode: ExecutionMode,
    /// Output byte emitted by a successfully committed output instruction.
    pub output: Option<u8>,
    /// Exact public result returned by the requested step.
    pub result: Result<StepOutcome, MachineError>,
}
