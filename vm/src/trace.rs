// File:
//   - trace.rs
// Path:
//   - vm/src/trace.rs
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
// Related documents:
// - docs/technical/runtime/vm/safe-rust-malbolge-vm.md
// - docs/technical/specification/malbolge-1998.md
//
// Large file:
//   - false
//

//! Deterministic in-memory trace records for classic VM execution.

use crate::machine::{MachineError, Registers, StepOutcome, Termination};
use crate::{ExecutionMode, Word};

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

/// Input observation attached to one successfully planned input instruction.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TraceInput {
    /// One concrete byte was consumed from the deterministic input stream.
    Byte(u8),
    /// The input stream was exhausted and classic EOF value 59048 was used.
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
    /// Explicit execution-mode identity for this requested step.
    pub mode: ExecutionMode,
    /// Output byte emitted by a successfully committed output instruction.
    pub output: Option<u8>,
    /// Exact public result returned by the requested step.
    pub result: Result<StepOutcome, MachineError>,
}
