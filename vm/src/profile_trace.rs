// File:
//   - profile_trace.rs
// Path:
//   - vm/src/profile_trace.rs
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
//   - Immutable observation records for profile-driven VM transitions.
// - Must-Not:
//   - Perform logging, scheduling, serialization, or mutate guest execution.
// - Allows:
//   - Inputs: profile identity, profile-width state, decoded bytes, and
//     effects.
//   - Outputs: deterministic trace records for verification and future tiers.
//   - Side effects: none.
// - Split-When:
//   - Split when persistent profile-trace serialization gains its own contract.
// - Merge-When:
//   - Merge when classic and profiled trace state share one width-safe type.
// - Summary:
//   - Observes every requested profile-driven step without changing semantics.
// - Description:
//   - Carries exact canonical profile identity and u32 profile-width state.
// - Usage:
//   - Emitted by `ProfileMachine::step_traced` and `run_traced` observers.
// - Defaults:
//   - Profile tracing is specification-only; legacy behavior stays
//     classic-only.
//
// Related documents:
// - docs/technical/runtime/vm/safe-rust-malbolge-vm.md
// - docs/technical/compatibility/scalable-malbolge-memory-model.md
//
// Large file:
//   - false

//! Immutable trace evidence for profile-driven safe Rust execution.

use crate::{
    ProfileDescriptor, ProfileMachineError, ProfileRegisters, StepOutcome,
    Termination, TraceInput,
};

/// Observable profile-driven machine state at one trace boundary.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ProfileMachineObservation {
    /// Number of input bytes consumed by committed transitions.
    pub input_consumed: usize,
    /// Number of output bytes emitted by committed transitions.
    pub output_len: usize,
    /// Profile-width register values at this boundary.
    pub registers: ProfileRegisters,
    /// Stable termination reason, when execution has terminated.
    pub termination: Option<Termination>,
}

/// Deterministic evidence emitted for one requested profile-driven step.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ProfileStepTrace {
    /// Observable machine state after the requested step returns.
    pub after: ProfileMachineObservation,
    /// Observable machine state before the requested step begins.
    pub before: ProfileMachineObservation,
    /// Decoded normative instruction byte, when decode was reached.
    pub decoded: Option<u8>,
    /// Current profile-width code cell fetched for this request.
    pub fetched_cell: Option<u32>,
    /// Input effect selected by a successfully planned input instruction.
    pub input: Option<TraceInput>,
    /// Output byte emitted by a successfully committed output instruction.
    pub output: Option<u8>,
    /// Exact canonical profile identity for the observed machine.
    pub profile: &'static ProfileDescriptor,
    /// Exact public result returned by the requested step.
    pub result: Result<StepOutcome, ProfileMachineError>,
}
